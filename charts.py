"""Plotly figure factory functions for the CEO Task Pulse dashboard."""

from datetime import date, timedelta
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

_TIMELINE_COLORS = {
    "Complete": "#34D399",
    "In Progress": "#60A5FA",
    "Assigned": "#64748B",
}
_TIMELINE_STACK_ORDER = ["Complete", "In Progress", "Assigned"]


def _rgba(hex_color: str, alpha: float) -> str:
    """Convert #RRGGBB to rgba(r,g,b,a)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _apply_layout(fig: go.Figure, **overrides) -> go.Figure:
    layout = {**LAYOUT_DEFAULTS}
    layout.update(overrides)
    fig.update_layout(**layout)
    return fig


def task_timeline(timeline_df: pd.DataFrame) -> go.Figure:
    """Stacked area chart of task counts over time with interactive rangeslider."""
    fig = go.Figure()

    # Compute stacked total for y-axis range
    total = timeline_df[_TIMELINE_STACK_ORDER].sum(axis=1)
    y_ceil = max(total.max() * 1.6, 10)

    for group in _TIMELINE_STACK_ORDER:
        if group not in timeline_df.columns:
            continue
        color = _TIMELINE_COLORS[group]
        fig.add_trace(go.Scatter(
            x=timeline_df.index,
            y=timeline_df[group],
            name=group,
            mode="lines",
            line=dict(width=0.5, color=color),
            stackgroup="one",
            fillcolor=_rgba(color, 0.6),
            hoverinfo="skip",
        ))

    # Invisible hover-target trace densified to hourly resolution so the tooltip
    # tracks the cursor as smoothly as the spike line (spikesnap="cursor").
    # Each hour maps to its parent day's values; the label shows that day's date.
    hover_y = y_ceil * 0.82
    hourly_x = []
    hourly_texts = []

    # Pre-build the label for each day
    day_labels = {}
    for d in timeline_df.index:
        row = timeline_df.loc[d]
        parts = [f"<b>{d.strftime('%b %d')}</b>"]
        for g in _TIMELINE_STACK_ORDER:
            swatch = (
                f"<span style='color:{_TIMELINE_COLORS[g]};"
                f"font-size:11px;'>\u25CF</span>"
            )
            parts.append(f"{swatch} <b>{g}</b>: {int(row[g])}")
        day_labels[d] = "<br>".join(parts)

    # Generate hourly points between first and last day
    for d in timeline_df.index:
        for h in range(24):
            ts = d + pd.Timedelta(hours=h)
            hourly_x.append(ts)
            # Snap to current day (hour 0-23 belongs to this day)
            hourly_texts.append(day_labels[d])

    fig.add_trace(go.Scatter(
        x=hourly_x,
        y=[hover_y] * len(hourly_x),
        mode="markers",
        marker=dict(size=1, opacity=0),
        showlegend=False,
        hovertext=hourly_texts,
        hoverinfo="text",
        hoverlabel=dict(
            bgcolor="#1E293B",
            bordercolor="rgba(148,163,184,0.2)",
            font=dict(color="#F1F5F9", size=12),
            align="left",
        ),
    ))

    # Anchor range to today so buttons like "1D" show today, not the last data point
    today = date.today()
    today_str = today.isoformat()
    data_start = timeline_df.index.min()

    fig.update_layout(
        hovermode="closest",
        hoverdistance=-1,
        spikedistance=-1,
        xaxis=dict(
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=0.25,
            spikecolor="rgba(255,255,255,0.35)",
            spikedash="4px,4px",
            range=[str(today - timedelta(days=7)), today_str],
            rangeslider=dict(
                visible=True,
                bgcolor="#1A1D27",
                bordercolor="rgba(148,163,184,0.1)",
                borderwidth=1,
                thickness=0.08,
                range=[str(data_start), today_str],
            ),
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1D", step="day", stepmode="backward"),
                    dict(count=7, label="1W", step="day", stepmode="backward"),
                    dict(count=14, label="2W", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(step="all", label="YTD"),
                ],
                bgcolor="#1A1D27",
                activecolor="#818CF8",
                bordercolor="rgba(148,163,184,0.15)",
                borderwidth=1,
                font=dict(color="#CBD5E1", size=11),
                x=0,
                y=-0.22,
            ),
            type="date",
            gridcolor="rgba(148,163,184,0.08)",
            zerolinecolor="rgba(148,163,184,0.12)",
            tickformat="%b %d",
            tickfont=dict(color="#94A3B8"),
        ),
        yaxis=dict(
            title=dict(text="Tasks", font=dict(color="#94A3B8", size=12)),
            range=[0, y_ceil],
            gridcolor="rgba(148,163,184,0.08)",
            zerolinecolor="rgba(148,163,184,0.12)",
            tickfont=dict(color="#94A3B8"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", size=11),
        ),
    )

    return _apply_layout(fig, height=400, margin=dict(l=50, r=20, t=50, b=60))


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

    # Truncate long owner names for y-axis readability on mobile
    pivot.index = [n[:14] + "\u2026" if len(n) > 14 else n for n in pivot.index]

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
        margin=dict(l=110, r=50, t=30, b=20),
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
            y=1.06,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", size=11),
            itemwidth=30,
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
    """Owner x Priority grid heatmap for active tasks.

    Uses shapes (filled rectangles) instead of multiple go.Heatmap traces to
    guarantee every cell renders correctly with per-column colour normalization.
    """
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
    n_owners = len(owners)
    n_prios = len(priorities)

    # Per-priority base colours
    prio_base_colors = {
        "Critical": "#EF4444",
        "Urgent": "#EF4444",
        "High": "#F97316",
        "Medium": "#FACC15",
        "Low": "#34D399",
        "Unset": "#60A5FA",
    }

    # Per-column normalisation: each priority's max maps to 1.0
    z_norm = z.copy().astype(float)
    for j in range(n_prios):
        col_max = z[:, j].max()
        z_norm[:, j] = z[:, j] / col_max if col_max > 0 else 0.0

    # -- Build figure with numeric axes, then relabel with category ticks ------
    fig = go.Figure()

    # Gap between cells in axis-unit fractions (4px visual gap)
    gap = 0.06
    half_gap = gap / 2

    shapes = []
    annotations = []
    hover_x = []
    hover_y = []
    hover_text = []

    for i in range(n_owners):
        for j in range(n_prios):
            val = int(z[i][j])
            norm = z_norm[i][j]

            # Map normalised value to alpha: 0 -> 0.0 (transparent), 1 -> 1.0
            if val == 0:
                alpha = 0.0
            else:
                # Minimum alpha of 0.18 so that even count=1 cells are visible
                alpha = 0.18 + 0.82 * norm

            base_hex = prio_base_colors.get(priorities[j], "#64748B")
            fill_color = _rgba(base_hex, alpha) if val > 0 else "rgba(0,0,0,0)"

            # Rectangle for cell (x=column index, y=row index; y is inverted)
            shapes.append(dict(
                type="rect",
                xref="x",
                yref="y",
                x0=j - 0.5 + half_gap,
                x1=j + 0.5 - half_gap,
                y0=i - 0.5 + half_gap,
                y1=i + 0.5 - half_gap,
                fillcolor=fill_color,
                line=dict(width=0),
                layer="below",
            ))

            # Count annotation centred in cell
            if val > 0:
                text_color = "#0F1117" if alpha > 0.55 else "#F1F5F9"
                annotations.append(dict(
                    x=j,
                    y=i,
                    text=str(val),
                    showarrow=False,
                    font=dict(color=text_color, size=13),
                    xref="x",
                    yref="y",
                ))

            # Hover data point
            hover_x.append(j)
            hover_y.append(i)
            hover_text.append(
                f"Owner: {owners[i]}<br>"
                f"Priority: {priorities[j]}<br>"
                f"Tasks: {val}"
            )

    # Vertical separator bar before "Unset" column
    if "Unset" in priorities:
        sep_x = priorities.index("Unset") - 0.5
        shapes.append(dict(
            type="line",
            xref="x",
            yref="paper",
            x0=sep_x,
            x1=sep_x,
            y0=0,
            y1=1,
            line=dict(color="rgba(148,163,184,0.15)", width=1, dash="dot"),
            layer="above",
        ))

    # Invisible scatter trace for hover interactivity
    fig.add_trace(go.Scatter(
        x=hover_x,
        y=hover_y,
        mode="markers",
        marker=dict(size=0.1, opacity=0),
        text=hover_text,
        hoverinfo="text",
        showlegend=False,
    ))

    fig.update_layout(shapes=shapes, annotations=annotations)

    h = max(350, n_owners * 44 + 80)
    return _apply_layout(
        fig,
        height=h,
        margin=dict(l=110, r=20, t=20, b=40),
        yaxis=dict(
            tickvals=list(range(n_owners)),
            ticktext=[n[:14] + "\u2026" if len(n) > 14 else n for n in owners],
            autorange="reversed",
            gridcolor="rgba(0,0,0,0)",
            zerolinecolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            tickvals=list(range(n_prios)),
            ticktext=priorities,
            side="top",
            gridcolor="rgba(0,0,0,0)",
            zerolinecolor="rgba(0,0,0,0)",
        ),
    )
