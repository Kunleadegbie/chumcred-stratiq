# ==========================================================
# core/narrative_engine.py
# Generates executive-style business narratives
# ==========================================================


def generate_executive_summary(report: dict) -> dict:

    company = report["company_info"]["company_name"]
    industry = report["company_info"]["industry"]

    bhi = report["bhi"]

    swot = report["swot"]

    strengths = swot["Strengths"]
    weaknesses = swot["Weaknesses"]
    opportunities = swot["Opportunities"]
    threats = swot["Threats"]


    # -----------------------------
    # Overall Assessment
    # -----------------------------

    if bhi >= 4:
        health = "strong"
    elif bhi >= 3:
        health = "moderate"
    else:
        health = "weak"


    overview = (
        f"{company} operates within the {industry} sector "
        f"and currently demonstrates a {health} level of "
        f"overall business health, with a Business Health Index "
        f"(BHI) of {bhi}."
    )


    # -----------------------------
    # Strengths
    # -----------------------------

    if strengths:
        strength_text = "Key strengths include: " + "; ".join(strengths) + "."
    else:
        strength_text = (
            "No major operational or financial strengths "
            "were identified during this assessment."
        )


    # -----------------------------
    # Weaknesses
    # -----------------------------

    if weaknesses:
        weakness_text = "Key weaknesses include: " + "; ".join(weaknesses) + "."
    else:
        weakness_text = (
            "No critical weaknesses were identified, "
            "indicating relatively stable internal performance."
        )


    # -----------------------------
    # Opportunities
    # -----------------------------

    if opportunities:
        opportunity_text = "Key growth opportunities include: " + "; ".join(opportunities) + "."
    else:
        opportunity_text = (
            "Current market positioning indicates limited "
            "short-term external growth opportunities."
        )


    # -----------------------------
    # Threats
    # -----------------------------

    if threats:
        threat_text = "Key external threats include: " + "; ".join(threats) + "."
    else:
        threat_text = (
            "No immediate external threats were identified "
            "that could significantly impact operations."
        )


    # -----------------------------
    # Priority Actions
    # -----------------------------

    if bhi < 3:
        priority = (
            "Immediate management attention is required to "
            "address structural and operational weaknesses."
        )

    elif bhi < 4:
        priority = (
            "Management should prioritize targeted performance "
            "improvements to strengthen competitiveness."
        )

    else:
        priority = (
            "Management should focus on sustaining performance "
            "and pursuing strategic expansion opportunities."
        )


    # -----------------------------
    # Final Output
    # -----------------------------

    return {
        "overview": overview,
        "strengths": strength_text,
        "weaknesses": weakness_text,
        "opportunities": opportunity_text,
        "threats": threat_text,
        "priority_actions": priority,
    }
