# ==========================================================
# core/benchmarking.py — Industry Benchmarks + Comparison
# ==========================================================

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        # guard NaN
        if v != v:
            return default
        return v
    except Exception:
        return default


# ----------------------------------------------------------
# BENCHMARK STORE
# Add/update industries here (keys MUST be normalized)
# ----------------------------------------------------------
BENCHMARKS: Dict[str, Dict[str, Dict[str, float]]] = {
    # NOTE: keep keys normalized (lowercase)
    "telecom": {
        # Each "metric" has median (you can expand later: p25/p75 etc.)
        "FINANCIAL": {"median": 3.0},
        "CUSTOMER": {"median": 3.0},
        "OPERATIONS": {"median": 3.0},
        "PEOPLE": {"median": 3.0},
        "BHI": {"median": 3.0},
    },
    "banking": {
        "FINANCIAL": {"median": 3.2},
        "CUSTOMER": {"median": 3.0},
        "OPERATIONS": {"median": 3.1},
        "PEOPLE": {"median": 3.0},
        "BHI": {"median": 3.1},
    },
    "fintech": {
        "FINANCIAL": {"median": 3.1},
        "CUSTOMER": {"median": 3.2},
        "OPERATIONS": {"median": 3.0},
        "PEOPLE": {"median": 2.9},
        "BHI": {"median": 3.0},
    },
}


# common aliases → canonical industry key
INDUSTRY_ALIASES = {
    "telecommunications": "telecom",
    "telco": "telecom",
    "telecoms": "telecom",
    "telecom": "telecom",
}


def _canonical_industry(industry: Any) -> str:
    i = _norm(industry)
    return INDUSTRY_ALIASES.get(i, i)


def _normalize_scores(scores: Any) -> Dict[str, float]:
    """
    Accepts:
      - dict(metric -> value)
      - list/tuple of rows like [(metric, value), ...]
      - sqlite rows / mixed
    Returns: dict[str,float]
    """
    out: Dict[str, float] = {}

    if scores is None:
        return out

    if isinstance(scores, dict):
        for k, v in scores.items():
            out[str(k)] = _to_float(v, 0.0)
        return out

    if isinstance(scores, (list, tuple)):
        for item in scores:
            # could be ("BHI", 2.45) OR {"metric":"BHI","value":2.45}
            if isinstance(item, dict):
                m = item.get("metric") or item.get("name") or item.get("kpi_id")
                v = item.get("value") if "value" in item else item.get("score")
                if m is not None:
                    out[str(m)] = _to_float(v, 0.0)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                out[str(item[0])] = _to_float(item[1], 0.0)

        return out

    return out


def compare_to_benchmark(scores: Any, industry: Any) -> List[Dict[str, Any]]:
    """
    Compares user scores (pillar averages + BHI) against industry median.
    Returns list of rows for dataframe/table.
    """
    industry_key = _canonical_industry(industry)
    store = BENCHMARKS.get(industry_key)

    if not store:
        return []

    sdict = _normalize_scores(scores)

    # we compare these metrics if present
    metrics_order = ["FINANCIAL", "CUSTOMER", "OPERATIONS", "PEOPLE", "BHI"]

    rows: List[Dict[str, Any]] = []
    for metric in metrics_order:
        your_val = _to_float(sdict.get(metric), 0.0)
        ref = store.get(metric) or {}
        med = _to_float(ref.get("median"), 0.0)

        gap = round(your_val - med, 2)
        status = "Above Median" if gap > 0 else ("Below Median" if gap < 0 else "At Median")

        rows.append(
            {
                "metric": metric,
                "your_score": round(your_val, 2),
                "industry_median": round(med, 2),
                "gap": gap,
                "status": status,
            }
        )

    return rows
