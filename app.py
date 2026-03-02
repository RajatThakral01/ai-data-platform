"""
app.py – Streamlit multi-page app for the AI Data Platform.

Run with:
    streamlit run app.py

Pages:
    1. Smart EDA          – automated exploratory data analysis
    2. ML Recommender     – train & compare ML models
    3. NL Query Engine    – ask questions in plain English
    4. Report Generator   – export a professional PDF report
"""

import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="AI Data Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load custom CSS ────────────────────────────────────────────────────────
_CSS_PATH = Path(__file__).parent / "assets" / "style.css"
if _CSS_PATH.exists():
    st.markdown(f"<style>{_CSS_PATH.read_text()}</style>", unsafe_allow_html=True)

# ── Module imports (lazy-safe) ─────────────────────────────────────────────
from modules.data_loader import load_data  # noqa: E402
from modules.eda import run_eda  # noqa: E402
from modules.ml_engine import run_ml  # noqa: E402
from modules.nl_query import execute_generated_code  # noqa: E402
from modules.report_gen import generate_report  # noqa: E402

# ── Page registry ──────────────────────────────────────────────────────────
_PAGES = {
    "📊  Smart EDA": "eda",
    "🤖  ML Recommender": "ml",
    "💬  NL Query Engine": "nlq",
    "📄  Report Generator": "report",
}


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
def _render_sidebar() -> str:
    """Render the dark sidebar with file uploader and page navigation.

    Returns the selected page key.
    """
    with st.sidebar:
        st.markdown("## 🧠 AI Data Platform")
        st.caption("Upload → Explore → Model → Report")
        st.divider()

        # ── File uploader ──────────────────────────────────────────────
        uploaded = st.file_uploader(
            "Upload a CSV or Excel file",
            type=["csv", "xlsx", "xls", "tsv"],
            key="file_uploader",
        )

        if uploaded is not None and (
            "uploaded_name" not in st.session_state
            or st.session_state["uploaded_name"] != uploaded.name
        ):
            _handle_upload(uploaded)

        # Show loaded dataset info
        if "df" in st.session_state:
            df = st.session_state["df"]
            st.success(f"✅  **{st.session_state.get('uploaded_name', 'file')}**")
            st.caption(f"{df.shape[0]:,} rows × {df.shape[1]} cols")
        else:
            st.info("Upload a file to get started.")

        st.divider()

        # ── Navigation ─────────────────────────────────────────────────
        page = st.radio(
            "Navigate",
            list(_PAGES.keys()),
            label_visibility="collapsed",
        )

        st.divider()
        st.caption("Built with ❤️ using Streamlit")

    return _PAGES[page]


def _handle_upload(uploaded) -> None:
    """Save uploaded file to a temp path, run data_loader, store in session."""
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name

    try:
        df, summary = load_data(tmp_path)
        st.session_state["df"] = df
        st.session_state["data_summary"] = summary
        st.session_state["uploaded_name"] = uploaded.name
        # Clear stale results
        for key in ("eda_results", "ml_results", "nlq_history"):
            st.session_state.pop(key, None)
    except Exception as exc:
        st.sidebar.error(f"Failed to load file: {exc}")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Smart EDA
# ═══════════════════════════════════════════════════════════════════════════
def _page_eda() -> None:
    st.markdown("# 📊 Smart EDA")
    st.markdown("Automated exploratory data analysis powered by Pandas & Plotly.")

    if "df" not in st.session_state:
        st.warning("⬅️  Upload a dataset in the sidebar to begin.")
        return

    df = st.session_state["df"]

    # ── Data preview ───────────────────────────────────────────────────
    with st.expander("🔍 Data Preview", expanded=True):
        st.dataframe(df.head(100), use_container_width=True, height=300)

    # ── Run EDA ────────────────────────────────────────────────────────
    if st.button("🚀  Run EDA", type="primary", use_container_width=True):
        with st.spinner("Analysing your data…"):
            results = run_eda(df)
            st.session_state["eda_results"] = results

    if "eda_results" not in st.session_state:
        st.info("Click **Run EDA** to generate the analysis.")
        return

    results = st.session_state["eda_results"]

    # ── Metric cards ───────────────────────────────────────────────────
    summary = st.session_state.get("data_summary", {})
    shape = summary.get("shape", df.shape)
    dup = summary.get("duplicate_count", 0)
    mv = results.get("missing_values", {})
    total_missing = mv.get("total_missing", 0)
    outliers = results.get("outliers", {})
    total_outlier_rows = outliers.get("total_outlier_rows", 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{shape[0]:,}")
    c2.metric("Columns", shape[1])
    c3.metric("Missing Cells", f"{total_missing:,}")
    c4.metric("Outlier Rows", f"{total_outlier_rows:,}")

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_stats, tab_missing, tab_corr, tab_dist, tab_cat, tab_outlier = st.tabs(
        ["📈 Statistics", "🔳 Missing", "🔗 Correlations",
         "📊 Distributions", "📋 Categories", "⚠️ Outliers"]
    )

    with tab_stats:
        _render_descriptive_stats(results)

    with tab_missing:
        _render_missing_values(results)

    with tab_corr:
        _render_correlation(results)

    with tab_dist:
        _render_distributions(results)

    with tab_cat:
        _render_categorical(results)

    with tab_outlier:
        _render_outliers(results)


def _render_descriptive_stats(results: dict) -> None:
    desc = results.get("descriptive_stats", {})
    if not desc:
        st.info("No descriptive statistics available.")
        return

    numeric = {c: s for c, s in desc.items() if "mean" in s}
    categorical = {c: s for c, s in desc.items() if "unique" in s and "mean" not in s}

    if numeric:
        st.markdown("#### Numeric Columns")
        st.dataframe(pd.DataFrame(numeric).T, use_container_width=True)

    if categorical:
        st.markdown("#### Categorical Columns")
        st.dataframe(pd.DataFrame(categorical).T, use_container_width=True)


def _render_missing_values(results: dict) -> None:
    mv = results.get("missing_values", {})
    cols = mv.get("columns", {})
    affected = {c: info for c, info in cols.items() if info.get("count", 0) > 0}

    if not affected:
        st.success("✅ No missing values detected!")
        return

    st.markdown(f"**Total missing cells:** {mv.get('total_missing', 0):,}")
    mv_df = pd.DataFrame(affected).T.rename(columns={
        "count": "Count",
        "percentage": "Percentage (%)",
    })
    display_cols = [c for c in ["Count", "Percentage (%)"] if c in mv_df.columns]
    st.dataframe(mv_df[display_cols].sort_values("Count", ascending=False), use_container_width=True)


def _render_correlation(results: dict) -> None:
    cm = results.get("correlation_matrix", {})
    fig = cm.get("figure")
    if fig is None:
        st.info("Need at least 2 numeric columns for a correlation matrix.")
        return
    st.plotly_chart(fig, use_container_width=True)


def _render_distributions(results: dict) -> None:
    plots = results.get("distribution_plots", {})
    if not plots:
        st.info("No numeric columns to plot.")
        return
    cols = list(plots.keys())
    selected = st.selectbox("Select column", cols, key="dist_col")
    if selected:
        st.plotly_chart(plots[selected], use_container_width=True)


def _render_categorical(results: dict) -> None:
    plots = results.get("categorical_plots", {})
    if not plots:
        st.info("No categorical columns to chart (or cardinality too high).")
        return
    cols = list(plots.keys())
    selected = st.selectbox("Select column", cols, key="cat_col")
    if selected:
        st.plotly_chart(plots[selected], use_container_width=True)


def _render_outliers(results: dict) -> None:
    outliers = results.get("outliers", {})
    total = outliers.get("total_outlier_rows", 0)
    st.markdown(f"**Rows with at least one outlier:** {total}")

    cols_out = outliers.get("columns", {})
    affected = {c: info for c, info in cols_out.items() if info.get("outlier_count", 0) > 0}

    if not affected:
        st.success("✅ No outliers detected via IQR method.")
        return

    out_df = pd.DataFrame(affected).T.rename(columns={
        "lower_bound": "Lower Bound",
        "upper_bound": "Upper Bound",
        "outlier_count": "Outlier Count",
        "outlier_indices": "Outlier Indices",
    })
    display_cols = [c for c in ["Lower Bound", "Upper Bound", "Outlier Count"] if c in out_df.columns]
    st.dataframe(out_df[display_cols], use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: ML Recommender
# ═══════════════════════════════════════════════════════════════════════════
def _page_ml() -> None:
    st.markdown("# 🤖 ML Recommender")
    st.markdown("Auto-detect task type, train 5 models, and compare performance.")

    if "df" not in st.session_state:
        st.warning("⬅️  Upload a dataset in the sidebar to begin.")
        return

    df = st.session_state["df"]

    # ── Target selection ───────────────────────────────────────────────
    target = st.selectbox(
        "Select the **target column** to predict",
        df.columns.tolist(),
        key="ml_target",
    )

    col1, col2 = st.columns(2)
    test_size = col1.slider("Test size (%)", 10, 40, 20, key="ml_test") / 100
    random_state = col2.number_input("Random seed", value=42, key="ml_seed")

    if st.button("🚀  Train Models", type="primary", use_container_width=True):
        with st.spinner("Training and evaluating models…"):
            try:
                result = run_ml(
                    df, target,
                    test_size=test_size,
                    random_state=int(random_state),
                )
                st.session_state["ml_results"] = result
            except Exception as exc:
                st.error(f"Training failed: {exc}")
                return

    if "ml_results" not in st.session_state:
        st.info("Select a target column and click **Train Models**.")
        return

    result = st.session_state["ml_results"]

    # ── Summary metrics ────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Task Type", result["task_type"].title())
    c2.metric("Best Model", result["best_model"] or "N/A")
    c3.metric("Train / Test", f"{result['train_samples']} / {result['test_samples']}")

    # ── Results table ──────────────────────────────────────────────────
    st.markdown("### Model Comparison")
    rows = []
    for r in sorted(result["results"], key=lambda x: x.get("rank") or 999):
        row = {"Rank": r.get("rank", "–"), "Model": r["model"]}
        row.update(r.get("metrics", {}))
        rows.append(row)

    res_df = pd.DataFrame(rows)
    st.dataframe(
        res_df.style.highlight_min(
            subset=[c for c in res_df.columns if c not in ("Rank", "Model")],
            color="#e8f5e9",
        ) if result["task_type"] == "regression" else
        res_df.style.highlight_max(
            subset=[c for c in res_df.columns if c not in ("Rank", "Model")],
            color="#e8f5e9",
        ),
        use_container_width=True,
        hide_index=True,
    )

    # ── Class labels ───────────────────────────────────────────────────
    if result.get("class_labels"):
        st.markdown(f"**Class labels:** {', '.join(str(l) for l in result['class_labels'])}")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: NL Query Engine
# ═══════════════════════════════════════════════════════════════════════════
def _page_nlq() -> None:
    st.markdown("# 💬 NL Query Engine")
    st.markdown("Ask questions about your data in plain English.")

    if "df" not in st.session_state:
        st.warning("⬅️  Upload a dataset in the sidebar to begin.")
        return

    df = st.session_state["df"]

    # ── Mode selector ──────────────────────────────────────────────────
    mode = st.radio(
        "Mode",
        ["🤖 AI-powered (Ollama)", "✏️ Manual code"],
        horizontal=True,
        key="nlq_mode",
    )

    if "🤖" in mode:
        _nlq_ai_mode(df)
    else:
        _nlq_manual_mode(df)


def _nlq_ai_mode(df: pd.DataFrame) -> None:
    """Use the LLM to generate and execute code."""
    from modules.nl_query import ask  # noqa: E402 – imports ollama

    question = st.text_area(
        "Ask a question about your data",
        placeholder="e.g. What are the top 5 rows by Revenue?",
        key="nlq_question",
    )

    col1, col2 = st.columns([3, 1])
    model = col2.text_input("Ollama model", value="mistral", key="nlq_model")

    if col1.button("🚀  Ask", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question.")
            return
        with st.spinner("Thinking…"):
            out = ask(df, question, model=model)

        if out["success"]:
            st.markdown("#### Generated Code")
            st.code(out["code"], language="python")
            st.markdown("#### Result")
            result = out["result"]
            if isinstance(result, pd.DataFrame):
                st.dataframe(result, use_container_width=True)
            elif isinstance(result, pd.Series):
                st.dataframe(result.to_frame(), use_container_width=True)
            else:
                st.write(result)
        else:
            st.error(f"Query failed: {out['error']}")
            if out.get("code"):
                st.markdown("#### Generated Code (failed)")
                st.code(out["code"], language="python")


def _nlq_manual_mode(df: pd.DataFrame) -> None:
    """Let the user write and execute their own Pandas code."""
    st.markdown("Write Pandas code below. The DataFrame is available as `df`. "
                "Store your answer in a variable called `result`.")

    code = st.text_area(
        "Python code",
        value="result = df.describe()",
        height=200,
        key="nlq_manual_code",
    )

    if st.button("▶️  Run Code", type="primary", use_container_width=True):
        with st.spinner("Executing…"):
            out = execute_generated_code(code, df)

        if out["success"]:
            st.markdown("#### Result")
            result = out["result"]
            if isinstance(result, pd.DataFrame):
                st.dataframe(result, use_container_width=True)
            elif isinstance(result, pd.Series):
                st.dataframe(result.to_frame(), use_container_width=True)
            else:
                st.write(result)
        else:
            st.error(f"Execution failed: {out['error']}")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Report Generator
# ═══════════════════════════════════════════════════════════════════════════
def _page_report() -> None:
    st.markdown("# 📄 Report Generator")
    st.markdown("Generate a professional PDF report from your analysis session.")

    if "df" not in st.session_state:
        st.warning("⬅️  Upload a dataset in the sidebar to begin.")
        return

    df = st.session_state["df"]
    summary = st.session_state.get("data_summary", {})

    # ── Report options ─────────────────────────────────────────────────
    st.markdown("### Report Settings")
    col1, col2 = st.columns(2)
    title = col1.text_input("Report title", "Data Analysis Report", key="rpt_title")
    author = col2.text_input("Author", "AI Data Platform", key="rpt_author")
    description = st.text_area(
        "Description (optional)",
        placeholder="A brief intro paragraph for the report…",
        key="rpt_desc",
    )

    # ── Section toggles ───────────────────────────────────────────────
    st.markdown("### Include Sections")
    inc_overview = st.checkbox("Dataset Overview", value=True, key="rpt_overview")
    inc_eda = st.checkbox(
        "EDA Statistics",
        value="eda_results" in st.session_state,
        disabled="eda_results" not in st.session_state,
        key="rpt_eda",
    )
    inc_ml = st.checkbox(
        "ML Model Comparison",
        value="ml_results" in st.session_state,
        disabled="ml_results" not in st.session_state,
        key="rpt_ml",
    )

    ai_summary = st.text_area(
        "AI Summary (paste or type)",
        placeholder="Paste an LLM-generated narrative here…",
        key="rpt_ai_summary",
    )

    # ── Generate ───────────────────────────────────────────────────────
    if st.button("📥  Generate PDF", type="primary", use_container_width=True):
        report_data = _build_report_data(
            df, summary, title, author, description,
            ai_summary if ai_summary.strip() else None,
            inc_overview, inc_eda, inc_ml,
        )

        with st.spinner("Generating PDF…"):
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf"
            ) as tmp:
                path = generate_report(report_data, tmp.name)

            with open(path, "rb") as f:
                pdf_bytes = f.read()

        st.success("✅ Report generated!")
        st.download_button(
            label="⬇️  Download PDF",
            data=pdf_bytes,
            file_name="analysis_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


def _build_report_data(
    df: pd.DataFrame,
    summary: dict,
    title: str,
    author: str,
    description: str | None,
    ai_summary: str | None,
    inc_overview: bool,
    inc_eda: bool,
    inc_ml: bool,
) -> dict:
    """Assemble the report data dictionary from session state."""
    data: dict = {
        "title": title,
        "author": author,
    }
    if description:
        data["description"] = description

    if inc_overview:
        data["dataset_overview"] = {
            "filename": st.session_state.get("uploaded_name", "N/A"),
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

    if inc_eda and "eda_results" in st.session_state:
        data["eda_summary"] = st.session_state["eda_results"]

    if inc_ml and "ml_results" in st.session_state:
        data["ml_comparison"] = st.session_state["ml_results"]

    if ai_summary:
        data["ai_summary"] = ai_summary

    return data


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    page = _render_sidebar()

    if page == "eda":
        _page_eda()
    elif page == "ml":
        _page_ml()
    elif page == "nlq":
        _page_nlq()
    elif page == "report":
        _page_report()


if __name__ == "__main__":
    main()
