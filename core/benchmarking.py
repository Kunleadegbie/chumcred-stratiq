# ==================================================
# core/benchmarking.py — FIXED (v2)
# - Handles benchmark refs being dict OR number
# - Handles scores being dict OR list/tuples
# - Returns rows (list[dict]) for easy DataFrame display
# - Avoids "int object is not subscriptable"
# ==================================================

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return float(default)
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return float(default)
        return v
    except Exception:
        return float(default)


def _ref_median(ref: Any) -> float:
    """
    Accepts benchmark reference as:
      - number (median itself)
      - dict with keys like median/value/p50/avg/mean
      - anything else -> 0.0
    """
    if isinstance(ref, (int, float)):
        return _to_float(ref, 0.0)

    if isinstance(ref, dict):
        for key in ("median", "value", "p50", "avg", "mean"):
            if key in ref:
                return _to_float(ref.get(key), 0.0)
        # last resort: first numeric in dict
        for v in ref.values():
            if isinstance(v, (int, float)):
                return _to_float(v, 0.0)

    return 0.0


def _load_benchmarks() -> Dict[str, Dict[str, Any]]:
    """
    Tries (in order):
      1) core.benchmark_data.BENCHMARKS
      2) data/benchmarks.json (if present)
    Expected shape:
      BENCHMARKS[industry][kpi_id] = {median: ...} OR number
    """
    # 1) Python module
    try:
        from core.benchmark_data import BENCHMARKS  # type: ignore
        if isinstance(BENCHMARKS, dict):
            return BENCHMARKS
    except Exception:
        pass

    # 2) JSON file
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "data", "benchmarks.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass

    return {}


def _normalize_scores(scores: Any) -> Dict[str, Any]:
    """
    Supports:
      - dict(kpi_id -> score OR dict)
      - list of tuples: [(kpi_id, score), ...]
      - list of dict rows: [{"kpi_id":..., "score":...}, ...]
    """
    if scores is None:
        return {}

    if isinstance(scores, dict):
        return scores

    if isinstance(scores, (list, tuple)):
        out: Dict[str, Any] = {}
        for item in scores:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                out[str(item[0])] = item[1]
            elif isinstance(item, dict):
                kid = item.get("kpi_id") or item.get("kpi") or item.get("id")
                val = item.get("score") if "score" in item else item.get("value")
                if kid is not None:
                    out[str(kid)] = val
        return out

    return {}


def compare_to_benchmark(scores: Any, industry: Optional[str]) -> List[Dict[str, Any]]:
    """
    Returns rows:
      [
        {"kpi_id": "...", "score": 3.0, "benchmark": 2.5, "gap": 0.5, "status": "Above"},
        ...
      ]
    """
    scores_map = _normalize_scores(scores)
    benches = _load_benchmarks()

    industry_key = (industry or "").strip()
    refset = benches.get(industry_key) or benches.get(industry_key.upper()) or benches.get("DEFAULT") or {}

    rows: List[Dict[str, Any]] = []
    for kpi_id, val in scores_map.items():
        # allow val to be dict-like
        if isinstance(val, dict):
            # common keys for db payloads
            val_num = _to_float(val.get("score", val.get("value")), 0.0)
        else:
            val_num = _to_float(val, 0.0)

        ref = refset.get(kpi_id, 0.0) if isinstance(refset, dict) else 0.0
        med = _ref_median(ref)
        gap = round(val_num - med, 2)

        status = "At"
        if gap > 0:
            status = "Above"
        elif gap < 0:
            status = "Below"

        rows.append(
            {
                "kpi_id": str(kpi_id),
                "score": round(val_num, 2),
                "benchmark": round(med, 2),
                "gap": gap,
                "status": status,
            }
        )

    # Stable ordering
    rows.sort(key=lambda r: r["kpi_id"])
    return rows
