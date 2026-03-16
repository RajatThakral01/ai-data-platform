import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
import sys
from pathlib import Path

# Add project root to sys.path so modules can be found if page is run directly via multi-page
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils import llm_logger

st.set_page_config(
    page_title="LLM Observatory",
    page_icon="🔭",
    layout="wide"
)

st.title("🔭 LLM Observatory")

# Provide an option to stop auto-refresh
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)

stats = llm_logger.get_summary_stats()
logs = llm_logger.get_all_logs(limit=200)

if not logs:
    st.info("No LLM logs found yet. Go use the app to generate some data!")
else:
    # Row 1: 4 Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Calls", stats["total_calls"])
    c2.metric("Avg Latency (ms)", f"{stats['avg_latency_ms']:.1f}")
    c3.metric("Success Rate", f"{stats['success_rate_pct']:.1f}%")
    c4.metric("Fallback Rate", f"{stats['fallback_rate_pct']:.1f}%")

    st.divider()

    # Row 2 & 3: Charts
    df_logs = pd.DataFrame(logs)
    if "timestamp" in df_logs.columns:
        df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"])

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        calls_per_module = stats.get("calls_per_module", {})
        if calls_per_module:
            df_modules = pd.DataFrame(list(calls_per_module.items()), columns=["Module", "Calls"])
            fig1 = px.bar(df_modules, x="Module", y="Calls", title="Calls per Module", template="plotly_dark")
            st.plotly_chart(fig1, use_container_width=True)
    
    with chart_col2:
        if not df_logs.empty and "timestamp" in df_logs.columns:
            # Sort by timestamp for line chart
            df_sorted = df_logs.sort_values("timestamp")
            fig2 = px.line(df_sorted, x="timestamp", y="latency_ms", color="model_used", title="Latency Over Time", template="plotly_dark", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # Row 4: Dataframe of last 50 log entries
    st.markdown("### Recent Log Entries")
    st.dataframe(df_logs.head(50), use_container_width=True)

    st.divider()

    # Thumbs up/down feedback on last 10 AI responses
    st.markdown("### AI Response Quality Feedback")
    st.caption("Rate the the last 10 responses on a scale from 1 (Poor) to 5 (Excellent)")
    
    recent_responses = [log for log in logs if log.get('success') and log.get('response')][:10]
    
    def update_rating(log_id, selectbox_key):
        val = st.session_state[selectbox_key]
        if val is not None:
            llm_logger.update_feedback(log_id, val)
            
    for log in recent_responses:
        with st.expander(f"Response {log['id']} - {log['module_name']} at {log['timestamp']}"):
            f_c1, f_c2 = st.columns([4, 1])
            prompt_preview = str(log.get('prompt', ''))[:800] + ("..." if len(str(log.get('prompt', ''))) > 800 else "")
            resp_preview = str(log.get('response', ''))[:800] + ("..." if len(str(log.get('response', ''))) > 800 else "")
            
            f_c1.markdown(f"**Prompt:**\n```text\n{prompt_preview}\n```")
            f_c1.markdown(f"**Response:**\n```text\n{resp_preview}\n```")
            
            f_c2.selectbox(
                "Rate Quality (1-5)", 
                options=[None, 1, 2, 3, 4, 5],
                index=[None, 1, 2, 3, 4, 5].index(log.get('feedback')) if log.get('feedback') else 0,
                key=f"feedback_{log['id']}",
                on_change=update_rating,
                args=(log['id'], f"feedback_{log['id']}")
            )

    st.divider()

    # Clear Logs button
    if 'confirm_clear' not in st.session_state:
        st.session_state.confirm_clear = False
        
    if st.button("🚨 Clear All Logs", type="primary"):
        st.session_state.confirm_clear = True
        st.rerun()
        
    if st.session_state.confirm_clear:
        st.warning("Are you sure you want to completely erase all LLM logs? This action cannot be undone.")
        cc1, cc2 = st.columns(2)
        if cc1.button("Yes, Clear Everything", type="primary"):
            llm_logger.clear_logs()
            st.session_state.confirm_clear = False
            st.success("All logs cleared successfully.")
            st.rerun()
        if cc2.button("Cancel"):
            st.session_state.confirm_clear = False
            st.rerun()

# Auto-refresh logic at the very end
if auto_refresh:
    ph = st.empty()
    for i in range(30, 0, -1):
        ph.caption(f"Waiting to auto-refresh in {i} seconds... (uncheck sidebar box to pause)")
        time.sleep(1)
    st.rerun()
