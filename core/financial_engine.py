# ==================================================
# core/financial_engine.py — 3-Year Financial Analysis
# ==================================================

import math


# --------------------------------------------------
# CAGR
# --------------------------------------------------

def calc_cagr(start, end, years=2):

    if start <= 0:
        return 0

    return (end / start) ** (1 / years) - 1


# --------------------------------------------------
# MAIN ENGINE
# --------------------------------------------------

def analyze_financials(data):

    """
    data = {
        "rev": [y2, y1, y],
        "ebitda": [...],
        "profit": [...],
        "assets": x,
        "equity": x,
        "current_assets": x,
        "current_liabilities": x,
        "debt": x,
        "ocf": x,
        "capex": x
    }
    """

    rev = data["rev"]
    ebitda = data["ebitda"]
    profit = data["profit"]

    # Growth
    g1 = (rev[1] - rev[0]) / rev[0] if rev[0] else 0
    g2 = (rev[2] - rev[1]) / rev[1] if rev[1] else 0
    cagr = calc_cagr(rev[0], rev[2], 2)


    # Margins
    ebitda_margin = ebitda[2] / rev[2] if rev[2] else 0
    net_margin = profit[2] / rev[2] if rev[2] else 0


    # Returns
    roa = profit[2] / data["assets"] if data["assets"] else 0
    roe = profit[2] / data["equity"] if data["equity"] else 0


    # Liquidity & Leverage
    current_ratio = (
        data["current_assets"] / data["current_liabilities"]
        if data["current_liabilities"] else 0
    )

    debt_ratio = data["debt"] / data["assets"] if data["assets"] else 0


    # Cash Flow
    fcf = data["ocf"] - data["capex"]


    return {

        "rev_growth_y1": g1,
        "rev_growth_y2": g2,
        "rev_cagr": cagr,

        "ebitda_margin": ebitda_margin,
        "net_margin": net_margin,

        "roa": roa,
        "roe": roe,

        "current_ratio": current_ratio,
        "debt_ratio": debt_ratio,

        "free_cash_flow": fcf
    }

