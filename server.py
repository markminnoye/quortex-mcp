import logging
import os
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.openapi import MCPType, RouteMap
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quortex-mcp")

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def merge_specs(base_spec, new_spec):
    """
    Naively merge new_spec into base_spec.
    """
    if not base_spec:
        return new_spec.copy()
        
    merged = base_spec.copy()
    
    # Merge paths
    if 'paths' in new_spec:
        if 'paths' not in merged:
            merged['paths'] = {}
        for path, methods in new_spec['paths'].items():
            if path in merged['paths']:
                logger.warning(f"Path collision: {path}. Overwriting with newer spec.")
            merged['paths'][path] = methods

    # Merge components
    if 'components' in new_spec:
        if 'components' not in merged:
            merged['components'] = {}
        
        for component_type, items in new_spec['components'].items():
            if component_type not in merged['components']:
                merged['components'][component_type] = {}
            
            for name, schema in items.items():
                if name in merged['components'][component_type]:
                    logger.debug(f"Component collision: {component_type}/{name}. Keeping existing version.")
                else:
                    merged['components'][component_type][name] = schema

    return merged

def create_mcp_server():
    # Define paths to specs relative to this script
    base_path = Path(__file__).parent
    api_dir = base_path / "api"

    if not api_dir.exists():
        logger.error(f"Could not find API directory at {api_dir}")
        return None

    # Find all YAML files in the api directory
    yaml_files = list(api_dir.glob("*.yaml"))
    
    if not yaml_files:
        logger.error("No YAML files found in api directory.")
        return None

    logger.info(f"Found {len(yaml_files)} API specs: {[f.name for f in yaml_files]}")

    merged_spec = {}
    
    # Iterate and merge
    for yaml_file in yaml_files:
        logger.info(f"Loading {yaml_file.name}...")
        spec = load_yaml(yaml_file)
        merged_spec = merge_specs(merged_spec, spec)

    # Set common info if needed, or rely on the first/last one
    if 'info' not in merged_spec:
        merged_spec['info'] = {'title': 'Quortex MCP', 'version': '1.0.0'}
    
    merged_spec['info']['title'] = "Quortex Unified API (MCP)"
    merged_spec['info']['description'] = "Unified MCP server for Quortex.io services"

    logger.info("Initializing FastMCP server...")
    
    route_maps = [
        # Map GET requests with path parameters to Resource Templates
        RouteMap(methods=["GET"], pattern=r".*\{.*\}.*", mcp_type=MCPType.RESOURCE_TEMPLATE),
        # Map all other GET requests to Resources
        RouteMap(methods=["GET"], mcp_type=MCPType.RESOURCE),
        # Map POST, PUT, DELETE, PATCH to Tools (default behavior, but good to be explicit for clarity)
        RouteMap(methods=["POST", "PUT", "DELETE", "PATCH"], mcp_type=MCPType.TOOL),
    ]

    # Configure client headers with auth token if available
    client_headers = {}
    auth_token = os.environ.get("QUORTEX_API_TOKEN")
    if auth_token:
        logger.info("Configuring API client with QUORTEX_API_TOKEN")
        client_headers["Authorization"] = f"Bearer {auth_token}"
    else:
        logger.warning("QUORTEX_API_TOKEN not found. API calls may fail if authentication is required.")

    # Configure Auth Provider
    auth_provider = None
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if google_client_id and google_client_secret:
        logger.info("Configuring Google OAuth Provider")
        auth_provider = GoogleProvider(
            client_id=google_client_id,
            client_secret=google_client_secret,
            base_url="http://localhost:8000"  # Default base URL, should match your server config
        )

    # httpx client is required for making requests
    mcp = FastMCP.from_openapi(
        merged_spec,
        client=httpx.AsyncClient(headers=client_headers),
        route_maps=route_maps,
        name="Quortex MCP",
        auth=auth_provider
    )

    # Apply global transformations
    default_org = os.environ.get("QUORTEX_ORG")
    if default_org:
        logger.info(f"Applying global 'org' transformation with default: {default_org}")
        
        # We need to wait for the tools to be loaded if from_openapi is async, 
        # but here it returns the mcp instance and tools are already parsed from spec.
        # Actually, from_openapi (FastMCPOpenAPI) parses the spec immediately in __init__.
        
        for tool_name, tool in mcp._tool_manager._tools.items():
            if "org" in tool.parameters.get("properties", {}):
                mcp.add_tool_transformation(
                    tool_name,
                    ToolTransformConfig(
                        arguments={
                            "org": ArgTransformConfig(
                                hide=True,
                                default=default_org
                            )
                        }
                    )
                )

    return mcp

# Create the MCP server instance globally
# This allows 'fastmcp run server.py' to find the 'mcp' object automatically
mcp = create_mcp_server()

def main():
    if mcp:
        logger.info("Starting Quortex MCP server...")
        mcp.run()

if __name__ == "__main__":
    main()