#!/bin/bash
# Test script for MCP API

echo "=== Testing MCP Traffic Analysis Server ==="
echo

echo "1. Listing available tools..."
echo '{"method":"tools/list","params":{}}' | uv run python mcp_api.py 2>/dev/null | jq '.tools[].name'
echo

echo "2. Testing get_route_comparison (서울역 → 인천공항)..."
echo '{
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
}' | uv run python mcp_api.py 2>/dev/null | jq -r '.content[0].text' | jq '.'
echo

echo "3. Testing analyze_route (강남역 → 홍대입구역)..."
echo '{
  "method": "tools/call",
  "params": {
    "name": "analyze_route",
    "arguments": {
      "waypoints": [
        {"latitude": 37.497952, "longitude": 127.027926, "name": "강남역"},
        {"latitude": 37.557527, "longitude": 126.923917, "name": "홍대입구역"}
      ],
      "route_name": "test_route"
    }
  }
}' | uv run python mcp_api.py 2>/dev/null | jq -r '.content[0].text' | jq '{
  status,
  route_name,
  duration_comparison: {
    original_seconds: .original_duration_seconds,
    traffic_adjusted_seconds: .traffic_adjusted_route.duration_seconds,
    difference_minutes: (.traffic_adjusted_route.time_difference_seconds / 60)
  },
  traffic: {
    condition: .traffic_adjusted_route.traffic_condition,
    average_speed_kmh: .traffic_adjusted_route.average_speed_kmh,
    segments_analyzed: .traffic_segments_found
  },
  roads: .route_roads_detected
}'

echo
echo "=== Test Complete ==="
