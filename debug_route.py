#!/usr/bin/env python3
"""Debug script to test route processing and find the list.get() error"""

import sys
sys.path.insert(0, '.')

from main import TrafficRouteMonitor
import json

# Test data
waypoints = [
    {"latitude": 37.513294, "longitude": 127.100183, "name": "잠실역"},
    {"latitude": 37.521624, "longitude": 126.924218, "name": "여의도"}
]

print("🔍 Starting debug test...")
print(f"Waypoints: {waypoints}")

# Initialize monitor
monitor = TrafficRouteMonitor()

# Get OSRM route
start_coords = [waypoints[0]['latitude'], waypoints[0]['longitude']]
end_coords = [waypoints[-1]['latitude'], waypoints[-1]['longitude']]

print(f"\n📍 Getting OSRM route from {start_coords} to {end_coords}")
osrm_route = monitor.route_processor.get_route_from_osrm(start_coords, end_coords)

if not osrm_route:
    print("❌ Failed to get OSRM route")
    sys.exit(1)

print(f"✅ Got OSRM route")
print(f"   Keys: {list(osrm_route.keys())}")

# Check routes structure
if 'routes' in osrm_route:
    routes = osrm_route['routes']
    print(f"   Routes type: {type(routes)}")
    print(f"   Routes length: {len(routes)}")
    
    if len(routes) > 0:
        route = routes[0]
        print(f"   Route[0] type: {type(route)}")
        print(f"   Route[0] keys: {list(route.keys()) if isinstance(route, dict) else 'NOT A DICT!'}")
        
        if isinstance(route, dict):
            print(f"   Duration: {route.get('duration')}")
            print(f"   Distance: {route.get('distance')}")
            print(f"   Has legs: {'legs' in route}")
            
            if 'legs' in route:
                legs = route['legs']
                print(f"   Legs type: {type(legs)}")
                print(f"   Legs length: {len(legs)}")
                
                if len(legs) > 0:
                    leg = legs[0]
                    print(f"   Leg[0] type: {type(leg)}")
                    print(f"   Leg[0] keys: {list(leg.keys()) if isinstance(leg, dict) else 'NOT A DICT!'}")
                    
                    if isinstance(leg, dict) and 'steps' in leg:
                        steps = leg['steps']
                        print(f"   Steps type: {type(steps)}")
                        print(f"   Steps length: {len(steps)}")
                        
                        if len(steps) > 0:
                            step = steps[0]
                            print(f"   Step[0] type: {type(step)}")
                            if isinstance(step, dict):
                                print(f"   Step[0] name: {step.get('name', 'NO NAME')}")

# Now create route_data structure like api.py does
route_data = {
    "resultCode": "Ok",
    "result": [
        {
            "waypoints": [
                {
                    "waypointType": "break",
                    "name": waypoints[0].get('name', 'Start'),
                    "location": {
                        "longitude": waypoints[0]['longitude'],
                        "latitude": waypoints[0]['latitude']
                    }
                },
                {
                    "waypointType": "last",
                    "name": waypoints[-1].get('name', 'End'),
                    "location": {
                        "longitude": waypoints[-1]['longitude'],
                        "latitude": waypoints[-1]['latitude']
                    }
                }
            ],
            "routes": osrm_route.get('routes', []),
            "code": osrm_route.get('code', 'Ok')
        }
    ]
}

print(f"\n📦 Created route_data structure")

# Now call check_route_traffic
print(f"\n🚦 Calling check_route_traffic...")
result = monitor.check_route_traffic(route_data, "debug_test")

if result:
    print(f"\n✅ check_route_traffic succeeded")
    print(f"   Result keys: {list(result.keys())}")
    print(f"   route_data type: {type(result['route_data'])}")
    print(f"   route_data keys: {list(result['route_data'].keys()) if isinstance(result['route_data'], dict) else 'NOT A DICT!'}")
    
    # Now test the api.py functions
    print(f"\n🧪 Testing _extract_route_roads...")
    from api import _extract_route_roads
    
    route_roads = _extract_route_roads(result['route_data'])
    print(f"   Extracted roads: {route_roads}")
    
    print(f"\n🧪 Testing _extract_traffic_adjusted_route...")
    from api import _extract_traffic_adjusted_route
    
    traffic_adjusted = _extract_traffic_adjusted_route(result)
    print(f"   Traffic adjusted: {traffic_adjusted is not None}")
    if traffic_adjusted:
        print(f"   Duration: {traffic_adjusted.get('duration_seconds')}")
    
else:
    print(f"❌ check_route_traffic failed")

print(f"\n✅ Debug test completed!")
