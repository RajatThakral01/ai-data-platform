"""
chart_config.py - Centralized chart styling module for the AI Data Platform.
Provides professional BI-tool standards for Plotly visualizations.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

POWER_BI_PALETTE = [
  "#118DFF", "#12239E", "#E66C37", "#6B007B",
  "#E044A7", "#744EC2", "#D9B300", "#D64550"
]

CHART_LAYOUT_BASE = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "#0d1117",
    "font": {"family": "Segoe UI, Inter, sans-serif", "color": "#E0E0E0", "size": 12},
    "margin": {"t": 60, "b": 60, "l": 60, "r": 30},
    "hoverlabel": {
        "bgcolor": "#1a1a2e", "font_size": 13,
        "font_family": "Segoe UI, Inter, sans-serif"
    },
    "xaxis": {
        "showgrid": False, "gridcolor": "rgba(33,38,45,0.8)",
        "linecolor": "rgba(255,255,255,0.1)", "tickfont": {"size": 11}
    },
    "yaxis": {
        "showgrid": True, "gridcolor": "rgba(33,38,45,0.8)",
        "linecolor": "rgba(255,255,255,0.1)", "tickfont": {"size": 11}
    }
}

def format_value(val: float | int | str, col_name: str = "") -> str:
    """Format a numeric value for display (K, M, %, etc)."""
    if pd.isna(val):
        return "N/A"
    
    if isinstance(val, str):
        return val

    try:
        abs_val = abs(float(val))
    except ValueError:
        return str(val)

    is_negative = val < 0
    sign = "-" if is_negative else ""
    
    c_lower = str(col_name).lower()
    is_financial = any(w in c_lower for w in ["sales", "revenue", "profit", "price", "cost", "amount", "fee", "income", "spend", "value"])
    is_percentage = any(w in c_lower for w in ["rate", "pct", "percent", "ratio", "churn", "discount"])
    
    cur = "$" if is_financial else ""
    
    if is_percentage and 0 <= abs_val <= 1.0:
        return f"{sign}{abs_val * 100:.1f}%"
        
    if abs_val >= 1_000_000_000:
        return f"{sign}{cur}{abs_val / 1_000_000_000:.1f}B".replace(".0B", "B")
    elif abs_val >= 1_000_000:
        return f"{sign}{cur}{abs_val / 1_000_000:.1f}M".replace(".0M", "M")
    elif abs_val >= 1_000:
        return f"{sign}{cur}{abs_val / 1_000:.1f}K".replace(".0K", "K")
    elif isinstance(val, int) or abs_val.is_integer():
        return f"{sign}{cur}{int(abs_val):,}"
    else:
        return f"{sign}{cur}{abs_val:,.2f}"


def apply_base_layout(fig: go.Figure, title: str, subtitle: str = None) -> go.Figure:
    """Apply the BASE layout dictionary to a Plotly figure."""
    fig.update_layout(**CHART_LAYOUT_BASE)
    
    # Configure precise title formatting
    import textwrap
    wrapped_title = "<br>".join(textwrap.wrap(title, width=40))
    title_text = f"<b>{wrapped_title}</b>"
    if subtitle:
        title_text += f"<br><span style='font-size:12px;color:#888888'>{subtitle}</span>"
        
    fig.update_layout(
        margin=dict(t=80),
        title={
            "text": title_text,
            "x": 0.05,
            "font": {"size": 14}
        },
        colorway=POWER_BI_PALETTE,
        modebar={"remove": ["zoom2d", "pan2d", "select2d", "lasso2d", "resetScale2d"]},
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title_text="",
            font=dict(size=11)
        )
    )
    # Remove Plotly Logo
    fig.layout.template.layout.margin.b = 60
    return fig

def add_bar_labels(fig: go.Figure, format_as: str = "auto", col_name: str = "") -> go.Figure:
    """
    Add text labels on top/end of bars in a bar chart.
    format_as: 'currency', 'percentage', 'number', 'auto'
    """
    # Plotly Express sometimes splits traces. Update all of them.
    for trace in fig.data:
        if isinstance(trace, go.Bar):
            if format_as == 'auto':
                # Use format_value via pandas apply or list comp
                vals = trace.y if trace.orientation != 'h' else trace.x
                text_labels = [format_value(v, col_name) for v in vals]
            elif format_as == 'currency':
                vals = trace.y if trace.orientation != 'h' else trace.x
                text_labels = [f"${v:,.2f}" if isinstance(v, (int, float)) else str(v) for v in vals]
            elif format_as == 'percentage':
                vals = trace.y if trace.orientation != 'h' else trace.x
                text_labels = [f"{v*100:.1f}%" if isinstance(v, (int, float)) else str(v) for v in vals]
            else:
                vals = trace.y if trace.orientation != 'h' else trace.x
                text_labels = [f"{v:,}" if isinstance(v, (int, float)) else str(v) for v in vals]
                
            trace.text = text_labels
            trace.textposition = "auto"
            trace.textfont = dict(family="Inter, sans-serif", size=11, color="white")
    return fig

def style_bar_chart(fig: go.Figure, color_by_value: bool = False, 
                    positive_color: str = "#4FCC8E", negative_color: str = "#F7644F") -> go.Figure:
    """
    Style a bar chart. Adjust corners and optional value-based coloring.
    """
    for i, trace in enumerate(fig.data):
        if isinstance(trace, go.Bar):
            trace.marker.line.width = 0
            
            if color_by_value:
                vals = trace.y if trace.orientation != 'h' else trace.x
                colors = [positive_color if v >= 0 else negative_color for v in vals]
                trace.marker.color = colors
            elif not trace.marker.color and "color" not in str(trace.hovertext):
                # Apply Power BI Palette to individual bars if not colored by a specific column
                vals = trace.x if trace.orientation == "h" else trace.y
                colors = [POWER_BI_PALETTE[j % len(POWER_BI_PALETTE)] for j in range(len(vals))]
                trace.marker.color = colors
                    
    # Force sorting on horizontal bars to ensure descending visually
    if fig.data and fig.data[0].orientation == 'h':
        fig.update_layout(yaxis={'categoryorder': 'total ascending'}) # Plotly plots bottom up
        
    return fig

def style_pie_chart(fig: go.Figure) -> go.Figure:
    """Style a pie chart into a professional donut."""
    fig.update_traces(
        hole=0.6,
        textposition='inside',
        textinfo='percent+label',
        marker=dict(colors=POWER_BI_PALETTE, line=dict(color='#0d1117', width=2)),
        hoverinfo='label+percent+value',
        hovertemplate="<b>%{label}</b><br>Value: %{value}<br>Share: %{percent}<extra></extra>"
    )
    
    # Calculate Total
    total_val = sum(fig.data[0].values) if fig.data and hasattr(fig.data[0], 'values') else 0
    fig.update_layout(
        annotations=[dict(text=f"Total<br><b>{format_value(total_val)}</b>", x=0.5, y=0.5, font_size=16, showarrow=False, font_family="Segoe UI, Inter, sans-serif")]
    )
    
    # Pull out the largest slice slightly for emphasis
    if fig.data:
        trace = fig.data[0]
        if hasattr(trace, 'values') and len(trace.values) > 0:
            max_idx = np.argmax(trace.values)
            pulls = [0] * len(trace.values)
            pulls[max_idx] = 0.05
            fig.update_traces(pull=pulls)
            
    fig.update_layout(
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05
        )
    )
    return fig

def style_line_chart(fig: go.Figure) -> go.Figure:
    """Style a line chart with area fills and markers."""
    fig.update_traces(
        mode='lines+markers',
        marker=dict(size=5, line=dict(width=1, color="#0d1117")),
        line=dict(width=3, shape="spline"),
        fill='tozeroy',
        fillcolor="rgba(17,141,255,0.1)"
    )
    
    # Custom hover template for line
    for trace in fig.data:
        trace.hovertemplate = "<b>%{x}</b><br>%{y}<extra></extra>"
        
    return fig

def add_sparkline(values_list: list[float], color: str = "#4F8EF7") -> str:
    """
    Generate a tiny Plotly HTML fig (sparkline) and return its HTML string.
    Suitable for rendering inside Streamlit components.
    """
    if not values_list or len(values_list) < 2:
        return ""
        
    # Determine color by trend if not explicitly passed
    if color == "#4F8EF7": 
        if values_list[-1] > values_list[0]:
            color = "#4FCC8E" # Green for up
        elif values_list[-1] < values_list[0]:
            color = "#F7644F" # Red for down
            
    fig = go.Figure(go.Scatter(
        x=list(range(len(values_list))), 
        y=values_list,
        mode='lines',
        line=dict(color=color, width=2, shape='spline'),
        hoverinfo='skip'
    ))
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
        height=40,
        width=120,
        showlegend=False
    )
    
    import plotly.io as pio
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config={'displayModeBar': False})
