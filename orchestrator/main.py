from __future__ import annotations

import asyncio
import json
import logging
import signal
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import click

from orchestrator.config import OrchestratorConfig

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging. INFO by default, DEBUG if verbose."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _get_client(config: OrchestratorConfig):
    """Return MockDevinClient if mock_mode, else DevinClient."""
    if config.mock_mode:
        from mock.mock_devin_client import MockDevinClient

        return MockDevinClient()
    else:
        from orchestrator.devin.client import DevinClient

        return DevinClient(
            api_key=config.devin_api_key,
            base_url=config.devin_api_base_url,
            max_retries=config.max_retries,
            retry_jitter_max=config.retry_jitter_max_seconds,
            circuit_breaker_threshold=config.circuit_breaker_threshold,
            circuit_breaker_cooldown=config.circuit_breaker_cooldown_seconds,
        )


def _ingest_findings(csv_path: str):
    """Run the full ingestion pipeline: parse → normalize → prioritize."""
    from orchestrator.ingest.normalizer import normalize_findings
    from orchestrator.ingest.parser import parse_findings_csv
    from orchestrator.ingest.prioritizer import prioritize_findings

    findings = parse_findings_csv(csv_path)
    findings = normalize_findings(findings)
    findings = prioritize_findings(findings)
    return findings


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """Coupang Security Remediation Orchestrator — powered by Devin."""
    _setup_logging(verbose)


@cli.command()
@click.argument("csv_path", type=click.Path(exists=True))
def ingest(csv_path: str) -> None:
    """Parse and prioritize findings from a CSV file."""
    findings = _ingest_findings(csv_path)

    # Summary
    click.echo(f"\n{'='*60}")
    click.echo(f"  Ingestion Summary")
    click.echo(f"{'='*60}")
    click.echo(f"  Total findings: {len(findings)}")

    # Per-severity counts
    severity_counts = Counter(f.severity.value for f in findings)
    click.echo(f"\n  By severity:")
    for sev in ["critical", "high", "medium", "low"]:
        count = severity_counts.get(sev, 0)
        click.echo(f"    {sev.upper():12s} {count}")

    # Per-category counts
    category_counts = Counter(f.category.value for f in findings)
    click.echo(f"\n  By category:")
    for cat, count in category_counts.most_common():
        click.echo(f"    {cat:30s} {count}")

    # Top 5 by priority
    click.echo(f"\n  Top 5 by priority:")
    for f in findings[:5]:
        click.echo(
            f"    [{f.priority_score:5.1f}] {f.finding_id} | {f.severity.value:8s} | "
            f"{f.category.value:30s} | {f.service_name}"
        )

    click.echo(f"{'='*60}\n")


@cli.command()
@click.argument("csv_path", type=click.Path(exists=True))
@click.option("--wave-size", default=None, type=int, help="Findings per wave (overrides config)")
def plan(csv_path: str, wave_size: int | None) -> None:
    """Generate wave-based remediation plan."""
    from orchestrator.planner.batch_planner import create_waves

    config = OrchestratorConfig()
    findings = _ingest_findings(csv_path)
    effective_wave_size = wave_size or config.wave_size
    waves = create_waves(findings, effective_wave_size)

    click.echo(f"\n{'='*60}")
    click.echo(f"  Remediation Plan")
    click.echo(f"{'='*60}")
    click.echo(f"  Total findings: {len(findings)}")
    click.echo(f"  Wave size: {effective_wave_size}")
    click.echo(f"  Number of waves: {len(waves)}")

    for wave in waves:
        click.echo(f"\n  Wave {wave.wave_number} ({len(wave.sessions)} findings):")
        for session in wave.sessions:
            f = session.finding
            click.echo(
                f"    {f.finding_id} | [{f.priority_score:5.1f}] {f.severity.value:8s} | "
                f"{f.category.value:30s} | {f.service_name}"
            )

    click.echo(f"\n{'='*60}\n")


async def _run_pipeline(
    client: object,
    waves: list,
    batch_run: object,
    tracker: object,
    config: OrchestratorConfig,
    findings: list | None = None,
    mock_client: object | None = None,
    ledger: object | None = None,
    run_id: str = "",
) -> object:
    """Run the full async pipeline in a single event loop."""
    from orchestrator.preflight import preflight_check
    from orchestrator.planner.playbook_selector import assign_playbooks, ensure_playbooks_uploaded
    from orchestrator.planner.wave_manager import WaveManager

    try:
        # Preflight checks (skip if no findings passed, e.g., for backward compat)
        if findings is not None:
            errors = await preflight_check(client, config, findings)
            if errors:
                for e in errors:
                    logger.error("Preflight: %s", e)
                raise RuntimeError("Preflight failed: " + "; ".join(errors))

        # Upload and assign playbooks
        playbook_ids = await ensure_playbooks_uploaded(client)
        waves = assign_playbooks(waves, playbook_ids)
        batch_run.waves = waves  # Update with assigned playbooks

        # Execute
        manager = WaveManager(
            client, config, tracker,
            data_source=batch_run.data_source,
            mock_client=mock_client,
            ledger=ledger,
            run_id=run_id,
        )
        return await manager.execute_run(batch_run)
    finally:
        await client.close()
        if mock_client is not None:
            await mock_client.close()


@cli.command()
@click.argument("csv_path", type=click.Path(exists=True))
@click.option("--wave-size", default=None, type=int, help="Findings per wave")
@click.option("--wave", "wave_num", type=int, default=None, help="Run only a specific wave number")
@click.option("--dry-run", is_flag=True, help="Show what would be dispatched without running")
@click.option("--live", is_flag=True, help="Use real Devin API (disable mock)")
@click.option("--hybrid", is_flag=True, help="Hybrid mode: real for connected repos, mock for others")
def run(csv_path: str, wave_size: int | None, wave_num: int | None, dry_run: bool, live: bool, hybrid: bool) -> None:
    """Full pipeline: ingest -> plan -> dispatch -> monitor."""
    from orchestrator.monitor.tracker import ProgressTracker
    from orchestrator.planner.batch_planner import create_waves

    config = OrchestratorConfig()

    # Override config based on CLI flags
    if live:
        config.mock_mode = False
    if hybrid:
        config.mock_mode = False
        config.hybrid_mode = True

    effective_wave_size = wave_size or config.wave_size

    findings = _ingest_findings(csv_path)

    waves = create_waves(findings, effective_wave_size)

    # Create client(s)
    mock_client = None
    if config.hybrid_mode:
        from mock.mock_devin_client import MockDevinClient
        from orchestrator.devin.client import DevinClient
        client = DevinClient(
            api_key=config.devin_api_key,
            base_url=config.devin_api_base_url,
            max_retries=config.max_retries,
            retry_jitter_max=config.retry_jitter_max_seconds,
            circuit_breaker_threshold=config.circuit_breaker_threshold,
            circuit_breaker_cooldown=config.circuit_breaker_cooldown_seconds,
        )
        mock_client = MockDevinClient()
    else:
        client = _get_client(config)

    # Filter to specific wave if requested
    if wave_num is not None:
        waves = [w for w in waves if w.wave_number == wave_num]
        if not waves:
            click.echo(f"Error: Wave {wave_num} not found.")
            return

    # Create BatchRun
    from orchestrator.models import BatchRun

    run_id = str(uuid.uuid4())[:8]
    total_findings = sum(len(w.sessions) for w in waves)

    batch_run = BatchRun(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        waves=waves,
        total_findings=total_findings,
    )

    if config.hybrid_mode:
        mode = "hybrid"
    elif config.mock_mode:
        mode = "mock"
    else:
        mode = "live"

    batch_run.data_source = mode

    click.echo(f"\n{'='*60}")
    click.echo(f"  Starting remediation run {run_id}")
    click.echo(f"  Mode: {mode}")
    click.echo(f"  Findings: {total_findings}, Waves: {len(waves)}, Wave size: {effective_wave_size}")
    click.echo(f"{'='*60}\n")

    # Dry run
    if dry_run:
        click.echo("  DRY RUN — showing what would be dispatched:\n")
        for wave in waves:
            click.echo(f"  Wave {wave.wave_number}:")
            for session in wave.sessions:
                f = session.finding
                click.echo(
                    f"    {f.finding_id} | {f.category.value:30s} | {f.severity.value:8s} | "
                    f"{f.service_name:20s} | playbook={session.playbook_id}"
                )
        click.echo(f"\n{'='*60}\n")
        asyncio.run(client.close())
        if mock_client is not None:
            asyncio.run(mock_client.close())
        return

    # Create tracker and save initial state
    tracker = ProgressTracker(batch_run, config.state_file_path, runs_dir="./runs")
    tracker.add_event("run_started", f"Remediation run {run_id} started")
    tracker.save_state()

    # Create idempotency ledger
    from orchestrator.devin.idempotency import IdempotencyLedger
    ledger_path = Path("./runs") / run_id / "idempotency.json"
    ledger = IdempotencyLedger(ledger_path)

    # Graceful shutdown handler
    interrupted = False

    def _handle_interrupt(signum: int, frame: object) -> None:
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            click.echo("\n  Interrupted — saving state and exiting gracefully...")
            batch_run.status = "interrupted"
            tracker.add_event("run_interrupted", "Run interrupted by user")
            tracker.save_state()

    original_handler = signal.signal(signal.SIGINT, _handle_interrupt)

    try:
        # Run the async pipeline
        batch_run = asyncio.run(
            _run_pipeline(
                client, waves, batch_run, tracker, config,
                findings, mock_client, ledger, run_id,
            )
        )
    except (KeyboardInterrupt, RuntimeError) as exc:
        if interrupted or "interrupted" in str(exc).lower():
            click.echo("  State saved. Run can be resumed.")
        else:
            raise
    finally:
        signal.signal(signal.SIGINT, original_handler)

    # Auto-extract memories
    try:
        count = tracker.extract_and_save_memories()
        if count > 0:
            click.echo(f"  Extracted {count} memory items.")
    except Exception as exc:
        logger.warning("Memory extraction failed: %s", exc)

    # Print final summary
    click.echo(f"\n{'='*60}")
    click.echo(f"  Run complete: {batch_run.successful}/{batch_run.total_findings} succeeded, "
               f"{batch_run.prs_created} PRs created")
    click.echo(f"  Failed: {batch_run.failed}, Status: {batch_run.status}")
    for wave in batch_run.waves:
        prs = sum(1 for s in wave.sessions if s.pr_url is not None)
        click.echo(
            f"    Wave {wave.wave_number}: {wave.success_count}/{wave.total_count} success, "
            f"{wave.failure_count} failed, {prs} PRs"
        )
    click.echo(f"{'='*60}\n")


@cli.command("extract-memory")
@click.option("--run-id", default=None, help="Run ID to extract from (default: latest)")
def extract_memory(run_id: str | None) -> None:
    """Extract memory items from a completed run."""
    from orchestrator.memory.extractor import extract_memories
    from orchestrator.memory.store import MemoryStore
    from orchestrator.models import BatchRun

    # Find the run
    if run_id:
        state_path = Path(f"./runs/{run_id}/state.json")
    else:
        # Find latest from index
        index_path = Path("./runs/index.json")
        if not index_path.exists():
            click.echo("No runs found.")
            return
        entries = json.loads(index_path.read_text(encoding="utf-8"))
        if not entries:
            click.echo("No runs found.")
            return
        run_id = entries[-1]["run_id"]
        state_path = Path(f"./runs/{run_id}/state.json")

    if not state_path.exists():
        click.echo(f"Run {run_id} state file not found.")
        return

    data = json.loads(state_path.read_text(encoding="utf-8"))
    batch_run = BatchRun.model_validate(data)

    items = extract_memories(batch_run)
    if not items:
        click.echo("No terminal sessions found — nothing to extract.")
        return

    store = MemoryStore()
    graph = store.load_graph()
    for item in items:
        graph = store.upsert(item, graph)
    store.save_graph(graph)

    click.echo(f"\n{'='*60}")
    click.echo(f"  Memory Extraction Complete")
    click.echo(f"{'='*60}")
    click.echo(f"  Run ID: {run_id}")
    click.echo(f"  Items extracted: {len(items)}")
    click.echo(f"  Graph entries: {len(graph.entries)}")
    click.echo(f"{'='*60}\n")


def _print_status(batch_run: object) -> None:
    """Print formatted status output for a BatchRun."""
    total = batch_run.total_findings
    completed = batch_run.completed
    pct = (completed / total * 100) if total > 0 else 0

    click.echo(f"\n{'='*60}")
    click.echo(f"  Run Status")
    click.echo(f"{'='*60}")
    click.echo(f"  Run ID:     {batch_run.run_id}")
    click.echo(f"  Status:     {batch_run.status}")
    click.echo(f"  Started:    {batch_run.started_at}")
    click.echo(f"\n  Completed:  {completed}/{total} ({pct:.0f}%)")
    click.echo(f"  Successful: {batch_run.successful}")
    click.echo(f"  Failed:     {batch_run.failed}")
    click.echo(f"  PRs:        {batch_run.prs_created}")

    click.echo(f"\n  Waves:")
    for wave in batch_run.waves:
        prs = sum(1 for s in wave.sessions if s.pr_url is not None)
        click.echo(
            f"    Wave {wave.wave_number} [{wave.status}]: "
            f"{wave.success_count}/{wave.total_count} success, "
            f"{wave.failure_count} failed, {prs} PRs"
        )

    click.echo(f"{'='*60}\n")


@cli.command()
def status() -> None:
    """Show current progress from state.json or latest run."""
    from orchestrator.models import BatchRun

    config = OrchestratorConfig()

    # Try runs/index.json first for latest run
    runs_index = Path("./runs/index.json")
    if runs_index.exists():
        try:
            entries = json.loads(runs_index.read_text(encoding="utf-8"))
            if entries:
                latest = entries[-1]
                run_state = Path(f"./runs/{latest['run_id']}/state.json")
                if run_state.exists():
                    data = json.loads(run_state.read_text(encoding="utf-8"))
                    batch_run = BatchRun.model_validate(data)
                    _print_status(batch_run)
                    return
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback to legacy state.json
    state_path = Path(config.state_file_path)
    if not state_path.exists():
        click.echo("No active run found.")
        return
    data = json.loads(state_path.read_text(encoding="utf-8"))
    batch_run = BatchRun.model_validate(data)
    _print_status(batch_run)


if __name__ == "__main__":
    cli()
