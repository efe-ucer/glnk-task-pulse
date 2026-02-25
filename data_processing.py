"""DataFrame construction, computed columns, and KPI computation."""

from datetime import date, timedelta
import pandas as pd


def build_dataframe(tasks: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert task dicts to a DataFrame with computed columns.

    Returns (df, df_by_owner) where df_by_owner explodes multi-owner rows.
    """
    df = pd.DataFrame(tasks)

    # Parse dates
    df["dueDate"] = pd.to_datetime(df["dueDate"], errors="coerce")

    # Fill nulls for categorical columns
    df["priority"] = df["priority"].fillna("Unset")
    df["owner"] = df["owner"].fillna("Unassigned")
    df["function"] = df["function"].fillna("Unset")
    df["focus"] = df["focus"].fillna("Unset")

    # Computed: overdue
    today = pd.Timestamp(date.today())
    df["is_overdue"] = (df["dueDate"] < today) & (df["status"] != "Complete")
    df["days_overdue"] = (today - df["dueDate"]).dt.days.clip(lower=0)
    df.loc[~df["is_overdue"], "days_overdue"] = 0

    # Aging buckets (for overdue tasks)
    df["aging_bucket"] = pd.cut(
        df["days_overdue"].where(df["is_overdue"], other=0),
        bins=[-1, 0, 7, 14, 28, 9999],
        labels=["Not Overdue", "0-7 days", "1-2 weeks", "2-4 weeks", "4+ weeks"],
    )

    # Due week (Monday of the week)
    df["due_week"] = df["dueDate"].dt.to_period("W").apply(
        lambda p: p.start_time if pd.notna(p) else pd.NaT
    )

    # Scorecard bucket
    df["scorecard_bucket"] = "On Track"
    df.loc[df["status"] == "Complete", "scorecard_bucket"] = "Completed"
    df.loc[df["is_overdue"], "scorecard_bucket"] = "Overdue"

    # Explode multi-owner rows for per-owner charts
    df_by_owner = (
        df.assign(owner=df["owner"].str.split(", "))
        .explode("owner")
        .reset_index(drop=True)
    )

    return df, df_by_owner


def build_timeline_data(df: pd.DataFrame, window: str = "1D") -> pd.DataFrame:
    """Aggregate task counts by date and status group for the timeline chart.

    Args:
        df: Task DataFrame with dueDate and status columns.
        window: Pandas resample frequency — "1D", "3D", or "7D".
    """
    tl = df[df["dueDate"].notna()].copy()
    if tl.empty:
        return pd.DataFrame()

    status_map = {
        "Complete": "Complete",
        "In Progress": "In Progress",
        "Waiting for Review": "In Progress",
        "Not Started": "Assigned",
        "Blocked": "Assigned",
    }
    tl["timeline_group"] = tl["status"].map(status_map).fillna("Assigned")
    tl["due_day"] = tl["dueDate"].dt.normalize()

    grouped = (
        tl.groupby(["due_day", "timeline_group"])
        .size()
        .unstack(fill_value=0)
    )
    for col in ["Complete", "In Progress", "Assigned"]:
        if col not in grouped.columns:
            grouped[col] = 0

    grouped = grouped[["Complete", "In Progress", "Assigned"]].sort_index()

    # Reindex to a continuous date range (min date → today) so the chart has no gaps
    today = pd.Timestamp(date.today())
    full_range = pd.date_range(start=grouped.index.min(), end=today, freq="D")
    grouped = grouped.reindex(full_range, fill_value=0)

    if window != "1D":
        # Aggregate into buckets, then forward-fill back to daily
        # so hover tracking is continuous (like a stock chart)
        grouped = grouped.resample(window).sum().resample("1D").ffill()
        # Ensure data extends to today even if last bucket ended earlier
        full_range = pd.date_range(start=grouped.index.min(), end=today, freq="D")
        grouped = grouped.reindex(full_range).ffill()

    return grouped


def compute_kpis(df: pd.DataFrame) -> dict:
    """Compute summary KPIs from the task DataFrame."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    due_this_week = df[
        (df["dueDate"] >= pd.Timestamp(week_start))
        & (df["dueDate"] <= pd.Timestamp(week_end))
    ].shape[0]

    total = len(df)
    complete = (df["status"] == "Complete").sum()
    active = total - int(complete)
    overdue = int(df["is_overdue"].sum())

    return {
        "total": total,
        "complete": int(complete),
        "active": active,
        "in_progress": int((df["status"] == "In Progress").sum()),
        "blocked": int((df["status"] == "Blocked").sum()),
        "not_started": int((df["status"] == "Not Started").sum()),
        "overdue": overdue,
        "overdue_rate": round(overdue / active * 100, 1) if active > 0 else 0,
        "completion_rate": round(complete / total * 100, 1) if total > 0 else 0,
        "due_this_week": int(due_this_week),
    }
