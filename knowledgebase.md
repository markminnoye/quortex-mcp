# Quortex MCP Knowledgebase

## Resources

### Building Custom API Services
- [OpenAPI Integration](https://gofastmcp.com/integrations/openapi)
- [FastAPI Integration](https://gofastmcp.com/integrations/fastapi)
- [Tool Transformation](https://gofastmcp.com/patterns/tool-transformation)
- [Decorating Methods](https://gofastmcp.com/patterns/decorating-methods)
- [CLI Pattern](https://gofastmcp.com/patterns/cli)
- [Testing](https://gofastmcp.com/patterns/testing)

## Development Notes

### FastMCP Best Practices

#### OpenAPI Integration
-   **Route Mapping**: Use `RouteMap` to control how OpenAPI paths are exposed. By default, everything is a Tool.
    -   Map `GET` requests to `MCPType.RESOURCE` (for lists) or `MCPType.RESOURCE_TEMPLATE` (for parameterized paths).
    -   Map `POST/PUT/DELETE` to `MCPType.TOOL`.
    -   Use `MCPType.EXCLUDE` to hide internal or admin routes (e.g., matching `/admin/` or tags like `internal`).
-   **Naming**: FastMCP automatically slugifies operation IDs. Use `mcp_names` explicitly in `from_openapi` to rename awkward tools.
-   **Collisions**: When merging specs, FastMCP (or our manual merge) handles them. Be defined about how conflicts are resolved (current approach: last write wins).

#### Tool Transformation
-   **Arguments**: Use `ArgTransform` to rename, describe, or hide arguments from the LLM. useful for technical parameters like `trace_id` that the LLM shouldn't worry about.
-   **Behavior**: Use `@tool.transform` to wrap tools with pre/post-processing logic (e.g. validation, logging).

#### Testing
-   **Pytest**: Use `pytest-asyncio` for async tests.
-   **Client**: Use `fastmcp.client.Client` with `transport=mcp` (direct object transport) to test without spawning a subprocess.
-   **Fixtures**: Create a pytest fixture for the initialized `FastMCP` server to reuse in tests.

### Context7 Integration
To query Context7 for FastMCP or OpenAPI advice:
1.  Use `resolve-library-id` with "FastMCP" to get the library ID (e.g., `/jlowin/fastmcp`).
2.  Use `query-docs` with the library ID and specific questions (e.g., "how to use RouteMap").

### Resources
-   [OpenAPI Integration](https://gofastmcp.com/integrations/openapi)
-   [FastAPI Integration](https://gofastmcp.com/integrations/fastapi)
-   [Tool Transformation](https://gofastmcp.com/patterns/tool-transformation)
-   [Decorating Methods](https://gofastmcp.com/patterns/decorating-methods)
-   [CLI Pattern](https://gofastmcp.com/patterns/cli)
-   [Testing](https://gofastmcp.com/patterns/testing)
