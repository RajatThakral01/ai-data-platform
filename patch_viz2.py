import re

with open("app.py", "r") as f:
    app_code = f.read()

# 1. Add import
if "from modules.visualisation import render_visualisation_page" not in app_code:
    app_code = app_code.replace(
        "from modules.report_gen import generate_report",
        "from modules.report_gen import generate_report  # noqa: E402\nfrom modules.visualisation import render_visualisation_page"
    )

# 2. Add to _PAGES
if '"📊  Data Insights": "viz",' not in app_code:
    app_code = app_code.replace(
        '"🤖  ML Recommender": "ml",\n    "💬  NL Query Engine": "nlq",',
        '"🤖  ML Recommender": "ml",\n    "📊  Data Insights": "viz",\n    "💬  NL Query Engine": "nlq",'
    )

# 3. Add to page routing in main logic
routing_snippet = '''    elif page == "ml":
        _page_ml()'''
new_routing_snippet = '''    elif page == "ml":
        _page_ml()
    elif page == "viz":
        render_visualisation_page()'''

app_code = app_code.replace(routing_snippet, new_routing_snippet)

with open("app.py", "w") as f:
    f.write(app_code)
