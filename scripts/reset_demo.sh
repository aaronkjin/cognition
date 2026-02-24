#!/usr/bin/env bash
# =============================================================================
# reset_demo.sh — Clean reset for the Coupang Security Remediation demo
#
# Cleans: local run state, memory store, GitHub PRs/branches, Devin sessions
# Safe to run multiple times. Prompts before destructive GitHub operations.
#
# Usage:
#   ./scripts/reset_demo.sh            # Full interactive reset
#   ./scripts/reset_demo.sh --yes      # Skip confirmation prompts
#   ./scripts/reset_demo.sh --local    # Local cleanup only (no GitHub/Devin)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Demo repos
REPOS=(
  "aaronkjin/coupang-payment-service"
  "aaronkjin/coupang-user-service"
  "aaronkjin/coupang-catalog-service"
)

# Parse flags
AUTO_YES=false
LOCAL_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --yes|-y) AUTO_YES=true ;;
    --local|-l) LOCAL_ONLY=true ;;
  esac
done

# Helpers
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; }

confirm() {
  if $AUTO_YES; then return 0; fi
  read -rp "$1 [y/N] " ans
  [[ "$ans" =~ ^[Yy] ]]
}

echo ""
echo "============================================================"
echo "  Demo Reset — Coupang Security Remediation Orchestrator"
echo "============================================================"
echo ""

# -------------------------------------------------------
# 1. Local cleanup
# -------------------------------------------------------
info "Step 1: Cleaning local state files..."

# runs/ directory
if [ -d "$PROJECT_ROOT/runs" ]; then
  rm -rf "$PROJECT_ROOT/runs"
  ok "Deleted runs/"
else
  ok "runs/ already clean"
fi

# Legacy state.json
if [ -f "$PROJECT_ROOT/state.json" ]; then
  rm -f "$PROJECT_ROOT/state.json"
  ok "Deleted state.json"
else
  ok "state.json already clean"
fi

# Memory store
if [ -f "$PROJECT_ROOT/orchestrator/memory/graph.json" ] || \
   [ -d "$PROJECT_ROOT/orchestrator/memory/items" ]; then
  rm -f "$PROJECT_ROOT/orchestrator/memory/graph.json"
  rm -rf "$PROJECT_ROOT/orchestrator/memory/items"
  ok "Deleted memory store (graph.json + items/)"
else
  ok "Memory store already clean"
fi

echo ""

if $LOCAL_ONLY; then
  info "Local-only mode — skipping GitHub and Devin cleanup."
  echo ""
  ok "Local reset complete."
  exit 0
fi

# -------------------------------------------------------
# 2. GitHub cleanup — close PRs and delete branches
# -------------------------------------------------------
info "Step 2: Cleaning GitHub demo repos..."
echo ""

# Check gh is available
if ! command -v gh &>/dev/null; then
  warn "gh CLI not found — skipping GitHub cleanup."
  warn "Manually close PRs and delete branches on the demo repos."
else
  for repo in "${REPOS[@]}"; do
    info "Checking $repo..."

    # List open PRs
    open_prs=$(gh pr list --repo "$repo" --state open --json number,title --jq '.[].number' 2>/dev/null || echo "")

    if [ -z "$open_prs" ]; then
      ok "  No open PRs"
    else
      pr_count=$(echo "$open_prs" | wc -l | tr -d ' ')
      echo "  Found $pr_count open PR(s):"
      gh pr list --repo "$repo" --state open --json number,title \
        --jq '.[] | "    #\(.number): \(.title)"' 2>/dev/null || true

      if confirm "  Close all open PRs on $repo?"; then
        for pr_num in $open_prs; do
          gh pr close "$pr_num" --repo "$repo" --delete-branch 2>/dev/null && \
            ok "  Closed PR #$pr_num and deleted its branch" || \
            warn "  Could not close PR #$pr_num"
        done
      fi
    fi

    # Delete any leftover remote branches (security/*, fix/*, devin-*)
    leftover_branches=$(gh api "repos/$repo/branches" --paginate --jq '.[].name' 2>/dev/null | \
      grep -E '^(security/|fix/|fix-|devin-|FIND-)' || echo "")

    if [ -n "$leftover_branches" ]; then
      branch_count=$(echo "$leftover_branches" | wc -l | tr -d ' ')
      echo "  Found $branch_count leftover branch(es):"
      echo "$leftover_branches" | while read -r b; do echo "    $b"; done

      if confirm "  Delete these branches on $repo?"; then
        echo "$leftover_branches" | while read -r branch; do
          gh api -X DELETE "repos/$repo/git/refs/heads/$branch" 2>/dev/null && \
            ok "  Deleted branch $branch" || \
            warn "  Could not delete branch $branch"
        done
      fi
    else
      ok "  No leftover branches"
    fi

    echo ""
  done
fi

# -------------------------------------------------------
# 3. Devin session cleanup (optional)
# -------------------------------------------------------
info "Step 3: Checking for active Devin sessions..."

DEVIN_API_KEY=""
if [ -f "$PROJECT_ROOT/.env" ]; then
  DEVIN_API_KEY=$(grep -E '^DEVIN_API_KEY=' "$PROJECT_ROOT/.env" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
fi

if [ -z "$DEVIN_API_KEY" ] || [ "$DEVIN_API_KEY" = "apk_user_your_key_here" ]; then
  warn "No valid DEVIN_API_KEY found — skipping Devin session cleanup."
  warn "Check https://app.devin.ai for any active sessions."
else
  # Fetch ALL recent sessions (not just working/blocked — any non-terminated
  # session counts against the concurrent session limit)
  all_sessions=$(curl -s -H "Authorization: Bearer $DEVIN_API_KEY" \
    "https://api.devin.ai/v1/sessions?limit=50" 2>/dev/null || echo "[]")

  # Terminate ALL sessions — finished/blocked/working all consume slots
  all_ids=$(echo "$all_sessions" | jq -r '.[].session_id' 2>/dev/null || echo "")

  if [ -z "$all_ids" ]; then
    ok "No Devin sessions found"
  else
    session_count=$(echo "$all_ids" | wc -l | tr -d ' ')
    echo "  Found $session_count session(s) on Devin platform"

    if confirm "  Terminate all Devin sessions to free concurrent slots?"; then
      terminated=0
      echo "$all_ids" | while read -r sid; do
        curl -s -X DELETE -H "Authorization: Bearer $DEVIN_API_KEY" \
          "https://api.devin.ai/v1/sessions/$sid" >/dev/null 2>&1 && \
          ok "  Terminated $sid" || \
          warn "  Could not terminate $sid"
      done
      # Wait a moment for Devin to release the slots
      info "Waiting 5s for Devin to release session slots..."
      sleep 5
      ok "Session cleanup complete"
    fi
  fi
fi

echo ""
echo "============================================================"
echo "  Demo reset complete!"
echo ""
echo "  To start a fresh live demo run:"
echo "    cd $PROJECT_ROOT"
echo "    python -m orchestrator.main run sample_data/findings_live.csv --live --wave-size 5"
echo ""
echo "  Dashboard:"
echo "    cd dashboard && npm run dev"
echo "============================================================"
echo ""
