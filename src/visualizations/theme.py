import plotly.graph_objects as go

FONT_FAMILY = "Inter, 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"
GRID_COLOR = "#E8EAED"
AXIS_COLOR = "#6B7280"
TEXT_COLOR = "#111827"


def apply_theme(fig: go.Figure, height: int | None = None, show_grid: bool = True) -> go.Figure:
    """Apply a consistent, clean-light design to any Plotly figure."""
    fig.update_layout(
        font=dict(family=FONT_FAMILY, size=13, color=TEXT_COLOR),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=30, t=60, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#E5E7EB",
            font=dict(family=FONT_FAMILY, size=12, color=TEXT_COLOR),
        ),
        title=dict(font=dict(size=17, color=TEXT_COLOR, family=FONT_FAMILY)),
        colorway=["#10B981", "#3B82F6", "#F59E0B", "#8B5CF6", "#EF4444", "#14B8A6"],
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR if show_grid else "rgba(0,0,0,0)",
        zerolinecolor="#E5E7EB",
        tickfont=dict(color=AXIS_COLOR),
        title_font=dict(color=AXIS_COLOR),
    )
    fig.update_xaxes(
        gridcolor=GRID_COLOR if show_grid else "rgba(0,0,0,0)",
        zerolinecolor="#E5E7EB",
        tickfont=dict(color=AXIS_COLOR),
        title_font=dict(color=AXIS_COLOR),
    )
    if height:
        fig.update_layout(height=height)
    return fig