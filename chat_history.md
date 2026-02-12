# ETA-ITS-API Chat History

## 2026-02-12: MCP API Logging Fix

### Issue
- MCP API가 stdout에 로깅을 출력하여 JSON 응답이 오염됨
- n8n MCP 클라이언트가 파싱 실패: "Invalid JSON" 에러
- MCP 프로토콜은 stdout에 오직 JSON만 출력해야 함

### Solution
- `mcp_api.py` 라인 13-18 수정
- logging을 `sys.stderr`로 리다이렉트
- 테스트 결과: 정상적으로 JSON 응답 반환 (서울역→인천공항 경로 분석 성공)

### Testing
```bash
# Test command
cat /tmp/test_mcp_request.json | uv run python mcp_api.py 2>/dev/null

# Result: Clean JSON output with traffic analysis
- 거리: 61.1 km
- 원래 시간: 59.3분
- 실시간 교통 반영: 91.3분 (+32.0분)
- 정체 구간: 만리재로, 마포대로, 강변북로, 공항대로
```

### Commit
- `43e303d`: Fix: Redirect logging to stderr for clean MCP JSON responses

---

## Previous Work (Summary)

### Dynamic Route Extraction
- 하드코딩된 "금낭화로" 제거
- OSRM 라우트 데이터에서 동적으로 도로명 추출
- 모든 경로에 대해 작동하도록 일반화

### OSRM Location Format Fix
- AttributeError 수정: list vs dict 형식 처리
- `maneuver.location`이 배열 `[lng, lat]` 또는 딕셔너리일 수 있음
- 두 형식 모두 지원하도록 안전 검사 추가

### MCP API Creation
- n8n 통합을 위한 MCP 서버 생성
- 두 가지 도구: `analyze_route`, `get_route_comparison`
- 프로토콜: `tools/list`, `tools/call`
- 문서: `MCP_README.md` 및 테스트 스크립트
