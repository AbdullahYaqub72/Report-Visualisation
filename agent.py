"""
agent.py — LangChain SQL Agent
Implements the full workflow: schema discovery → SQL generation → validation → execution
"""
import os
import re
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, text, inspect
from langchain_community.utilities import SQLDatabase

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# LLM Factory
# ─────────────────────────────────────────────
def init_llm(provider: str, model_name: str, api_key: str):
    """Dynamically initialize LLM based on provider."""
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0)

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0)

    else:
        raise ValueError(f"Unsupported provider: '{provider}'. Choose from: openai, google, anthropic")


# ─────────────────────────────────────────────
# SQL Cleaning
# ─────────────────────────────────────────────
def clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM SQL output."""
    raw = re.sub(r"```sql\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```\s*", "", raw)
    # Remove explanatory lines before/after SQL
    lines = [l for l in raw.strip().splitlines() if l.strip()]
    # Find the first line that looks like SQL
    sql_keywords = ("select", "with", "explain", "show")
    start = 0
    for i, line in enumerate(lines):
        if any(line.strip().lower().startswith(kw) for kw in sql_keywords):
            start = i
            break
    return "\n".join(lines[start:]).strip()


# ─────────────────────────────────────────────
# JSON Serialisation helper
# ─────────────────────────────────────────────
def json_safe(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return str(obj)


# ─────────────────────────────────────────────
# Main Agent Entry Point
# ─────────────────────────────────────────────
async def run_sql_agent(
    provider: str,
    model_name: str,
    api_key: str,
    db_url: str,
    query: str,
) -> Dict:
    """
    Full pipeline:
      1. Connect to DB & list tables
      2. Fetch schema for relevant tables
      3. Generate SQL via LLM
      4. Validate/fix SQL via LLM
      5. Execute and return structured results
    """

    # ── 1. Init LLM & DB ──────────────────────────────
    model = init_llm(provider, model_name, api_key)
    db = SQLDatabase.from_uri(db_url, sample_rows_in_table_info=2)
    dialect = db.dialect
    tables = db.get_usable_table_names()
    schema = db.get_table_info()

    logger.info(f"Connected to {dialect}. Tables: {tables}")

    # ── 2. Generate SQL ───────────────────────────────
    gen_prompt = f"""You are a senior {dialect} SQL engineer. Given the database schema below and the user question, write a single correct {dialect} SELECT query.

DATABASE SCHEMA:
{schema}

USER QUESTION: {query}

RULES:
- Output ONLY the SQL query — no explanation, no markdown, no comments
- Use only tables and columns that exist in the schema
- Never use DML (INSERT, UPDATE, DELETE, DROP)
- Add LIMIT 200 unless the question asks for all records
- Handle NULLs gracefully
- Use table aliases for readability
"""
    sql_resp = model.invoke(gen_prompt)
    sql_raw = sql_resp.content if hasattr(sql_resp, "content") else str(sql_resp)
    sql_query = clean_sql(sql_raw)
    logger.info(f"Generated SQL:\n{sql_query}")

    # ── 3. Validate / fix SQL ─────────────────────────
    val_prompt = f"""You are a meticulous {dialect} SQL reviewer. Check the following query for common bugs and rewrite it only if needed.

SCHEMA (for reference):
{schema}

SQL TO REVIEW:
{sql_query}

Check for:
- NOT IN with NULLs (use NOT EXISTS instead)
- Wrong column names or missing aliases
- UNION vs UNION ALL confusion
- Incorrect data-type comparisons
- Missing GROUP BY columns
- Off-by-one in BETWEEN

Output ONLY the final SQL query — no commentary.
"""
    val_resp = model.invoke(val_prompt)
    val_raw = val_resp.content if hasattr(val_resp, "content") else str(val_resp)
    validated_sql = clean_sql(val_raw) or sql_query

    logger.info(f"Validated SQL:\n{validated_sql}")

    # ── 4. Execute ────────────────────────────────────
    engine = create_engine(db_url)
    with engine.connect() as conn:
        try:
            result = conn.execute(text(validated_sql))
        except Exception as exec_err:
            logger.warning(f"Validated SQL failed ({exec_err}); retrying with original")
            result = conn.execute(text(sql_query))
            validated_sql = sql_query

        column_names: List[str] = list(result.keys())
        raw_rows = result.fetchall()

    # ── 5. Serialise rows ─────────────────────────────
    rows: List[Dict] = []
    for row in raw_rows:
        safe_row = {col: json_safe(val) for col, val in zip(column_names, row)}
        rows.append(safe_row)

    return {
        "sql_query": validated_sql,
        "data": rows,
        "columns": column_names,
        "dialect": dialect,
        "table_count": len(tables),
    }
