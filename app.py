"""
app.py – Streamlit multi-page app for the AI Data Platform.

Run with:
    streamlit run app.py

Pages:
    1. Smart EDA          – automated exploratory data analysis
    2. Data Cleaning      – interactive data cleaning & prep
    3. ML Recommender     – train & compare ML models
    4. NL Query Engine    – ask questions in plain English
    5. Report Generator   – export a professional PDF report
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Force load .env from project root
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

import tempfile

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
from modules.visualisation import render_visualisation_page  # noqa: E402
from modules.visualisation import detect_dataset_type, _render_auto_charts, _render_ml_results, _generate_business_insights, _render_custom_builder

# ── Page registry ──────────────────────────────────────────────────────────
_PAGES = {
    "📊  Smart EDA": "eda",
    "🧹  Data Cleaning": "clean",
    "🤖  ML Recommender": "ml",
    "📊  Data Insights": "viz",
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
            key="nav_radio",
        )

        st.divider()

        # ── LLM Priority Chain (status indicators) ────────────────────
        st.markdown("**🧠 AI Priority**")
        st.caption("➀ **Groq** (llama-3.3-70b) — fastest")
        st.caption("➁ **Gemini** (2.0-flash) — fallback")
        st.caption("➂ **Ollama** (mistral) — local")

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
        for key in ("eda_results", "ml_results", "nlq_history",
                     "df_cleaning_wip", "df_cleaned", "clean_ai_suggestions"):
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
# PAGE: Data Cleaning
# ═══════════════════════════════════════════════════════════════════════════
def _page_clean() -> None:
    st.markdown("# 🧹 Data Cleaning")
    st.markdown("Clean and prepare your data before modelling.")

    if "df" not in st.session_state:
        st.warning("⬅️  Upload a dataset in the sidebar to begin.")
        return

    from modules.data_cleaner import (
        missing_value_summary, fill_missing,
        detect_duplicates, remove_duplicates,
        detect_outliers_iqr, remove_outliers, cap_outliers,
        suggest_type_fixes, fix_column_type,
        drop_columns, build_before_after_summary,
        get_ai_cleaning_suggestions, auto_clean_data
    )

    original_df = st.session_state["df"]
    # Work on a copy (or the already-in-progress cleaned copy)
    if "df_cleaning_wip" not in st.session_state:
        st.session_state["df_cleaning_wip"] = original_df.copy()
    df = st.session_state["df_cleaning_wip"]

    # ── 0. Auto Clean & Prepare for ML ─────────────────────────────────
    if st.button("🚀 Auto Clean & Prepare for ML", type="primary", use_container_width=True):
        with st.spinner("Auto-cleaning data..."):
            cleaned_df, report = auto_clean_data(original_df)
            st.session_state["df"] = cleaned_df.copy()
            st.session_state["df_cleaned"] = True
            st.session_state["df_cleaning_wip"] = cleaned_df.copy()
            st.session_state["auto_clean_report"] = report

            st.session_state.pop("eda_results", None)
            st.session_state.pop("ml_results", None)
        st.rerun()

    if st.session_state.get("df_cleaned") and "auto_clean_report" in st.session_state:
        st.success("✅ **Data is ready for ML training!**")
        def goto_ml():
            st.session_state["nav_radio"] = "🤖  ML Recommender"

        st.button("➡️ Go to ML Recommender", on_click=goto_ml, type="primary")

        report = st.session_state["auto_clean_report"]
        st.markdown("### 📝 Auto Clean Report")
        if report.get("dropped_id_cols"):
            st.markdown(f"- **Dropped {len(report['dropped_id_cols'])} ID columns** ({', '.join(report['dropped_id_cols'])}) — reason: unique identifiers add no predictive value")
        if report.get("dropped_geo_cols"):
            st.markdown(f"- **Dropped {len(report['dropped_geo_cols'])} Geo columns** ({', '.join(report['dropped_geo_cols'])}) — reason: completely irrelevant for ML")
        if report.get("dropped_missing_cols"):
            st.markdown(f"- **Dropped {len(report['dropped_missing_cols'])} columns** ({', '.join(report['dropped_missing_cols'])}) — reason: > 70% missing values")
        if report.get("filled_missing"):
            for col, info in report["filled_missing"].items():
                st.markdown(f"- **Filled {info['count']} missing values in {col}** with {info['strategy']} ({info['value']}) — reason: preserve data while handling nulls")
        if report.get("removed_duplicates"):
            st.markdown(f"- **Removed {report['removed_duplicates']} duplicate rows** — reason: prevent data leakage and bias")
        if report.get("capped_outliers"):
            cols = list(report["capped_outliers"].keys())
            st.markdown(f"- **Capped outliers in {len(cols)} column(s)** ({', '.join(cols)}) — reason: extreme values detected, capped to preserve data integrity")
        if report.get("encoded_cols"):
            st.markdown(f"- **Encoded {len(report['encoded_cols'])} categorical columns to numeric** — reason: ML models require numeric input")

        st.markdown("#### Before vs After")
        summary_m = build_before_after_summary(original_df, st.session_state["df_cleaning_wip"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", summary_m["cleaned_rows"], delta=-summary_m["rows_removed"])
        c2.metric("Missing Values", summary_m["cleaned_missing"], delta=-(summary_m["original_missing"] - summary_m["cleaned_missing"]))
        c3.metric("Columns", summary_m["cleaned_cols"], delta=-summary_m["cols_removed"])

        st.divider()

    with st.expander("Advanced Manual Controls", expanded=False):
        # ── 1. AI Cleaning Suggestions ─────────────────────────────────────
        st.markdown("### 0️⃣ AI Cleaning Suggestions")
        if st.button("Get AI Recommendations", key="clean_ai_btn"):
            with st.spinner("Asking AI for cleaning advice…"):
                eda = st.session_state.get("eda_results")
                suggestions, error = get_ai_cleaning_suggestions(df, eda_summary=eda)
            if suggestions:
                st.session_state["clean_ai_suggestions"] = suggestions
            elif error:
                st.error(f"⚠️ AI suggestions failed: {error}")
            else:
                st.warning("AI returned an empty response. Try again.")

        if "clean_ai_suggestions" in st.session_state:
            st.markdown(st.session_state["clean_ai_suggestions"])

        # ── 1. Missing Value Handling ──────────────────────────────────────
        st.markdown("### 1️⃣ Missing Value Handling")
        mv = missing_value_summary(df)
        if mv.empty:
            st.success("No missing values! ✅")
        else:
            st.dataframe(mv, use_container_width=True, hide_index=True)
            col_to_fix = st.selectbox(
                "Column to fix",
                mv["Column"].tolist(),
                key="clean_mv_col",
            )
            strategy = st.selectbox(
                "Strategy",
                ["drop", "mean", "median", "mode", "custom"],
                key="clean_mv_strat",
            )
            custom_val = None
            if strategy == "custom":
                custom_val = st.text_input("Custom fill value", key="clean_mv_custom")

            if st.button("Apply Missing Value Fix", key="clean_mv_btn"):
                df = fill_missing(df, col_to_fix, strategy, custom_val)
                st.session_state["df_cleaning_wip"] = df
                st.success(f"Applied **{strategy}** to `{col_to_fix}`.")
                st.rerun()

        st.divider()

        # ── 2. Duplicate Removal ───────────────────────────────────────────
        st.markdown("### 2️⃣ Duplicate Removal")
        dup_count = detect_duplicates(df)
        if dup_count == 0:
            st.success("No duplicates found! ✅")
        else:
            st.warning(f"Found **{dup_count}** duplicate rows.")
            if st.button("Remove Duplicates", key="clean_dup_btn"):
                df = remove_duplicates(df)
                st.session_state["df_cleaning_wip"] = df
                st.success(f"Removed {dup_count} duplicates.")
                st.rerun()

        st.divider()

        # ── 3. Outlier Removal ─────────────────────────────────────────────
        st.markdown("### 3️⃣ Outlier Detection & Handling")
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if not num_cols:
            st.info("No numeric columns for outlier analysis.")
        else:
            out_col = st.selectbox("Numeric column", num_cols, key="clean_out_col")
            info = detect_outliers_iqr(df, out_col)
            if info["count"] == 0:
                st.success(f"No outliers in `{out_col}`. ✅")
            else:
                st.warning(
                    f"**{info['count']}** outliers in `{out_col}` "
                    f"(bounds: {info['lower_bound']} – {info['upper_bound']})"
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Remove Outliers", key="clean_out_rm"):
                        df = remove_outliers(df, out_col)
                        st.session_state["df_cleaning_wip"] = df
                        st.success(f"Removed {info['count']} outlier rows.")
                        st.rerun()
                with c2:
                    if st.button("Cap Outliers", key="clean_out_cap"):
                        df = cap_outliers(df, out_col)
                        st.session_state["df_cleaning_wip"] = df
                        st.success("Outliers capped to IQR bounds.")
                        st.rerun()

        st.divider()

        # ── 4. Data Type Fixing ────────────────────────────────────────────
        st.markdown("### 4️⃣ Data Type Fixing")
        fixes = suggest_type_fixes(df)
        if not fixes:
            st.success("All column types look correct! ✅")
        else:
            for fix in fixes:
                col_name = fix["column"]
                st.markdown(
                    f"**`{col_name}`**: {fix['current']} → {fix['suggested']}"
                )
                target = "numeric" if "numeric" in fix["suggested"] else "datetime"
                if st.button(f"Convert `{col_name}`", key=f"clean_type_{col_name}"):
                    df = fix_column_type(df, col_name, target)
                    st.session_state["df_cleaning_wip"] = df
                    st.success(f"Converted `{col_name}` to {target}.")
                    st.rerun()

        st.divider()

        # ── 5. Column Dropping ─────────────────────────────────────────────
        st.markdown("### 5️⃣ Drop Columns")
        cols_to_drop = st.multiselect(
            "Select columns to drop",
            df.columns.tolist(),
            key="clean_drop_cols",
        )
        if cols_to_drop and st.button("Drop Selected Columns", key="clean_drop_btn"):
            df = drop_columns(df, cols_to_drop)
            st.session_state["df_cleaning_wip"] = df
            st.success(f"Dropped {len(cols_to_drop)} column(s).")
            st.rerun()

        st.divider()

        # ── 6. Before / After Preview ──────────────────────────────────────
        st.markdown("### 📊 Before / After Summary")
        summary = build_before_after_summary(original_df, df)
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", summary["cleaned_rows"], delta=-summary["rows_removed"])
        c2.metric("Missing Values", summary["cleaned_missing"],
                  delta=-(summary["original_missing"] - summary["cleaned_missing"]))
        c3.metric("Duplicates", summary["cleaned_duplicates"],
                  delta=-(summary["original_duplicates"] - summary["cleaned_duplicates"]))

        c4, c5 = st.columns(2)
        c4.metric("Original Columns", summary["original_cols"])
        c5.metric("Cleaned Columns", summary["cleaned_cols"],
                  delta=-summary["cols_removed"])

        st.divider()

        # ── 7. Finalize & Download ─────────────────────────────────────────
        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("✅  Save Cleaned Data", type="primary", use_container_width=True,
                          key="clean_save_btn"):
                st.session_state["df"] = df.copy()
                st.session_state["df_cleaned"] = True
                # Invalidate previous EDA / ML so they re-run on cleaned data
                st.session_state.pop("eda_results", None)
                st.session_state.pop("ml_results", None)
                st.success(
                    "Cleaned dataset saved! "
                    "ML Recommender will now use the cleaned data."
                )

        with col_b:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️  Download CSV",
                data=csv,
                file_name="cleaned_data.csv",
                mime="text/csv",
                use_container_width=True,
                key="clean_dl_btn",
            )

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
    if st.session_state.get("df_cleaned"):
        st.info("✅ Using **cleaned** dataset.")

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

    # Highlight the best model row with dark green + white bold text
    best_model = result.get("best_model")

    def _style_best_row(row):
        if row["Model"] == best_model:
            return [
                "background-color: #1a7a3c; color: white; font-weight: bold"
            ] * len(row)
        return [""] * len(row)

    st.dataframe(
        res_df.style.apply(_style_best_row, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    # ── Class labels ───────────────────────────────────────────────────
    if result.get("class_labels"):
        st.markdown(f"**Class labels:** {', '.join(str(l) for l in result['class_labels'])}")

    # ── AI Summary (one-shot LLM call) ─────────────────────────────────
    _ml_ai_summary(result)


def _ml_ai_summary(result: dict) -> None:
    """Generate a one-shot LLM summary of ML results (single API call)."""

    # Only generate once per result set (cache in session state)
    cache_key = f"ml_summary_{result.get('best_model', '')}_{result.get('task_type', '')}"
    if cache_key in st.session_state:
        summary_data = st.session_state[cache_key]
        st.markdown("### 🧠 AI Analysis")
        st.info(summary_data["text"])
        if summary_data.get("warning"):
            st.warning(summary_data["warning"])
        return

    if st.button("🧠  Generate AI Summary", key="ml_ai_btn", use_container_width=True):
        # Build a compact text summary for the LLM prompt
        task = result["task_type"]
        best = result.get("best_model", "N/A")
        lines = [f"Task: {task}, Best model: {best}"]
        for r in sorted(result.get("results", []), key=lambda x: x.get("rank") or 999):
            m = r.get("metrics", {})
            metrics_str = ", ".join(f"{k}={v}" for k, v in m.items())
            lines.append(f"  {r.get('rank', '–')}. {r['model']}: {metrics_str}")

        prompt = (
            "Role: data scientist. 2-3 sentences: which model won, why (cite metrics), "
            "one recommendation.\n\n" + "\n".join(lines)
        )

        with st.spinner("Generating AI summary…"):
            try:
                from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL
                summary_text, meta = get_llm_response(
                    prompt,
                    temperature=0.4,
                    max_tokens=300,
                    groq_model=GROQ_MODEL_SMALL,
                )
                warning = meta.get("fallback_warning")

                # Cache so we don't re-call the LLM
                st.session_state[cache_key] = {
                    "text": summary_text,
                    "warning": warning,
                    "backend_used": meta.get("backend_used"),
                    "model_used": meta.get("model_used"),
                }

                st.markdown("### 🧠 AI Analysis")
                st.info(summary_text)
                st.caption(f"✅ Generated by **{meta.get('backend_used', '').title()}** ({meta.get('model_used', 'N/A')})")
                if warning:
                    st.warning(warning)
            except Exception as exc:
                st.error(f"AI summary failed: {exc}")

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
        ["🤖 AI-powered (LLM)", "✏️ Manual code"],
        horizontal=True,
        key="nlq_mode",
    )

    if "🤖" in mode:
        _nlq_ai_mode(df)
    else:
        _nlq_manual_mode(df)


def _nlq_ai_mode(df: pd.DataFrame) -> None:
    """Use the LLM to generate and execute code."""
    from modules.nl_query import ask  # noqa: E402 – imports llm

    question = st.text_area(
        "Ask a question about your data",
        placeholder="e.g. What are the top 5 rows by Revenue?",
        key="nlq_question",
    )

    st.caption("🧠 Priority: **Groq** → Gemini → Ollama")

    if st.button("🚀  Ask", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question.")
            return
        with st.spinner("Thinking…"):
            out = ask(df, question)

        if out.get("fallback_warning"):
            st.warning(out["fallback_warning"])

        # Show which backend actually answered
        if out.get("backend_used"):
            st.caption(f"✅ Answered by **{out['backend_used'].title()}** ({out.get('model_used', 'N/A')})")

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
    inc_viz = st.checkbox(
        "Visualizations (Data Insights)",
        value="viz_charts" in st.session_state,
        disabled="viz_charts" not in st.session_state,
        key="rpt_viz",
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
            inc_overview, inc_eda, inc_ml, inc_viz,
        )
        # Pass backend config for AI-generated report sections
        report_data["llm_backend"] = st.session_state.get("llm_backend", "ollama")
        report_data["ollama_model"] = st.session_state.get("llm_model", "mistral")
        report_data["gemini_api_key"] = os.getenv("GEMINI_API_KEY")

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
    inc_viz: bool,
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

    if inc_viz and "viz_charts" in st.session_state:
        data["viz_charts"] = st.session_state["viz_charts"]

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
    elif page == "clean":
        _page_clean()
    elif page == "ml":
        _page_ml()
    elif page == "viz":
        render_visualisation_page()
    elif page == "nlq":
        _page_nlq()
    elif page == "report":
        _page_report()


if __name__ == "__main__":
    main()
