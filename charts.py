"""Plotly figure factory functions for the CEO Task Pulse dashboard."""

import plotly.graph_objects as go
import pandas as pd

from config import (
    PRIORITY_ORDER,
    FOCUS_COLORS,
    SCORECARD_COLORS,
    SCORECARD_ORDER,
    LAYOUT_DEFAULTS,
    CHART_CONFIG,
)

_LABEL_COLOR = "#94A3B8"


def _apply_layout(fig: go.Figure, **overrides) -> go.Figure:
    layout = {**LAYOUT_DEFAULTS}
    layout.update(overrides)
    fig.update_layout(**layout)
    return fig


def owner_scorecard(df_by_owner: pd.DataFrame) -> go.Figure:
    """Horizontal stacked bar: Completed | On Track | Overdue per owner."""
    pivot = (
        df_by_owner.groupby(["owner", "scorecard_bucket"])
        .size()
        .unstack(fill_value=0)
    )
    # Ensure all buckets exist
    for b in SCORECARD_ORDER:
        if b not in pivot.columns:
            pivot[b] = 0

    pivot["Total"] = pivot[SCORECARD_ORDER].sum(axis=1)
    pivot = pivot.sort_values("Total", ascending=True)  # bottom-up in Plotly

    avg = pivot["Total"].mean()
    n_owners = len(pivot)

    fig = go.Figure()
    for bucket in SCORECARD_ORDER:
        fig.add_trace(go.Bar(
            y=pivot.index,
            x=pivot[bucket],
            name=bucket,
            orientation="h",
            marker=dict(
                color=SCORECARD_COLORS[bucket],
                line=dict(width=0),
            ),
            text=pivot[bucket].apply(lambda v: str(v) if v > 0 else ""),
            textposition="inside",
            textfont=dict(color="#0F1117", size=11),
            customdata=pivot["Total"].astype(int).values,
            hovertemplate=(
                "<b>%{y}</b><br>"
                + bucket + ": %{x}<br>"
                "Total: %{customdata}"
                "<extra></extra>"
            ),
        ))

    # Total annotations on the right edge
    for i, (owner, row) in enumerate(pivot.iterrows()):
        fig.add_annotation(
            x=row["Total"],
            y=owner,
            text=str(int(row["Total"])),
            showarrow=False,
            xanchor="left",
            xshift=8,
            font=dict(color="#94A3B8", size=12),
        )

    # Average line
    fig.add_vline(
        x=avg,
        line_dash="dot",
        line_color="rgba(148,163,184,0.3)",
        line_width=1,
        annotation_text=f"Avg: {avg:.1f}",
        annotation_font=dict(color="#94A3B8", size=10),
        annotation_position="top",
    )

    fig.update_layout(barmode="stack")
    h = max(350, n_owners * 50 + 60)
    return _apply_layout(
        fig,
        height=h,
        margin=dict(l=140, r=50, t=20, b=20),
        xaxis=dict(
            showticklabels=False,
            gridcolor="rgba(148,163,184,0.08)",
            zerolinecolor="rgba(148,163,184,0.12)",
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            zerolinecolor="rgba(0,0,0,0)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", size=11),
        ),
    )


def category_treemap(df: pd.DataFrame) -> tuple[go.Figure, int]:
    """Function > Focus hierarchy treemap. Returns (fig, n_uncategorized)."""
    filtered = df[(df["function"] != "Unset") & (df["focus"] != "Unset")]
    n_uncategorized = len(df) - len(filtered)

    if filtered.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No categorized tasks to display",
            showarrow=False,
            font=dict(size=14, color="#94A3B8"),
        )
        return _apply_layout(fig, height=400), n_uncategorized

    grouped = (
        filtered.groupby(["function", "focus"])
        .size()
        .reset_index(name="count")
    )

    labels = []
    parents = []
    values = []
    colors = []

    branch_colors = {
        "Tech": "#1E2433",
        "Business": "#1E2830",
    }

    # Add branch nodes (function level)
    functions = grouped["function"].unique()
    for func in functions:
        func_total = grouped.loc[grouped["function"] == func, "count"].sum()
        labels.append(func)
        parents.append("")
        values.append(func_total)
        colors.append(branch_colors.get(func, "#1A1D27"))

    # Add leaf nodes (focus level)
    for _, row in grouped.iterrows():
        labels.append(row["focus"])
        parents.append(row["function"])
        values.append(row["count"])
        colors.append(FOCUS_COLORS.get(row["focus"], "#60A5FA"))

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            line=dict(color="#0F1117", width=2),
        ),
        texttemplate="<b>%{label}</b><br>%{value} tasks",
        textfont=dict(size=12),
        root_color="#0F1117",
        branchvalues="total",
    ))

    # Footnote for uncategorized tasks
    if n_uncategorized > 0:
        fig.add_annotation(
            text=f"<i>{n_uncategorized} tasks not categorized</i>",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0,
            y=-0.06,
            xanchor="left",
            font=dict(color="#475569", size=11),
        )

    return _apply_layout(
        fig,
        height=400,
        margin=dict(l=8, r=8, t=8, b=40),
    ), n_uncategorized


def priority_heatmap(df_by_owner: pd.DataFrame) -> go.Figure:
    """Owner x Priority grid heatmap for active tasks."""
    active = df_by_owner[df_by_owner["status"] != "Complete"]

    if active.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No active tasks to display",
            showarrow=False,
            font=dict(size=14, color="#94A3B8"),
        )
        return _apply_layout(fig, height=300)

    # Priority columns in order, Unset last
    prio_cols = [p for p in PRIORITY_ORDER if p in active["priority"].unique()]

    pivot = (
        active.groupby(["owner", "priority"])
        .size()
        .unstack(fill_value=0)
    )
    # Ensure all priority columns exist
    for p in prio_cols:
        if p not in pivot.columns:
            pivot[p] = 0
    pivot = pivot[prio_cols]

    # Sort owners by total task count desc (busiest at top)
    pivot["_total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("_total", ascending=False)
    pivot = pivot.drop(columns="_total")

    z = pivot.values
    owners = list(pivot.index)
    priorities = list(pivot.columns)

    # Normalize for colorscale (0-1)
    z_max = z.max() if z.max() > 0 else 1
    z_norm = z / z_max

    # Custom indigo colorscale
    colorscale = [
        [0.0, "rgba(15,17,23,0)"],
        [0.01, "rgba(129,140,248,0.08)"],
        [0.25, "rgba(129,140,248,0.25)"],
        [0.5, "rgba(129,140,248,0.5)"],
        [0.75, "#818CF8"],
        [1.0, "#C4B5FD"],
    ]

    fig = go.Figure(go.Heatmap(
        z=z_norm,
        x=priorities,
        y=owners,
        colorscale=colorscale,
        showscale=False,
        xgap=3,
        ygap=3,
        hovertemplate="Owner: %{y}<br>Priority: %{x}<br>Tasks: %{customdata}<extra></extra>",
        customdata=z,
    ))

    # Cell annotations (actual counts)
    for i, owner in enumerate(owners):
        for j, prio in enumerate(priorities):
            val = int(z[i][j])
            fig.add_annotation(
                x=prio,
                y=owner,
                text=str(val) if val > 0 else "",
                showarrow=False,
                font=dict(color="#F1F5F9", size=12),
            )

    n_owners = len(owners)
    h = max(300, n_owners * 36 + 60)
    return _apply_layout(
        fig,
        height=h,
        margin=dict(l=140, r=20, t=20, b=40),
        yaxis=dict(
            autorange="reversed",
            gridcolor="rgba(0,0,0,0)",
            zerolinecolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            side="top",
            gridcolor="rgba(0,0,0,0)",
            zerolinecolor="rgba(0,0,0,0)",
        ),
    )
