"""Accounting MCP Server — nhật ký chung → T-accounts → Google Sheet."""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.tools import register_all
from app.capability_bind import bind_declared_capabilities

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="accounting",
    instructions="""
    Accounting MCP posts Vietnamese general journals (Sổ nhật ký chung .xlsx) to
    classical T-accounts and exports a Google Sheet with tabs T-accounts and
    Sơ đồ chữ T. Amounts are deterministic — never invent balances.

    Tools:
    - parse_nhat_ky_chung: ingest Work Item attachment, Drive fileId, or file_base64
    - build_t_accounts: double-entry post from a parse artifact
    - export_t_account_workbook: write Google Sheet (or return matrix when dry_run)

    Prefer this over LLM reconstruction of full journals.
    """,
)

register_all(mcp)


bind_declared_capabilities(mcp)

_base_app = mcp.http_app()


async def health(request):
    return JSONResponse({"status": "ok", "service": "accounting-mcp"})


http_app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", _base_app),
    ],
    lifespan=getattr(_base_app, "lifespan", None),
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Accounting MCP Server (stdio mode)")
    mcp.run()
