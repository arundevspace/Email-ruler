# Email Ruler

Lightweight mail ingestion and rule-based processing using Gmail API, local SQLite storage, and pluggable rules.

**Quick summary**: fetch emails from Gmail into a local DB, evaluate user-defined rules, and perform actions (mark read, move labels). The project supports processed-state tracking to avoid reprocessing and a small CLI to reset processed flags.

**Requirements**
- Python 3.10+ (this repo was tested with 3.14)
- A virtual environment (recommended)

**Setup**
1. Create and activate a virtual environment (zsh):
```bash
python -m venv venv
source venv/bin/activate
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Google API credentials:
- Go to Google Cloud Console → APIs & Services → Credentials and create an OAuth 2.0 Client ID (Application type: Desktop).
- Download the JSON and save it as `client_secret.json` in the project root.
- Enable the Gmail API for the project: https://console.developers.google.com/apis/api/gmail.googleapis.com/overview?project=<YOUR_PROJECT_ID>
- If your app is unverified, add your Google account as a "Test user" on the OAuth consent screen (APIs & Services → OAuth consent screen) so you can grant consent.

Security note: do NOT commit `client_secret.json` or `token.pickle` — they are included in `.gitignore`. If these credentials were ever exposed, rotate them in the Cloud Console.

**Files of interest**
- `clients/gmail_client.py` — Gmail API wrapper (fetch, mark read/unread, move messages).
- `data/data_manager.py` — SQLite DB manager. Tracks `processed` state to avoid reprocessing.
- `rules/rules_processor.py` — Rule evaluation and action execution logic.
- `ingest_data.py` — Standalone ingestion script (fetches and saves emails).
- `main.py` — Main runner: ingests, loads unprocessed emails, runs rules, marks processed.
- `manage.py` — CLI for DB maintenance (`reset-processed`).
- `rules/rules.json` — Example JSON rules file used by the processor.

**Common commands**
- Run ingestion only (fetch and save):
```bash
python ingest_data.py
```
- Run the full processor (ingest + apply rules):
```bash
python main.py
```
- Reset processed flags (examples):
```bash
# mark a single message unprocessed
./manage.py reset-processed --id <MESSAGE_ID>

# mark all messages unprocessed (prompts for confirmation)
./manage.py reset-processed --all

# mark messages older than 30 days as unprocessed
./manage.py reset-processed --older-than 30
```
- Run tests (pytest):
```bash
pip install -r requirements.txt
pytest -q
```

**Rules**
- Rules are currently loaded from `rules/rules.json` (see `rules/rules_processor.py`).
- You can add file-based rules (we can add YAML loader on request). Rules use `predicate` (`All` or `Any`) and lists of `conditions` + `actions`.

**Behavior: processed-state and history**
- The DB now contains a `processed` integer column (0 = not processed, 1 = processed). The code ensures the column exists on startup and sets `processed=0` for new messages.
- `ingest_data.py` avoids re-fetching messages already present in the DB (reduces Gmail API quota usage).
- `main.py` processes only unprocessed messages and marks them processed after rule evaluation.



