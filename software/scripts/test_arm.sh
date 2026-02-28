#!/bin/bash
# 机械臂分步冒烟测试
# Usage: bash software/scripts/test_arm.sh [ARM_BASE_URL]
#   默认: http://localhost:9000

BASE="${1:-http://localhost:9000}"
OK=0; FAIL=0

check() {
  local step="$1"; local cmd="$2"
  echo -n "[$step] $cmd ... "
  result=$(eval "$cmd" 2>&1)
  if echo "$result" | grep -q '"ok": *true\|"ok":true'; then
    echo "✅  $result"
    ((OK++))
  else
    echo "❌  $result"
    ((FAIL++))
  fi
}

echo "=== 机械臂冒烟测试 · $BASE ==="
echo ""

check "status"           "curl -s $BASE/status"
check "pick_tile"        "curl -s -X POST $BASE/pick_tile        -H 'Content-Type: application/json' -d '{\"safe\":true}'"
check "present_to_camera""curl -s -X POST $BASE/present_to_camera -H 'Content-Type: application/json' -d '{\"safe\":true}'"
check "throw_to_discard" "curl -s -X POST $BASE/throw_to_discard  -H 'Content-Type: application/json' -d '{\"safe\":true}'"
check "home"             "curl -s -X POST $BASE/home              -H 'Content-Type: application/json' -d '{}'"
check "pick_tile(2)"     "curl -s -X POST $BASE/pick_tile        -H 'Content-Type: application/json' -d '{\"safe\":true}'"
check "present_to_camera(2)""curl -s -X POST $BASE/present_to_camera -H 'Content-Type: application/json' -d '{\"safe\":true}'"
check "return_tile"      "curl -s -X POST $BASE/return_tile       -H 'Content-Type: application/json' -d '{\"safe\":true}'"
check "home(2)"          "curl -s -X POST $BASE/home              -H 'Content-Type: application/json' -d '{}'"
check "nod"              "curl -s -X POST $BASE/nod               -H 'Content-Type: application/json' -d '{}'"
check "shake"            "curl -s -X POST $BASE/shake             -H 'Content-Type: application/json' -d '{}'"
check "estop"            "curl -s -X POST $BASE/estop             -H 'Content-Type: application/json' -d '{}'"

echo ""
echo "=== 结果: ${OK} 通过 / ${FAIL} 失败 ==="
