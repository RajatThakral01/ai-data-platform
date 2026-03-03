import re

# ----------------- Patch modules/data_cleaner.py -----------------
with open("modules/data_cleaner.py", "r") as f:
    cleaner_code = f.read()

# Make sure we don't add it twice
if "def auto_clean_data" not in cleaner_code:
    new_imports = "from typing import Any\nimport warnings\n"
    if "from typing import Any" not in cleaner_code:
        cleaner_code = cleaner_code.replace("import pandas as pd", new_imports + "import pandas as pd")
    
    cleaner_code += '''

# ---------------------------------------------------------------------------
# Auto Clean
# ---------------------------------------------------------------------------
def auto_clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Automatically clean the DataFrame for ML processing.
    Returns the cleaned DataFrame and a report dictionary detailing all steps.
    """
    cleaned = df.copy()
    report: dict[str, Any] = {}

    # 1. Drop unique identifiers
    id_cols = [col for col in cleaned.columns if len(cleaned) > 0 and cleaned[col].nunique() == len(cleaned)]
    if id_cols:
        cleaned.drop(columns=id_cols, inplace=True)
        report["dropped_id_cols"] = id_cols

    # 2. Drop geographical columns
    geo_keywords = ['lat', 'long', 'zip', 'country', 'state', 'city', 'latitude', 'longitude', 'postal']
    geo_cols = [col for col in cleaned.columns if any(k in str(col).lower() for k in geo_keywords)]
    geo_cols = list(set(geo_cols))
    if geo_cols:
        cleaned.drop(columns=geo_cols, inplace=True)
        report["dropped_geo_cols"] = geo_cols

    # 3. Drop columns with > 70% missing
    threshold = 0.7 * len(cleaned)
    high_missing_cols = [col for col in cleaned.columns if cleaned[col].isna().sum() > threshold]
    if high_missing_cols:
        cleaned.drop(columns=high_missing_cols, inplace=True)
        report["dropped_missing_cols"] = high_missing_cols

    # 4. Fill missing
    filled_missing = {}
    for col in cleaned.columns:
        missing_count = int(cleaned[col].isna().sum())
        if missing_count > 0:
            if pd.api.types.is_numeric_dtype(cleaned[col]):
                val = float(cleaned[col].median()) if pd.notna(cleaned[col].median()) else 0.0
                strategy = "median"
            else:
                mode_val = cleaned[col].mode()
                val = mode_val.iloc[0] if not mode_val.empty else "Unknown"
                strategy = "mode"
            cleaned[col] = cleaned[col].fillna(val)
            filled_missing[col] = {"count": missing_count, "strategy": strategy, "value": str(val)}
    if filled_missing:
        report["filled_missing"] = filled_missing

    # 5. Remove duplicates
    dup_count = int(cleaned.duplicated().sum())
    if dup_count > 0:
        cleaned.drop_duplicates(inplace=True)
        cleaned.reset_index(drop=True, inplace=True)
        report["removed_duplicates"] = dup_count

    # 6. Cap outliers
    capped_outliers = {}
    num_cols = cleaned.select_dtypes(include="number").columns
    for col in num_cols:
        q1 = cleaned[col].quantile(0.25)
        q3 = cleaned[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outliers_mask = (cleaned[col] < lower) | (cleaned[col] > upper)
        outliers_count = int(outliers_mask.sum())
        if outliers_count > 0:
            cleaned[col] = cleaned[col].clip(lower=lower, upper=upper)
            capped_outliers[col] = outliers_count
    if capped_outliers:
        report["capped_outliers"] = capped_outliers

    # 7. Label Encoding
    encoded_cols = []
    try:
        from sklearn.preprocessing import LabelEncoder
        for col in cleaned.select_dtypes(include=['object', 'category']).columns:
            cleaned[col] = LabelEncoder().fit_transform(cleaned[col].astype(str))
            encoded_cols.append(col)
    except ImportError:
        for col in cleaned.select_dtypes(include=['object', 'category']).columns:
            cleaned[col] = pd.factorize(cleaned[col])[0]
            encoded_cols.append(col)
    if encoded_cols:
        report["encoded_cols"] = encoded_cols

    return cleaned, report
'''
    with open("modules/data_cleaner.py", "w") as f:
        f.write(cleaner_code)

# ----------------- Patch app.py -----------------
with open("app.py", "r") as f:
    app_code = f.read()

app_code = app_code.replace('''page = st.radio(
            "Navigate",
            list(_PAGES.keys()),
            label_visibility="collapsed",
        )''', '''page = st.radio(
            "Navigate",
            list(_PAGES.keys()),
            label_visibility="collapsed",
            key="nav_radio",
        )''')


page_clean_match = re.search(r'def _page_clean\(\) -> None:.*?# ═══════════════════════════════════════════════════════════════════════════\n# PAGE: ML Recommender', app_code, flags=re.DOTALL)
if page_clean_match:
    original_page_clean = page_clean_match.group(0)
    
    new_page_clean = '''def _page_clean() -> None:
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
# PAGE: ML Recommender'''
    
    app_code = app_code.replace(original_page_clean, new_page_clean)
    with open("app.py", "w") as f:
        f.write(app_code)
