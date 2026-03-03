import re

with open("app.py", "r") as f:
    app_code = f.read()

# 1. Import module
if "from modules.visualisation import" not in app_code:
    import_block = "from modules.report_gen import generate_report  # noqa: E402\nfrom modules.visualisation import detect_dataset_type, _render_auto_charts, _render_ml_results, _generate_business_insights, _render_custom_builder"
    app_code = app_code.replace("from modules.report_gen import generate_report  # noqa: E402", import_block)

# 2. Add to _PAGES
if '"📊  Data Insights": "viz",' not in app_code:
    pages_block = '"🤖  ML Recommender": "ml",\n    "📊  Data Insights": "viz",\n    "💬  NL Query Engine": "nlq",'
    app_code = app_code.replace('"🤖  ML Recommender": "ml",\n    "💬  NL Query Engine": "nlq",', pages_block)

with open("app.py", "w") as f:
    f.write(app_code)
