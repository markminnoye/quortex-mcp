import pytest
from fastmcp.client import Client
from fastmcp.server.openapi import MCPType
from server import main, merge_specs, load_yaml
from pathlib import Path

# Note: server.py main() runs the server directly, which blocks. 
# Ideally we should refactor server.py to expose the 'mcp' object without running it.
# For now, we will verify the spec merging and configuration logic.

@pytest.fixture
def sample_spec():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "list_users",
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/users/{id}": {
                "get": {
                    "operationId": "get_user",
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/users/create": {
                "post": {
                    "operationId": "create_user",
                    "responses": {"201": {"description": "Created"}}
                }
            }
        }
    }

def test_merge_specs_logic():
    base = {"paths": {"/a": {"get": {}}}}
    new = {"paths": {"/b": {"get": {}}}}
    merged = merge_specs(base, new)
    assert "/a" in merged["paths"]
    assert "/b" in merged["paths"]

# To test FastMCP integration, we need to inspect the RouteMap logic.
# Since we can't easily introspect the 'mcp' object inside server.py without refactoring,
# We will create a test that verifies the RouteMap regexes work as expected.

from fastmcp.server.openapi import RouteMap

def test_route_map_matching():
    # Replicate the logic from server.py
    route_maps = [
        RouteMap(methods=["GET"], pattern=r".*\{.*\}.*", mcp_type=MCPType.RESOURCE_TEMPLATE),
        RouteMap(methods=["GET"], mcp_type=MCPType.RESOURCE),
        RouteMap(methods=["POST", "PUT", "DELETE", "PATCH"], mcp_type=MCPType.TOOL),
    ]

    # Helper to simulate fastmcp's matching logic (simplified)
    import re
    def match(method, path, maps):
        for rm in maps:
            if method not in rm.methods:
                continue
            if rm.pattern and not re.match(rm.pattern, path):
                continue
            return rm.mcp_type
        return None

    # Test cases
    assert match("GET", "/users", route_maps) == MCPType.RESOURCE
    assert match("GET", "/users/{id}", route_maps) == MCPType.RESOURCE_TEMPLATE
    assert match("POST", "/users", route_maps) == MCPType.TOOL
    assert match("PUT", "/users/{id}", route_maps) == MCPType.TOOL

