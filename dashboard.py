"""
dashboard.py — Full HTML Dashboard Generator
Produces a self-contained, browser-ready dashboard file using Chart.js.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

PALETTE = [
    "#00D4FF", "#7C3AED", "#10B981", "#F59E0B",
    "#EF4444", "#3B82F6", "#EC4899", "#84CC16",
]


def _js_data(data: List[Dict], col: str) -> str:
    vals = [row.get(col) for row in data]
    return json.dumps(vals)


def _top_n(data: List[Dict], label_col: str, value_col: str, n: int = 20) -> tuple[List, List]:
    """Return top-n rows by value_col (numeric sort)."""
    def to_float(v):
        try:
            return float(str(v).replace(",", ""))
        except Exception:
            return 0

    sorted_data = sorted(data, key=lambda r: to_float(r.get(value_col, 0)), reverse=True)[:n]
    labels = [str(r.get(label_col, "")) for r in sorted_data]
    values = [to_float(r.get(value_col, 0)) for r in sorted_data]
    return labels, values


# ─────────────────────────────────────────────
# Per-chart HTML + JS generators
# ─────────────────────────────────────────────
def _line_chart(cid: str, rec: Dict, data: List[Dict]) -> tuple[str, str]:
    x_col = rec.get("x_col", "")
    y_col = rec.get("y_col", "")
    labels = json.dumps([str(r.get(x_col, "")) for r in data])
    values = json.dumps([
        (lambda v: float(str(v).replace(",", "")) if v is not None else None)(r.get(y_col))
        for r in data
    ])
    html = f"""<div class="chart-card" id="card-{cid}">
  <div class="chart-header">
    <div>
      <div class="chart-title">{rec['title']}</div>
      <div class="chart-desc">{rec['description']}</div>
    </div>
    <button class="dl-btn" onclick="downloadChart('{cid}')">⬇ PNG</button>
  </div>
  <div class="chart-wrap"><canvas id="{cid}"></canvas></div>
</div>"""
    js = f"""(function(){{
  const ctx = document.getElementById('{cid}').getContext('2d');
  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: {labels},
      datasets: [{{
        label: '{y_col}',
        data: {values},
        borderColor: '{PALETTE[0]}',
        backgroundColor: '{PALETTE[0]}22',
        borderWidth: 2.5,
        tension: 0.4,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 7,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ mode: 'index' }} }},
      scales: {{
        x: {{ grid: {{ color: '#1e2d40' }}, ticks: {{ maxRotation: 45, color: '#64748b' }} }},
        y: {{ grid: {{ color: '#1e2d40' }}, ticks: {{ color: '#64748b' }} }}
      }}
    }}
  }});
}})();"""
    return html, js


def _bar_chart(cid: str, rec: Dict, data: List[Dict], horizontal: bool = False) -> tuple[str, str]:
    x_col = rec.get("x_col", "")
    y_col = rec.get("y_col", "")
    labels, values = _top_n(data, x_col, y_col)
    labels_json = json.dumps(labels)
    values_json = json.dumps(values)
    colors_json = json.dumps([PALETTE[i % len(PALETTE)] for i in range(len(labels))])
    chart_type = "bar"
    index_axis = "'y'" if horizontal else "'x'"
    html = f"""<div class="chart-card" id="card-{cid}">
  <div class="chart-header">
    <div>
      <div class="chart-title">{rec['title']}</div>
      <div class="chart-desc">{rec['description']}</div>
    </div>
    <button class="dl-btn" onclick="downloadChart('{cid}')">⬇ PNG</button>
  </div>
  <div class="chart-wrap"><canvas id="{cid}"></canvas></div>
</div>"""
    js = f"""(function(){{
  const ctx = document.getElementById('{cid}').getContext('2d');
  new Chart(ctx, {{
    type: '{chart_type}',
    data: {{
      labels: {labels_json},
      datasets: [{{
        label: '{y_col}',
        data: {values_json},
        backgroundColor: {colors_json},
        borderRadius: 6,
        borderSkipped: false,
      }}]
    }},
    options: {{
      indexAxis: {index_axis},
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ color: '#1e2d40' }}, ticks: {{ color: '#64748b' }} }},
        y: {{ grid: {{ color: '#1e2d40' }}, ticks: {{ color: '#64748b' }} }}
      }}
    }}
  }});
}})();"""
    return html, js


def _pie_chart(cid: str, rec: Dict, data: List[Dict]) -> tuple[str, str]:
    label_col = rec.get("label_col", "")
    value_col = rec.get("value_col", "")
    labels, values = _top_n(data, label_col, value_col, n=10)
    labels_json = json.dumps(labels)
    values_json = json.dumps(values)
    colors_json = json.dumps(PALETTE[:len(labels)])
    html = f"""<div class="chart-card" id="card-{cid}">
  <div class="chart-header">
    <div>
      <div class="chart-title">{rec['title']}</div>
      <div class="chart-desc">{rec['description']}</div>
    </div>
    <button class="dl-btn" onclick="downloadChart('{cid}')">⬇ PNG</button>
  </div>
  <div class="chart-wrap"><canvas id="{cid}"></canvas></div>
</div>"""
    js = f"""(function(){{
  const ctx = document.getElementById('{cid}').getContext('2d');
  new Chart(ctx, {{
    type: 'doughnut',
    data: {{
      labels: {labels_json},
      datasets: [{{
        data: {values_json},
        backgroundColor: {colors_json},
        borderWidth: 2,
        borderColor: '#111827',
        hoverOffset: 8,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ position: 'right', labels: {{ color: '#e2e8f0', padding: 16, font: {{ size: 12 }} }} }},
        tooltip: {{ callbacks: {{
          label: function(ctx) {{
            const total = ctx.dataset.data.reduce((a,b) => a+b, 0);
            const pct = ((ctx.parsed / total) * 100).toFixed(1);
            return ` ${{ctx.label}}: ${{ctx.formattedValue}} (${{pct}}%)`;
          }}
        }} }}
      }}
    }}
  }});
}})();"""
    return html, js


def _scatter_chart(cid: str, rec: Dict, data: List[Dict]) -> tuple[str, str]:
    x_col = rec.get("x_col", "")
    y_col = rec.get("y_col", "")

    def to_float(v):
        try:
            return float(str(v).replace(",", ""))
        except Exception:
            return None

    points = [
        {"x": to_float(r.get(x_col)), "y": to_float(r.get(y_col))}
        for r in data
        if to_float(r.get(x_col)) is not None and to_float(r.get(y_col)) is not None
    ]
    pts_json = json.dumps(points)
    html = f"""<div class="chart-card" id="card-{cid}">
  <div class="chart-header">
    <div>
      <div class="chart-title">{rec['title']}</div>
      <div class="chart-desc">{rec['description']}</div>
    </div>
    <button class="dl-btn" onclick="downloadChart('{cid}')">⬇ PNG</button>
  </div>
  <div class="chart-wrap"><canvas id="{cid}"></canvas></div>
</div>"""
    js = f"""(function(){{
  const ctx = document.getElementById('{cid}').getContext('2d');
  new Chart(ctx, {{
    type: 'scatter',
    data: {{
      datasets: [{{
        label: '{x_col} vs {y_col}',
        data: {pts_json},
        backgroundColor: '{PALETTE[0]}99',
        pointRadius: 6,
        pointHoverRadius: 9,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ title: {{ display: true, text: '{x_col}', color: '#94a3b8' }}, grid: {{ color: '#1e2d40' }}, ticks: {{ color: '#64748b' }} }},
        y: {{ title: {{ display: true, text: '{y_col}', color: '#94a3b8' }}, grid: {{ color: '#1e2d40' }}, ticks: {{ color: '#64748b' }} }}
      }}
    }}
  }});
}})();"""
    return html, js


def _table_html(data: List[Dict], columns: List[str]) -> str:
    max_rows = 200
    rows_shown = data[:max_rows]
    header = "".join(f"<th onclick=\"sortTable(this)\">{c} ↕</th>" for c in columns)
    body_rows = ""
    for row in rows_shown:
        cells = "".join(f"<td>{row.get(c, '')}</td>" for c in columns)
        body_rows += f"<tr>{cells}</tr>"
    truncated = f'<p class="trunc-note">Showing {len(rows_shown)} of {len(data)} rows.</p>' if len(data) > max_rows else ""
    return f"""<div class="chart-card full-width" id="card-table">
  <div class="chart-header">
    <div>
      <div class="chart-title">Raw Data Table</div>
      <div class="chart-desc">All query results — click column headers to sort</div>
    </div>
    <button class="dl-btn" onclick="downloadCSV()">⬇ CSV</button>
  </div>
  {truncated}
  <div class="table-wrap">
    <table id="data-table">
      <thead><tr>{header}</tr></thead>
      <tbody>{body_rows}</tbody>
    </table>
  </div>
</div>"""


# ─────────────────────────────────────────────
# Master Dashboard Generator
# ─────────────────────────────────────────────
def generate_dashboard(
    query: str,
    sql: str,
    data: List[Dict],
    columns: List[str],
    analysis: Dict,
    charts: List[Dict],
) -> str:
    """Return a self-contained HTML dashboard string."""

    chart_htmls: List[str] = []
    chart_scripts: List[str] = []
    seen_types: set[str] = set()

    for i, rec in enumerate(charts):
        cid = f"chart_{i}"
        ct = rec.get("type", "table")

        if ct == "line":
            h, js = _line_chart(cid, rec, data)
            chart_htmls.append(h)
            chart_scripts.append(js)

        elif ct == "bar":
            h, js = _bar_chart(cid, rec, data, horizontal=False)
            chart_htmls.append(h)
            chart_scripts.append(js)

        elif ct == "bar_horizontal":
            h, js = _bar_chart(cid, rec, data, horizontal=True)
            chart_htmls.append(h)
            chart_scripts.append(js)

        elif ct == "pie":
            h, js = _pie_chart(cid, rec, data)
            chart_htmls.append(h)
            chart_scripts.append(js)

        elif ct == "scatter":
            h, js = _scatter_chart(cid, rec, data)
            chart_htmls.append(h)
            chart_scripts.append(js)

        elif ct == "table" and "table" not in seen_types:
            chart_htmls.append(_table_html(data, columns))

        seen_types.add(ct)

    # KPI cards for numeric columns
    kpi_cards = ""
    if analysis.get("stats"):
        kpi_cards = '<div class="kpi-row">'
        for col, s in list(analysis["stats"].items())[:4]:
            kpi_cards += f"""<div class="kpi-card">
  <div class="kpi-value">{s.get('sum', s.get('mean', '—'))}</div>
  <div class="kpi-label">{col} (sum)</div>
  <div class="kpi-sub">avg {s.get('mean', '—')} · range {s.get('min', '—')}–{s.get('max', '—')}</div>
</div>"""
        kpi_cards += "</div>"

    data_json_str = json.dumps(data[:200])
    columns_json_str = json.dumps(columns)
    row_count = analysis.get("row_count", len(data))
    col_count = analysis.get("col_count", len(columns))
    n_charts = len([c for c in charts if c["type"] != "table"])
    insights_html = analysis.get("insights", "").replace("**", "<strong>").replace("*", "<em>")
    # Simple bold/italic
    import re as _re
    insights_html = _re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", analysis.get("insights", ""))
    insights_html = _re.sub(r"\*(.*?)\*", r"<em>\1</em>", insights_html)

    rec_items = "".join(
        f'<li class="rec-item"><span class="rec-badge {r["type"]}">{r["type"].upper()}</span>'
        f'<span><strong>{r["title"]}</strong> — {r.get("reasoning","")}</span></li>'
        for r in charts if r["type"] != "table"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SQL AI Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:       #080c15;
  --surf:     #0f1623;
  --surf2:    #151d2e;
  --border:   #1a2540;
  --accent:   #00d4ff;
  --accent2:  #7c3aed;
  --green:    #10b981;
  --text:     #e2e8f0;
  --muted:    #4a5e7a;
  --mono:     'JetBrains Mono', monospace;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--text); font-family:'Sora',sans-serif; min-height:100vh; }}

/* ── Header ── */
header {{
  background: linear-gradient(135deg, #0f1623 0%, #0a1020 100%);
  border-bottom: 1px solid var(--border);
  padding: 20px 40px;
  display: flex; align-items: center; justify-content: space-between;
}}
.logo {{ font-size:22px; font-weight:800; background:linear-gradient(135deg,var(--accent),var(--accent2)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }}
.logo span {{ font-weight:300; }}
.badge {{ font-size:11px; color:var(--muted); background:var(--surf2); padding:4px 10px; border-radius:20px; border:1px solid var(--border); }}

/* ── Layout ── */
.container {{ max-width:1500px; margin:0 auto; padding:36px 40px; }}

/* ── Section title ── */
.section-label {{ font-size:10px; text-transform:uppercase; letter-spacing:2px; color:var(--accent); font-weight:600; margin-bottom:10px; }}

/* ── Meta cards ── */
.meta-row {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px; }}
.meta-card {{
  background:var(--surf); border:1px solid var(--border); border-radius:14px; padding:22px;
}}
.query-text {{ font-size:16px; color:var(--text); line-height:1.7; font-style:italic; }}
.sql-block {{
  background:#060b12; border:1px solid #1a2540; border-radius:10px;
  padding:16px 18px; font-family:var(--mono); font-size:12.5px; color:#7effa8;
  overflow-x:auto; white-space:pre-wrap; line-height:1.7; max-height:220px;
}}

/* ── KPI row ── */
.kpi-row {{ display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }}
.kpi-card {{
  flex:1; min-width:160px; background:var(--surf); border:1px solid var(--border);
  border-radius:14px; padding:20px; border-top:2px solid var(--accent);
}}
.kpi-value {{ font-size:28px; font-weight:800; color:var(--accent); font-family:var(--mono); }}
.kpi-label {{ font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--muted); margin-top:4px; }}
.kpi-sub {{ font-size:11px; color:var(--muted); margin-top:6px; }}

/* ── Stat strip ── */
.stat-strip {{ display:flex; gap:12px; margin-bottom:24px; }}
.stat-pill {{
  background:var(--surf); border:1px solid var(--border); border-radius:30px;
  padding:8px 18px; font-size:13px; display:flex; align-items:center; gap:8px;
}}
.stat-pill strong {{ color:var(--accent); }}

/* ── Insights ── */
.insights-card {{
  background:var(--surf); border:1px solid var(--border); border-radius:14px;
  padding:22px; margin-bottom:24px;
}}
.insights-text {{ font-size:14px; line-height:1.9; color:#94a3b8; }}
.insights-text strong {{ color:var(--text); }}
.insights-text em {{ color:var(--accent); font-style:normal; }}

/* ── Recs ── */
.recs-card {{
  background:var(--surf); border:1px solid var(--border); border-radius:14px;
  padding:22px; margin-bottom:28px;
}}
.rec-list {{ list-style:none; display:flex; flex-direction:column; gap:10px; margin-top:12px; }}
.rec-item {{ display:flex; align-items:flex-start; gap:12px; font-size:13px; color:#94a3b8; }}
.rec-badge {{ font-size:10px; font-weight:700; padding:3px 8px; border-radius:4px; white-space:nowrap; font-family:var(--mono); }}
.rec-badge.line {{ background:#00d4ff22; color:#00d4ff; }}
.rec-badge.bar, .rec-badge.bar_horizontal {{ background:#7c3aed22; color:#a78bfa; }}
.rec-badge.pie {{ background:#10b98122; color:#34d399; }}
.rec-badge.scatter {{ background:#f59e0b22; color:#fbbf24; }}

/* ── Charts grid ── */
.charts-grid {{
  display:grid; grid-template-columns:repeat(auto-fit, minmax(520px, 1fr));
  gap:24px; margin-bottom:32px;
}}
.chart-card {{
  background:var(--surf); border:1px solid var(--border); border-radius:14px; padding:24px;
  transition: border-color .2s;
}}
.chart-card:hover {{ border-color: var(--accent); }}
.chart-card.full-width {{ grid-column:1/-1; }}
.chart-header {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:18px; }}
.chart-title {{ font-size:15px; font-weight:600; }}
.chart-desc {{ font-size:12px; color:var(--muted); margin-top:3px; }}
.chart-wrap {{ position:relative; height:300px; }}
.dl-btn {{
  background:var(--surf2); border:1px solid var(--border); color:var(--muted);
  padding:6px 12px; border-radius:8px; font-size:11px; cursor:pointer;
  font-family:'Sora',sans-serif; white-space:nowrap;
  transition: all .2s;
}}
.dl-btn:hover {{ border-color:var(--accent); color:var(--accent); }}

/* ── Table ── */
.table-wrap {{ overflow:auto; max-height:420px; border-radius:10px; margin-top:14px; border:1px solid var(--border); }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{
  background:var(--surf2); padding:10px 14px; text-align:left;
  font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--accent);
  border-bottom:1px solid var(--border); position:sticky; top:0; cursor:pointer;
  white-space:nowrap; font-weight:600;
}}
th:hover {{ background:#1e2d40; }}
td {{ padding:10px 14px; border-bottom:1px solid #0f1a28; color:#94a3b8; }}
tr:hover td {{ background:#111e30; color:var(--text); }}
.trunc-note {{ font-size:12px; color:var(--muted); margin-bottom:8px; }}
footer {{
  text-align:center; padding:32px; font-size:12px; color:var(--muted);
  border-top:1px solid var(--border); margin-top:40px;
}}
</style>
</head>
<body>
<header>
  <div class="logo">⚡ SQL AI <span>Dashboard</span></div>
  <div class="badge">Auto-generated · {row_count:,} rows · {n_charts} charts</div>
</header>

<div class="container">

  <!-- Query + SQL -->
  <div class="meta-row">
    <div class="meta-card">
      <div class="section-label">Natural Language Query</div>
      <div class="query-text">"{query}"</div>
    </div>
    <div class="meta-card">
      <div class="section-label">Generated SQL</div>
      <div class="sql-block">{sql}</div>
    </div>
  </div>

  <!-- Stats strip -->
  <div class="stat-strip">
    <div class="stat-pill">📦 <strong>{row_count:,}</strong> rows returned</div>
    <div class="stat-pill">📋 <strong>{col_count}</strong> columns</div>
    <div class="stat-pill">📊 <strong>{n_charts}</strong> charts generated</div>
    <div class="stat-pill">🏷 <strong>{len(analysis.get('categorical_cols',[]))}</strong> categorical</div>
    <div class="stat-pill">🔢 <strong>{len(analysis.get('numeric_cols',[]))}</strong> numeric</div>
    {f'<div class="stat-pill">📅 <strong>{len(analysis.get("datetime_cols",[]))}</strong> datetime</div>' if analysis.get('datetime_cols') else ''}
  </div>

  <!-- KPI cards -->
  {kpi_cards}

  <!-- Insights -->
  <div class="insights-card">
    <div class="section-label">Data Insights</div>
    <div class="insights-text">{insights_html}</div>
  </div>

  <!-- Recommendations -->
  {f'<div class="recs-card"><div class="section-label">Visualization Recommendations</div><ul class="rec-list">{rec_items}</ul></div>' if rec_items else ''}

  <!-- Charts -->
  <div class="charts-grid">
    {"".join(chart_htmls)}
  </div>

</div>

<footer>
  Generated by SQL AI Dashboard &nbsp;·&nbsp; Powered by LangChain + Chart.js
</footer>

<script>
const RAW_DATA = {data_json_str};
const COLUMNS = {columns_json_str};

Chart.defaults.color = '#4a5e7a';
Chart.defaults.borderColor = '#1a2540';
Chart.defaults.font.family = "'Sora', sans-serif";

{"".join(chart_scripts)}

/* ── Download chart as PNG ── */
function downloadChart(id) {{
  const canvas = document.getElementById(id);
  if (!canvas) return;
  const link = document.createElement('a');
  link.download = id + '.png';
  link.href = canvas.toDataURL('image/png', 1.0);
  link.click();
}}

/* ── Download data as CSV ── */
function downloadCSV() {{
  const header = COLUMNS.join(',');
  const rows = RAW_DATA.map(r => COLUMNS.map(c => JSON.stringify(r[c] ?? '')).join(','));
  const csv = [header, ...rows].join('\\n');
  const blob = new Blob([csv], {{ type: 'text/csv' }});
  const link = document.createElement('a');
  link.download = 'query_results.csv';
  link.href = URL.createObjectURL(blob);
  link.click();
}}

/* ── Table sort ── */
function sortTable(th) {{
  const table = document.getElementById('data-table');
  if (!table) return;
  const colIdx = Array.from(th.parentNode.children).indexOf(th);
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const asc = th.dataset.sort !== 'asc';
  th.dataset.sort = asc ? 'asc' : 'desc';
  rows.sort((a, b) => {{
    const aVal = a.cells[colIdx]?.textContent.trim() ?? '';
    const bVal = b.cells[colIdx]?.textContent.trim() ?? '';
    const aNum = parseFloat(aVal.replace(/,/g,''));
    const bNum = parseFloat(bVal.replace(/,/g,''));
    if (!isNaN(aNum) && !isNaN(bNum)) return asc ? aNum - bNum : bNum - aNum;
    return asc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
</script>
</body>
</html>"""
