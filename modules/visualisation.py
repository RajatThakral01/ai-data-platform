import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import BytesIO

# ---------------------------------------------------------------------------
# Core Helpers
# ---------------------------------------------------------------------------
def detect_dataset_type(df: pd.DataFrame) -> str:
    """Automatically classifies the dataset type."""
    cols = [str(c).lower() for c in df.columns]
    
    # 1. Timeseries
    if any(k in c for c in cols for k in ['date', 'time', 'year', 'month']):
        return 'timeseries'
        
    target = st.session_state.get('ml_target')
    if not target and 'ml_results' in st.session_state:
        target = st.session_state.get('ml_results', {}).get('target_col')

    if target and target in df.columns:
        n_unique = df[target].nunique()
        is_num = pd.api.types.is_numeric_dtype(df[target])
        
        # 2. Classification
        if n_unique <= 2:
            return 'classification'
            
        # 3. Regression
        if is_num and n_unique > 2:
            return 'regression'
            
    # 4. Categorical
    cat_cols = df.select_dtypes(include=['object', 'category']).columns
    if len(df.columns) > 0 and (len(cat_cols) / len(df.columns)) > 0.6:
        return 'categorical'
        
    # 5. General
    return 'general'

def _save_chart_for_report(key: str, fig) -> None:
    import plotly.io as pio
    if 'viz_charts' not in st.session_state:
        st.session_state['viz_charts'] = {}
    st.session_state['viz_charts'][key] = pio.to_json(fig)

# ---------------------------------------------------------------------------
# KPI Cards Row
# ---------------------------------------------------------------------------
def _render_kpi_cards(df: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Records", f"{len(df):,}")
    c2.metric("Numeric Columns", len(df.select_dtypes(include='number').columns))
    c3.metric("Categorical Columns", len(df.select_dtypes(include=['object', 'category']).columns))
    
    total_cells = df.size
    missing_cells = df.isna().sum().sum()
    pct_missing = (missing_cells / total_cells) * 100 if total_cells > 0 else 0
    c4.metric("Data Completeness %", f"{100 - pct_missing:.1f}%")

# ---------------------------------------------------------------------------
# Smart Auto Charts
# ---------------------------------------------------------------------------
def _render_auto_charts(df: pd.DataFrame, ds_type: str) -> None:
    st.markdown("### 📈 Smart Auto Charts")
    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    c1, c2 = st.columns(2)
    
    # Always show: Top numeric column distribution (Histogram)
    with c1:
        if num_cols:
            top_num = df[num_cols].nunique().idxmax()
            fig_hist = px.histogram(df, x=top_num, template='plotly_dark', title=f"Distribution of {top_num}")
            st.plotly_chart(fig_hist, use_container_width=True)
            _save_chart_for_report("hist", fig_hist)
            
    # Always show: Correlation heatmap
    with c2:
        if len(num_cols) >= 2:
            corr = df[num_cols].corr()
            fig_corr = px.imshow(corr, text_auto=True, template='plotly_dark', title="Numeric Correlation Heatmap")
            st.plotly_chart(fig_corr, use_container_width=True)
            _save_chart_for_report("corr", fig_corr)

    # Type specific charts
    if ds_type == 'timeseries':
        date_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['date', 'time', 'year', 'month'])]
        if date_cols and num_cols:
            d_col = date_cols[0]
            n_col = df[num_cols].nunique().idxmax()
            
            c3, c4 = st.columns(2)
            with c3:
                fig_line = px.line(df.sort_values(d_col), x=d_col, y=n_col, template='plotly_dark', title=f"{n_col} over Time")
                st.plotly_chart(fig_line, use_container_width=True)
                _save_chart_for_report("ts_line", fig_line)
            with c4:
                try:
                    # Attempt group by
                    avg_df = df.groupby(d_col)[n_col].mean().reset_index()
                    fig_bar = px.bar(avg_df, x=d_col, y=n_col, template='plotly_dark', title=f"Average {n_col} by {d_col}")
                    st.plotly_chart(fig_bar, use_container_width=True)
                    _save_chart_for_report("ts_bar", fig_bar)
                except Exception:
                    pass

    elif ds_type == 'classification':
        target = st.session_state.get('ml_target')
        if not target and 'ml_results' in st.session_state:
            target = st.session_state.get('ml_results', {}).get('target_col')
            
        if target and target in df.columns:
            c3, c4 = st.columns(2)
            with c3:
                val_counts = df[target].value_counts().reset_index()
                val_counts.columns = [target, 'Count']
                fig_bar = px.bar(val_counts, x=target, y='Count', template='plotly_dark', title=f"{target} Value Counts")
                st.plotly_chart(fig_bar, use_container_width=True)
                _save_chart_for_report("clf_bar", fig_bar)
                
                fig_pie = px.pie(val_counts, names=target, values='Count', template='plotly_dark', title=f"{target} Distribution")
                st.plotly_chart(fig_pie, use_container_width=True)
                _save_chart_for_report("clf_pie", fig_pie)
                
            with c4:
                cat_f = [c for c in cat_cols if c != target]
                if cat_f:
                    top_cat = df[cat_f].nunique().idxmax()
                    cross = pd.crosstab(df[top_cat], df[target]).reset_index()
                    melted = cross.melt(id_vars=top_cat, value_vars=cross.columns[1:])
                    fig_stack = px.bar(melted, x=top_cat, y='value', color=target, barmode='group', template='plotly_dark', title=f"{top_cat} by {target}")
                    st.plotly_chart(fig_stack, use_container_width=True)
                    _save_chart_for_report("clf_stack", fig_stack)

    elif ds_type == 'regression':
        target = st.session_state.get('ml_target')
        if target and target in df.columns and pd.api.types.is_numeric_dtype(df[target]):
            num_f = [c for c in num_cols if c != target]
            if num_f:
                corr_with_target = df[num_f].corrwith(df[target]).abs()
                if not corr_with_target.isna().all():
                    top_corr = corr_with_target.idxmax()
                    c3, c4 = st.columns(2)
                    with c3:
                        fig_scatter = px.scatter(df, x=top_corr, y=target, template='plotly_dark', title=f"{top_corr} vs {target}")
                        st.plotly_chart(fig_scatter, use_container_width=True)
                        _save_chart_for_report("reg_scatter", fig_scatter)
                        
                    with c4:
                        if cat_cols:
                            top_cat = df[cat_cols].nunique().idxmin()
                            fig_box = px.box(df, x=top_cat, y=target, template='plotly_dark', title=f"{target} by {top_cat}")
                            st.plotly_chart(fig_box, use_container_width=True)
                            _save_chart_for_report("reg_box", fig_box)

    elif ds_type == 'categorical':
        if len(cat_cols) >= 1:
            c3, c4 = st.columns(2)
            top_cat = df[cat_cols].nunique().idxmax()
            with c3:
                counts = df[top_cat].value_counts().nlargest(10).reset_index()
                counts.columns = [top_cat, 'Count']
                fig_hbar = px.bar(counts, x='Count', y=top_cat, orientation='h', template='plotly_dark', title=f"Top 10 {top_cat}")
                st.plotly_chart(fig_hbar, use_container_width=True)
                _save_chart_for_report("cat_hbar", fig_hbar)
                
            with c4:
                if len(cat_cols) >= 2:
                    cat2 = cat_cols[1] if cat_cols[0] == top_cat else cat_cols[0]
                    top_c1 = df[top_cat].value_counts().nlargest(5).index
                    top_c2 = df[cat2].value_counts().nlargest(5).index
                    subset = df[df[top_cat].isin(top_c1) & df[cat2].isin(top_c2)]
                    cross = pd.crosstab(subset[top_cat], subset[cat2]).reset_index()
                    melted = cross.melt(id_vars=top_cat, value_vars=cross.columns[1:])
                    fig_grp = px.bar(melted, x=top_cat, y='value', color=cat2, barmode='group', template='plotly_dark', title=f"{top_cat} & {cat2}")
                    st.plotly_chart(fig_grp, use_container_width=True)
                    _save_chart_for_report("cat_grp", fig_grp)


# ---------------------------------------------------------------------------
# ML Results Visualisation
# ---------------------------------------------------------------------------
def _render_ml_results(ml_results: dict) -> None:
    st.markdown("### 🤖 ML Performance")
    c1, c2 = st.columns(2)
    
    with c1:
        models = []
        scores = []
        task_type = ml_results.get("task_type")
        metric_name = "Accuracy" if task_type == "classification" else "R²"
        metric_key = "accuracy" if task_type == "classification" else "r2"
        
        for r in ml_results.get('results', []):
            models.append(r['model'])
            scores.append(r.get('metrics', {}).get(metric_key, 0))
            
        if models:
            res_df = pd.DataFrame({"Model": models, metric_name: scores})
            fig_comp = px.bar(res_df, x="Model", y=metric_name, template='plotly_dark', title="Model Comparison")
            st.plotly_chart(fig_comp, use_container_width=True)
            _save_chart_for_report("ml_comp", fig_comp)
            
    with c2:
        if task_type == "classification":
            cm = ml_results.get("confusion_matrix")
            labels = ml_results.get("class_labels")
            if cm is not None and len(cm) > 0:
                fig_cm = px.imshow(cm, x=labels, y=labels, text_auto=True, template='plotly_dark', 
                                  title="Confusion Matrix (Best Model)")
                st.plotly_chart(fig_cm, use_container_width=True)
                _save_chart_for_report("ml_cm", fig_cm)
        elif task_type == "regression":
            best_res = next((r for r in ml_results.get('results', []) if r['model'] == ml_results.get('best_model')), None)
            if best_res and 'y_test' in ml_results and 'y_pred' in best_res:
                y_test = ml_results['y_test']
                y_pred = best_res['y_pred']
                if len(y_test) > 0 and len(y_pred) > 0:
                    fig_act = px.scatter(x=y_test, y=y_pred, template='plotly_dark', 
                                        title="Actual vs Predicted", labels={'x': 'Actual', 'y': 'Predicted'})
                    fig_act.add_trace(go.Scatter(x=[min(y_test), max(y_test)], y=[min(y_test), max(y_test)], 
                                                mode='lines', name='Perfect', line=dict(dash='dash', color='red')))
                    st.plotly_chart(fig_act, use_container_width=True)
                    _save_chart_for_report("ml_act", fig_act)
    
    # Feature Importance for Random Forest
    feat_imp = ml_results.get("feature_importance")
    if feat_imp and len(feat_imp) > 0:
        imp_df = pd.DataFrame(list(feat_imp.items()), columns=['Feature', 'Importance'])
        imp_df = imp_df.sort_values('Importance', ascending=True).tail(10)
        fig_imp = px.bar(imp_df, x='Importance', y='Feature', orientation='h', template='plotly_dark', 
                        title="Feature Importance")
        st.plotly_chart(fig_imp, use_container_width=True)
        _save_chart_for_report("ml_imp", fig_imp)

# ---------------------------------------------------------------------------
# Business Insights
# ---------------------------------------------------------------------------
def _generate_business_insights(df: pd.DataFrame) -> None:
    st.markdown("### 🧠 AI Business Insights")
    if st.button("🧠 Generate Business Insights", type="primary"):
        with st.spinner("Analyzing findings and contacting LLM..."):
            try:
                from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL
                
                num_cols = df.select_dtypes(include='number').columns
                findings = []
                findings.append(f"Total rows: {len(df)}")
                
                if len(num_cols) > 0:
                    top_num = df[num_cols].nunique().idxmax()
                    findings.append(f"Highest variance numeric column is {top_num} with max value {df[top_num].max()}")
                    if len(num_cols) >= 2:
                        corr = df[num_cols].corr().unstack().sort_values(ascending=False).drop_duplicates()
                        corr = corr[corr < 0.99]
                        if not corr.empty:
                            k1, k2 = corr.index[0]
                            v = corr.iloc[0]
                            findings.append(f"Strongest correlation is between {k1} and {k2} ({v:.2f})")
                            
                cat_cols = df.select_dtypes(include=['object', 'category']).columns
                if len(cat_cols) > 0:
                    top_cat = cat_cols[0]
                    count = df[top_cat].value_counts().iloc[0]
                    v_name = df[top_cat].value_counts().index[0]
                    findings.append(f"Most frequent {top_cat} is {v_name} ({count} occurrences)")
                    
                prompt = (
                    "You are a business analyst. Based on these data findings, write exactly 5 bullet point "
                    "business insights that a non-technical manager would understand. Each insight must start "
                    "with an emoji and include a specific number from the data.\n\n"
                    f"findings: {findings}"
                )
                
                text, _ = get_llm_response(
                    prompt, 
                    temperature=0.4, 
                    max_tokens=300, 
                    groq_model=GROQ_MODEL_SMALL
                )
                
                st.session_state['viz_insights'] = text
            except Exception as e:
                st.error(f"Failed to generate insights: {e}")

    if 'viz_insights' in st.session_state:
        st.info(st.session_state['viz_insights'])

# ---------------------------------------------------------------------------
# Custom Chart Builder
# ---------------------------------------------------------------------------
def _render_custom_builder(df: pd.DataFrame) -> None:
    with st.expander("🛠️ Build Custom Chart"):
        c1, c2, c3, c4 = st.columns(4)
        x_axis = c1.selectbox("X Axis", df.columns.tolist(), key="cust_x")
        
        num_cols = df.select_dtypes(include='number').columns.tolist()
        y_axis = c2.selectbox("Y Axis", num_cols if num_cols else df.columns.tolist(), key="cust_y")
        
        chart_type = c3.selectbox("Chart Type", ["Bar", "Line", "Scatter", "Box", "Histogram"], key="cust_t")
        
        cat_cols = ["None"] + df.select_dtypes(include=['object', 'category']).columns.tolist()
        color_by = c4.selectbox("Color By", cat_cols, key="cust_c")
        
        if st.button("Generate Chart"):
            c = None if color_by == "None" else color_by
            fig = None
            try:
                if chart_type == "Bar":
                    agg = df.groupby(x_axis)[y_axis].mean().reset_index() if not c else df.groupby([x_axis, c])[y_axis].mean().reset_index()
                    fig = px.bar(agg, x=x_axis, y=y_axis, color=c, template='plotly_dark')
                elif chart_type == "Line":
                    fig = px.line(df, x=x_axis, y=y_axis, color=c, template='plotly_dark')
                elif chart_type == "Scatter":
                    fig = px.scatter(df, x=x_axis, y=y_axis, color=c, template='plotly_dark')
                elif chart_type == "Box":
                    fig = px.box(df, x=x_axis, y=y_axis, color=c, template='plotly_dark')
                elif chart_type == "Histogram":
                    fig = px.histogram(df, x=x_axis, y=y_axis, color=c, template='plotly_dark')
                    
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    _save_chart_for_report("custom", fig)
            except Exception as e:
                st.error(f"Could not generate {chart_type} chart: {e}")

# ---------------------------------------------------------------------------
# Main Render Entry
# ---------------------------------------------------------------------------
def render_visualisation_page() -> None:
    st.markdown("# 📊 Data Insights Dashboard")
    st.markdown("Automatic visual insights and deep dives into your dataset.")

    if 'df' not in st.session_state:
        st.warning("⬅️ Upload a dataset in the sidebar to begin.")
        return

    df = st.session_state['df']
    
    # Step 1: Detect Type
    ds_type = detect_dataset_type(df)
    st.caption(f"Detected Dataset Type: **{ds_type.title()}**")
    
    # Step 2: KPI Cards Row
    _render_kpi_cards(df)
    st.divider()
    
    # Step 3: Smart Auto Charts
    _render_auto_charts(df, ds_type)
    st.divider()
    
    # Step 4: ML Results
    if 'ml_results' in st.session_state:
        _render_ml_results(st.session_state['ml_results'])
        st.divider()
        
    # Step 5: AI Business Insights
    _generate_business_insights(df)
    st.divider()
    
    # Step 6: Custom Chart Builder
    _render_custom_builder(df)
    
    # Step 7: Export to Report (Automatically handled via _save_chart_for_report)
    if st.button("📑 Add Insights to Report", type="secondary"):
        st.success("Charts saved to session! The Report Generator can now include them.")
