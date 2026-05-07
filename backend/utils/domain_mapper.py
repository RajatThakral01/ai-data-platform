"""
Domain Column Mapper
Maps semantic column roles to actual DataFrame column names
using fuzzy pattern matching. Pure Python — no LLM needed.
"""

from __future__ import annotations
import re


# ── Domain → semantic role → candidate column name patterns ──────────────────

DOMAIN_COLUMN_MAP: dict[str, dict[str, list[str]]] = {

    "telecom": {
        "churn_col":      ["churn", "churned", "churn_label",
                           "customer_churn", "is_churn", "attrition"],
        "tenure_col":     ["tenure", "months", "duration",
                           "tenure_months", "customer_age", "account_age"],
        "charges_col":    ["monthlycharges", "monthly_charges", "charges",
                           "monthly_fee", "bill", "arpu", "revenue"],
        "contract_col":   ["contract", "contract_type", "plan",
                           "subscription", "plan_type"],
        "services_cols":  ["internetservice", "phoneservice", "streaming",
                           "techsupport", "onlinesecurity", "multiplelines"],
        "payment_col":    ["paymentmethod", "payment_method", "payment",
                           "billing_type"],
        "total_col":      ["totalcharges", "total_charges", "total_revenue",
                           "lifetime_value", "clv"],
    },

    "retail": {
        "revenue_col":    ["revenue", "sales", "amount", "total",
                           "total_sales", "sale_amount", "net_sales"],
        "product_col":    ["product", "item", "sku", "product_name",
                           "item_name", "product_category"],
        "category_col":   ["category", "department", "segment",
                           "product_type", "class"],
        "date_col":       ["date", "order_date", "created_at",
                           "purchase_date", "transaction_date", "sale_date"],
        "customer_col":   ["customer", "customer_id", "client",
                           "buyer", "user_id"],
        "quantity_col":   ["quantity", "qty", "units", "units_sold",
                           "volume", "count"],
        "discount_col":   ["discount", "discount_pct", "markdown",
                           "promo", "offer"],
        "profit_col":     ["profit", "margin", "gross_profit",
                           "net_profit", "profit_margin"],
    },

    "finance": {
        "amount_col":     ["amount", "transaction_amount", "value",
                           "sum", "total", "debit", "credit"],
        "date_col":       ["date", "transaction_date", "created_at",
                           "posted_date", "booking_date"],
        "account_col":    ["account", "account_id", "account_number",
                           "account_type"],
        "type_col":       ["type", "transaction_type", "category",
                           "payment_type", "txn_type"],
        "balance_col":    ["balance", "closing_balance", "running_balance",
                           "available_balance"],
        "fraud_col":      ["fraud", "is_fraud", "fraudulent",
                           "anomaly", "flag", "suspicious"],
        "risk_col":       ["risk", "risk_score", "risk_level",
                           "credit_score", "rating"],
    },

    "hr": {
        "attrition_col":  ["attrition", "churn", "left", "resigned",
                           "terminated", "turnover", "exit"],
        "salary_col":     ["salary", "income", "compensation", "pay",
                           "monthly_income", "annual_salary", "wage"],
        "department_col": ["department", "dept", "division", "team",
                           "business_unit", "function"],
        "tenure_col":     ["tenure", "years_at_company", "experience",
                           "seniority", "years_in_role", "months_employed"],
        "performance_col":["performance", "rating", "performance_rating",
                           "score", "review_score", "appraisal"],
        "age_col":        ["age", "employee_age", "years_old"],
        "role_col":       ["jobrole", "job_role", "title", "position",
                           "job_title", "designation"],
        "satisfaction_col":["satisfaction", "job_satisfaction",
                            "engagement", "happiness_score"],
    },

    "marketing": {
        "campaign_col":   ["campaign", "campaign_name", "campaign_id",
                           "ad_name", "promotion"],
        "clicks_col":     ["clicks", "click_count", "total_clicks"],
        "impressions_col":["impressions", "views", "reach", "exposure"],
        "conversion_col": ["conversion", "converted", "is_converted",
                           "signup", "purchase"],
        "ctr_col":        ["ctr", "click_through_rate", "click_rate"],
        "spend_col":      ["spend", "cost", "budget", "ad_spend",
                           "marketing_cost", "cpc"],
        "revenue_col":    ["revenue", "return", "roas", "roi",
                           "attributed_revenue"],
        "channel_col":    ["channel", "source", "medium", "platform",
                           "ad_platform", "network"],
    },

    "healthcare": {
        "diagnosis_col":  ["diagnosis", "condition", "disease", "icd",
                           "primary_diagnosis"],
        "age_col":        ["age", "patient_age", "age_at_admission"],
        "outcome_col":    ["outcome", "result", "status", "readmission",
                           "mortality", "survived"],
        "cost_col":       ["cost", "charges", "billing", "total_cost",
                           "hospital_charges"],
        "stay_col":       ["stay", "length_of_stay", "los",
                           "admission_days", "days_admitted"],
        "department_col": ["department", "ward", "unit", "specialty"],
    },

    "logistics": {
        "delivery_col":   ["delivery", "delivered", "on_time",
                           "delivery_status", "fulfillment"],
        "date_col":       ["date", "order_date", "delivery_date",
                           "ship_date", "dispatch_date"],
        "delay_col":      ["delay", "days_late", "lateness",
                           "delay_days", "late_delivery"],
        "origin_col":     ["origin", "source", "from", "warehouse",
                           "origin_city"],
        "destination_col":["destination", "to", "dest",
                           "delivery_city", "destination_city"],
        "cost_col":       ["cost", "shipping_cost", "freight",
                           "logistics_cost", "transport_cost"],
        "weight_col":     ["weight", "mass", "kg", "lbs",
                           "shipment_weight"],
    },

    "ecommerce": {
        "revenue_col":    ["revenue", "sales", "gmv", "order_value",
                           "total_amount"],
        "product_col":    ["product", "item", "sku", "asin",
                           "product_name"],
        "category_col":   ["category", "department", "segment"],
        "date_col":       ["date", "order_date", "created_at",
                           "purchase_date"],
        "return_col":     ["return", "returned", "refund",
                           "is_returned", "cancellation"],
        "rating_col":     ["rating", "review_score", "stars",
                           "customer_rating"],
        "session_col":    ["session", "visits", "pageviews",
                           "sessions"],
    },
}

DOMAIN_COLUMN_MAP["other"]      = DOMAIN_COLUMN_MAP["retail"]
DOMAIN_COLUMN_MAP["general"]    = DOMAIN_COLUMN_MAP["retail"]


# ── Fuzzy column matcher ──────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase, strip spaces and underscores for fuzzy matching."""
    return re.sub(r"[\s_\-]", "", text.lower())


def match_columns(
    domain: str,
    df_columns: list[str],
    avoid_cols: list[str] = None,
) -> dict[str, str | list[str] | None]:
    """
    Match DataFrame columns to semantic roles for the given domain.

    Returns a dict mapping role_name → matched_column_name (or None).
    Multi-value roles (ending in _cols) return a list.

    Example output for telecom:
    {
        "churn_col":    "Churn",
        "tenure_col":   "tenure",
        "charges_col":  "MonthlyCharges",
        "contract_col": "Contract",
        "services_cols": ["InternetService", "PhoneService"],
        "payment_col":  "PaymentMethod",
        "total_col":    "TotalCharges",
    }
    """
    avoid_cols = avoid_cols or []
    role_map   = DOMAIN_COLUMN_MAP.get(domain.lower(), DOMAIN_COLUMN_MAP["general"])

    norm_to_original: dict[str, str] = {
        _normalize(col): col
        for col in df_columns
        if col not in avoid_cols
    }

    result: dict[str, str | list[str] | None] = {}

    for role, patterns in role_map.items():
        is_multi = role.endswith("_cols")
        matched: list[str] = []

        for pattern in patterns:
            norm_pattern = _normalize(pattern)
            if norm_pattern in norm_to_original:
                col = norm_to_original[norm_pattern]
                if col not in matched:
                    matched.append(col)
            else:
                for norm_col, original_col in norm_to_original.items():
                    if norm_pattern in norm_col or norm_col in norm_pattern:
                        if original_col not in matched:
                            matched.append(original_col)

        if is_multi:
            result[role] = matched if matched else []
        else:
            result[role] = matched[0] if matched else None

    return result


def get_avoid_columns(df_columns: list[str]) -> list[str]:
    """
    Auto-detect ID/index/code columns that should be avoided in charts.
    These are columns likely to be identifiers, not metrics.
    """
    avoid_patterns = [
        "id", "uuid", "guid", "key", "code", "number", "no",
        "index", "ref", "phone", "zip", "postal", "lat",
        "lon", "latitude", "longitude", "ip", "hash",
    ]
    avoid = []
    for col in df_columns:
        norm = _normalize(col)
        if any(p == norm or norm.endswith(p) or norm.startswith(p)
               for p in avoid_patterns):
            avoid.append(col)
    return avoid