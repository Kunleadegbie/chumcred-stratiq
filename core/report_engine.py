# ==========================================================
# core/report_engine.py
# Builds unified business review payload
# ==========================================================

from datetime import datetime

from db.repository import (
    get_review_by_id,
    get_kpi_inputs,
    get_scores,
)

from core.scoring_engine import compute_scores
from core.benchmarking import compare_to_benchmark
from core.swot_engine import generate_swot
from core.recommender import generate_recommendations


# ----------------------------------------------------------
# Main Report Builder
# ----------------------------------------------------------

def generate_report_payload(review_id: int) -> dict:
    """
    Assemble full business diagnostic report
    for a given review ID.
    """

    # -----------------------------
    # Company Info
    # -----------------------------

    review = get_review_by_id(review_id)

    if not review:
        raise ValueError("Invalid review ID")

    company_info = {
        "review_id": review[0],
        "company_name": review[1],
        "industry": review[2],
        "created_at": review[3],
    }

    # -----------------------------
    # KPI Inputs
    # -----------------------------

    inputs = get_kpi_inputs(review_id)

    if not inputs:
        raise ValueError("No KPI inputs found")

    # -----------------------------
    # Scores
    # -----------------------------

    scores, pillars, bhi = compute_scores(inputs)

    # Normalize score format (dict-safe)
    normalized_scores = []

    for item in scores:

        if isinstance(item, dict):

            normalized_scores.append({
                "kpi": item.get("kpi_id") or item.get("kpi"),
                "value": item.get("value") or item.get("raw_value"),
                "score": item.get("score"),
                "pillar": item.get("pillar"),
            })

        elif isinstance(item, (list, tuple)) and len(item) >= 4:

            normalized_scores.append({
                "kpi": item[0],
                "value": item[1],
                "score": item[2],
                "pillar": item[3],
            })

    # -----------------------------
    # Benchmarking
    # -----------------------------

    benchmarks = compare_to_benchmark(
        normalized_scores,
        company_info["industry"]
    )

    # -----------------------------
    # SWOT
    # -----------------------------

    swot = generate_swot(normalized_scores, benchmarks)

    # -----------------------------
    # Recommendations
    # -----------------------------

    recommendations = generate_recommendations(swot)

    # -----------------------------
    # Meta
    # -----------------------------

    meta = {
        "generated_at": datetime.now().isoformat(),
        "version": "2.0",
        "engine": "Chumcred StratIQ",
    }

    # -----------------------------
    # Final Payload
    # -----------------------------

    payload = {
        "company_info": company_info,
        "kpi_inputs": inputs,
        "scores": normalized_scores,
        "pillars": pillars,
        "bhi": round(bhi, 2),
        "benchmarks": benchmarks,
        "swot": swot,
        "recommendations": recommendations,
        "meta": meta,
    }

    return payload
