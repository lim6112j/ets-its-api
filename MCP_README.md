# MCP API for n8n Integration

This MCP (Model Context Protocol) server exposes traffic route analysis tools for use with n8n workflows.

## Installation

### 1. Configure MCP Server

Add to your MCP configuration (e.g., `~/.config/mcp/settings.json` or n8n MCP config):

```json
{
  "mcpServers": {
    "traffic-analysis": {
      "command": "uv",
      "args": ["run", "python", "mcp_api.py"],
      "cwd": "/Users/nixos/workspace/eta-its-api",
      "env": {},
      "disabled": false
    }
  }
}
```

### 2. Make Script Executable

```bash
chmod +x mcp_api.py
```

## Available Tools

### 1. `analyze_route`

Analyze traffic conditions for a route with multiple waypoints.

**Parameters:**
- `waypoints` (array, required): Array of waypoint objects
  - `latitude` (number, required)
  - `longitude` (number, required)
  - `name` (string, optional)
- `route_name` (string, optional): Name for the route

**Example Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "analyze_route",
    "arguments": {
      "waypoints": [
        {
          "latitude": 37.497952,
          "longitude": 127.027926,
          "name": "강남역"
        },
        {
          "latitude": 37.557527,
          "longitude": 126.923917,
          "name": "홍대입구역"
        }
      ],
      "route_name": "gangnam_to_hongdae"
    }
  }
}
```

**Example Response:**
```json
{
  "status": "success",
  "route_name": "gangnam_to_hongdae",
  "original_duration_seconds": 916,
  "original_distance_meters": 13650,
  "original_speed_kmh": 53.6,
  "route_roads_detected": ["강남대로", "백범로", "양화로"],
  "traffic_segments_found": 4265,
  "traffic_adjusted_route": {
    "duration_seconds": 2823,
    "distance_meters": 13650,
    "average_speed_kmh": 17.4,
    "time_difference_seconds": 1907,
    "time_difference_percent": 208.2,
    "traffic_condition": "heavy_delay"
  }
}
```

### 2. `get_route_comparison`

Get a simple comparison of estimated vs traffic-adjusted route time.

**Parameters:**
- `start_lat` (number, required): Starting latitude
- `start_lng` (number, required): Starting longitude
- `end_lat` (number, required): Ending latitude
- `end_lng` (number, required): Ending longitude
- `start_name` (string, optional): Name of start location (default: "Start")
- `end_name` (string, optional): Name of end location (default: "End")

**Example Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_route_comparison",
    "arguments": {
      "start_lat": 37.554264,
      "start_lng": 126.970606,
      "end_lat": 37.469075,
      "end_lng": 126.450667,
      "start_name": "서울역",
      "end_name": "인천공항"
    }
  }
}
```

**Example Response:**
```json
{
  "status": "success",
  "route": "서울역 → 인천공항",
  "distance_km": 52.3,
  "estimated_duration_minutes": 38.5,
  "traffic_adjusted_duration_minutes": 67.2,
  "time_difference_minutes": 28.7,
  "traffic_condition": "heavy_delay",
  "average_speed_kmh": 46.7,
  "roads_on_route": ["공항대로", "제2경인고속도로"]
}
```

## Testing the MCP Server

### Test with echo

```bash
echo '{"method":"tools/list","params":{}}' | uv run python mcp_api.py
```

### Test analyze_route

```bash
echo '{
  "method": "tools/call",
  "params": {
    "name": "analyze_route",
    "arguments": {
      "waypoints": [
        {"latitude": 37.5, "longitude": 127.0, "name": "Start"},
        {"latitude": 37.6, "longitude": 126.9, "name": "End"}
      ]
    }
  }
}' | uv run python mcp_api.py
```

## Using with n8n

### 1. Add MCP Tool Node

In your n8n workflow:
1. Add **MCP Tool** node
2. Select **traffic-analysis** server
3. Choose tool: `analyze_route` or `get_route_comparison`

### 2. Configure Parameters

For `analyze_route`:
- Set `waypoints` as JSON array
- Optionally set `route_name`

For `get_route_comparison`:
- Set start/end coordinates
- Optionally set location names

### 3. Process Response

The response will include:
- Route analysis data
- Traffic-adjusted timing
- Road names on the route
- Traffic condition assessment

## Example n8n Workflow

```
Trigger (Webhook/Schedule)
  ↓
Set Coordinates (JSON)
  ↓
MCP Tool: analyze_route
  ↓
IF Node (check traffic_condition)
  ├─ heavy_delay → Send Alert
  └─ normal → Log Info
```

## Traffic Condition Values

- `heavy_delay`: Time difference > 20%
- `moderate_delay`: Time difference 10-20%
- `normal`: Time difference ±10%
- `faster_than_expected`: Time difference < -10%

## Error Handling

All tools return a `status` field:
- `"success"`: Operation completed
- `"error"`: Operation failed (check `error` field for details)

## Data Sources

- **Routing**: OSRM (Open Source Routing Machine)
- **Traffic**: ITS (Intelligent Transport Systems) API - Korean government real-time traffic data
- **Coverage**: Seoul metropolitan area

## Requirements

- Python 3.10+
- Running OSRM server
- Access to ITS traffic API
- Dependencies: see `requirements.txt` or `pyproject.toml`

## Troubleshooting

### "Unknown method" Error

❌ **Incorrect:**
```json
{"method": "tools/get_route_comparison", "params": {...}}
```

✅ **Correct:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_route_comparison",
    "arguments": {...}
  }
}
```

**Remember:** MCP protocol has only two methods:
- `tools/list` - to list available tools
- `tools/call` - to execute a tool (specify tool name in `params.name`)

### Quick Test Commands

**List tools:**
```bash
echo '{"method":"tools/list","params":{}}' | uv run python mcp_api.py 2>/dev/null
```

**Call get_route_comparison:**
```bash
echo '{
  "method": "tools/call",
  "params": {
    "name": "get_route_comparison",
    "arguments": {
      "start_lat": 37.5546,
      "start_lng": 126.9700,
      "end_lat": 37.4691,
      "end_lng": 126.4505,
      "start_name": "서울역",
      "end_name": "인천공항"
    }
  }
}' | uv run python mcp_api.py 2>/dev/null | jq -r '.content[0].text' | jq '.'
```

**Call analyze_route:**
```bash
echo '{
  "method": "tools/call",
  "params": {
    "name": "analyze_route",
    "arguments": {
      "waypoints": [
        {"latitude": 37.5, "longitude": 127.0, "name": "Start"},
        {"latitude": 37.6, "longitude": 126.9, "name": "End"}
      ]
    }
  }
}' | uv run python mcp_api.py 2>/dev/null | jq -r '.content[0].text' | jq '.'
```
