# ⚡ SQL AI Dashboard

**Natural Language → SQL → Interactive Dashboard**

A full-stack application that wraps a LangChain SQL agent with a premium UI and automatic data visualization.

---

## Architecture

```
sql-ai-dashboard/
├── backend/
│   ├── main.py          ← FastAPI app (entry point)
│   ├── agent.py         ← LangChain SQL agent (NL→SQL→execute)
│   ├── analyzer.py      ← Data type detection + chart recommendation
│   └── dashboard.py     ← Self-contained HTML dashboard generator
├── frontend/
│   └── index.html       ← Single-file React-less frontend (no build step)
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
cd sql-ai-dashboard
pip install -r requirements.txt
```

> For MySQL support: `pip install pymysql`  
> For PostgreSQL: `pip install psycopg2-binary` (already in requirements)

---

### 2. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API will be at: `http://localhost:8000`  
API docs (Swagger): `http://localhost:8000/docs`

---

### 3. Open the frontend

Simply open `frontend/index.html` in your browser — no build step, no npm.

> **Tip:** If you get CORS errors, open via a local server:
> ```bash
> cd frontend && python -m http.server 3000
> ```
> Then visit `http://localhost:3000`

---

## Configuration

Fill in the UI form:

| Field | Example |
|-------|---------|
| Provider | `google` / `openai` / `anthropic` |
| Model Name | `gemini-2.5-flash`, `gpt-4o`, `claude-opus-4-5` |
| API Key | Your provider key |
| Database URL | `postgresql+psycopg2://user:pass@host:5432/db` |
| Query | "Which user bought the most songs and on which date?" |

---

## Supported Databases

| Database | Connection URI |
|----------|---------------|
| PostgreSQL | `postgresql+psycopg2://user:pass@host:5432/db` |
| MySQL | `mysql+pymysql://user:pass@host:3306/db` |
| SQLite | `sqlite:///./mydb.db` |
| Supabase | `postgresql+psycopg2://postgres:pass@db.xxx.supabase.co:5432/postgres` |
| Neon | `postgresql+psycopg2://user:pass@ep-xxx.us-east-1.aws.neon.tech/db` |

---

## API Reference

### `POST /api/query`

```json
{
  "provider":    "google",
  "model_name":  "gemini-2.5-flash",
  "api_key":     "your-key",
  "db_url":      "postgresql+psycopg2://...",
  "query":       "Which user has the most purchases?"
}
```

**Response:**
```json
{
  "sql_query":             "SELECT ...",
  "data":                  [...],
  "columns":               ["user", "count"],
  "row_count":             42,
  "insights":              "Query returned 42 rows...",
  "chart_recommendations": [...],
  "dashboard_html":        "<!DOCTYPE html>..."
}
```

### `POST /api/dashboard`

Same request body, but returns the dashboard as a downloadable HTML file.

---

## How It Works

```
User Query
    │
    ▼
┌──────────────────────────────────────────┐
│  agent.py (LangChain SQL Agent)          │
│                                          │
│  1. Connect to DB via SQLAlchemy         │
│  2. Fetch schema (tables + columns)      │
│  3. LLM generates SQL query              │
│  4. LLM validates + fixes SQL            │
│  5. Execute query, serialize results     │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  analyzer.py (Data Intelligence)         │
│                                          │
│  - Detect column types (datetime,        │
│    numeric, categorical)                 │
│  - Compute stats (min/max/avg/sum)       │
│  - Count cardinality                     │
│  - Generate human-readable insights      │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  Chart Recommendation Engine             │
│                                          │
│  datetime + numeric  → Line chart        │
│  categorical + num   → Bar / Pie chart   │
│  two numerics        → Scatter plot      │
│  single numeric      → Histogram         │
│  always              → Data table        │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  dashboard.py (Dashboard Generator)      │
│                                          │
│  - Self-contained HTML + Chart.js        │
│  - KPI cards, multiple charts            │
│  - Sortable data table                   │
│  - PNG download per chart                │
│  - CSV export                            │
└──────────────────────────────────────────┘
```

---

## Dashboard Features

The generated dashboard HTML is **fully self-contained** — it can be:
- Opened directly in any browser
- Emailed or shared
- Embedded in other pages

**Interactive features:**
- 📊 Multiple chart types (line, bar, doughnut, scatter)
- ⬇ Download each chart as PNG
- ⬇ Export data as CSV
- ↕ Click column headers to sort the data table
- 🎨 Dark theme with responsive layout

---

## Development

To add a new LLM provider, edit `backend/agent.py`:

```python
elif provider == "mistral":
    from langchain_mistralai import ChatMistralAI
    return ChatMistralAI(model=model_name, api_key=api_key, temperature=0)
```

To add a new chart type, add a generator function in `backend/dashboard.py` and a detection rule in `backend/analyzer.py`.

---

## Security Notes

- API keys are **never logged or stored** — they are used per-request only
- Only `SELECT` queries are generated (enforced in the LLM prompt)
- Database credentials exist only in memory for the duration of the request
- Use environment variables for production deployments:

```bash
export BACKEND_CORS_ORIGINS="https://yourdomain.com"
```

---

*Built with FastAPI · LangChain · SQLAlchemy · Chart.js*
