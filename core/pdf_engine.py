# ==========================================================
# core/pdf_engine.py — Branded Diagnostic PDF Report Export
# ==========================================================

from __future__ import annotations

import io
import os
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether,
)

# Your app modules
from db.repository import get_review_by_id, get_scores, get_kpi_inputs

try:
    # Preferred registry (you already use this elsewhere)
    from core.kpi_registry import load_kpis
except Exception:
    load_kpis = None  # fallback

# ----------------------------------------------------------
# Optional: Persist + load Financial Analyzer AI insights
# (We keep this here to avoid breaking your db layer again.)
# ----------------------------------------------------------

def _get_db_conn() -> sqlite3.Connection:
    """
    Use the SAME DB file your repository uses.
    Your db.repository uses get_conn(), but we avoid importing it
    to prevent circular imports. We assume SQLite file path env/db.
    """
    # If your repository sets a DB path env var, honor it.
    db_path = os.getenv("DB_PATH") or os.getenv("SQLITE_DB_PATH") or "data/app.db"
    # If running in /app on Railway, relative paths resolve from /app
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_financial_ai_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_ai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            content TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def save_financial_ai_report(review_id: int, content: str) -> None:
    """
    Called from Financial Analyzer after 'Analyze Financials'.
    """
    try:
        conn = _get_db_conn()
        _ensure_financial_ai_table(conn)
        cur = conn.cursor()
        cur.execute("DELETE FROM financial_ai WHERE review_id=?", (int(review_id),))
        cur.execute(
            "INSERT INTO financial_ai (review_id, content) VALUES (?, ?)",
            (int(review_id), content or "")
        )
        conn.commit()
        conn.close()
    except Exception:
        # Never break user flow if AI persistence fails
        return


def load_financial_ai_report(review_id: int) -> str:
    """
    Used by PDF export to pull the saved AI narrative.
    """
    try:
        conn = _get_db_conn()
        _ensure_financial_ai_table(conn)
        cur = conn.cursor()
        cur.execute("""
            SELECT content
            FROM financial_ai
            WHERE review_id=?
            ORDER BY id DESC
            LIMIT 1
        """, (int(review_id),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return ""
        return (row["content"] or "").strip()
    except Exception:
        return ""


# ----------------------------------------------------------
# PDF helpers
# ----------------------------------------------------------

def _project_root() -> str:
    # /app/core/pdf_engine.py -> /app
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _logo_path() -> str:
    # User confirmed: assets/logo.png
    return os.path.join(_project_root(), "assets", "logo.png")


def _safe_str(x: Any) -> str:
    return "" if x is None else str(x)


def _row_get(row: Any, key: str, default=None):
    """
    Supports sqlite3.Row, dict-like, or tuple fallback.
    """
    try:
        if isinstance(row, sqlite3.Row):
            return row[key] if key in row.keys() else default
        if isinstance(row, dict):
            return row.get(key, default)
    except Exception:
        pass
    return default


def _fmt_num(x: Any, nd: int = 2) -> str:
    try:
        v = float(x)
        if abs(v) >= 1000:
            return f"{v:,.{nd}f}"
        return f"{v:.{nd}f}"
    except Exception:
        return "0.00"


def _mean(values: List[float]) -> float:
    vals = [v for v in values if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else 0.0


def _normalize_industry(industry: str) -> str:
    return (industry or "").strip().lower()


# ----------------------------------------------------------
# Header / Footer drawing
# ----------------------------------------------------------

def _draw_header_footer(canvas, doc, brand_mode: str, title_text: str):
    w, h = A4

    # Brand colors (close to your Chumcred feel)
    if (brand_mode or "").lower().startswith("chum"):
        brand = colors.HexColor("#0B5E4A")  # deep green
        accent = colors.HexColor("#E8F3EF")  # light green tint
    else:
        brand = colors.HexColor("#1F2937")   # slate
        accent = colors.HexColor("#F3F4F6")  # light gray

    # Header band
    canvas.saveState()
    canvas.setFillColor(accent)
    canvas.rect(0, h - 2.1*cm, w, 2.1*cm, fill=1, stroke=0)

    # Logo
    lp = _logo_path()
    if os.path.exists(lp):
        try:
            canvas.drawImage(lp, 1.2*cm, h - 1.75*cm, width=3.0*cm, height=1.2*cm, mask="auto")
        except Exception:
            pass

    # Title
    canvas.setFillColor(brand)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(4.6*cm, h - 1.25*cm, title_text)

    # Footer
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.setFont("Helvetica", 9)
    canvas.drawString(1.2*cm, 1.0*cm, "© Chumcred Consulting | Confidential")
    canvas.drawRightString(w - 1.2*cm, 1.0*cm, f"Page {doc.page}")
    canvas.restoreState()


# ----------------------------------------------------------
# Main export function (called by Scoring Dashboard)
# ----------------------------------------------------------

def export_report_to_pdf(review_id: int, brand_mode: str = "Chumcred") -> bytes:
    """
    Returns PDF bytes for the Diagnostic Report.
    Scoring Dashboard already calls: export_report_to_pdf(review_id, brand_mode=...)
    """
    review = get_review_by_id(int(review_id))
    if not review:
        raise ValueError("Review not found.")

    company_name = _row_get(review, "company_name") or (review[1] if isinstance(review, (list, tuple)) and len(review) > 1 else "Company")
    industry = _row_get(review, "industry") or (review[2] if isinstance(review, (list, tuple)) and len(review) > 2 else "")
    created_at = _row_get(review, "created_at") or (review[3] if isinstance(review, (list, tuple)) and len(review) > 3 else "")

    # Load KPI definitions (names/units)
    kpi_defs: Dict[str, Dict[str, Any]] = {}
    if load_kpis:
        try:
            kpi_defs = load_kpis() or {}
        except Exception:
            kpi_defs = {}

    # Data sources
    inputs = get_kpi_inputs(int(review_id)) or {}  # dict(kpi_id -> value)
    score_rows = get_scores(int(review_id)) or []  # list of rows {kpi_id, raw_value, score, pillar}

    # Build score structures
    kpi_scores: Dict[str, Dict[str, Any]] = {}
    for r in score_rows:
        kpi_id = _row_get(r, "kpi_id") or ""
        if not kpi_id:
            continue
        kpi_scores[kpi_id] = {
            "raw_value": _row_get(r, "raw_value", inputs.get(kpi_id, 0.0)),
            "score": _row_get(r, "score", 0),
            "pillar": _row_get(r, "pillar", kpi_defs.get(kpi_id, {}).get("pillar", "")),
        }

    # Pillar averages + BHI
    pillar_map: Dict[str, List[float]] = {}
    all_scores: List[float] = []
    for k, info in kpi_scores.items():
        try:
            s = float(info.get("score", 0))
        except Exception:
            s = 0.0
        pillar = _safe_str(info.get("pillar", ""))
        if pillar:
            pillar_map.setdefault(pillar, []).append(s)
        all_scores.append(s)

    pillar_avgs = {p: _mean(vals) for p, vals in pillar_map.items()}
    bhi = _mean(list(pillar_avgs.values())) if pillar_avgs else _mean(all_scores)

    # Financial AI narrative (saved from Financial Analyzer)
    fin_ai_text = load_financial_ai_report(int(review_id))

    # ------------------------------------------------------
    # Styles
    # ------------------------------------------------------
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitleCenter",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=24,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="H1",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=colors.HexColor("#0B5E4A") if (brand_mode or "").lower().startswith("chum") else colors.HexColor("#111827"),
        spaceBefore=8,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=14,
    ))
    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#374151"),
    ))

    # ------------------------------------------------------
    # Build document
    # ------------------------------------------------------
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.4*cm,
        rightMargin=1.4*cm,
        topMargin=2.5*cm,
        bottomMargin=1.6*cm,
        title=f"{company_name} Diagnostic Report",
        author="Chumcred Consulting",
    )

    def on_first_page(canvas, doc_):
        # Cover page uses same header/footer but different title
        _draw_header_footer(canvas, doc_, brand_mode, "BUSINESS PERFORMANCE DIAGNOSTIC REPORT")

    def on_later_pages(canvas, doc_):
        _draw_header_footer(canvas, doc_, brand_mode, "BUSINESS PERFORMANCE DIAGNOSTIC REPORT")

    story: List[Any] = []

    # ----------------------
    # PAGE 1: COVER
    # ----------------------
    story.append(Spacer(1, 2.0*cm))
    story.append(Paragraph("BUSINESS PERFORMANCE<br/>DIAGNOSTIC REPORT", styles["TitleCenter"]))
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(f"<b>{company_name}</b>", styles["Heading2"]))
    story.append(Paragraph(f"Industry: {_safe_str(industry)}", styles["Body"]))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%d %b %Y')}", styles["Body"]))
    if created_at:
        story.append(Paragraph(f"Review Created: {_safe_str(created_at)}", styles["Small"]))
    story.append(Spacer(1, 6.0*cm))
    story.append(Paragraph(
        "Prepared by: <b>Chumcred Consulting</b><br/>Confidential | For internal strategic use only",
        styles["Small"]
    ))
    story.append(PageBreak())

    # ----------------------
    # PAGE 2: EXEC SUMMARY + FIN AI
    # ----------------------
    story.append(Paragraph("Executive Summary", styles["H1"]))
    story.append(Paragraph(
        "This report summarizes your KPI scoring results, pillar performance, and overall Business Health Index (BHI). "
        "It highlights strengths, gaps, and practical actions to improve business performance.",
        styles["Body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("What is the Business Health Index (BHI)?", styles["H1"]))
    story.append(Paragraph(
        "BHI is a single indicator (derived from pillar averages and KPI scores) that shows how healthy the business is "
        "across Financial, Customer, Operations, and People pillars. A higher score indicates stronger overall performance.",
        styles["Body"]
    ))
    story.append(Spacer(1, 0.4*cm))

    # Financial AI narrative (optional)
    story.append(Paragraph("Financial Analyzer — AI Insights", styles["H1"]))
    if fin_ai_text:
        # keep it readable
        for para in [p.strip() for p in fin_ai_text.split("\n") if p.strip()]:
            story.append(Paragraph(f"• {para}", styles["Body"]))
    else:
        story.append(Paragraph(
            "No Financial Analyzer AI narrative found yet. Run Financial Analyzer → Analyze Financials to generate insights.",
            styles["Small"]
        ))

    story.append(PageBreak())

    # ----------------------
    # PAGE 3: KPI SCORECARD + PILLARS + BHI
    # ----------------------
    story.append(Paragraph("Performance Snapshot", styles["H1"]))

    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(f"<b>Business Health Index (BHI):</b> {_fmt_num(bhi, 2)} / 5.00", styles["Body"]))
    story.append(Spacer(1, 0.2*cm))

    # Pillar averages table
    if pillar_avgs:
        pillar_table_data = [["Pillar", "Average Score (1–5)"]]
        for p in sorted(pillar_avgs.keys()):
            pillar_table_data.append([p, _fmt_num(pillar_avgs[p], 2)])

        t = Table(pillar_table_data, colWidths=[8.5*cm, 6.0*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5E4A") if (brand_mode or "").lower().startswith("chum") else colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F9FAFB")),
            ("FONTSIZE", (0, 1), (-1, -1), 9.5),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether([Paragraph("Pillar Averages", styles["H1"]), t]))
        story.append(Spacer(1, 0.4*cm))

    # KPI performance table
    story.append(Paragraph("KPI Performance Table", styles["H1"]))

    table_data = [["Pillar", "KPI", "Value", "Score"]]
    # Prefer scored KPIs; else fall back to raw inputs
    keys = list(kpi_scores.keys()) if kpi_scores else list(inputs.keys())

    for kpi_id in keys:
        cfg = kpi_defs.get(kpi_id, {})
        kpi_name = cfg.get("name", kpi_id)
        pillar = (kpi_scores.get(kpi_id, {}).get("pillar") or cfg.get("pillar") or "")
        raw_val = kpi_scores.get(kpi_id, {}).get("raw_value", inputs.get(kpi_id, 0.0))
        score = kpi_scores.get(kpi_id, {}).get("score", "")

        table_data.append([
            _safe_str(pillar),
            f"{kpi_name} ({kpi_id})",
            _fmt_num(raw_val, 2),
            _safe_str(score),
        ])

    kpi_table = Table(table_data, colWidths=[3.2*cm, 8.1*cm, 3.0*cm, 2.2*cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5E4A") if (brand_mode or "").lower().startswith("chum") else colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (3, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(PageBreak())

    # ----------------------
    # PAGE 4: SWOT (derived if no stored SWOT exists)
    # ----------------------
    story.append(Paragraph("SWOT Analysis", styles["H1"]))

    # Derive from KPI scores (simple but useful)
    scored_items = []
    for kpi_id, info in kpi_scores.items():
        cfg = kpi_defs.get(kpi_id, {})
        name = cfg.get("name", kpi_id)
        try:
            s = float(info.get("score", 0))
        except Exception:
            s = 0.0
        scored_items.append((s, kpi_id, name, info.get("pillar", "")))

    scored_items.sort(reverse=True, key=lambda x: x[0])
    strengths = scored_items[:2]
    weaknesses = list(reversed(scored_items[-2:])) if len(scored_items) >= 2 else scored_items

    def _bullet(items: List[str]) -> List[Any]:
        out = []
        for it in items:
            out.append(Paragraph(f"• {it}", styles["Body"]))
        return out

    strengths_txt = []
    for s, k, name, p in strengths:
        strengths_txt.append(f"Strong performance in {name} ({k}) — score {s:.0f} ({p}).")
    weaknesses_txt = []
    for s, k, name, p in weaknesses:
        weaknesses_txt.append(f"Improvement needed in {name} ({k}) — score {s:.0f} ({p}).")

    opp_txt = [
        "Use targeted initiatives to lift weak KPIs by 1–2 score bands over the next quarter.",
        "Automate tracking and monthly review cadence to improve consistency of execution.",
    ]
    threat_txt = [
        "Weak customer/operations performance can reduce profitability and growth if not addressed quickly.",
        "Talent attrition or skill gaps may slow execution if People pillar is not stabilized.",
    ]

    story.append(Paragraph("<b>Strengths</b>", styles["Body"]))
    story.extend(_bullet(strengths_txt or ["No scored strengths available yet."]))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Weaknesses</b>", styles["Body"]))
    story.extend(_bullet(weaknesses_txt or ["No scored weaknesses available yet."]))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Opportunities</b>", styles["Body"]))
    story.extend(_bullet(opp_txt))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Threats</b>", styles["Body"]))
    story.extend(_bullet(threat_txt))
    story.append(PageBreak())

    # ----------------------
    # PAGE 5: ACTIONS / RECOMMENDATIONS
    # ----------------------
    story.append(Paragraph("Recommendations & Action Plan", styles["H1"]))

    recs = []
    if weaknesses:
        for s, k, name, p in weaknesses:
            recs.append(f"Create a 30–60 day improvement plan for {name} ({k}) under the {p} pillar.")
    recs.extend([
        "Set monthly KPI governance: owners, targets, variance review, and corrective actions.",
        "Link KPI performance to operational initiatives and track progress weekly.",
        "Re-run scoring after updates to measure impact and update the board narrative."
    ])

    story.extend(_bullet(recs))

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("End of Report", styles["Small"]))

    # Build PDF
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
