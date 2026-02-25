"""Constants, color maps, and configuration for the analytics dashboard."""

NOTION_DATABASE_ID = "2ed102cf-99d3-80ed-8f68-c870cde88b4b"
FALLBACK_DATA_PATH = "tasks_data.json"

STATUS_ORDER = ["Not Started", "Blocked", "In Progress", "Waiting for Review", "Complete"]
PRIORITY_ORDER = ["Critical", "Urgent", "High", "Medium", "Low", "Unset"]

STATUS_COLORS = {
    "Not Started": "#64748B",
    "Blocked": "#F87171",
    "In Progress": "#60A5FA",
    "Waiting for Review": "#FBBF24",
    "Complete": "#34D399",
}

PRIORITY_COLORS = {
    "Critical": "#EF4444",
    "Urgent": "#F97316",
    "High": "#F59E0B",
    "Medium": "#818CF8",
    "Low": "#34D399",
    "Unset": "#64748B",
}

FUNCTION_COLORS = {
    "Tech": "#60A5FA",
    "Business": "#F97316",
    "Unset": "#64748B",
}

FOCUS_COLORS = {
    "Web - Glinky AI": "#60A5FA",
    "Web - Health Explorer": "#34D399",
    "Mobile App": "#A78BFA",
    "General": "#FBBF24",
    "Outreach/Sales": "#F97316",
    "Hemostemix": "#F87171",
    "Internal Ops": "#6EE7B7",
    "Marketing": "#F472B6",
    "Account Mgmt": "#38BDF8",
    "Material Prep": "#94A3B8",
}

SCORECARD_COLORS = {
    "Completed": "#34D399",
    "On Track": "#60A5FA",
    "Overdue": "#F87171",
}
SCORECARD_ORDER = ["Completed", "On Track", "Overdue"]

# Dark-mode Plotly layout defaults
LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", color="#CBD5E1", size=12),
    margin=dict(l=40, r=20, t=48, b=40),
    height=400,
    hoverlabel=dict(
        bgcolor="#1E293B",
        bordercolor="rgba(148,163,184,0.2)",
        font=dict(color="#F1F5F9", size=13, family="Inter, -apple-system, BlinkMacSystemFont, sans-serif"),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94A3B8", size=11),
    ),
    xaxis=dict(
        gridcolor="rgba(148,163,184,0.08)",
        zerolinecolor="rgba(148,163,184,0.12)",
    ),
    yaxis=dict(
        gridcolor="rgba(148,163,184,0.08)",
        zerolinecolor="rgba(148,163,184,0.12)",
    ),
)

# Plotly chart display config (hides modebar for clean embedded look)
CHART_CONFIG = {"displayModeBar": False}
