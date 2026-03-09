# d2l-mcp-server-notion
MCP server connecting D2L to Notion

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Client / AI Agent                │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI  (main.py)                    │
│          /courses  /assignments  /sync/*                │
└──────────┬───────────────────────────┬──────────────────┘
           │                           │
┌──────────▼──────────┐   ┌────────────▼────────────────┐
│   mcp_tools.py      │   │      notion_sync.py         │
│  (business logic)   │   │   (Notion API client)       │
└──────────┬──────────┘   └─────────────────────────────┘
           │
    ┌──────┴───────┐
    │              │
┌───▼────┐  ┌──────▼──────┐
│db.py   │  │d2l_client.py│
│(SQLAlc │  │(httpx +     │
│ hemy + │  │ Valence API)│
│Postgres│  └─────────────┘
└───┬────┘
    │
┌───▼───────────────┐
│   PostgreSQL      │   ← persistent store
│   Redis (cache)   │   ← TTL cache for D2L responses
└───────────────────┘
```

---
# Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/courses` | List all synced courses |
| `POST` | `/sync/courses` | Fetch courses from D2L → PostgreSQL |
| `GET` | `/assignments/{course_id}` | List assignments for a course |
| `POST` | `/sync/{course_id}/assignments` | Fetch assignments → PostgreSQL |
| `GET` | `/quizzes/{course_id}` | List quizzes for a course |
| `POST` | `/sync/{course_id}/quizzes` | Fetch quizzes → PostgreSQL |
| `GET` | `/syllabus/{course_id}` | Fetch syllabus from D2L |
| `POST` | `/sync/{course_id}/syllabus` | Sync syllabus → Notion page |

Full interactive docs available at `http://localhost:8000/docs` when running.

---

## Quick start

### With Docker (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/campusmcp.git
cd campusmcp

cp .env.example .env
# Fill in D2L_API_TOKEN, NOTION_API_TOKEN in .env

docker compose up --build
```

The API will be live at `http://localhost:8000`.

### Without Docker

```bash
# Requires Python 3.14+ and a running PostgreSQL instance
pip install uv
uv sync

cp .env.example .env
# Fill in all values in .env

uvicorn main:app --reload
```

---