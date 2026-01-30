# ==========================================================
# core/billing_engine.py
# Subscription & Usage Enforcement
# ==========================================================

import json
from datetime import date

from db.repository import get_user_subscription


# ----------------------------------------------------------
# LOAD PLANS
# ----------------------------------------------------------

def load_plans():

    with open("data/plans.json", "r") as f:
        return json.load(f)


PLANS = load_plans()


# ----------------------------------------------------------
# GET ACTIVE PLAN
# ----------------------------------------------------------

def get_active_plan(user_id: int):

    sub = get_user_subscription(user_id)

    if not sub:
        return None

    if not sub["is_active"]:
        return None

    if sub["end_date"] and date.today() > date.fromisoformat(sub["end_date"]):
        return None

    return sub


# ----------------------------------------------------------
# USAGE CHECKS
# ----------------------------------------------------------

def can_create_review(user_id, role=None):

    # Admin unlimited
    if role == "Admin":
        return True


    plan = get_active_plan(user_id)

    if not plan:
        return False


    limit = plan["max_reviews"]
    used = plan["used_reviews"]

    return used < limit


def can_export(user_id: int) -> bool:

    plan = get_active_plan(user_id)

    if not plan:
        return False

    limit = plan["max_exports"]

    used = plan["used_exports"]

    return used < limit


def can_use_advisor(user_id, role=None):

    # Admin always allowed
    if role == "Admin":
        return True


    plan = get_active_plan(user_id)

    if not plan:
        return False


    plan_name = plan["plan"]

    return PLANS[plan_name]["advisor"]


