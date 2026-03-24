import logging
from .client import metabase_post, metabase_get, get_database_id, get_table_id, METABASE_URL

logger = logging.getLogger(__name__)

def create_dashboard(session_id: str, filename: str, domain: str,
                     insights: dict) -> str | None:
    try:
        db_id = get_database_id()
        if not db_id:
            logger.error("Could not find Metabase database ID")
            return None

        table_id = get_table_id(db_id, "uploaded_data")
        if not table_id:
            logger.error("Could not find uploaded_data table in Metabase")
            return None

        dashboard = metabase_post("/api/dashboard", {
            "name": f"AI Analysis: {filename}",
            "description": f"Auto-generated | Domain: {domain}",
            "parameters": []
        })

        if not dashboard:
            logger.error("Failed to create Metabase dashboard")
            return None

        dashboard_id = dashboard["id"]
        charts = _get_charts_for_domain(domain, insights, table_id, db_id, session_id)

        for i, chart_def in enumerate(charts[:5]):
            card = metabase_post("/api/card", chart_def)
            if card:
                metabase_post(f"/api/dashboard/{dashboard_id}/cards", {
                    "cardId": card["id"],
                    "col": (i % 2) * 12,
                    "row": (i // 2) * 8,
                    "size_x": 12,
                    "size_y": 8
                })

        return f"{METABASE_URL}/dashboard/{dashboard_id}"

    except Exception as e:
        logger.error(f"Auto-dashboard creation failed: {e}")
        return None


def _get_charts_for_domain(domain, insights, table_id, db_id, session_id):
    charts = [_make_row_count_card(table_id, db_id, session_id)]
    domain_map = {
        "telecom": _telecom_charts,
        "retail": _retail_charts,
        "ecommerce": _retail_charts,
        "finance": _finance_charts,
    }
    fn = domain_map.get(domain.lower(), _generic_charts)
    charts.extend(fn(table_id, db_id, session_id, insights))
    return [c for c in charts if c is not None]


def _make_row_count_card(table_id, db_id, session_id):
    return {
        "name": "Total Records",
        "display": "scalar",
        "dataset_query": {
            "database": db_id,
            "type": "native",
            "native": {
                "query": f"SELECT COUNT(*) FROM uploaded_data WHERE session_id = '{session_id}'"
            }
        },
        "visualization_settings": {}
    }


def _telecom_charts(table_id, db_id, session_id, insights):
    return [
        {
            "name": "Churn Distribution",
            "display": "pie",
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": f"SELECT (data->>'churn_flag')::text as churn_status, COUNT(*) as count FROM uploaded_data WHERE session_id = '{session_id}' GROUP BY churn_status"
                }
            },
            "visualization_settings": {}
        },
        {
            "name": "Contract Type Breakdown",
            "display": "bar",
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": f"SELECT (data->>'contract_type')::text as contract_type, COUNT(*) as count FROM uploaded_data WHERE session_id = '{session_id}' GROUP BY contract_type ORDER BY count DESC"
                }
            },
            "visualization_settings": {}
        }
    ]


def _retail_charts(table_id, db_id, session_id, insights):
    return [
        {
            "name": "Sales by Category",
            "display": "bar",
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": f"SELECT (data->>'category')::text as category, SUM((data->>'sales')::float) as total_sales FROM uploaded_data WHERE session_id = '{session_id}' GROUP BY category ORDER BY total_sales DESC LIMIT 10"
                }
            },
            "visualization_settings": {}
        }
    ]


def _finance_charts(table_id, db_id, session_id, insights):
    return _generic_charts(table_id, db_id, session_id, insights)


def _generic_charts(table_id, db_id, session_id, insights):
    return [
        {
            "name": "Data Sample",
            "display": "table",
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": f"SELECT data FROM uploaded_data WHERE session_id = '{session_id}' LIMIT 100"
                }
            },
            "visualization_settings": {}
        }
    ]
