"""
analyzer.py — Data Analysis & Visualization Recommendation Engine
Detects column types and intelligently recommends chart types.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────
# Type Detection
# ─────────────────────────────────────────────
_DATE_PATTERNS = [
    r"^\d{4}-\d{2}-\d{2}",          # ISO date
    r"^\d{4}-\d{2}-\d{2}T",         # ISO datetime
    r"^\d{2}/\d{2}/\d{4}",          # MM/DD/YYYY
    r"^\d{4}$",                      # bare year
    r"^\d{4}-\d{2}$",               # year-month
]

def _looks_datetime(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    return any(re.match(p, val.strip()) for p in _DATE_PATTERNS)


def _looks_numeric(val: Any) -> bool:
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str):
        try:
            float(val.replace(",", ""))
            return True
        except ValueError:
            return False
    return False


def detect_column_types(data: List[Dict], columns: List[str]) -> Dict[str, str]:
    """Return a mapping of column → 'datetime' | 'numeric' | 'categorical'."""
    if not data:
        return {c: "unknown" for c in columns}

    types: Dict[str, str] = {}
    sample = data[:min(20, len(data))]

    for col in columns:
        values = [row[col] for row in sample if row.get(col) is not None]
        if not values:
            types[col] = "unknown"
            continue

        dt_hits = sum(1 for v in values if _looks_datetime(v))
        num_hits = sum(1 for v in values if _looks_numeric(v))
        n = len(values)

        if dt_hits / n >= 0.7:
            types[col] = "datetime"
        elif num_hits / n >= 0.7:
            types[col] = "numeric"
        else:
            types[col] = "categorical"

    return types


# ─────────────────────────────────────────────
# Numeric stats helper
# ─────────────────────────────────────────────
def _col_stats(data: List[Dict], col: str) -> Dict:
    vals = []
    for row in data:
        v = row.get(col)
        if v is not None and _looks_numeric(v):
            try:
                vals.append(float(str(v).replace(",", "")))
            except Exception:
                pass
    if not vals:
        return {}
    return {
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
        "mean": round(sum(vals) / len(vals), 4),
        "sum": round(sum(vals), 4),
        "count": len(vals),
    }


# ─────────────────────────────────────────────
# Main Analysis Function
# ─────────────────────────────────────────────
def analyze_data(data: List[Dict], columns: List[str]) -> Dict:
    """Full data analysis; returns a rich dict used by the dashboard generator."""
    row_count = len(data)
    col_count = len(columns)

    if row_count == 0:
        return {
            "col_types": {},
            "row_count": 0,
            "col_count": col_count,
            "numeric_cols": [],
            "datetime_cols": [],
            "categorical_cols": [],
            "stats": {},
            "insights": "The query returned no rows. Verify your data or refine the question.",
            "cardinality": {},
        }

    col_types = detect_column_types(data, columns)

    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
    categorical_cols = [c for c, t in col_types.items() if t == "categorical"]

    # Cardinality (unique count per categorical)
    cardinality: Dict[str, int] = {}
    for col in categorical_cols:
        unique_vals = {str(row.get(col)) for row in data if row.get(col) is not None}
        cardinality[col] = len(unique_vals)

    # Numeric stats
    stats: Dict[str, Dict] = {}
    for col in numeric_cols:
        stats[col] = _col_stats(data, col)

    # ── Build human-readable insights ─────────────
    parts: List[str] = [
        f"Query returned **{row_count:,} rows** across **{col_count} columns**."
    ]
    if datetime_cols:
        parts.append(f"📅 Time-series columns detected: *{', '.join(datetime_cols)}*.")
    if numeric_cols:
        metric_summaries = []
        for col in numeric_cols[:3]:
            s = stats.get(col, {})
            if s:
                metric_summaries.append(f"*{col}* (range: {s['min']}–{s['max']}, avg: {s['mean']})")
        parts.append(f"📊 Numeric metrics: {'; '.join(metric_summaries)}.")
    if categorical_cols:
        cat_summaries = [f"*{c}* ({cardinality[c]} unique)" for c in categorical_cols[:4]]
        parts.append(f"🏷 Categorical dimensions: {', '.join(cat_summaries)}.")

    # Dataset size note
    if row_count == 1:
        parts.append("Single-row result — best displayed as KPI cards.")
    elif row_count <= 10:
        parts.append("Small dataset — every value can be displayed individually.")
    elif row_count <= 50:
        parts.append("Moderate dataset — grouped/aggregated visuals recommended.")
    else:
        parts.append("Large dataset — top-N slicing applied for clarity in charts.")

    # High-cardinality warning
    high_card = [c for c, n in cardinality.items() if n > 30]
    if high_card:
        parts.append(
            f"⚠️ High-cardinality columns ({', '.join(high_card)}) — only top 20 values shown in charts."
        )

    return {
        "col_types": col_types,
        "row_count": row_count,
        "col_count": col_count,
        "numeric_cols": numeric_cols,
        "datetime_cols": datetime_cols,
        "categorical_cols": categorical_cols,
        "stats": stats,
        "cardinality": cardinality,
        "insights": " ".join(parts),
    }


# ─────────────────────────────────────────────
# Chart Recommendation Engine
# ─────────────────────────────────────────────
def recommend_charts(analysis: Dict) -> List[Dict]:
    """Return an ordered list of chart recommendations, most appropriate first."""
    numeric_cols = analysis.get("numeric_cols", [])
    datetime_cols = analysis.get("datetime_cols", [])
    categorical_cols = analysis.get("categorical_cols", [])
    row_count = analysis.get("row_count", 0)
    cardinality = analysis.get("cardinality", {})

    if row_count == 0:
        return [{"type": "table", "title": "Empty Result", "description": "No data to visualize.", "primary": True}]

    recs: List[Dict] = []

    # ── Pattern 1: Time series ─────────────────────
    if datetime_cols and numeric_cols:
        recs.append({
            "type": "line",
            "title": f"{numeric_cols[0]} over {datetime_cols[0]}",
            "description": f"Trend of {numeric_cols[0]} across time",
            "x_col": datetime_cols[0],
            "y_col": numeric_cols[0],
            "primary": True,
            "reasoning": "Datetime × numeric → best shown as a line chart to reveal trends.",
        })

    # ── Pattern 2: Category vs numeric → bar ──────
    if categorical_cols and numeric_cols:
        cat = categorical_cols[0]
        num = numeric_cols[0]
        n_unique = cardinality.get(cat, 0)
        recs.append({
            "type": "bar",
            "title": f"{num} by {cat}",
            "description": f"Compare {num} across different {cat} values",
            "x_col": cat,
            "y_col": num,
            "primary": not datetime_cols,
            "reasoning": "Categorical × numeric → bar chart shows relative magnitudes clearly.",
        })

        # Horizontal bar for many categories
        if n_unique > 10:
            recs.append({
                "type": "bar_horizontal",
                "title": f"{num} by {cat} (horizontal)",
                "description": f"Horizontal layout handles long {cat} labels better",
                "x_col": cat,
                "y_col": num,
                "primary": False,
                "reasoning": "Many categories → horizontal bar prevents label overlap.",
            })

        # Pie chart for ≤ 10 categories
        if n_unique <= 10:
            recs.append({
                "type": "pie",
                "title": f"Share of {num} by {cat}",
                "description": f"Proportion each {cat} contributes to total {num}",
                "label_col": cat,
                "value_col": num,
                "primary": False,
                "reasoning": "≤10 categories → pie chart illustrates proportions intuitively.",
            })

    # ── Pattern 3: Two numerics → scatter ────────
    if len(numeric_cols) >= 2:
        recs.append({
            "type": "scatter",
            "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
            "description": f"Correlation between {numeric_cols[0]} and {numeric_cols[1]}",
            "x_col": numeric_cols[0],
            "y_col": numeric_cols[1],
            "primary": False,
            "reasoning": "Two numeric columns → scatter plot reveals correlation.",
        })

    # ── Pattern 4: Single numeric → histogram ─────
    if len(numeric_cols) == 1 and not categorical_cols and row_count > 5:
        recs.append({
            "type": "histogram",
            "title": f"Distribution of {numeric_cols[0]}",
            "description": f"Frequency distribution of {numeric_cols[0]}",
            "col": numeric_cols[0],
            "primary": not recs,
            "reasoning": "Single numeric → histogram shows value distribution.",
        })

    # ── Always add table ───────────────────────────
    recs.append({
        "type": "table",
        "title": "Raw Data Table",
        "description": "Full tabular view with sorting",
        "primary": not recs,
        "reasoning": "Table is always useful for detailed inspection.",
    })

    # Guarantee exactly one primary
    has_primary = any(r.get("primary") for r in recs)
    if not has_primary and recs:
        recs[0]["primary"] = True

    return recs
