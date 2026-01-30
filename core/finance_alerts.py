# ==================================================
# core/finance_alerts.py — Financial Risk Alerts
# ==================================================


def generate_finance_alerts(results):

    alerts = []


    # Growth
    if results["rev_cagr"] < 0:
        alerts.append(("CRITICAL", "Revenue is declining"))


    # Margin
    if results["ebitda_margin"] < 0.1:
        alerts.append(("HIGH", "Very low operating margin"))


    # Liquidity
    if results["current_ratio"] < 1:
        alerts.append(("CRITICAL", "Liquidity risk detected"))


    # Leverage
    if results["debt_ratio"] > 0.65:
        alerts.append(("HIGH", "Excessive leverage"))


    # Cash Flow
    if results["free_cash_flow"] < 0:
        alerts.append(("MEDIUM", "Negative free cash flow"))


    return alerts
