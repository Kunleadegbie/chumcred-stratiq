# core/benchmarking.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import math

# If you already have a benchmark store elsewhere, import it here.
# The store can be:
# - dict[str, dict[str, dict]]   e.g. BENCHMARKS[industry][kpi_id] = {"median": 10, "p25": 5, ...}
# - dict[str, dict[str, number]] e.g. BENCHMARKS[industry][kpi_id] = 10
# - list[dict]                   e.g. [{"industry":"Telecom", "kpi_id":"FIN_REV_GROWTH", "median":10}, ...]
try:
    from core.benchmark_data import BENCHMARKS  # optional; OK if missing
except Exception:
    BENCHMARKS = None


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _norm(s: Any) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()


def _resolve_benchmarks_for_industry(industry: str) -> Any:
    """
    Returns the benchmark object for the industry if found, else None.
    Handles:
      - BENCHMARKS as dict keyed by industry (case-insensitive)
      - BENCHMARKS as list of rows
    """
    if BENCHMARKS is None:
        return None

    ind_key = _norm(industry)

    # Dict shape
    if isinstance(BENCHMARKS, dict):
        # Try exact match (case-insensitive)
        for k, v in BENCHMARKS.items():
            if _norm(k) == ind_key:
                return v
        return None

    # List shape
    if isinstance(BENCHMARKS, list):
        # filter by industry field
        rows = []
        for row in BENCHMARKS:
            if isinstance(row, dict) and _norm(row.get("industry")) == ind_key:
                rows.append(row)
        return rows or None

    return None


def _get_ref(ref_obj: Any) -> Dict[str, float]:
    """
    Normalize reference into dict with keys: median, p25, p75 (optional).
    Accepts:
      - number -> {"median": number}
      - dict -> pulls median/p25/p75 if present; otherwise tries common alternatives
    """
    if isinstance(ref_obj, (int, float)):
        return {"median": _safe_float(ref_obj)}
    if isinstance(ref_obj, dict):
        # Common patterns
        median = (
            ref_obj.get("median")
            if "median" in ref_obj
            else ref_obj.get("p50", ref_obj.get("avg", ref_obj.get("mean", 0.0)))
        )
        p25 = ref_obj.get("p25", ref_obj.get("q1", ref_obj.get("lower", None)))
        p75 = ref_obj.get("p75", ref_obj.get("q3", ref_obj.get("upper", None)))

        out = {"median": _safe_float(median)}
        if p25 is not None:
            out["p25"] = _safe_float(p25)
        if p75 is not None:
            out["p75"] = _safe_float(p75)
        return out

    # Unknown: default
    return {"median": 0.0}


def compare_to_benchmark(scores: Union[Dict[str, Any], List[Any]], industry: str) -> List[Dict[str, Any]]:
    """
    Compare KPI values against industry benchmarks.
    `scores` can be:
      - dict[kpi_id] = value
      - list of tuples/dicts from db
    Returns list of rows for dataframe display.
    """
    bench = _resolve_benchmarks_for_industry(industry)
    if not bench:
        return []

    # Normalize scores dict
    score_map: Dict[str, float] = {}

    if isinstance(scores, dict):
        for k, v in scores.items():
            score_map[str(k)] = _safe_float(v, 0.0)

    elif isinstance(scores, list):
        # Common db formats:
        # (kpi_id, value) or (kpi_id, value, score) or dict{"kpi_id":..,"value":..}
        for item in scores:
            if isinstance(item, dict):
                kpi_id = item.get("kpi_id") or item.get("id") or item.get("kpi")
                val = item.get("value", item.get("val", item.get("score", 0.0)))
                if kpi_id:
                    score_map[str(kpi_id)] = _safe_float(val, 0.0)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                score_map[str(item[0])] = _safe_float(item[1], 0.0)

    results: List[Dict[str, Any]] = []

    # Case A: bench is dict keyed by kpi_id
    if isinstance(bench, dict):
        for kpi_id, your_val in score_map.items():
            # find benchmark key case-insensitively
            ref_obj = None
            for bk, bv in bench.items():
                if _norm(bk) == _norm(kpi_id):
                    ref_obj = bv
                    break
            if ref_obj is None:
                continue

            ref = _get_ref(ref_obj)
            gap = round(_safe_float(your_val) - _safe_float(ref.get("median", 0.0)), 2)

            results.append(
                {
                    "kpi_id": kpi_id,
                    "your_value": round(_safe_float(your_val), 2),
                    "benchmark_median": round(_safe_float(ref.get("median", 0.0)), 2),
                    "gap_vs_median": gap,
                    "benchmark_p25": round(_safe_float(ref.get("p25", None), 0.0), 2) if "p25" in ref else None,
                    "benchmark_p75": round(_safe_float(ref.get("p75", None), 0.0), 2) if "p75" in ref else None,
                }
            )

        return results

    # Case B: bench is list of dict rows
    if isinstance(bench, list):
        for row in bench:
            if not isinstance(row, dict):
                continue
            kpi_id = row.get("kpi_id") or row.get("kpi") or row.get("id")
            if not kpi_id:
                continue

            # only compare if user has the KPI
            your_val = score_map.get(str(kpi_id))
            if your_val is None:
                continue

            ref = _get_ref(row)
            gap = round(_safe_float(your_val) - _safe_float(ref.get("median", 0.0)), 2)

            results.append(
                {
                    "kpi_id": str(kpi_id),
                    "your_value": round(_safe_float(your_val), 2),
                    "benchmark_median": round(_safe_float(ref.get("median", 0.0)), 2),
                    "gap_vs_median": gap,
                    "benchmark_p25": round(_safe_float(ref.get("p25", None), 0.0), 2) if "p25" in ref else None,
                    "benchmark_p75": round(_safe_float(ref.get("p75", None), 0.0), 2) if "p75" in ref else None,
                }
            )

        return results

    return []
