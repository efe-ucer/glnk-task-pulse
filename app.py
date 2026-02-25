"""Streamlit entry point: single-page CEO Task Pulse dashboard."""

from datetime import date, timedelta
import streamlit as st

st.set_page_config(
    page_title="GLNK Task Pulse",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom dark-mode CSS — no sidebar, no tabs
st.markdown("""
<style>
    /* Hide Streamlit chrome */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}

    /* Hide sidebar */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}

    /* Layout */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 0rem;
        max-width: 1200px;
    }

    /* Selectbox styling */
    [data-testid="stSelectbox"] > div > div {
        background: #1A1D27;
        border-radius: 8px;
    }

    /* Expander styling */
    [data-testid="stExpander"] {
        background: #1A1D27;
        border-radius: 8px;
        border: 1px solid rgba(148,163,184,0.1);
        margin-top: 32px;
    }

    /* DataFrames */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(148,163,184,0.1);
        border-radius: 8px;
    }

    /* Dividers */
    hr {
        border-color: rgba(148,163,184,0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

from notion_client_module import get_tasks
from data_processing import build_dataframe, build_timeline_data, compute_kpis
from config import CHART_CONFIG
import charts


# --- Helper: section header ---
def section_header(text: str):
    st.markdown(
        f"""<div style="
            margin-top: 48px;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(148,163,184,0.1);
            font-size: 1.1rem;
            font-weight: 600;
            color: #E2E8F0;
        ">{text}</div>""",
        unsafe_allow_html=True,
    )


# --- Helper: KPI card HTML ---
def kpi_card(label: str, value: str, accent: str) -> str:
    return f"""
    <div style="
        background: #1A1D27;
        border-left: 4px solid {accent};
        border-radius: 8px;
        padding: 16px 20px;
    ">
        <div style="
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748B;
            margin-bottom: 6px;
        ">{label}</div>
        <div style="
            font-size: 2rem;
            font-weight: 700;
            color: #F1F5F9;
        ">{value}</div>
    </div>
    """


# --- Data loading ---
tasks, source = get_tasks()
df_all, df_by_owner_all = build_dataframe(tasks)


# --- Header row ---
h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([3, 1, 2, 2, 1.5])

with h_col1:
    st.markdown(
        '<span style="font-size:1.4rem; font-weight:700; color:#F1F5F9;">GLNK Task Pulse</span>',
        unsafe_allow_html=True,
    )

# h_col2 is a spacer

with h_col3:
    all_owners_list = sorted(df_by_owner_all["owner"].unique())
    sel_owner = st.selectbox("Owner", ["All Owners"] + all_owners_list, label_visibility="collapsed")

with h_col4:
    sel_time = st.selectbox(
        "Time Range",
        ["All Time", "This Week", "This Month", "Overdue Only"],
        label_visibility="collapsed",
    )

with h_col5:
    col_status, col_btn = st.columns([2, 1])
    with col_status:
        if source == "live":
            st.markdown(
                '<span style="color:#34D399; font-size:0.85rem;">● Live</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span style="color:#F59E0B; font-size:0.85rem;">● Fallback</span>',
                unsafe_allow_html=True,
            )
    with col_btn:
        if st.button("↻", help="Refresh data"):
            st.cache_data.clear()
            st.rerun()


# --- Apply filters ---
df = df_all.copy()
df_by_owner = df_by_owner_all.copy()

# Owner filter
if sel_owner != "All Owners":
    # For df: keep rows where the owner string contains the selected owner
    df = df[df["owner"].str.contains(sel_owner, na=False)]
    # For df_by_owner: exact match on exploded owner column
    df_by_owner = df_by_owner[df_by_owner["owner"] == sel_owner]

# Time range filter
today = date.today()
if sel_time == "This Week":
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    df = df[
        (df["dueDate"] >= str(week_start)) & (df["dueDate"] <= str(week_end))
    ]
    df_by_owner = df_by_owner[
        (df_by_owner["dueDate"] >= str(week_start)) & (df_by_owner["dueDate"] <= str(week_end))
    ]
elif sel_time == "This Month":
    month_start = today.replace(day=1)
    # Last day of month
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    df = df[
        (df["dueDate"] >= str(month_start)) & (df["dueDate"] <= str(month_end))
    ]
    df_by_owner = df_by_owner[
        (df_by_owner["dueDate"] >= str(month_start)) & (df_by_owner["dueDate"] <= str(month_end))
    ]
elif sel_time == "Overdue Only":
    df = df[df["is_overdue"]]
    df_by_owner = df_by_owner[df_by_owner["is_overdue"]]


# --- KPI Row ---
kpis = compute_kpis(df)

# Accent color logic
active_accent = "#818CF8"

overdue_rate = kpis["overdue_rate"]
if overdue_rate > 20:
    overdue_accent = "#EF4444"
elif overdue_rate > 10:
    overdue_accent = "#F59E0B"
else:
    overdue_accent = "#34D399"

completion_rate = kpis["completion_rate"]
if completion_rate > 70:
    completion_accent = "#34D399"
elif completion_rate > 40:
    completion_accent = "#F59E0B"
else:
    completion_accent = "#EF4444"

blocked = kpis["blocked"]
if blocked > 3:
    blocked_accent = "#EF4444"
elif blocked > 0:
    blocked_accent = "#F59E0B"
else:
    blocked_accent = "#34D399"

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(kpi_card("Active Tasks", str(kpis["active"]), active_accent), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_card("Overdue Rate", f"{kpis['overdue_rate']}%", overdue_accent), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card("Completion", f"{kpis['completion_rate']}%", completion_accent), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_card("Blocked", str(kpis["blocked"]), blocked_accent), unsafe_allow_html=True)


# --- Task Timeline Section ---
tl_hdr_col, tl_spacer, tl_lbl_col, tl_sel_col = st.columns([6, 2, 0.5, 1])
with tl_hdr_col:
    section_header("Task Timeline")
with tl_lbl_col:
    st.markdown(
        '<span style="font-size:0.7rem; color:#64748B; margin-top:60px; display:block;">View</span>',
        unsafe_allow_html=True,
    )
with tl_sel_col:
    st.markdown('<div style="margin-top:48px;">', unsafe_allow_html=True)
    tl_view = st.selectbox(
        "Timeline view",
        ["1d", "3d", "1w"],
        index=1,
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)

_view_to_freq = {"1d": "1D", "3d": "3D", "1w": "7D"}
timeline_data = build_timeline_data(df, window=_view_to_freq[tl_view])
if not timeline_data.empty:
    st.plotly_chart(
        charts.task_timeline(timeline_data),
        use_container_width=True,
        config=CHART_CONFIG,
    )
else:
    st.info("No tasks with due dates to display timeline.")

section_header("Priority Matrix")
st.plotly_chart(charts.priority_heatmap(df_by_owner), use_container_width=True, config=CHART_CONFIG)


# --- Team Performance Section ---
section_header("Team Performance")

st.plotly_chart(charts.owner_scorecard(df_by_owner), use_container_width=True, config=CHART_CONFIG)

# Overdue expander
overdue_df = df[df["is_overdue"]][["title", "owner", "priority", "status", "dueDate", "days_overdue"]]
overdue_df = overdue_df.sort_values("days_overdue", ascending=False)

with st.expander(f"View Overdue Tasks ({len(overdue_df)})", expanded=False):
    if not overdue_df.empty:
        st.dataframe(
            overdue_df.rename(columns={
                "title": "Task",
                "owner": "Owner",
                "priority": "Priority",
                "status": "Status",
                "dueDate": "Due Date",
                "days_overdue": "Days Overdue",
            }),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No overdue tasks with current filters.")


# --- Work Breakdown Section ---
section_header("Work Breakdown")

treemap_fig, n_uncat = charts.category_treemap(df)
st.plotly_chart(treemap_fig, use_container_width=True, config=CHART_CONFIG)
