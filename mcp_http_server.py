#!/usr/bin/env python3
"""
MCP HTTP Streaming Server for Traffic Route Analysis
Exposes traffic analysis API as MCP tools via HTTP streaming for n8n integration
"""

import json
import logging
import asyncio
from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from main import TrafficRouteMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the traffic monitor
monitor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global monitor
    logger.info("Initializing TrafficRouteMonitor")
    monitor = TrafficRouteMonitor()
    yield
    logger.info("Shutting down MCP HTTP Server")

app = FastAPI(
    title="MCP Traffic Analysis Server",
    description="MCP server for traffic route analysis via HTTP streaming",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for n8n
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def analyze_route(
    waypoints: list[dict[str, Any]],
    route_name: str | None = None
) -> dict[str, Any]:
    """
    Analyze traffic conditions for a route between waypoints.
    
    Args:
        waypoints: List of waypoint dicts with latitude, longitude, and optional name
                  Example: [{"latitude": 37.5, "longitude": 127.0, "name": "Start"}]
        route_name: Optional name for the route
    
    Returns:
        Dict with route analysis including traffic data
    """
    try:
        logger.info(f"Analyzing route with {len(waypoints)} waypoints")
        
        if len(waypoints) < 2:
            return {
                "error": "At least 2 waypoints are required",
                "status": "error"
            }
        
        # Validate waypoints
        for i, wp in enumerate(waypoints):
            if 'latitude' not in wp or 'longitude' not in wp:
                return {
                    "error": f"Waypoint {i} missing latitude or longitude",
                    "status": "error"
                }
        
        # Generate route name if not provided
        if not route_name:
            start_name = waypoints[0].get('name', 'start')
            end_name = waypoints[-1].get('name', 'end')
            route_name = f"{start_name}_to_{end_name}"
        
        # Get OSRM route
        start_coords = [waypoints[0]['latitude'], waypoints[0]['longitude']]
        end_coords = [waypoints[-1]['latitude'], waypoints[-1]['longitude']]
        
        osrm_route = monitor.route_processor.get_route_from_osrm(start_coords, end_coords)
        
        if not osrm_route:
            return {
                "error": "Could not calculate route between waypoints",
                "status": "error"
            }
        
        # Create route_data structure
        route_data = {
            "resultCode": "Ok",
            "result": [
                {
                    "waypoints": [
                        {
                            "waypointType": "break" if i == 0 else "last" if i == len(waypoints) - 1 else "via",
                            "name": wp.get('name', f"Point {i+1}"),
                            "location": {
                                "longitude": wp['longitude'],
                                "latitude": wp['latitude']
                            }
                        }
                        for i, wp in enumerate(waypoints)
                    ],
                    "routes": osrm_route.get('routes', []),
                    "code": osrm_route.get('code', 'Ok')
                }
            ]
        }
        
        # Analyze with traffic
        result = monitor.check_route_traffic(route_data, route_name)
        
        if not result:
            return {
                "error": "Failed to analyze route traffic",
                "status": "error"
            }
        
        # Extract and format response
        route_info = result['route_data']
        matched_traffic = result.get('matched_traffic', [])
        
        # Extract route roads
        from api import _extract_route_roads, _extract_traffic_adjusted_route
        
        route_roads = _extract_route_roads(route_info)
        traffic_adjusted = _extract_traffic_adjusted_route(result)
        
        response = {
            "status": "success",
            "route_name": route_name,
            "original_duration_seconds": route_info['duration'],
            "original_distance_meters": route_info['distance'],
            "original_speed_kmh": (route_info['distance'] / 1000) / (route_info['duration'] / 3600),
            "route_roads_detected": route_roads,
            "traffic_segments_found": len(matched_traffic),
            "traffic_adjusted_route": traffic_adjusted if traffic_adjusted else None
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in analyze_route: {str(e)}", exc_info=True)
        return {
            "error": f"Internal error: {str(e)}",
            "status": "error"
        }


def get_route_comparison(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    start_name: str = "Start",
    end_name: str = "End"
) -> dict[str, Any]:
    """
    Get a simple comparison of estimated vs traffic-adjusted route time.
    
    Args:
        start_lat: Starting latitude
        start_lng: Starting longitude
        end_lat: Ending latitude
        end_lng: Ending longitude
        start_name: Name of starting location
        end_name: Name of ending location
    
    Returns:
        Dict with comparison data
    """
    waypoints = [
        {"latitude": start_lat, "longitude": start_lng, "name": start_name},
        {"latitude": end_lat, "longitude": end_lng, "name": end_name}
    ]
    
    result = analyze_route(waypoints, f"{start_name}_to_{end_name}")
    
    if result.get('status') == 'error':
        return result
    
    # Simplified response
    traffic_data = result.get('traffic_adjusted_route', {})
    
    return {
        "status": "success",
        "route": f"{start_name} → {end_name}",
        "distance_km": result['original_distance_meters'] / 1000,
        "estimated_duration_minutes": result['original_duration_seconds'] / 60,
        "traffic_adjusted_duration_minutes": traffic_data.get('duration_seconds', 0) / 60,
        "time_difference_minutes": traffic_data.get('time_difference_seconds', 0) / 60,
        "traffic_condition": traffic_data.get('traffic_condition', 'unknown'),
        "average_speed_kmh": traffic_data.get('average_speed_kmh', result['original_speed_kmh']),
        "roads_on_route": result.get('route_roads_detected', [])
    }


# MCP Protocol HTTP Handlers
def handle_mcp_message(message: dict[str, Any]) -> dict[str, Any]:
    """Handle individual MCP protocol messages"""
    
    method = message.get('method')
    params = message.get('params', {})
    msg_id = message.get('id')
    
    if method == 'initialize':
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "traffic-analysis-mcp",
                    "version": "1.0.0"
                }
            }
        }
    
    elif method == 'tools/list':
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "analyze_route",
                        "description": "Analyze traffic conditions for a route with multiple waypoints",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "waypoints": {
                                    "type": "array",
                                    "description": "Array of waypoints with latitude, longitude, and optional name",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "latitude": {"type": "number"},
                                            "longitude": {"type": "number"},
                                            "name": {"type": "string"}
                                        },
                                        "required": ["latitude", "longitude"]
                                    }
                                },
                                "route_name": {
                                    "type": "string",
                                    "description": "Optional name for the route"
                                }
                            },
                            "required": ["waypoints"]
                        }
                    },
                    {
                        "name": "get_route_comparison",
                        "description": "Get simple comparison of estimated vs actual traffic time between two points",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "start_lat": {"type": "number", "description": "Starting latitude"},
                                "start_lng": {"type": "number", "description": "Starting longitude"},
                                "end_lat": {"type": "number", "description": "Ending latitude"},
                                "end_lng": {"type": "number", "description": "Ending longitude"},
                                "start_name": {"type": "string", "description": "Name of start location"},
                                "end_name": {"type": "string", "description": "Name of end location"}
                            },
                            "required": ["start_lat", "start_lng", "end_lat", "end_lng"]
                        }
                    }
                ]
            }
        }
    
    elif method == 'tools/call':
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        try:
            if tool_name == 'analyze_route':
                result = analyze_route(
                    waypoints=arguments.get('waypoints', []),
                    route_name=arguments.get('route_name')
                )
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
            
            elif tool_name == 'get_route_comparison':
                result = get_route_comparison(
                    start_lat=arguments.get('start_lat'),
                    start_lng=arguments.get('start_lng'),
                    end_lat=arguments.get('end_lat'),
                    end_lng=arguments.get('end_lng'),
                    start_name=arguments.get('start_name', 'Start'),
                    end_name=arguments.get('end_name', 'End')
                )
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Unknown method: {method}"
            }
        }


async def stream_mcp_response(request_data: dict[str, Any]) -> AsyncGenerator[str, None]:
    """Generate streaming response for MCP protocol"""
    try:
        response = handle_mcp_message(request_data)
        # Format as JSON-RPC over HTTP streaming
        yield json.dumps(response) + "\n"
    except Exception as e:
        logger.error(f"Error in stream_mcp_response: {e}", exc_info=True)
        error_response = {
            "jsonrpc": "2.0",
            "id": request_data.get('id'),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        yield json.dumps(error_response) + "\n"


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Main MCP HTTP streaming endpoint
    Handles MCP protocol requests via HTTP streaming
    """
    try:
        body = await request.json()
        logger.info(f"Received MCP request: {body.get('method', 'unknown')}")
        
        return StreamingResponse(
            stream_mcp_response(body),
            media_type="application/json",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}")
        return Response(
            content=json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                }
            }),
            media_type="application/json",
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error in mcp_endpoint: {e}", exc_info=True)
        return Response(
            content=json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }),
            media_type="application/json",
            status_code=500
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-traffic-analysis"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "mcp_http_server:app",
        host="0.0.0.0",
        port=3003,
        reload=True,
        log_level="info"
    )
