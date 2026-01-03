import os

from fastapi import FastAPI
from server import mcp

# Optional authentication via environment variable
token = os.environ.get("MCP_AUTH_TOKEN")
if token:
    from fastmcp.server.auth import BearerAuthProvider
    mcp.auth = BearerAuthProvider(token=token)

# Create ASGI app with MCP mounted at /mcp
mcp_app = mcp.http_app(path="/mcp")
app = FastAPI(lifespan=mcp_app.lifespan)
app.mount("/", mcp_app)
