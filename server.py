from typing import Annotated
from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.dependencies import CurrentContext
from datetime import datetime

mcp = FastMCP(
    name="todo",
    instructions=r"""
A stateful todo list manager that maintains tasks throughout an agent session. Each task has a description (content), an active form for display during execution (activeForm), and a status (pending, in_progress, or completed). The entire todo list is replaced atomically with each update. Each session maintains its own independent todo list.
""".strip(),
)

# Per-session todo storage: session_id -> list of todos
_session_todos: dict[str, list[dict]] = {}


def _get_session_key(ctx: Context) -> str:
    """Get a unique key for the current session."""
    # Use session_id if available (HTTP transports), otherwise fall back to client_id or a default
    return ctx.session_id or ctx.client_id or "default"


def _get_todos(session_key: str) -> list[dict]:
    """Get todos for a session, creating empty list if needed."""
    if session_key not in _session_todos:
        _session_todos[session_key] = []
    return _session_todos[session_key]


def _format_todos(todos: list[dict]) -> str:
    """Format todos for display."""
    if not todos:
        return "Todo list is empty."

    lines = ["Todo List:"]
    for i, todo in enumerate(todos, 1):
        status_icon = {
            "pending": "[ ]",
            "in_progress": "[~]",
            "completed": "[x]",
        }.get(todo.get("status", "pending"), "[ ]")

        content = todo.get("content", "")
        active_form = todo.get("activeForm", "")
        status = todo.get("status", "pending")

        if status == "in_progress":
            lines.append(f"{i}. {status_icon} {active_form}")
        else:
            lines.append(f"{i}. {status_icon} {content}")

    pending = sum(1 for t in todos if t.get("status") == "pending")
    in_progress = sum(1 for t in todos if t.get("status") == "in_progress")
    completed = sum(1 for t in todos if t.get("status") == "completed")
    lines.append(f"\nSummary: {pending} pending, {in_progress} in progress, {completed} completed")

    return "\n".join(lines)


@mcp.tool(
    name="write_todos",
    title="Write Todo List",
    description="Replace the entire todo list with a new list of todos. Each todo must have 'content' (imperative task description), 'activeForm' (present continuous form), and 'status' (pending/in_progress/completed).",
    exclude_args=["cutoff_date"],
    tags={"backtesting_supported"},
)
async def write_todos(
    todos: Annotated[list[dict], "List of todo objects with 'content', 'activeForm', and 'status' fields"],
    cutoff_date: Annotated[str, "The date must be in the format YYYY-MM-DD"] = datetime.now().strftime("%Y-%m-%d"),
    ctx: Context = CurrentContext(),
) -> str:
    session_key = _get_session_key(ctx)

    validated_todos = []
    for todo in todos:
        if not isinstance(todo, dict):
            continue

        content = todo.get("content", "")
        active_form = todo.get("activeForm", "")
        status = todo.get("status", "pending")

        if not content:
            continue

        if status not in ("pending", "in_progress", "completed"):
            status = "pending"

        validated_todos.append({
            "content": content,
            "activeForm": active_form or content,
            "status": status,
        })

    _session_todos[session_key] = validated_todos
    return _format_todos(validated_todos)
