from core.kpi_registry import load_kpis, load_pillar_weights


def score_value(value, rules):
    for r in rules:
        mn = r.get("min")
        mx = r.get("max")

        if (mn is None or value >= mn) and (mx is None or value <= mx):
            return r["score"]

    return 0


def compute_scores(kpi_inputs: dict):
    kpis = load_kpis()
    pillar_weights = load_pillar_weights()

    results = []
    pillar_totals = {}
    pillar_counts = {}

    for kpi_id, value in kpi_inputs.items():

        cfg = kpis.get(kpi_id)
        if not cfg:
            continue

        score = score_value(value, cfg["scoring_rules"])
        pillar = cfg["pillar"]

        results.append({
            "kpi_id": kpi_id,
            "value": value,
            "score": score,
            "pillar": pillar
        })

        pillar_totals[pillar] = pillar_totals.get(pillar, 0) + score
        pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1

    # Pillar averages
    pillar_scores = {}

    for p in pillar_totals:
        pillar_scores[p] = round(
            pillar_totals[p] / pillar_counts[p],
            2
        )

    # Business Health Index
    bhi = 0

    for p, avg in pillar_scores.items():
        weight = pillar_weights.get(p, 0)
        bhi += avg * weight

    bhi = round(bhi, 2)

    return results, pillar_scores, bhi
