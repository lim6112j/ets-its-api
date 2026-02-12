# MCP HTTP Streaming Server

HTTP streaming-based MCP server for n8n integration.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python mcp_http_server.py
```

The server will run on `http://localhost:8000`

## Endpoints

- **POST /mcp** - Main MCP protocol endpoint (HTTP streaming)
- **GET /health** - Health check endpoint

## n8n Configuration

In n8n's MCP Client Tool node:

1. Choose **HTTP Streamable** transport
2. Set URL to: `http://localhost:8000/mcp`
3. Add authentication headers if needed

## Available Tools

### analyze_route
Analyze traffic conditions for a route with multiple waypoints.

**Parameters:**
- `waypoints` (array, required): Array of waypoint objects with:
  - `latitude` (number, required)
  - `longitude` (number, required)
  - `name` (string, optional)
- `route_name` (string, optional): Name for the route

**Example:**
```json
{
  "waypoints": [
    {"latitude": 37.5, "longitude": 127.0, "name": "Start"},
    {"latitude": 37.6, "longitude": 127.1, "name": "End"}
  ],
  "route_name": "test_route"
}
```

### get_route_comparison
Get simple comparison of estimated vs traffic-adjusted route time.

**Parameters:**
- `start_lat` (number, required): Starting latitude
- `start_lng` (number, required): Starting longitude
- `end_lat` (number, required): Ending latitude
- `end_lng` (number, required): Ending longitude
- `start_name` (string, optional): Name of start location
- `end_name` (string, optional): Name of end location

## Testing

Test with curl:
```bash
# Initialize
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# List tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# Call tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
      "name":"get_route_comparison",
      "arguments":{
        "start_lat":37.5,
        "start_lng":127.0,
        "end_lat":37.6,
        "end_lng":127.1
      }
    }
  }'
```

## Differences from stdio version (mcp_api.py)

- **Transport**: HTTP streaming instead of stdin/stdout
- **Format**: JSON-RPC 2.0 compliant responses
- **Framework**: FastAPI with async support
- **Integration**: Works directly with n8n MCP Client Tool node
- **Deployment**: Can be deployed as a standalone web service
