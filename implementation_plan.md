# Quortex MCP Server Implementation Plan

The goal is to create an MCP server that exposes the Quortex.io services, specifically the "Switch API" and "User API".

## User Review Required
> [!IMPORTANT]
> This implementation assumes that `FastMCP` (via the `fastmcp` library) is the desired approach as per the user's reference to `gofastmcp.com`. The server will be written in Python.

## Proposed Changes

### `quortex-mcp` Project
The project is moved to `/Users/markminnoye/git/quortex-mcp`.

#### [NEW] [requirements.txt](file:///Users/markminnoye/git/quortex-mcp/requirements.txt)
Dependencies:
- `fastmcp`
- `httpx`
- `pyyaml`

#### [NEW] [server.py](file:///Users/markminnoye/git/quortex-mcp/server.py)
This script will:
1.  Load OpenAPI YAML files from the `api/` directory.
2.  Merge the OpenAPI specifications.
    -   **Paths**: Combined directly.
    -   **Schemas**: Merged. If collisions occur (e.g. standard `Error` types), we will assume they are compatible or prioritize one, logging a warning.
3.  Initialize `FastMCP` with the merged spec.
4.  Configure the server name as "Quortex MCP".

#### [MODIFY] [server.py](file:///Users/markminnoye/git/quortex-mcp/server.py)
Improvements:
-   **Route Mapping**: Implement `RouteMap` to treat `GET` requests as Resources/Templates where appropriate, and `POST` as Tools.
-   **Organization**: Use the merged spec for `FastMCP`, utilizing its built-in OpenAPI parsing capabilities more effectively.

#### [NEW] [tests/test_server.py](file:///Users/markminnoye/git/quortex-mcp/tests/test_server.py)
New test file using `pytest` and `fastmcp.client`.

#### [NEW] [requirements.txt](file:///Users/markminnoye/git/quortex-mcp/requirements.txt)
Update to include `pytest`, `pytest-asyncio`.

## Verification Plan

### Automated Tests
-   **Unit Tests**: Run `pytest` to execute `tests/test_server.py`.
    -   Test that tools are listed correctly.
    -   Test that resources are listed correctly (if mapped).
    -   Test a simple tool call (mocking the HTTP client if necessary, or hitting a safe endpoint).
-   **Startup Test**: `python server.py` (already verified).

### Manual Verification
-   Run the server and connect with an Inspector to verify the new "Resource" organization of GET requests.
