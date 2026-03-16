import streamlit as st
import sys
from pathlib import Path

# Add project root to sys.path so modules can be found if page is run directly via multi-page
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import core business logic from the renamed module
from modules.data_insights import render_visualisation_page

st.set_page_config(
    page_title="Data Insights",
    page_icon="📊",
    layout="wide"
)

# Render the page logic
render_visualisation_page()
