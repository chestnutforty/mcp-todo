import inspect
import pytest
from unittest.mock import MagicMock, AsyncMock
from server import write_todos, mcp, _session_todos, _format_todos


def reset_todos():
    """Reset the global todo state for test isolation."""
    _session_todos.clear()


class MockContext:
    """Mock context for testing."""
    def __init__(self, session_id: str = "test-session"):
        self.session_id = session_id
        self.client_id = None


class TestWriteTodosToolConfiguration:
    """Tests for write_todos tool configuration."""

    def test_tool_is_registered(self):
        """write_todos tool should be registered with the MCP server."""
        tools = mcp._tool_manager._tools
        assert "write_todos" in tools

    def test_tool_has_todos_parameter(self):
        """write_todos tool must have 'todos' as a function parameter."""
        sig = inspect.signature(write_todos.fn)
        params = list(sig.parameters.keys())
        assert "todos" in params

    def test_tool_does_not_have_backtesting_tag(self):
        """write_todos tool should not have backtesting_supported tag."""
        tool = write_todos
        tags = getattr(tool, "tags", set()) or set()
        assert "backtesting_supported" not in tags

    def test_tool_does_not_have_cutoff_date(self):
        """write_todos tool should not have cutoff_date parameter."""
        sig = inspect.signature(write_todos.fn)
        params = list(sig.parameters.keys())
        assert "cutoff_date" not in params

    def test_context_parameter_excluded_from_schema(self):
        """Context parameter should be excluded from the tool schema."""
        tool = write_todos
        schema_params = tool.parameters.get("properties", {}).keys()
        assert "ctx" not in schema_params


class TestWriteTodosFunctionality:
    """Tests for write_todos tool functionality."""

    def setup_method(self):
        """Reset state before each test."""
        reset_todos()

    @pytest.mark.asyncio
    async def test_write_empty_list(self):
        """Writing an empty list should clear todos."""
        ctx = MockContext()
        result = await write_todos.fn([], ctx)
        assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_write_single_todo(self):
        """Writing a single todo should work."""
        ctx = MockContext()
        todos = [{"content": "Fix bug", "activeForm": "Fixing bug", "status": "pending"}]
        result = await write_todos.fn(todos, ctx)
        assert "Fix bug" in result
        assert "[ ]" in result  # pending icon

    @pytest.mark.asyncio
    async def test_write_multiple_todos(self):
        """Writing multiple todos should work."""
        ctx = MockContext()
        todos = [
            {"content": "Task 1", "activeForm": "Working on task 1", "status": "pending"},
            {"content": "Task 2", "activeForm": "Working on task 2", "status": "in_progress"},
            {"content": "Task 3", "activeForm": "Working on task 3", "status": "completed"},
        ]
        result = await write_todos.fn(todos, ctx)
        assert "Task 1" in result
        assert "Working on task 2" in result  # in_progress shows activeForm
        assert "Task 3" in result

    @pytest.mark.asyncio
    async def test_state_persistence_within_session(self):
        """State should persist between calls within the same session."""
        ctx = MockContext(session_id="session-1")

        todos1 = [{"content": "First", "activeForm": "First", "status": "pending"}]
        await write_todos.fn(todos1, ctx)

        todos2 = [
            {"content": "First", "activeForm": "First", "status": "completed"},
            {"content": "Second", "activeForm": "Second", "status": "pending"},
        ]
        result = await write_todos.fn(todos2, ctx)
        assert "First" in result
        assert "Second" in result
        assert "2." in result  # Should show 2 items

    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Different sessions should have isolated todo lists."""
        ctx1 = MockContext(session_id="session-1")
        ctx2 = MockContext(session_id="session-2")

        # Write to session 1
        todos1 = [{"content": "Session 1 task", "activeForm": "Session 1 task", "status": "pending"}]
        await write_todos.fn(todos1, ctx1)

        # Write to session 2
        todos2 = [{"content": "Session 2 task", "activeForm": "Session 2 task", "status": "pending"}]
        await write_todos.fn(todos2, ctx2)

        # Verify session isolation
        assert "session-1" in _session_todos
        assert "session-2" in _session_todos
        assert len(_session_todos["session-1"]) == 1
        assert len(_session_todos["session-2"]) == 1
        assert _session_todos["session-1"][0]["content"] == "Session 1 task"
        assert _session_todos["session-2"][0]["content"] == "Session 2 task"

    @pytest.mark.asyncio
    async def test_invalid_status_defaults_to_pending(self):
        """Invalid status should default to pending."""
        ctx = MockContext()
        todos = [{"content": "Test", "activeForm": "Testing", "status": "invalid"}]
        result = await write_todos.fn(todos, ctx)
        assert "[ ]" in result  # pending icon

    @pytest.mark.asyncio
    async def test_missing_active_form_uses_content(self):
        """Missing activeForm should default to content."""
        ctx = MockContext()
        todos = [{"content": "Test task", "status": "in_progress"}]
        result = await write_todos.fn(todos, ctx)
        assert "Test task" in result

    @pytest.mark.asyncio
    async def test_empty_content_skipped(self):
        """Todos with empty content should be skipped."""
        ctx = MockContext()
        todos = [
            {"content": "", "activeForm": "Empty", "status": "pending"},
            {"content": "Valid", "activeForm": "Valid", "status": "pending"},
        ]
        result = await write_todos.fn(todos, ctx)
        assert "Valid" in result
        assert "1." in result  # Only one item
        assert "2." not in result

    @pytest.mark.asyncio
    async def test_summary_counts(self):
        """Summary should show correct counts."""
        ctx = MockContext()
        todos = [
            {"content": "A", "activeForm": "A", "status": "pending"},
            {"content": "B", "activeForm": "B", "status": "pending"},
            {"content": "C", "activeForm": "C", "status": "in_progress"},
            {"content": "D", "activeForm": "D", "status": "completed"},
        ]
        result = await write_todos.fn(todos, ctx)
        assert "2 pending" in result
        assert "1 in progress" in result
        assert "1 completed" in result


class TestAllToolsBacktestingConsistency:
    """Tests to ensure all tools have consistent backtesting configuration."""

    def get_all_tools(self):
        """Get all registered tools from the MCP server."""
        return mcp._tool_manager._tools

    def test_all_non_backtest_tools_have_correct_configuration(self):
        """All tools without backtesting_supported tag must NOT have cutoff_date."""
        tools = self.get_all_tools()

        for tool_name, tool in tools.items():
            tags = getattr(tool, "tags", set()) or set()

            if "backtesting_supported" not in tags:
                sig = inspect.signature(tool.fn)
                params = list(sig.parameters.keys())
                assert "cutoff_date" not in params, (
                    f"Tool '{tool_name}' does not have backtesting_supported tag but has "
                    f"'cutoff_date' function parameter. This is inconsistent."
                )
