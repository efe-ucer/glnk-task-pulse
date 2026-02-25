"""Notion API data fetching with caching and fallback to local JSON."""

import json
import httpx
import streamlit as st
from config import NOTION_DATABASE_ID, FALLBACK_DATA_PATH

_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


@st.cache_data(ttl=300, show_spinner="Fetching tasks from Notion...")
def fetch_tasks_from_notion(database_id: str) -> list[dict]:
    """Paginate through a Notion database and return flat task dicts."""
    token = st.secrets.get("NOTION_TOKEN", "")
    if not token or token == "ntn_YOUR_TOKEN_HERE":
        raise ValueError("No valid Notion token configured")

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }

    all_results = []
    has_more = True
    next_cursor = None

    with httpx.Client(headers=headers, timeout=30.0) as client:
        while has_more:
            body = {"page_size": 100}
            if next_cursor:
                body["start_cursor"] = next_cursor
            response = client.post(
                f"{_NOTION_API}/databases/{database_id}/query",
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            all_results.extend(data["results"])
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

    tasks = []
    for page in all_results:
        tasks.append(_extract_task(page))
    return tasks


def _extract_task(page: dict) -> dict:
    """Extract a flat task dict from a Notion page object."""
    page_id = page["id"]
    props = page["properties"]
    last_edited = page.get("last_edited_time")

    # Title
    title_prop = props.get("Task Name", props.get("Name", {}))
    title_parts = title_prop.get("title", [])
    title = "".join(p.get("plain_text", "") for p in title_parts)

    # Status
    status_obj = props.get("Status", {})
    status = status_obj.get("status", {}).get("name") if status_obj.get("status") else None

    # Priority (select)
    priority_obj = props.get("Priority", {})
    priority = priority_obj.get("select", {}).get("name") if priority_obj.get("select") else None

    # Owner (people)
    owner_obj = props.get("Owner", {})
    people = owner_obj.get("people", [])
    owner = ", ".join(p.get("name", "Unknown") for p in people) if people else None

    # Due Date
    due_obj = props.get("Due Date", {})
    due_date = None
    if due_obj.get("date"):
        due_date = due_obj["date"].get("start", "")[:10] or None

    # Function (select)
    func_obj = props.get("Function", {})
    function = func_obj.get("select", {}).get("name") if func_obj.get("select") else None

    # Focus (select)
    focus_obj = props.get("Focus", {})
    focus = focus_obj.get("select", {}).get("name") if focus_obj.get("select") else None

    return {
        "id": page_id,
        "title": title,
        "status": status or "Not Started",
        "priority": priority,
        "owner": owner,
        "dueDate": due_date,
        "function": function,
        "focus": focus,
        "lastEdited": last_edited,
    }


def load_fallback_data(path: str = FALLBACK_DATA_PATH) -> list[dict]:
    """Load tasks from local JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def get_tasks(
    database_id: str = NOTION_DATABASE_ID,
    fallback_path: str = FALLBACK_DATA_PATH,
) -> tuple[list[dict], str]:
    """Try Notion API first, fall back to local JSON. Returns (tasks, source)."""
    try:
        tasks = fetch_tasks_from_notion(database_id)
        return tasks, "live"
    except Exception:
        tasks = load_fallback_data(fallback_path)
        return tasks, "fallback"
