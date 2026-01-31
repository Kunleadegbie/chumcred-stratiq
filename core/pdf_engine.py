# ==========================================================
# core/pdf_engine.py
# Generates Board / Executive PDF Reports
# ==========================================================

from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image
)

from reportlab.lib.colors import black, lightgrey, HexColor

from core.report_engine import generate_report_payload
from core.narrative_engine import generate_executive_summary
from core.finance_advisor import generate_finance_insights


# ==========================================================
# BRANDING CONFIG
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

LOGO_PATH = BASE_DIR / "assets" / "logo.png"


BRAND = {
    "name": "Chumcred StratIQ",
    "tagline": "AI-Powered Business & Financial Intelligence Platform",
    "color": "#0F766E",
    "footer": "© Chumcred Consulting | Confidential",
}


WHITE_LABEL = {
    "name": "Confidential Management Report",
    "tagline": "Prepared for Internal Use",
    "color": "#1F2933",
    "footer": "Strictly Confidential",
}


# ==========================================================
# MAIN EXPORT FUNCTION
# ==========================================================

def export_report_to_pdf(
    review_id: int,
    brand_mode: str = "branded",
    output_dir: str = "exports"
):
    """
    Generate board / executive PDF report.
    """

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------

    report = generate_report_payload(review_id)

    narrative = generate_executive_summary(report)

    company = report["company_info"]["company_name"]

    # AI Finance Advisor (if available)
    try:
        finance_insights = generate_finance_insights(
            report.get("kpi_inputs", {})
        )
    except Exception:
        finance_insights = []


    # --------------------------------------------------
    # BRANDING
    # --------------------------------------------------

    brand = BRAND if brand_mode == "branded" else WHITE_LABEL

    main_color = HexColor(brand["color"])


    # --------------------------------------------------
    # OUTPUT PATH
    # --------------------------------------------------

    out_dir = BASE_DIR / output_dir
    out_dir.mkdir(exist_ok=True)

    filename = f"{company}_Diagnostic_Report_{datetime.now().year}.pdf"

    filepath = out_dir / filename


    # --------------------------------------------------
    # DOCUMENT SETUP
    # --------------------------------------------------

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    elements = []


    # --------------------------------------------------
    # CUSTOM STYLES
    # --------------------------------------------------

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=main_color,
    )

    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=12,
    )

    header_style = ParagraphStyle(
        "Header",
        parent=styles["Heading2"],
        textColor=main_color,
    )


    # ==================================================
    # COVER PAGE
    # ==================================================

    elements.append(Spacer(1, 40))


    if brand_mode == "branded" and LOGO_PATH.exists():

        try:
            logo = Image(str(LOGO_PATH), width=120, height=70)
            logo.hAlign = "CENTER"

            elements.append(logo)
            elements.append(Spacer(1, 20))

        except Exception:
            pass


    elements.append(Paragraph(brand["name"], title_style))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(brand["tagline"], subtitle_style))
    elements.append(Spacer(1, 40))

    elements.append(
        Paragraph("Business Diagnostic Report", styles["h1"])
    )

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(f"Company: {company}", styles["h3"])
    )

    elements.append(Spacer(1, 10))

    elements.append(
        Paragraph(
            f"Industry: {report['company_info']['industry']}",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 10))

    elements.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%d %B %Y')}",
            styles["Normal"]
        )
    )

    elements.append(PageBreak())


    # ==================================================
    # EXECUTIVE SUMMARY
    # ==================================================

    elements.append(Paragraph("Executive Summary", header_style))
    elements.append(Spacer(1, 15))


    for key in [
        "overview",
        "strengths",
        "weaknesses",
        "opportunities",
        "threats",
        "priority_actions",
    ]:

        text = narrative.get(key, "")

        elements.append(Paragraph(text, styles["Normal"]))
        elements.append(Spacer(1, 10))


    elements.append(PageBreak())


    # ==================================================
    # BUSINESS HEALTH
    # ==================================================

    elements.append(
        Paragraph("Business Health Overview", header_style)
    )

    elements.append(Spacer(1, 15))


    bhi = report["bhi"]

    elements.append(
        Paragraph(
            f"Business Health Index (BHI): {bhi} / 5.0",
            styles["h3"]
        )
    )

    elements.append(Spacer(1, 25))


    # ==================================================
    # KPI TABLE
    # ==================================================

    elements.append(
        Paragraph("KPI Performance", header_style)
    )

    elements.append(Spacer(1, 10))


    table_data = [["KPI", "Score", "Pillar"]]


    for item in report["scores"]:

        kpi = item.get("kpi")

        try:
            score = round(float(item.get("score", 0)), 2)
        except:
            score = 0

        pillar = item.get("pillar")

        table_data.append([kpi, score, pillar])


    table = Table(
        table_data,
        colWidths=[220, 80, 150]
    )


    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, black),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )


    elements.append(table)
    elements.append(PageBreak())


    # ==================================================
    # AI FINANCIAL ADVISOR
    # ==================================================

    elements.append(
        Paragraph("AI Financial Advisor Insights", header_style)
    )

    elements.append(Spacer(1, 15))


    if not finance_insights:

        elements.append(
            Paragraph(
                "No financial advisory insights available.",
                styles["Normal"]
            )
        )

    else:

        for i, insight in enumerate(finance_insights, 1):

            elements.append(
                Paragraph(
                    f"{i}. {insight}",
                    styles["Normal"]
                )
            )

            elements.append(Spacer(1, 5))


    elements.append(PageBreak())


    # ==================================================
    # SWOT
    # ==================================================

    elements.append(Paragraph("SWOT Analysis", header_style))
    elements.append(Spacer(1, 15))


    for section, items in report["swot"].items():

        elements.append(
            Paragraph(section, styles["h3"])
        )

        elements.append(Spacer(1, 5))


        if not items:

            elements.append(
                Paragraph("None identified.", styles["Normal"])
            )

        else:

            for i in items:

                elements.append(
                    Paragraph(f"- {i}", styles["Normal"])
                )


        elements.append(Spacer(1, 10))


    elements.append(PageBreak())


    # ==================================================
    # RECOMMENDATIONS
    # ==================================================

    elements.append(
        Paragraph("Strategic Recommendations", header_style)
    )

    elements.append(Spacer(1, 10))


    for i, rec in enumerate(report["recommendations"], 1):

        elements.append(
            Paragraph(f"{i}. {rec}", styles["Normal"])
        )

        elements.append(Spacer(1, 5))


    # ==================================================
    # FOOTER
    # ==================================================

    def footer(canvas, doc):

        canvas.saveState()

        canvas.setFont("Helvetica", 9)

        canvas.drawCentredString(
            A4[0] / 2,
            20,
            brand["footer"]
        )

        canvas.restoreState()


    # ==================================================
    # BUILD
    # ==================================================

    doc.build(
        elements,
        onFirstPage=footer,
        onLaterPages=footer
    )


    return str(filepath)
