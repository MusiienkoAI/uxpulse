# UXPulse (Local-First Scaffold)

Local-first product scaffold for:

- FastAPI backend for event ingest + issue APIs
- Postgres storage
- Python analytics job that generates issue cards
- VS Code extension that displays issues and links to source files

## Structure

- `docker-compose.yml`
- `backend/`
- `analytics/`
- `extension/`

## Quick Start

1. Start infra and backend:
   - `docker compose up --build`
2. Open backend docs:
   - `http://localhost:8000/docs`
3. (Optional) Generate issues from ingested events:
   - `python analytics/job_generate_issues.py`
4. Run extension:
   - `cd extension`
   - `npm i`
   - `npm run compile`
   - Press `F5` in VS Code/Cursor to launch Extension Development Host
Python project for analyzing UX of React Native application 
