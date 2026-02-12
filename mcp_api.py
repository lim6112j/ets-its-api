#!/usr/bin/env python3
"""
MCP Server for Traffic Route Analysis
Exposes traffic analysis API as MCP tools for n8n integration
"""

import json
import sys
import logging
from typing import Any
from main import TrafficRouteMonitor

# Setup logging - must use stderr for MCP protocol (stdout is for JSON responses)
import sys as _sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=_sys.stderr  # MCP protocol requires stdout for JSON only
)
logger = logging.getLogger(__name__)

# Initialize the traffic monitor
monitor = TrafficRouteMonitor()


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
        Dict with route analysis including:
        - original_duration_seconds: OSRM estimated duration
        - original_distance_meters: Route distance
        - traffic_adjusted_route: Traffic-adjusted timing info
        - route_roads_detected: List of roads on the route
        - traffic_segments_used: Number of traffic segments analyzed
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


# MCP Server Protocol Implementation
def handle_mcp_request(request: dict[str, Any]) -> dict[str, Any]:
    """Handle MCP protocol requests"""
    
    method = request.get('method')
    params = request.get('params', {})
    
    if method == 'tools/list':
        # List available tools
        return {
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
    
    elif method == 'tools/call':
        # Execute a tool
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if tool_name == 'analyze_route':
            result = analyze_route(
                waypoints=arguments.get('waypoints', []),
                route_name=arguments.get('route_name')
            )
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        
        elif tool_name == 'get_route_comparison':
            result = get_route_comparison(
                start_lat=arguments.get('start_lat'),
                start_lng=arguments.get('start_lng'),
                end_lat=arguments.get('end_lat'),
                end_lng=arguments.get('end_lng'),
                start_name=arguments.get('start_name', 'Start'),
                end_name=arguments.get('end_name', 'End')
            )
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    else:
        return {"error": f"Unknown method: {method}"}


def main():
    """Main entry point for MCP server"""
    logger.info("Starting MCP Traffic Analysis Server")
    
    # Read from stdin and write to stdout (MCP protocol)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_mcp_request(request)
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            print(json.dumps({"error": "Invalid JSON"}))
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()


if __name__ == '__main__':
    main()
