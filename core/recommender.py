def generate_recommendations(swot):

    recs = []

    for w in swot["Weaknesses"]:
        recs.append(f"Improve performance on {w}")

    for t in swot["Threats"]:
        recs.append(f"Mitigate risk related to {t}")

    if not recs:
        recs.append("Maintain current performance level")

    return recs
