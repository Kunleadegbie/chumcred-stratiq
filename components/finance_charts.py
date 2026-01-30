# ==================================================
# components/finance_charts.py — Board Financial Charts
# ==================================================

import matplotlib.pyplot as plt


# --------------------------------------------------
# Revenue Trend
# --------------------------------------------------

def plot_revenue(rev):

    fig, ax = plt.subplots()

    ax.plot(["Y-2", "Y-1", "Y"], rev, marker="o")

    ax.set_title("Revenue Trend (3 Years)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Revenue")

    return fig


# --------------------------------------------------
# EBITDA Margin
# --------------------------------------------------

def plot_ebitda_margin(rev, ebitda):

    margin = [
        (e / r * 100) if r else 0
        for r, e in zip(rev, ebitda)
    ]

    fig, ax = plt.subplots()

    ax.plot(["Y-2", "Y-1", "Y"], margin, marker="o")

    ax.set_title("EBITDA Margin (%)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Margin %")

    return fig


# --------------------------------------------------
# Net Profit Trend
# --------------------------------------------------

def plot_profit(profit):

    fig, ax = plt.subplots()

    ax.plot(["Y-2", "Y-1", "Y"], profit, marker="o")

    ax.set_title("Net Profit Trend")
    ax.set_xlabel("Year")
    ax.set_ylabel("Profit")

    return fig


# --------------------------------------------------
# Debt Ratio
# --------------------------------------------------

def plot_debt_ratio(debt, assets):

    ratio = (debt / assets * 100) if assets else 0

    fig, ax = plt.subplots()

    ax.bar(["Debt / Assets"], [ratio])

    ax.set_title("Debt Ratio (%)")

    return fig


# --------------------------------------------------
# Current Ratio
# --------------------------------------------------

def plot_current_ratio(ca, cl):

    ratio = (ca / cl) if cl else 0

    fig, ax = plt.subplots()

    ax.bar(["Current Ratio"], [ratio])

    ax.set_title("Liquidity (Current Ratio)")

    return fig


# --------------------------------------------------
# Cash vs CAPEX
# --------------------------------------------------

def plot_cashflow(ocf, capex):

    fig, ax = plt.subplots()

    ax.bar(["Operating Cash Flow", "CAPEX"], [ocf, capex])

    ax.set_title("Cash Flow vs CAPEX")

    return fig
