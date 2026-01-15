import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx
import yaml
from fastmcp import FastMCP
# GoogleProvider removed
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.openapi import MCPType, RouteMap
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quortex-mcp")

class QuortexAuth(httpx.Auth):
    """
    Custom HTTPX Auth class that automatically fetches and refreshes 
    the Quortex Access Token using an API Key Secret.
    """
    def __init__(self, api_key_secret: str):
        self.api_key_secret = api_key_secret
        self.access_token: Optional[str] = None
        self.expiry: float = 0
        self.token_url = "https://api.quortex.io/1.0/token/"

    async def async_auth_flow(self, request: httpx.Request):
        now = time.time()
        
        # Refresh token if missing or expiring soon (within 60s)
        if not self.access_token or now > self.expiry - 60:
            logger.info("🔑 Refreshing Quortex access token...")
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        self.token_url,
                        json={"api_key_secret": self.api_key_secret.strip()}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    self.access_token = data["access_token"]
                    # If expires_at is provided, parse it, otherwise default to 24h
                    expires_at_str = data.get("expires_at")
                    if expires_at_str:
                        # Assuming ISO format from API
                        from datetime import datetime
                        dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                        self.expiry = dt.timestamp()
                    else:
                        self.expiry = now + (24 * 60 * 60)
                        
                    logger.info(f"✅ Token refreshed. Expires at: {time.ctime(self.expiry)}")
                except Exception as e:
                    logger.error(f"❌ Failed to fetch Quortex token: {e}")
                    raise

        request.headers["Authorization"] = f"Bearer {self.access_token}"
        yield request

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

    # Configure authentication for outgoing API requests
    api_auth = None
    api_key = os.environ.get("QUORTEX_API_KEY")
    if api_key:
        logger.info("Using QUORTEX_API_KEY for automatic token management")
        api_auth = QuortexAuth(api_key)
    else:
        # Fallback to direct token if provided
        auth_token = os.environ.get("QUORTEX_API_TOKEN")
        if auth_token:
            logger.info("Using QUORTEX_API_TOKEN for static authentication")
            # We can use a simple dict for headers or a custom auth for static token
            api_auth = httpx.Auth() # dummy for now, handled below
        else:
            logger.warning("Neither QUORTEX_API_KEY nor QUORTEX_API_TOKEN found. API calls may fail.")

    # Configure client
    client_kwargs = {}
    if api_auth and isinstance(api_auth, QuortexAuth):
        client_kwargs["auth"] = api_auth
    elif os.environ.get("QUORTEX_API_TOKEN"):
        client_kwargs["headers"] = {"Authorization": f"Bearer {os.environ['QUORTEX_API_TOKEN']}"}

    # Configure Auth Provider for MCP Server access
    mcp_auth_provider = None
    
    # Support Static Token (e.g. from 1Password injection)
    mcp_server_token = os.environ.get("MCP_SERVER_TOKEN")
    
    if mcp_server_token:
        logger.info("Configuring Static Token Auth for MCP Server")
        mcp_auth_provider = StaticTokenVerifier(
            tokens={
                mcp_server_token: {
                    "username": "authorized_client",
                    "role": "admin"
                }
            }
        )

    # httpx client is required for making requests
    mcp = FastMCP.from_openapi(
        merged_spec,
        client=httpx.AsyncClient(**client_kwargs),
        route_maps=route_maps,
        name="Quortex MCP",
        auth=mcp_auth_provider
    )

    # Apply global transformations
    default_org = os.environ.get("QUORTEX_ORG")
    if default_org:
        logger.info(f"Applying global 'org' transformation with default: {default_org}")
        
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
mcp = create_mcp_server()

def main():
    if mcp:
        logger.info("Starting Quortex MCP server...")
        mcp.run()

if __name__ == "__main__":
    main()