import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import json

from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL, GROQ_MODEL_LARGE
from utils import chart_config

DOMAIN_STYLES = {
  "e-commerce":  {"emoji": "🛒", "color": "#118DFF"},
  "telecom":     {"emoji": "📡", "color": "#E66C37"},
  "retail":      {"emoji": "🏪", "color": "#12239E"},
  "finance":     {"emoji": "💰", "color": "#D9B300"},
  "hr":          {"emoji": "👥", "color": "#6B007B"},
  "healthcare":  {"emoji": "🏥", "color": "#E044A7"},
  "marketing":   {"emoji": "📣", "color": "#744EC2"},
  "logistics":   {"emoji": "🚚", "color": "#D64550"},
  "other":       {"emoji": "📊", "color": "#8b949e"},
}

# ---------------------------------------------------------------------------
# Core Helpers
# ---------------------------------------------------------------------------
def _save_chart_for_report(key: str, fig) -> None:
    import plotly.io as pio
    if 'viz_charts' not in st.session_state:
        st.session_state['viz_charts'] = {}
    st.session_state['viz_charts'][key] = pio.to_json(fig)

def _get_dataset_metadata(df: pd.DataFrame) -> dict:
    """Helper to extract common metadata for LLM prompts."""
    return {
        "columns": df.columns.tolist(),
        "dtypes": [str(d) for d in df.dtypes],
        "rows": len(df),
        "missing_pct": round(df.isna().sum().sum() / df.size * 100, 2) if df.size > 0 else 0,
        "sample": df.head(5).to_dict(orient="records"),
        "numeric_cols": df.select_dtypes(include="number").columns.tolist(),
        "categorical_cols": df.select_dtypes(include=["object", "category"]).columns.tolist(),
    }

def detect_business_context(df: pd.DataFrame) -> dict | None:
    file_name = st.session_state.get("uploaded_name", "dataset")
    cache_key = f"business_context_{file_name}"
    
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    meta = _get_dataset_metadata(df)
    
    prompt = (
        f"Given this dataset with columns: {meta['columns']}\n"
        f"and sample data: {meta['sample']}\n"
        f"and basic stats: {meta['rows']} rows, dtypes: {meta['dtypes']}\n\n"
        "Answer in JSON only:\n"
        "{\n"
        "  \"domain\": \"e-commerce | telecom | retail | finance | hr | healthcare | marketing | logistics | other\",\n"
        "  \"business_entity\": \"what is one row? e.g. customer, order, employee, transaction, product\",\n"
        "  \"target_metric\": \"the most important column to optimize, e.g. Sales, Churn, Profit, Revenue\",\n"
        "  \"business_questions\": [\n"
        "    \"exact question 1 this business would want answered\",\n"
        "    \"exact question 2\",\n"
        "    \"exact question 3\", \n"
        "    \"exact question 4\",\n"
        "    \"exact question 5\"\n"
        "  ],\n"
        "  \"kpi_columns\": {\n"
        "    \"primary\": \"most important numeric column name\",\n"
        "    \"secondary\": \"second most important numeric column name\",\n"
        "    \"rate_metric\": \"column representing a rate/% if exists else null\",\n"
        "    \"volume_metric\": \"column representing count/volume if exists else null\"\n"
        "  },\n"
        "  \"avoid_columns\": [\"list of columns that are IDs, codes, indexes — not useful for charts\"]\n"
        "}"
    )
    
    try:
        text, _ = get_llm_response(prompt, temperature=0.1, max_tokens=1000, groq_model=GROQ_MODEL_LARGE, module_name="data_insights")
        text = text[text.find('{'):text.rfind('}')+1]
        ctx = json.loads(text)
        st.session_state[cache_key] = ctx
        return ctx
    except Exception:
        return None

def sanitize_chart_data(df: pd.DataFrame, x_col: str, y_col: str, 
                        c_col: str = None, agg: str = "none") -> pd.DataFrame:
    """Pre-processes and sanitizes data for charting to fix Pandas index issues."""
    plot_df = df.copy()
    
    # 1. Clean categorical X and Color columns to always be string so Plotly 
    # renders them as discrete categories instead of trying to map indices
    is_cat_x = False
    if x_col in plot_df.columns:
        if not pd.api.types.is_numeric_dtype(plot_df[x_col]) or plot_df[x_col].nunique() < 20:
            plot_df[x_col] = plot_df[x_col].astype(str)
            is_cat_x = True
            
    if c_col in plot_df.columns:
        plot_df[c_col] = plot_df[c_col].astype(str)
        
    # 2. Aggregations (must happen AFTER string cast to ensure proper grouping)
    if agg in ["sum", "mean", "count"] and y_col:
        group_cols = [x_col]
        if c_col: group_cols.append(c_col)
        
        if agg == "sum":
            plot_df = plot_df.groupby(group_cols)[y_col].sum().reset_index()
        elif agg == "mean":
            plot_df = plot_df.groupby(group_cols)[y_col].mean().reset_index()
        elif agg == "count":
            plot_df = plot_df.groupby(group_cols)[y_col].count().reset_index()
            
    if x_col in plot_df.columns:
        plot_df[x_col] = plot_df[x_col].astype(str)
            
    # 3. Truncate / Sort categorical data to prevent overcrowding
    if is_cat_x and len(plot_df) > 1:
        if y_col and y_col in plot_df.columns:
            # Sort by Y descending and take Top 15 categories max
            if not c_col: # Sorting stacked/grouped bars is complex, skip for color splits
                plot_df = plot_df.sort_values(y_col, ascending=False).head(15)
        else:
            plot_df = plot_df.head(15)

    return plot_df

# ---------------------------------------------------------------------------
# Step 1: Executive Summary
# ---------------------------------------------------------------------------
def _render_executive_summary(df: pd.DataFrame) -> None:
    # ALWAYS use original unencoded dataframe
    # Never use cleaned_df for visualizations
    original_df = st.session_state.get("df")
    if original_df is not None:
        df = original_df

    file_name = st.session_state.get("uploaded_name", "dataset")
    cache_key = f"exec_summary_{file_name}"
    
    if cache_key not in st.session_state:
        meta = _get_dataset_metadata(df)
        prompt = (
            "You are a senior business analyst. Here is a dataset: "
            f"columns={meta['columns']}, dtypes={meta['dtypes']}, "
            f"sample={meta['sample']}, key stats={meta['rows']} rows, {meta['missing_pct']}% missing. "
            "Write a 2-sentence executive summary of what this dataset is about and what is the single "
            "most important business insight visible in the data. Be specific with numbers."
        )
        try:
            text, _ = get_llm_response(prompt, max_tokens=300, groq_model=GROQ_MODEL_SMALL, module_name="data_insights")
            st.session_state[cache_key] = text
        except Exception as e:
            st.session_state[cache_key] = f"Could not generate summary: {str(e)}"
            
    with st.container(border=True):
        st.markdown("### 📋 Executive Summary")
        st.info(st.session_state[cache_key])

# ---------------------------------------------------------------------------
# Step 2: Dynamic Business KPIs
# ---------------------------------------------------------------------------
def _render_dynamic_kpis(df: pd.DataFrame) -> None:
    # ALWAYS use original unencoded dataframe
    # Never use cleaned_df for visualizations
    original_df = st.session_state.get("df")
    if original_df is not None:
        df = original_df

    file_name = st.session_state.get("uploaded_name", "dataset")
    cache_key = f"dynamic_kpis_{file_name}"
    
    context_key = f"business_context_{file_name}"
    context = st.session_state.get(context_key)
    
    if cache_key not in st.session_state:
        kpis = []
        if context and "kpi_columns" in context:
            kpi_dict = context["kpi_columns"]
            primary = kpi_dict.get("primary")
            secondary = kpi_dict.get("secondary")
            rate_o = kpi_dict.get("rate_metric")
            vol_o = kpi_dict.get("volume_metric")
            
            if primary: kpis.append({"name": f"Total {primary}", "column": primary, "calculation": "sum"})
            if secondary: kpis.append({"name": f"Total {secondary}", "column": secondary, "calculation": "sum"})
            if primary: kpis.append({"name": f"Avg {primary}", "column": primary, "calculation": "mean"})
            
            if rate_o:
                kpis.append({"name": rate_o, "column": rate_o, "calculation": "mean"})
            elif vol_o:
                kpis.append({"name": f"Total {vol_o}", "column": vol_o, "calculation": "sum"})
        else:
            meta = _get_dataset_metadata(df)
            num_cols = meta.get("numeric_cols", [])
            
            blacklist = ["id", "row", "postal", "zip", "code", "index", "key", "lat", "lon", "longitude", "latitude", "phone", "count"]
            
            valid_cols = []
            for c in num_cols:
                c_low = c.lower()
                if not any(b in c_low for b in blacklist):
                    valid_cols.append(c)
                    
            used_cols = set()
            
            # 1. Revenue / Sales
            revenue_cols = [c for c in valid_cols if any(w in c.lower() for w in ["sales", "revenue", "amount", "gmv", "income"])]
            if revenue_cols:
                col = revenue_cols[0]
                kpis.append({"name": "Total Revenue", "column": col, "calculation": "sum"})
                used_cols.add(col)
                
            # 2. Profit
            profit_cols = [c for c in valid_cols if any(w in c.lower() for w in ["profit", "margin", "earning"]) and c not in used_cols]
            if profit_cols:
                col = profit_cols[0]
                kpis.append({"name": "Total Profit", "column": col, "calculation": "sum"})
                used_cols.add(col)
                
            # 3. Rate / Score
            rate_cols = [c for c in valid_cols if any(w in c.lower() for w in ["rate", "churn", "score", "satisfaction", "pct", "percent", "ratio"]) and c not in used_cols]
            if rate_cols:
                col = rate_cols[0]
                kpis.append({"name": col, "column": col, "calculation": "mean"})
                used_cols.add(col)
                
            # 4. Volume / Count
            vol_cols = [c for c in valid_cols if any(w in c.lower() for w in ["quantity", "qty", "units", "orders", "customers", "tenure", "charges", "fee"]) and c not in used_cols]
            if vol_cols:
                col = vol_cols[0]
                is_mean = any(w in col.lower() for w in ["tenure", "fee", "charges", "rate"])
                kpis.append({"name": col, "column": col, "calculation": "mean" if is_mean else "sum"})
                used_cols.add(col)
        
        # Fill remaining slots with N/A
        while len(kpis) < 4:
            kpis.append({"name": "N/A", "column": None, "calculation": "none"})
            
        st.session_state[cache_key] = kpis[:4]

    kpis = st.session_state[cache_key]
    cols = st.columns(4)
    for i, kpi in enumerate(kpis):
        col_name = kpi.get("column")
        calc = kpi.get("calculation", "").lower()
        val_str = "—"
        trend_html = None
        trend_color = "normal"
        
        if col_name and col_name in df.columns:
            try:
                if calc == "sum":
                    val_raw = df[col_name].sum()
                else:
                    val_raw = df[col_name].mean()
                
                val_str = chart_config.format_value(val_raw, col_name=col_name)
                
                # Context-aware Delta logic
                # Only show delta if a date/time column is detected.
                date_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns.tolist()
                if not date_cols:
                    for c in df.columns:
                        if 'date' in c.lower():
                            try:
                                df_temp = pd.to_datetime(df[c])
                                date_cols.append(c)
                                break
                            except Exception:
                                pass
                
                if date_cols and len(df) > 10:
                    dc = date_cols[0]
                    # Attempt to sort by date
                    try:
                        df_dt = df.assign(**{"_temp_dt": pd.to_datetime(df[dc])}).sort_values(by="_temp_dt")
                    except Exception:
                        df_dt = df
                    n = len(df_dt)
                    cutoff = int(n * 0.3)
                    
                    if cutoff > 0:
                        first_30 = df_dt.iloc[:cutoff]
                        last_30 = df_dt.iloc[-cutoff:]
                        if calc == "sum":
                            val1 = first_30[col_name].sum()
                            val2 = last_30[col_name].sum()
                        else:
                            val1 = first_30[col_name].mean()
                            val2 = last_30[col_name].mean()
                            
                        if not pd.isna(val1) and not pd.isna(val2) and val1 != 0:
                            pct_change = ((val2 - val1) / abs(val1)) * 100
                            if pct_change >= 0:
                                trend_html = f"↑ vs earlier period"
                                trend_color = "normal"
                            else:
                                trend_html = f"↓ vs earlier period"
                                trend_color = "inverse"
                        else:
                            trend_html = None
                    else:
                        trend_html = None
                else:
                    trend_html = None


            except Exception:
                val_str = "Error"
                trend_html = None
                
        with cols[i]:
            with st.container():
                st.markdown(f"""
                    <div style="background:#0d1117; border:1px solid #21262d; 
                    border-radius:10px; padding:15px; margin-bottom:15px;">
                        <p style="color:#8b949e; font-size:11px; font-weight:600; 
                        text-transform:uppercase; margin:0; padding-bottom:5px;">{" ".join(dict.fromkeys(kpi.get("name", "Metric").split()))}</p>
                        <h2 style="color:white; font-size:28px; font-weight:700; margin:0; padding-bottom:5px;">{val_str}</h2>
                        <span style="color:{'#4FCC8E' if trend_color == 'normal' else '#F7644F' if trend_color == 'inverse' else '#888'}; font-size:13px; font-weight:500;">
                            {trend_html if trend_html else '—'}
                        </span>
                    </div>
                """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Steps 3 & 4: AI Chart Planner & Renderer
# ---------------------------------------------------------------------------
def _render_ai_charts(df: pd.DataFrame) -> None:
    # ALWAYS use original unencoded dataframe
    # Never use cleaned_df for visualizations
    original_df = st.session_state.get("df")
    if original_df is not None:
        df = original_df

    st.markdown("### 📈 AI Business Charts")
    
    file_name = st.session_state.get("uploaded_name", "dataset")
    cache_key = f"ai_charts_{file_name}"
    
    if cache_key not in st.session_state:
        with st.spinner("AI is determining the best charts to build..."):
            meta = _get_dataset_metadata(df)
            context_key = f"business_context_{file_name}"
            context = st.session_state.get(context_key, {})
            domain = context.get("domain", "general")
            entity = context.get("business_entity", "row")
            target_metric = context.get("target_metric", "key metric")
            avoid_cols = context.get("avoid_columns", [])
            b_qs = context.get("business_questions", [])
            
            prompt = (
                f"You are a senior business analyst. This is a {domain} dataset "
                f"where each row represents a {entity}. "
                f"The business wants to optimize {target_metric}.\n\n"
                f"Column names: {meta['columns']}\n"
                f"Data types: {meta['dtypes']}\n"
                f"Sample rows: {meta['sample']}\n"
                f"Columns to AVOID (IDs/codes): {avoid_cols}\n\n"
                "Generate exactly 5 chart specifications that answer these specific business questions:\n"
                f"{b_qs}\n\n"
                "Rules:\n"
                "- Each chart must directly answer one business question\n"
                f"- Only use columns from: {meta['columns']} minus {avoid_cols}\n"
                "- Choose chart type based on data:\n"
                "  * bar for category comparisons\n"
                "  * line for time series (if date column exists)\n"
                "  * scatter for relationships between 2 numeric columns\n"
                "  * pie/donut for composition (max 7 categories)\n"
                "  * histogram for distributions\n"
                "- If x column represents time or sequential numeric values with more than 15 unique values (like tenure_months, age, days), use chart_type: 'line' not 'bar'\n"
                "- For bar charts: use the categorical column as x, numeric as y\n"
                "- Aggregation: specify 'sum', 'mean', 'count', or 'none'\n\n"
                "Return ONLY this JSON array, no explanation. JSON format:\n"
                "[\n"
                "  {\n"
                "    \"chart_type\": \"bar\",\n"
                "    \"x_column\": \"exact column name\",\n"
                "    \"y_column\": \"exact column name\", \n"
                "    \"color_column\": null,\n"
                "    \"aggregation\": \"sum\",\n"
                "    \"title\": \"descriptive title\",\n"
                "    \"business_question\": \"which question this answers\",\n"
                "    \"insight_hint\": \"what pattern to look for in this chart\"\n"
                "  }\n"
                "]"
            )
            try:
                text, _ = get_llm_response(prompt, temperature=0.2, max_tokens=1500, groq_model=GROQ_MODEL_LARGE, module_name="data_insights")
                text = text[text.find('['):text.rfind(']')+1]
                specs = json.loads(text)
                st.session_state[cache_key] = specs[:5]
            except Exception as e:
                st.error(f"Failed to generate chart specs: {e}")
                st.session_state[cache_key] = []
                return

    specs = st.session_state[cache_key]
    
    # Store all generated figures for the export button later
    if "current_dashboard_figs" not in st.session_state:
        st.session_state["current_dashboard_figs"] = []
    st.session_state["current_dashboard_figs"] = []
    
    # Define gridded layout for charts
    if len(specs) >= 2:
        top_cols = st.columns([0.6, 0.4])
    else:
        top_cols = st.columns(1)
        
    if len(specs) > 2:
        bottom_cols = st.columns(3)
    else:
        bottom_cols = []
    
    for i, spec in enumerate(specs):
        try:
            q = spec.get("business_question", spec.get("question", "Business Question"))
            title = spec.get("title", "Analysis")
            orig_c_type = spec.get("chart_type", "").lower()
            x_col = spec.get("x_column", spec.get("x"))
            y_col = spec.get("y_column", spec.get("y"))
            c_col = spec.get("color_column")
            agg = spec.get("aggregation", "none").lower()
            insight_hint = spec.get("insight_hint")
            
            # Retrieve user widget overrides
            custom_c_type = st.session_state.get(f"ctrl_type_{i}", orig_c_type).lower()
            custom_theme = st.session_state.get(f"ctrl_theme_{i}", "Default")
            custom_labels = st.session_state.get(f"ctrl_labels_{i}", True)
            
            if custom_c_type == "horizontal bar": custom_c_type = "bar"
            if custom_c_type == "donut": custom_c_type = "pie"
            
            if x_col not in df.columns: continue
            if y_col and y_col not in df.columns: y_col = None
            if c_col and c_col not in df.columns: c_col = None
            
            # Apply data sanitization using original unencoded dataframe
            orig_df = st.session_state.get("df_raw", st.session_state.get("original_df", df))
            plot_df = sanitize_chart_data(orig_df, x_col, y_col, c_col, agg)
            
            # Explicitly cast x to string for all charts to prevent ordinal axes forcing integers
            if x_col in plot_df.columns and plot_df[x_col].dtype.kind in 'iuM':
                plot_df[x_col] = plot_df[x_col].astype(str)
                
            chart_df = plot_df.copy()
            
            if x_col in chart_df.columns:
                x_values = chart_df[x_col].unique()
                all_numeric = all(str(v).replace('.','').replace('-','').isdigit() for v in x_values)
                if all_numeric and len(x_values) <= 10:
                    original_df = st.session_state.get("df")
                    if original_df is not None and x_col in original_df.columns:
                        original_vals = original_df[x_col].unique()
                        if not all(str(v).replace('.','').replace('-','').isdigit() for v in original_vals):
                            chart_df = original_df.copy()
                            chart_df[x_col] = chart_df[x_col].astype(str)
            
            fig = None
            orient = "v"
            # Set target height depending on placement
            target_height = 380 if i < 2 else 320
            
            if custom_c_type == "bar":
                # Determine orientation based on label length or user override
                if st.session_state.get(f"ctrl_type_{i}", "").lower() == "horizontal bar":
                    orient = "h"
                elif pd.api.types.is_string_dtype(plot_df[x_col]) and len(plot_df) > 0:
                    avg_len = plot_df[x_col].str.len().mean()
                    if avg_len > 8:
                        orient = "h"
                        
                if orient == "h":
                    chart_df[y_col] = chart_df[y_col].astype(str)
                    fig = px.bar(chart_df, x=y_col, y=x_col, color=c_col, orientation="h")
                else:
                    chart_df[x_col] = chart_df[x_col].astype(str)
                    fig = px.bar(chart_df, x=x_col, y=y_col, color=c_col)
                fig = chart_config.style_bar_chart(fig)
                if custom_labels:
                    fig = chart_config.add_bar_labels(fig, format_as="auto", col_name=y_col if orient == "v" else x_col)
                fig.update_layout(height=max(target_height, len(chart_df)*30 if orient == "h" else target_height))
                
            elif custom_c_type == "line":
                chart_df[x_col] = chart_df[x_col].astype(str)
                fig = px.line(chart_df.sort_values(x_col), x=x_col, y=y_col, color=c_col)
                fig = chart_config.style_line_chart(fig)
                
            elif custom_c_type == "scatter":
                scatter_df = orig_df.copy() # Use completely raw for scatter to avoid stringified numeric columns
                scatter_df = scatter_df.dropna(subset=[x_col, y_col])
                if len(scatter_df) > 500:
                    scatter_df = scatter_df.sample(min(500, len(scatter_df)))
                    
                if pd.api.types.is_numeric_dtype(scatter_df[x_col]) and scatter_df[x_col].nunique() < 20:
                    import numpy as np
                    scatter_df[x_col] = scatter_df[x_col] + np.random.uniform(-0.005, 0.005, size=len(scatter_df))
                    
                fig = px.scatter(scatter_df, x=x_col, y=y_col, color=c_col)
                
            elif custom_c_type == "pie" or custom_c_type == "donut":
                chart_df[x_col] = chart_df[x_col].astype(str)
                fig = px.pie(chart_df, names=x_col, values=y_col)
                fig = chart_config.style_pie_chart(fig)
                if st.session_state.get(f"ctrl_type_{i}", "").lower() == "pie":
                    fig.update_traces(hole=0) # Flat pie override
                
            elif custom_c_type == "histogram":
                chart_df[x_col] = chart_df[x_col].astype(str)
                fig = px.histogram(chart_df, x=x_col, y=y_col, color=c_col)
                
            elif custom_c_type == "box":
                chart_df[x_col] = chart_df[x_col].astype(str)
                fig = px.box(chart_df, x=x_col, y=y_col, color=c_col)
                
            elif custom_c_type == "heatmap":
                if y_col and c_col:
                    cross = pd.crosstab(chart_df[x_col].astype(str), chart_df[y_col].astype(str), values=chart_df[c_col], aggfunc='mean').fillna(0)
                    fig = px.imshow(cross)
                    
            if fig:
                # Apply color themes
                if custom_theme == "Warm":
                    fig.update_layout(colorway=["#FF5722", "#FF9800", "#FFC107", "#FFEB3B", "#F44336"])
                elif custom_theme == "Cool":
                    fig.update_layout(colorway=["#2196F3", "#03A9F4", "#00BCD4", "#009688", "#3F51B5"])
                elif custom_theme == "Monochrome":
                    fig.update_layout(colorway=["#607D8B", "#78909C", "#90A4AE", "#B0BEC5", "#CFD8DC"])
                    
                # Ensure base layout applies last so custom adjustments aren't overwritten
                fig = chart_config.apply_base_layout(fig, title=title, subtitle=q)
                
                # Auto rotate labels 45 deg if there are >6 categories
                if x_col in plot_df.columns and len(plot_df[x_col].unique()) > 6 and custom_c_type in ["bar", "line", "area", "histogram"]:
                    if orient == "v":
                        fig.update_layout(xaxis_tickangle=-45)
                        
                fig.update_layout(minreducedheight=target_height)
                if not hasattr(fig.layout, 'height') or fig.layout.height is None:
                    fig.update_layout(height=target_height)
                
                # Assign to corresponding column in grid
                if i < 2:
                    target_col = top_cols[i] if len(top_cols) > i else top_cols[0]
                else:
                    target_col = bottom_cols[(i - 2) % len(bottom_cols)] if bottom_cols else st
                
                with target_col:
                    st.plotly_chart(fig, use_container_width=True)
                    
                    if insight_hint:
                        st.markdown(f'<p style="color:#8b949e; font-size:12px; font-style:italic; word-wrap:break-word;">💡 {insight_hint}</p>', unsafe_allow_html=True)
                        
                    _save_chart_for_report(f"ai_chart_{i}", fig)
                    st.session_state["current_dashboard_figs"].append(fig)
                    
                    # Chart level controls (below chart)
                    with st.expander("⚙️ Settings"):
                        c_type_opts = ["Bar", "Horizontal Bar", "Line", "Scatter", "Pie", "Donut", "Histogram", "Box", "Heatmap"]
                        default_type = orig_c_type.title()
                        if default_type == "Pie": default_type = "Donut" # Prefer donut
                        if default_type == "Bar" and orient == "h": default_type = "Horizontal Bar"
                        
                        if default_type not in c_type_opts: default_type = "Bar"
                        
                        cc1, cc2 = st.columns(2)
                        cc1.selectbox("Type", c_type_opts, index=c_type_opts.index(default_type), key=f"ctrl_type_{i}")
                        cc2.toggle("Data Labels", value=True, key=f"ctrl_labels_{i}")
                
        except Exception as e:
            st.warning(f"Failed to render chart {i+1}: {str(e)}")
            continue


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
    # ALWAYS use original unencoded dataframe
    # Never use cleaned_df for visualizations
    original_df = st.session_state.get("df")
    if original_df is not None:
        df = original_df

    st.markdown("### 🧠 AI Business Insights")
    if st.button("🧠 Generate Business Insights", type="primary"):
        with st.spinner("Analyzing findings and contacting LLM..."):
            try:
                from llm.client_factory import get_llm_response, GROQ_MODEL_SMALL
                
                num_cols = df.select_dtypes(include='number').columns
                findings = []
                findings.append(f"Total rows: {len(df)}")
                
                # Missing value count
                missing_total = df.isna().sum().sum()
                findings.append(f"Total missing values: {missing_total}")
                
                # Actual churn rate if churn column exists
                churn_cols = [c for c in df.columns if 'churn' in str(c).lower()]
                if churn_cols:
                    churn_col = churn_cols[0]
                    # Try to map to boolean
                    churn_mask = df[churn_col].astype(str).str.lower().isin(['yes', 'true', '1'])
                    if churn_mask.any():
                        churn_pct = (churn_mask.sum() / len(df)) * 100
                        findings.append(f"Actual churn rate: {churn_pct:.1f}%")

                if len(num_cols) > 0:
                    top_num = df[num_cols].var().idxmax()
                    mean_val = df[top_num].mean()
                    findings.append(f"Mean of highest variance numeric column ({top_num}): {mean_val:.2f}")
                    
                    if len(num_cols) >= 2:
                        corr = df[num_cols].corr()
                        
                        # Find strongest correlation pair (excluding self correlation)
                        import numpy as np
                        np.fill_diagonal(corr.values, 0)
                        
                        stack = corr.unstack()
                        strongest_pair = stack.abs().idxmax()
                        k1, k2 = strongest_pair
                        v = corr.loc[k1, k2]
                        findings.append(f"Strongest numerical correlation: {k1} & {k2} ({v:.2f} coefficient)")
                            
                cat_cols = df.select_dtypes(include=['object', 'category']).columns
                if len(cat_cols) > 0:
                    top_cat = df[cat_cols].nunique().idxmax()
                    count = df[top_cat].value_counts().iloc[0]
                    v_name = df[top_cat].value_counts().index[0]
                    findings.append(f"Top category by count: {v_name} in column '{top_cat}' with exactly {count} occurrences")
                    
                prompt = (
                    "You are a senior business analyst presenting to the CEO. Write 5 bullet point insights. "
                    "Each must: start with an action emoji, include a specific number from the findings, explain business impact, "
                    "suggest one action. Max 2 sentences each.\n"
                    "IMPORTANT: Return plain text only. Do not use any XML tags, HTML tags, markdown formatting, or special characters. No <para>, no **bold**, no #headers. Just plain bullet points starting with an emoji.\n\n"
                    f"findings: {findings}"
                )
                
                text, _ = get_llm_response(
                    prompt, 
                    temperature=0.4, 
                    max_tokens=400, 
                    groq_model=GROQ_MODEL_SMALL,
                    module_name="data_insights"
                )
                
                import re
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'\*\*', '', text)
                st.session_state['viz_insights'] = text.strip()
            except Exception as e:
                st.error(f"Failed to generate insights: {e}")

    if 'viz_insights' in st.session_state:
        st.markdown(f"""
        <div style="background:#0d1117; border:1px solid #21262d; border-left:4px solid #4F8EF7; border-radius:8px; padding:20px; margin:20px 0;">
            <h4 style="margin-top:0; color:white;">AI Business Insights</h4>
            <div style="color:#E0E0E0; line-height:1.6;">
                {st.session_state['viz_insights'].replace(chr(10), '<br>')}
            </div>
        </div>
        """, unsafe_allow_html=True)

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
    if 'df' not in st.session_state:
        st.warning("⬅️ Upload a dataset in the sidebar to begin.")
        return

    df = st.session_state['df']
    
    # Dashboard Mode Toggle
    if "dashboard_mode" not in st.session_state:
        st.session_state["dashboard_mode"] = False

    if st.session_state["dashboard_mode"]:
        st.markdown("""<style>
          section[data-testid="stSidebar"] {display: none;}
          .main .block-container {max-width: 100%; padding: 1rem;}
        </style>""", unsafe_allow_html=True)
        
        _, btn_col = st.columns([0.85, 0.15])
        with btn_col:
            if st.button("❌ Exit Dashboard Mode", use_container_width=True):
                st.session_state["dashboard_mode"] = False
                st.rerun()
    else:
        _, btn_col = st.columns([0.85, 0.15])
        with btn_col:
            if st.button("📊 Dashboard Mode", use_container_width=True):
                st.session_state["dashboard_mode"] = True
                st.rerun()

    # Professional Loading Experience
    file_name = st.session_state.get("uploaded_name", "dataset")
    context_key = f"business_context_{file_name}"
    
    if context_key not in st.session_state:
        with st.status("Initializing Dashboard...", expanded=True) as status:
            st.write("🔍 Detecting business domain...")
            import time
            time.sleep(1) # Intentional wait to feel professional
            st.write("📊 Identifying key metrics...")
            context = detect_business_context(df)
            st.write("✅ Dashboard ready")
            status.update(label="Dashboard ready", state="complete", expanded=False)
    else:
        context = st.session_state[context_key]

    
    # ROW 1 — Header bar
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        domain = context.get('domain', 'other').lower() if context else 'other'
        d_style = DOMAIN_STYLES.get(domain, DOMAIN_STYLES["other"])
        badge_html = f"""
        <div style="display:inline-flex; align-items:center; background-color:{d_style['color']}20; border:1px solid {d_style['color']}; border-radius:15px; padding:2px 10px; margin-left:15px;">
            <span style="margin-right:5px;">{d_style['emoji']}</span>
            <span style="color:{d_style['color']}; font-weight:600; font-size:14px;">{domain.title()}</span>
        </div>
        """
        st.markdown(f"<h3 style='margin:0; padding:0; display:flex; align-items:center;'>{file_name} <span style='font-size:16px; color:#888; font-weight:normal; margin-left:15px; border-left:1px solid #444; padding-left:15px;'>{len(df):,} rows</span> {badge_html}</h3>", unsafe_allow_html=True)

    with col2:
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("📥 Export Dashboard", use_container_width=True):
                if "current_dashboard_figs" in st.session_state and st.session_state["current_dashboard_figs"]:
                    import plotly.io as pio
                    from datetime import datetime
                    
                    html_str = "<html><head><title>Dashboard Export</title></head><body style='background-color:#0f0f1e; color:white; font-family:sans-serif;'>"
                    html_str += "<h1 style='text-align:center; padding-top:20px;'>Data Insights Dashboard</h1>"
                    for idx, fig in enumerate(st.session_state["current_dashboard_figs"]):
                        fig_html = pio.to_html(fig, include_plotlyjs=(idx==0), full_html=False)
                        html_str += f"<div style='margin-bottom: 40px; padding: 20px;'>{fig_html}</div>"
                    html_str += "</body></html>"
                    
                    st.download_button(
                        label="Download HTML",
                        data=html_str,
                        file_name=f"{file_name.split('.')[0]}_{datetime.now().strftime('%Y%m%d')}_dashboard.html",
                        mime="text/html",
                        use_container_width=True
                    )
                else:
                    st.warning("Render AI charts first!")
        with btn_c2:
            st.button("Tableau Export", use_container_width=True, disabled=True, help="Coming soon")
            
    st.markdown("<hr style='margin-top:10px; margin-bottom:20px; border:0; border-top:1px solid #2a2a4a;'>", unsafe_allow_html=True)
    
    # Step 1: Executive Summary
    _render_executive_summary(df)
    st.divider()
    
    # Step 2: Dynamic Business KPIs
    _render_dynamic_kpis(df)
    st.divider()
    
    # Step 3 & 4: AI Charts
    _render_ai_charts(df)
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
