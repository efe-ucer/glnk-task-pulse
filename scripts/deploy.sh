#!/usr/bin/env bash
set -euo pipefail

# GLNK Task Pulse — deploy to private GitHub repo
# Streamlit Cloud deployment and Notion embed require manual browser steps (printed at end).

REPO_NAME="glnk-task-pulse"

# ── Step 1: Check prerequisites ──────────────────────────────────────────────
echo "Checking prerequisites..."

for cmd in git gh python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is not installed. Please install it first."
    exit 1
  fi
done
echo "  git, gh, python3 — OK"

# ── Step 2: Authenticate GitHub CLI ──────────────────────────────────────────
if ! gh auth status &>/dev/null; then
  echo "GitHub CLI not authenticated. Logging in..."
  gh auth login
fi
echo "  gh auth — OK"

# ── Step 3: Initialize repo and stage files ──────────────────────────────────
if [ ! -d .git ]; then
  git init
  echo "  git init — OK"
else
  echo "  git repo already initialized — OK"
fi

# Explicit file list — no secrets, no venv, no local tooling
git add \
  app.py \
  charts.py \
  config.py \
  data_processing.py \
  notion_client_module.py \
  requirements.txt \
  tasks_data.json \
  .gitignore \
  .python-version \
  .streamlit/config.toml \
  .streamlit/secrets.toml.example \
  scripts/deploy.sh

echo "  Files staged — OK"

# ── Step 4: Commit ───────────────────────────────────────────────────────────
git commit -m "Initial commit — GLNK Task Pulse dashboard"
echo "  Commit created — OK"

# ── Step 5: Create private repo and push ─────────────────────────────────────
if gh repo view "$REPO_NAME" &>/dev/null; then
  echo "  Repo '$REPO_NAME' already exists on GitHub — pushing..."
  git remote get-url origin &>/dev/null || git remote add origin "$(gh repo view "$REPO_NAME" --json sshUrl -q .sshUrl)"
  git push -u origin main
else
  gh repo create "$REPO_NAME" --private --source=. --push
fi
echo "  GitHub repo — OK"

# ── Step 6: Next steps (browser required) ────────────────────────────────────
cat <<'NEXT'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Code pushed. Complete these steps in your browser:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. STREAMLIT CLOUD
   - Go to https://share.streamlit.io
   - Sign in with your GitHub account
   - Click "New app"
   - Select repo: glnk-task-pulse  |  branch: main  |  file: app.py
   - Open "Advanced settings" → paste your NOTION_TOKEN
   - Click Deploy

2. VERIFY
   - Visit: https://<your-app>.streamlit.app/?embed=true&embed_options=dark_theme
   - Confirm the dashboard loads and shows "Live" status

3. NOTION EMBED
   - Create or open the CEO's Notion page
   - Paste the Streamlit URL → click "Create embed"
   - Resize to full width, ~900px height
   - Add a note above: "Live dashboard — data refreshes every 5 min.
     First visit of the day may take ~15s to load."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT
