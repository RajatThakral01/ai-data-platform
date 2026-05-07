"""
Business Questions Library
Predefined analytically relevant questions per domain.
Each question maps to exact chart specs using semantic
column roles from domain_mapper.py.
"""

from __future__ import annotations


# ── Type definition ───────────────────────────────────────────────────────────

# Each question entry:
# {
#   "question":        str   — the business question
#   "chart_type":      str   — bar/line/donut/pie/scatter/histogram
#   "x_role":          str   — semantic role for x axis (from domain_mapper)
#   "y_role":          str | None — semantic role for y axis
#   "aggregation":     str   — sum/mean/count/none
#   "title":           str   — chart title
#   "insight_hint":    str   — what pattern to look for
#   "is_kpi":          bool  — whether this also generates a KPI card
#   "kpi_label":       str | None — label for KPI card if is_kpi=True
#   "priority":        int   — 1=must have, 2=important, 3=nice to have
# }

DOMAIN_QUESTIONS: dict[str, list[dict]] = {

    "telecom": [
        {
            "question":     "What is the overall churn rate?",
            "chart_type":   "donut",
            "x_role":       "churn_col",
            "y_role":       None,
            "aggregation":  "count",
            "title":        "Churn Distribution",
            "insight_hint": "Look for churn rate above 15% as a warning signal",
            "is_kpi":       True,
            "kpi_label":    "Churn Rate",
            "priority":     1,
        },
        {
            "question":     "Which contract type has the highest churn?",
            "chart_type":   "bar",
            "x_role":       "contract_col",
            "y_role":       "churn_col",
            "aggregation":  "count",
            "title":        "Churn by Contract Type",
            "insight_hint": "Month-to-month contracts typically drive most churn",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     1,
        },
        {
            "question":     "Does customer tenure affect churn likelihood?",
            "chart_type":   "line",
            "x_role":       "tenure_col",
            "y_role":       "churn_col",
            "aggregation":  "mean",
            "title":        "Churn Rate by Customer Tenure",
            "insight_hint": "New customers (< 12 months) typically churn more",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     1,
        },
        {
            "question":     "How are monthly charges distributed?",
            "chart_type":   "histogram",
            "x_role":       "charges_col",
            "y_role":       None,
            "aggregation":  "none",
            "title":        "Monthly Charges Distribution",
            "insight_hint": "Bimodal distribution indicates two customer segments",
            "is_kpi":       True,
            "kpi_label":    "Avg Monthly Charges",
            "priority":     2,
        },
        {
            "question":     "Which payment method is most common among churners?",
            "chart_type":   "bar",
            "x_role":       "payment_col",
            "y_role":       "churn_col",
            "aggregation":  "count",
            "title":        "Churn by Payment Method",
            "insight_hint": "Electronic check users tend to have higher churn",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     2,
        },
        {
            "question":     "What is the total revenue at risk from churners?",
            "chart_type":   "bar",
            "x_role":       "contract_col",
            "y_role":       "charges_col",
            "aggregation":  "sum",
            "title":        "Monthly Revenue by Contract Type",
            "insight_hint": "Revenue concentration in month-to-month = high risk",
            "is_kpi":       True,
            "kpi_label":    "Total Monthly Revenue",
            "priority":     1,
        },
    ],

    "retail": [
        {
            "question":     "Which product categories generate the most revenue?",
            "chart_type":   "bar",
            "x_role":       "category_col",
            "y_role":       "revenue_col",
            "aggregation":  "sum",
            "title":        "Revenue by Category",
            "insight_hint": "Top 3 categories typically drive 80% of revenue",
            "is_kpi":       True,
            "kpi_label":    "Total Revenue",
            "priority":     1,
        },
        {
            "question":     "What is the sales trend over time?",
            "chart_type":   "line",
            "x_role":       "date_col",
            "y_role":       "revenue_col",
            "aggregation":  "sum",
            "title":        "Revenue Trend Over Time",
            "insight_hint": "Look for seasonal patterns and dips",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     1,
        },
        {
            "question":     "What is the distribution of order values?",
            "chart_type":   "histogram",
            "x_role":       "revenue_col",
            "y_role":       None,
            "aggregation":  "none",
            "title":        "Order Value Distribution",
            "insight_hint": "High skew suggests few large orders dominate",
            "is_kpi":       True,
            "kpi_label":    "Avg Order Value",
            "priority":     2,
        },
        {
            "question":     "Which products have the highest sales volume?",
            "chart_type":   "bar",
            "x_role":       "product_col",
            "y_role":       "quantity_col",
            "aggregation":  "sum",
            "title":        "Top Products by Units Sold",
            "insight_hint": "Compare with revenue — high volume low revenue = low margin",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     2,
        },
        {
            "question":     "How does discounting affect profit?",
            "chart_type":   "scatter",
            "x_role":       "discount_col",
            "y_role":       "profit_col",
            "aggregation":  "none",
            "title":        "Discount vs Profit Margin",
            "insight_hint": "Negative correlation means discounting hurts margins",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     3,
        },
    ],

    "finance": [
        {
            "question":     "What is the transaction volume over time?",
            "chart_type":   "line",
            "x_role":       "date_col",
            "y_role":       "amount_col",
            "aggregation":  "sum",
            "title":        "Transaction Volume Over Time",
            "insight_hint": "Sudden spikes may indicate fraud or data issues",
            "is_kpi":       True,
            "kpi_label":    "Total Transaction Value",
            "priority":     1,
        },
        {
            "question":     "What is the distribution of transaction amounts?",
            "chart_type":   "histogram",
            "x_role":       "amount_col",
            "y_role":       None,
            "aggregation":  "none",
            "title":        "Transaction Amount Distribution",
            "insight_hint": "Heavy tail suggests high-value outlier transactions",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     1,
        },
        {
            "question":     "Which transaction types have the highest volume?",
            "chart_type":   "bar",
            "x_role":       "type_col",
            "y_role":       "amount_col",
            "aggregation":  "sum",
            "title":        "Transaction Volume by Type",
            "insight_hint": "Imbalanced types can signal operational risk",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     2,
        },
        {
            "question":     "What proportion of transactions are flagged as fraud?",
            "chart_type":   "donut",
            "x_role":       "fraud_col",
            "y_role":       None,
            "aggregation":  "count",
            "title":        "Fraud vs Legitimate Transactions",
            "insight_hint": "Any fraud rate above 2% requires immediate investigation",
            "is_kpi":       True,
            "kpi_label":    "Fraud Rate",
            "priority":     1,
        },
    ],

    "hr": [
        {
            "question":     "What is the overall employee attrition rate?",
            "chart_type":   "donut",
            "x_role":       "attrition_col",
            "y_role":       None,
            "aggregation":  "count",
            "title":        "Employee Attrition Rate",
            "insight_hint": "Industry average attrition is 10-15% annually",
            "is_kpi":       True,
            "kpi_label":    "Attrition Rate",
            "priority":     1,
        },
        {
            "question":     "Which departments have the highest attrition?",
            "chart_type":   "bar",
            "x_role":       "department_col",
            "y_role":       "attrition_col",
            "aggregation":  "count",
            "title":        "Attrition by Department",
            "insight_hint": "High attrition in key departments signals culture issues",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     1,
        },
        {
            "question":     "Does salary level affect attrition?",
            "chart_type":   "bar",
            "x_role":       "role_col",
            "y_role":       "salary_col",
            "aggregation":  "mean",
            "title":        "Average Salary by Job Role",
            "insight_hint": "Roles with below-market salary show higher attrition",
            "is_kpi":       True,
            "kpi_label":    "Avg Salary",
            "priority":     2,
        },
        {
            "question":     "How does tenure relate to attrition?",
            "chart_type":   "histogram",
            "x_role":       "tenure_col",
            "y_role":       None,
            "aggregation":  "none",
            "title":        "Employee Tenure Distribution",
            "insight_hint": "Peak attrition typically occurs in year 1-2",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     2,
        },
        {
            "question":     "How does performance rating relate to attrition?",
            "chart_type":   "bar",
            "x_role":       "performance_col",
            "y_role":       "attrition_col",
            "aggregation":  "count",
            "title":        "Attrition by Performance Rating",
            "insight_hint": "High performers leaving is most critical signal",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     2,
        },
    ],

    "marketing": [
        {
            "question":     "Which campaigns have the best conversion rate?",
            "chart_type":   "bar",
            "x_role":       "campaign_col",
            "y_role":       "conversion_col",
            "aggregation":  "mean",
            "title":        "Conversion Rate by Campaign",
            "insight_hint": "Top campaign conversion benchmarks are 2-5%",
            "is_kpi":       True,
            "kpi_label":    "Avg Conversion Rate",
            "priority":     1,
        },
        {
            "question":     "Which channels drive the most revenue?",
            "chart_type":   "bar",
            "x_role":       "channel_col",
            "y_role":       "revenue_col",
            "aggregation":  "sum",
            "title":        "Revenue by Marketing Channel",
            "insight_hint": "Compare channel revenue vs spend for true ROI",
            "is_kpi":       True,
            "kpi_label":    "Total Revenue",
            "priority":     1,
        },
        {
            "question":     "What is the CTR trend over time?",
            "chart_type":   "line",
            "x_role":       "date_col",
            "y_role":       "ctr_col",
            "aggregation":  "mean",
            "title":        "Click-Through Rate Over Time",
            "insight_hint": "Declining CTR signals ad fatigue",
            "is_kpi":       False,
            "kpi_label":    None,
            "priority":     2,
        },
        {
            "question":     "What is the spend vs revenue ratio by channel?",
            "chart_type":   "bar",
            "x_role":       "channel_col",
            "y_role":       "spend_col",
            "aggregation":  "sum",
            "title":        "Marketing Spend by Channel",
            "insight_hint": "Channels with high spend and low revenue = inefficient",
            "is_kpi":       True,
            "kpi_label":    "Total Ad Spend",
            "priority":     1,
        },
    ],
}

# Fallback for unknown domains
DOMAIN_QUESTIONS["ecommerce"] = DOMAIN_QUESTIONS["retail"]
DOMAIN_QUESTIONS["other"]     = DOMAIN_QUESTIONS["retail"]
DOMAIN_QUESTIONS["general"]   = DOMAIN_QUESTIONS["retail"]


# ── Question filter function ──────────────────────────────────────────────────

def get_applicable_questions(
    domain: str,
    matched_columns: dict[str, str | list | None],
    max_questions: int = 6,
) -> list[dict]:
    """
    Returns only questions where required columns were matched.
    Sorted by priority (1 first), limited to max_questions.

    Args:
        domain:          detected domain string
        matched_columns: output of domain_mapper.match_columns()
        max_questions:   max charts to generate (default 6)

    Returns:
        list of applicable question dicts, sorted by priority
    """
    questions = DOMAIN_QUESTIONS.get(
        domain.lower(), DOMAIN_QUESTIONS["general"]
    )

    applicable = []
    for q in questions:
        x_role = q.get("x_role")
        y_role = q.get("y_role")

        # x_role must be matched and not None
        x_matched = matched_columns.get(x_role)
        if not x_matched:
            continue

        # y_role must be matched if specified
        if y_role is not None:
            y_matched = matched_columns.get(y_role)
            if not y_matched:
                continue

        applicable.append(q)

    # Sort by priority, take top max_questions
    applicable.sort(key=lambda q: q.get("priority", 99))
    return applicable[:max_questions]