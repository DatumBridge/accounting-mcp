"""MCP tool registration for accounting-mcp."""

from app.tools import accounting_tools


def register_all(mcp) -> None:
    accounting_tools.register(mcp)
