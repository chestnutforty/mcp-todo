# MCP Todo - Stateful Todo List Manager

A simple FastMCP server for managing a stateful todo list throughout an agent session.

## Available Tools

### write_todos

Replace the entire todo list with a new list of todos.

**Parameters:**
- `todos`: List of todo objects, each containing:
  - `content` (required): Task description in imperative form (e.g., "Fix the bug")
  - `activeForm` (required): Present continuous form shown during execution (e.g., "Fixing the bug")
  - `status` (required): One of `pending`, `in_progress`, or `completed`

**Returns:** Formatted view of the updated todo list with summary counts.

## Installation

```bash
pip install -e .
```

## Running the Server

```bash
python server.py
```

Or with FastMCP CLI:

```bash
fastmcp run server.py
```

## Example Usage

```python
write_todos([
    {"content": "Research API options", "activeForm": "Researching API options", "status": "completed"},
    {"content": "Implement authentication", "activeForm": "Implementing authentication", "status": "in_progress"},
    {"content": "Write tests", "activeForm": "Writing tests", "status": "pending"},
    {"content": "Deploy to production", "activeForm": "Deploying to production", "status": "pending"}
])
```

Output:
```
Todo List:
1. [x] Research API options
2. [~] Implementing authentication
3. [ ] Write tests
4. [ ] Deploy to production

Summary: 2 pending, 1 in progress, 1 completed
```

## Design Notes

This server mirrors Claude Code's TodoWrite tool behavior:
- Single atomic tool that replaces the entire list
- No separate CRUD operations
- State persists in-memory throughout the session
- Model manages additions/deletions/updates by rewriting the whole list

## Running Tests

```bash
pip install -e ".[test]"
pytest
```
