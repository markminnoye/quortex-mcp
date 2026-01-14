# Quortex MCP Server

This is a Model Context Protocol (MCP) server for Quortex.io services. It dynamically loads valid OpenAPI YAML specifications from the `api/` directory and exposes them as tools to your AI assistant.

## Prerequisites

- Python 3.10+
- `pip`

## Installation

1. Navigate to this directory:
   ```bash
   cd quortex-mcp
   ```

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the server:

```bash
python server.py
```

### Configuration

- `QUORTEX_ORG`: (Optional) Set this environment variable to your Quortex Organization UUID. If set, the `org` parameter will be hidden from the AI assistant and automatically supplied to all API calls.

### Adding New APIs

To add more Quortex services, simply drop the valid OpenAPI YAML file into the `api/` directory. The server will automatically pick it up and merge it on the next restart.

## What is this?

This is a **Model Context Protocol (MCP)** server. MCP is a standard that allows AI assistants (like Claude, IDE, etc.) to connect to external tools and data sources.

By running this server, you expose the Quortex APIs as a set of executable tools to your AI agent. This means:

1.  **Context Awareness**: Your AI assistant can "read" the state of your Quortex tools.
2.  **Actionable**: You can ask your AI assistant to perform actions on your behalf.
