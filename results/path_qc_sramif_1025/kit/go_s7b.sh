#!/bin/bash
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
OT_S6_HOLD_MARGIN=0 "$K/stageA_b.sh" "$K"; rc=$?
echo "go_s7b stageA rc $rc $(date -Is)" >> "$K/image.txt"
"$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1
exit $rc
