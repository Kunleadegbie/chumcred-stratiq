# ==========================================================
# core/advisor_engine.py
# Business Advisor / Copilot Engine
# ==========================================================


from core.report_engine import generate_report_payload
from core.narrative_engine import generate_executive_summary


# ----------------------------------------------------------
# Main Advisor
# ----------------------------------------------------------

def ask_business_advisor(review_id: int, question: str) -> str:
    """
    Answer business questions using system intelligence.
    """

    report = generate_report_payload(review_id)

    narrative = generate_executive_summary(report)

    q = question.lower()


    # --------------------------------------------------
    # Profitability
    # --------------------------------------------------

    if any(k in q for k in ["profit", "ebitda", "margin", "profitability"]):

        bhi = report["bhi"]

        if bhi >= 4:
            return (
                "Profitability is strong and above industry expectations. "
                "Management should focus on sustaining cost discipline "
                "and revenue optimization."
            )

        elif bhi >= 3:
            return (
                "Profitability is moderate. "
                "There is room for improvement through better cost control "
                "and revenue diversification."
            )

        else:
            return (
                "Profitability is weak and requires urgent attention. "
                "A detailed cost restructuring and pricing review is recommended."
            )


    # --------------------------------------------------
    # Growth
    # --------------------------------------------------

    if any(k in q for k in ["growth", "revenue", "sales"]):

        recs = report["recommendations"]

        if recs:
            return (
                "Revenue growth can be improved by focusing on the following: "
                + " ".join(recs[:2])
            )

        return "Growth opportunities are currently limited based on available data."


    # --------------------------------------------------
    # Risk
    # --------------------------------------------------

    if any(k in q for k in ["risk", "threat", "compliance"]):

        threats = report["swot"]["Threats"]

        if threats:
            return (
                "Key business risks include: " + "; ".join(threats)
            )

        return (
            "No major operational or regulatory risks were identified "
            "in the current assessment."
        )


    # --------------------------------------------------
    # Operations
    # --------------------------------------------------

    if any(k in q for k in ["operation", "cost", "efficiency"]):

        weak = report["swot"]["Weaknesses"]

        if weak:
            return (
                "Operational efficiency can be improved by addressing: "
                + "; ".join(weak)
            )

        return "Operations are currently stable with no major inefficiencies."


    # --------------------------------------------------
    # Default
    # --------------------------------------------------

    return (
        "Your question requires deeper strategic review. "
        "Please consult the executive summary and KPI dashboard "
        "for more detailed insights."
    )
