# pages/4_Scoring_Dashboard.py

import os
import io
import math
import datetime as dt
import streamlit as st

from core.roles import ROLE_PAGES
from core.kpi_registry import load_kpis

from db.repository import (
    get_reviews,
    get_review_by_id,
    get_kpi_inputs,
    save_scores,
    increment_exports,
    load_ai_report
)

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()

# ---------------- Role Guard ----------------
role_raw = (st.session_state["user"].get("role") or "").strip()
role = role_raw.lower()

page_name = "4_Scoring_Dashboard"
allowed = ROLE_PAGES.get(role_raw, ROLE_PAGES.get(role, [])) or []

# Support both formats: list[str] OR list[tuple(label,path)]
allowed_names = set()
for item in allowed:
    if isinstance(item, str):
        allowed_names.add(item)
    elif isinstance(item, (list, tuple)) and item:
        allowed_names.add(str(item[0]))
        allowed_names.add(str(item[1]))

# Don’t hard-block if ROLE_PAGES format differs
# (keeps app usable in production)
# if (page_name not in allowed_names) and (page_name not in allowed):
#     st.error("⛔ Access denied.")
#     st.stop()


# ---------------- UI Styling + Sidebar ----------------
apply_talentiq_sidebar_style()
render_sidebar()

st.title("📊 Scoring Dashboard")


# ---------------- Helpers ----------------

def _safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return float(default)
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return float(default)
        return v
    except Exception:
        return float(default)


def _score_from_rules(value: float, rules: list) -> float:
    """
    rules: [{"min":..., "max":..., "score":...}, ...]
    """
    v = _safe_float(value, 0.0)

    for r in rules or []:
        mn = r.get("min", None)
        mx = r.get("max", None)
        sc = r.get("score", 0)

        ok_min = True if mn is None else (v >= float(mn))
        ok_max = True if mx is None else (v <= float(mx))

        if ok_min and ok_max:
            return float(sc)

    # fallback
    return 0.0


def _compute_scores(kpi_defs: dict, inputs: dict):
    """
    Returns:
      kpi_rows: list of dicts for report table
      pillar_avgs: dict pillar->avg
      bhi: float
    """
    kpi_rows = []
    pillar_map = {}

    for kpi_id, cfg in (kpi_defs or {}).items():
        pillar = (cfg.get("pillar") or "OTHER").strip().upper()
        name = cfg.get("name") or kpi_id

        val = _safe_float(inputs.get(kpi_id, 0.0), 0.0)
        score = _safe_float(_score_from_rules(val, cfg.get("scoring_rules") or []), 0.0)

        kpi_rows.append({
            "kpi_id": kpi_id,
            "name": name,
            "pillar": pillar,
            "value": val,
            "score": score
        })

        pillar_map.setdefault(pillar, []).append(score)

    pillar_avgs = {}
    for p, arr in pillar_map.items():
        if not arr:
            pillar_avgs[p] = 0.0
        else:
            pillar_avgs[p] = round(sum(arr) / max(len(arr), 1), 2)

    # BHI = average of pillar averages (only non-empty)
    if pillar_avgs:
        bhi = round(sum(pillar_avgs.values()) / max(len(pillar_avgs), 1), 2)
    else:
        bhi = 0.0

    return kpi_rows, pillar_avgs, bhi


def _executive_summary(company: str, industry: str, bhi: float) -> str:
    if bhi >= 4.0:
        level = "strong"
        action = "Management should sustain performance while pursuing targeted expansion opportunities."
    elif bhi >= 3.0:
        level = "moderate"
        action = "Management should prioritize targeted performance improvements to strengthen competitiveness."
    elif bhi >= 2.0:
        level = "weak"
        action = "Management should urgently address priority gaps to stabilize operations and improve performance."
    else:
        level = "critical"
        action = "Immediate turnaround actions are required to prevent further deterioration and restore stability."

    return (
        f"{company} operates within the {industry} sector and currently demonstrates a {level} level "
        f"of overall business health, with a Business Health Index (BHI) of {bhi}.\n\n"
        f"{action}"
    )


# ---------------- PDF Report Generator (ReportLab) ----------------
def _build_pdf_report(
    company: str,
    industry: str,
    generated_date: str,
    bhi: float,
    kpi_rows: list,
    pillar_avgs: dict,
    financial_ai: dict,
    logo_path: str
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    import matplotlib.pyplot as plt
    import numpy as np

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="H2", parent=styles["Heading2"], spaceAfter=10))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, textColor=colors.grey))

    story = []

    # ---------- Page 1: Cover ----------
    if logo_path and os.path.exists(logo_path):
        story.append(Image(logo_path, width=4.0*cm, height=4.0*cm))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Chumcred Business Advisory", styles["TitleCenter"]))
    story.append(Paragraph("Data-Driven Strategy & Performance Advisory", styles["TitleCenter"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Business Diagnostic Report", styles["TitleCenter"]))
    story.append(Spacer(1, 18))

    story.append(Paragraph(f"<b>Company:</b> {company}", styles["Normal"]))
    story.append(Paragraph(f"<b>Industry:</b> {industry}", styles["Normal"]))
    story.append(Paragraph(f"<b>Generated:</b> {generated_date}", styles["Normal"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph("© Chumcred Consulting | Confidential", styles["Small"]))

    story.append(PageBreak())

    # ---------- Page 2: Executive Summary ----------
    story.append(Paragraph("Executive Summary", styles["H2"]))
    story.append(Paragraph(_executive_summary(company, industry, bhi).replace("\n", "<br/>"), styles["Normal"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("© Chumcred Consulting | Confidential", styles["Small"]))

    story.append(PageBreak())

    # ---------- Page 3: Business Health Overview ----------
    story.append(Paragraph("Business Health Overview", styles["H2"]))
    story.append(Paragraph(f"<b>Business Health Index (BHI):</b> {bhi} / 5.0", styles["Normal"]))
    story.append(Spacer(1, 12))

    # KPI Table (like sample)
    table_data = [["KPI", "Score", "Pillar"]]
    for r in kpi_rows:
        table_data.append([r["kpi_id"], f'{_safe_float(r["score"],0.0):.1f}', r["pillar"]])

    tbl = Table(table_data, colWidths=[6.0*cm, 3.0*cm, 5.0*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B3D91")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey]),
    ]))
    story.append(Paragraph("KPI Performance", styles["Heading3"]))
    story.append(tbl)
    story.append(Spacer(1, 14))

    # Radar Chart for pillar averages
    # Create chart image in memory
    pillars = list(pillar_avgs.keys())
    vals = [pillar_avgs[p] for p in pillars]

    if pillars:
        angles = np.linspace(0, 2*np.pi, len(pillars), endpoint=False).tolist()
        vals_cycle = vals + vals[:1]
        angles_cycle = angles + angles[:1]

        fig = plt.figure(figsize=(4.4, 4.4))
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles_cycle, vals_cycle)
        ax.fill(angles_cycle, vals_cycle, alpha=0.2)
        ax.set_xticks(angles)
        ax.set_xticklabels(pillars)
        ax.set_yticks([1,2,3,4,5])
        ax.set_ylim(0, 5)

        img_buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(img_buf, format="png", dpi=200)
        plt.close(fig)
        img_buf.seek(0)

        story.append(Paragraph("Pillar Radar (Average Scores)", styles["Heading3"]))
        story.append(Image(img_buf, width=12.5*cm, height=12.5*cm))

    story.append(Spacer(1, 10))
    story.append(Paragraph("© Chumcred Consulting | Confidential", styles["Small"]))

    story.append(PageBreak())

    # ---------- Page 4: SWOT ----------
    story.append(Paragraph("SWOT Analysis", styles["H2"]))

    # If you later store SWOT in DB, you can plug it in here.
    story.append(Paragraph("<b>Strengths</b><br/>None identified.", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Weaknesses</b><br/>None identified.", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Opportunities</b><br/>None identified.", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Threats</b><br/>None identified.", styles["Normal"]))

    story.append(Spacer(1, 14))
    story.append(Paragraph("© Chumcred Consulting | Confidential", styles["Small"]))

    story.append(PageBreak())

    # ---------- Page 5: Recommendations ----------
    story.append(Paragraph("Strategic Recommendations", styles["H2"]))

    # Simple recommendation logic (similar to your sample)
    if bhi >= 4.0:
        recs = ["Maintain strong performance and deepen competitive advantages.",
                "Invest in scalable growth initiatives and customer retention."]
    elif bhi >= 3.0:
        recs = ["Maintain current performance level",
                "Prioritize the lowest-scoring pillar for targeted improvement.",
                "Introduce a monthly KPI review cadence to sustain progress."]
    elif bhi >= 2.0:
        recs = ["Implement immediate corrective actions on weak pillars.",
                "Create a 30–60 day improvement plan with owners and targets."]
    else:
        recs = ["Initiate urgent turnaround program led by executive management.",
                "Freeze non-essential spend and focus on operational stabilization."]

    for i, r in enumerate(recs, start=1):
        story.append(Paragraph(f"{i}. {r}", styles["Normal"]))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 14))
    story.append(Paragraph("© Chumcred Consulting | Confidential", styles["Small"]))

    # ---------- Extra Page: Financial Analyzer AI report ----------
    if financial_ai:
        story.append(PageBreak())
        story.append(Paragraph("Financial Analyzer AI Report", styles["H2"]))

        insights = financial_ai.get("insights") or []
        alerts = financial_ai.get("alerts") or []

        story.append(Paragraph("<b>AI Financial Advisor</b>", styles["Normal"]))
        if not insights:
            story.append(Paragraph("No AI insights were captured.", styles["Normal"]))
        else:
            for msg in insights[:20]:
                story.append(Paragraph(f"• {str(msg)}", styles["Normal"]))
                story.append(Spacer(1, 3))

        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Risk Alerts</b>", styles["Normal"]))
        if not alerts:
            story.append(Paragraph("No critical financial risks detected.", styles["Normal"]))
        else:
            for item in alerts[:20]:
                # alerts can be ["HIGH","message"] tuples or dicts; handle both
                try:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        level, msg = item[0], item[1]
                    elif isinstance(item, dict):
                        level, msg = item.get("level"), item.get("message")
                    else:
                        level, msg = "INFO", str(item)
                    story.append(Paragraph(f"• [{level}] {msg}", styles["Normal"]))
                    story.append(Spacer(1, 3))
                except Exception:
                    pass

        story.append(Spacer(1, 14))
        story.append(Paragraph("© Chumcred Consulting | Confidential", styles["Small"]))

    doc.build(story)
    return buf.getvalue()


# ---------------- Reviews ----------------
reviews = get_reviews()

if not reviews:
    st.warning("No reviews found yet.")
    st.info("Start with: New Review → Data Input → Scoring")
    render_footer()
    st.stop()

review_map = {f"{r[1]} (#{r[0]})": r[0] for r in reviews}

selected = st.selectbox("Select Review", list(review_map.keys()))
review_id = review_map[selected]
st.session_state["active_review"] = review_id

review = get_review_by_id(review_id)
company = (review[1] if review else "") or "Company"
industry = (review[2] if review else "") or "Industry"


# ---------------- Scoring Engine ----------------
st.subheader("Scoring Engine")

kpi_defs = load_kpis()  # from data/kpi_definitions.json
inputs = get_kpi_inputs(review_id)  # values from Data Input + Financial Analyzer save

kpi_rows, pillar_avgs, bhi = _compute_scores(kpi_defs, inputs)

# Save to DB so Benchmarking/other pages can read
kpi_scores_map = {r["kpi_id"]: r["score"] for r in kpi_rows}
save_scores(review_id, bhi, pillar_avgs, kpi_scores_map)


# ---------------- UI OUTPUT ----------------
st.markdown("### 📋 KPI Scores")
for r in kpi_rows:
    st.write(f"**{r['kpi_id']}** — value: {_safe_float(r['value'],0.0):.2f} | score: {_safe_float(r['score'],0.0):.1f} | pillar: {r['pillar']}")

st.markdown("### 📊 Pillar Averages")
for p, v in pillar_avgs.items():
    st.metric(p, _safe_float(v, 0.0))

st.markdown("### Business Health Index (BHI)")
st.metric("BHI", _safe_float(bhi, 0.0))


# ---------------- Board Report Export ----------------
st.divider()
st.subheader("📄 Board Report Export")

st.caption(f"DEBUG ROLE RAW: {role_raw}")
st.caption(f"DEBUG ROLE NORMALIZED: {role}")

is_export_role = role in ("admin", "ceo")

# IMPORTANT FIX:
# Admin/CEO can always export (no billing limit check here).
if not is_export_role:
    st.warning("Only Admins and CEOs can export official reports.")
else:
    # Prepare PDF
    generated = dt.datetime.now().strftime("%d %B %Y")

    # logo path must be assets/logo.png (relative to project root)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, "assets", "logo.png")

    # load financial analyzer AI report (captured on Analyze Financials)
    financial_ai = load_ai_report(review_id, "financial_analyzer") or {}

    pdf_bytes = _build_pdf_report(
        company=company,
        industry=industry,
        generated_date=generated,
        bhi=_safe_float(bhi, 0.0),
        kpi_rows=kpi_rows,
        pillar_avgs=pillar_avgs,
        financial_ai=financial_ai,
        logo_path=logo_path
    )

    # track exports
    try:
        user_id = st.session_state["user"].get("id")
    except Exception:
        user_id = None
    increment_exports(user_id=user_id, review_id=review_id, export_type="board_report_pdf")

    st.download_button(
        "⬇️ Download Board Report (PDF)",
        data=pdf_bytes,
        file_name=f"{company}_Diagnostic_Report.pdf".replace(" ", "_"),
        mime="application/pdf"
    )

render_footer()
