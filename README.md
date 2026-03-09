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