import json
from pathlib import Path

DATA_DIR = Path(__file__).parents[1] / "data" / "benchmarks"


def load_benchmarks(industry: str):

    file = industry.lower() + ".json"
    path = DATA_DIR / file

    if not path.exists():
        return {}

    with open(path) as f:
        return json.load(f)


def compare_to_benchmark(scores, industry):

    bench = load_benchmarks(industry)

    results = []

    for kpi, val, score, pillar in scores:

        ref = bench.get(kpi)

        if not ref:
            continue

        gap = round(val - ref["median"], 2)

        status = "Above" if gap >= 0 else "Below"

        results.append({
            "kpi": kpi,
            "company": val,
            "benchmark": ref["median"],
            "gap": gap,
            "status": status
        })

    return results
