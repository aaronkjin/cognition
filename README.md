# Cognition

Security Remediation Orchestrator for Coupang.

Orchestrates parallel [Devin](https://devin.ai) sessions to remediate security findings at scale. Ingests findings from CSV, dispatches wave-based Devin sessions with category-specific playbooks, monitors progress via structured output, and surfaces everything through a real-time dashboard.

## Links

Presentation: https://docs.google.com/presentation/d/1KJ04dFyg6Eh7YJcpWy26zXFAUHs8E9lCHezieyXHgvI/edit?usp=sharing

System design: https://excalidraw.com/#json=kd5N1txWhsNigS0IWoeoo,Umh7ikVqk5SWZ8HPH7bgqw

Video demo: https://www.loom.com/share/9f4b0a6445cf464f8754b709cbc90a87

## Prerequisites

- Python 3.11+
- Node.js 18+

## Setup

```bash
cp .env.example .env
# Edit .env with your DEVIN_API_KEY (or leave MOCK_MODE=true)

pip install -e ".[dev]"
cd dashboard && npm install && cd ..
```

## Run

```bash
# Orchestrator (mock mode by default)
python -m orchestrator.main run sample_data/findings.csv --wave-size 5

# Dashboard (separate terminal)
cd dashboard && npm run dev
# → http://localhost:3000
```

## CLI Commands

```bash
python -m orchestrator.main ingest sample_data/findings.csv   # Parse + prioritize
python -m orchestrator.main plan sample_data/findings.csv      # Preview wave plan
python -m orchestrator.main run sample_data/findings.csv       # Full pipeline
python -m orchestrator.main run ... --dry-run                  # Show without executing
python -m orchestrator.main run ... --live                     # Real Devin API
python -m orchestrator.main run ... --hybrid                   # Live for connected repos, mock for rest
python -m orchestrator.main status                             # Current run progress
```

## Tests

```bash
pytest
```

## Project Structure

```
orchestrator/     Python orchestrator (ingest, plan, dispatch, monitor)
dashboard/        Next.js dashboard (reads state.json, auto-refreshes)
playbooks/        .devin.md remediation playbooks per finding category
mock/             Mock Devin client for local development
sample_data/      Demo CSV with ~20 findings
tests/            pytest suite
```
