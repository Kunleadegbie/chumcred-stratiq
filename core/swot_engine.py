# ==========================================================
# core/swot_engine.py
# Generates SWOT analysis from scores & benchmarks
# Supports dict and tuple formats
# ==========================================================


def _extract_score_item(item):
    """
    Normalize score item into (kpi, score).
    Supports dict and tuple formats.
    """

    # Dict format
    if isinstance(item, dict):

        kpi = item.get("kpi") or item.get("name")

        score = item.get("score")

        return kpi, score


    # Tuple/List format
    if isinstance(item, (list, tuple)) and len(item) >= 3:

        return item[0], item[2]


    return None, None


# ----------------------------------------------------------
# Main SWOT Engine
# ----------------------------------------------------------

def generate_swot(scores, benchmarks):

    strengths = []
    weaknesses = []
    opportunities = []
    threats = []


    # -----------------------------
    # Process KPI Scores
    # -----------------------------

    for item in scores:

        kpi, raw_score = _extract_score_item(item)

        if not kpi:
            continue


        # Force numeric
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            continue


        # Strength / Weakness
        if score >= 4:
            strengths.append(f"Strong performance in {kpi}")

        elif score <= 2:
            weaknesses.append(f"Weak performance in {kpi}")


    # -----------------------------
    # Process Benchmarks
    # -----------------------------

    if benchmarks:

        for row in benchmarks:

            # Expect dict format
            kpi = row.get("kpi")

            gap = row.get("gap")


            try:
                gap_val = float(gap)
            except (TypeError, ValueError):
                continue


            # Opportunity / Threat
            if gap_val > 0:
                opportunities.append(
                    f"Opportunity to improve {kpi} versus industry"
                )

            elif gap_val < 0:
                threats.append(
                    f"Underperformance risk in {kpi}"
                )


    return {
        "Strengths": strengths,
        "Weaknesses": weaknesses,
        "Opportunities": opportunities,
        "Threats": threats
    }
