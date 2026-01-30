# ==================================================
# core/finance_advisor.py — Financial AI Advisor
# ==================================================

from core.gpt_engine import generate_gpt_response


def build_prompt(results, rule_insights):

    prompt = f"""
You are analyzing a company's financial performance.

Key Metrics:
- Revenue CAGR: {results.get("rev_cagr")}%
- EBITDA Margin: {results.get("ebitda_margin")}%
- Debt Ratio: {results.get("debt_ratio")}
- Current Ratio: {results.get("current_ratio")}
- Cash Flow Coverage: {results.get("cashflow_coverage")}

Rule-Based Findings:
{chr(10).join(rule_insights)}

Provide:
1. Executive summary
2. Main financial risks
3. Growth opportunities
4. Strategic recommendations

Write professionally.
"""

    return prompt


def generate_finance_insights(results):

    rule_insights = []

    # ---------- RULE ENGINE ----------

    if results["ebitda_margin"] < 10:
        rule_insights.append("Low profitability margin")

    if results["debt_ratio"] > 0.7:
        rule_insights.append("High leverage risk")

    if results["current_ratio"] < 1.2:
        rule_insights.append("Weak liquidity position")

    if results["rev_cagr"] < 5:
        rule_insights.append("Slow revenue growth")

    if not rule_insights:
        rule_insights.append("Overall financial position is stable")

    # ---------- GPT LAYER ----------

    prompt = build_prompt(results, rule_insights)

    ai_text = generate_gpt_response(prompt)

    return [
        "Rule Summary: " + "; ".join(rule_insights),
        "AI Analysis: " + ai_text
    ]


