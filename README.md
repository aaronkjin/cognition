# Cognition

Security Remediation Orchestrator for Coupang.

<img width="1604" height="1040" alt="Image" src="https://github.com/user-attachments/assets/b21ca47f-540a-4e8a-b7b2-e61adfbdd164" />

Orchestrates parallel [Devin](https://devin.ai) sessions to remediate security findings at scale. Ingests findings, dispatches wave-based Devin sessions with category-specific playbooks, monitors progress via structured output, and surfaces everything through a dashboard interface.

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
# edit .env with your DEVIN_API_KEY

pip install -e ".[dev]"
cd dashboard && npm install && cd ..
```

## Run

```bash
# orchestrator
python -m orchestrator.main run sample_data/findings_live.csv --wave-size 5

# dashboard (on separate terminal)
cd dashboard && npm run dev
# http://localhost:3000
```

## CLI Commands

```bash
python -m orchestrator.main ingest sample_data/findings_live.csv    # parse + prioritize
python -m orchestrator.main plan sample_data/findings_live.csv      # preview wave plan
python -m orchestrator.main run sample_data/findings_live.csv       # full pipeline
python -m orchestrator.main run ... --dry-run                       # show w/o executing
python -m orchestrator.main run ... --live                          # real Devin API
python -m orchestrator.main run ... --hybrid                        # live for connected repos, mock for rest
python -m orchestrator.main status                                  # current run progress
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
