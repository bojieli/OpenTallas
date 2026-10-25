#!/bin/bash
# hold gate per COORD 10:05 ruling (margin 0) + post-legalisation residual passes (hold_pass.tcl); restore pre-hold GRT DB first.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); HB=$K/run/results/asap7/kq_qfd_dv_s8x_btab_adj0/base
for i in $(seq 1 60); do docker ps --format "{{.Names}}" | grep -q "^sramif-.*btab_s7\|^sramif-btab-" || break; sleep 10; done
cp "$HB/5_1_grt_prehold.odb" "$HB/5_1_grt.odb"; cp "$HB/route_prehold.guide" "$HB/route.guide"
OT_S6_HOLD_MARGIN=0 "$K/hold_s6.sh"; rc=$?
echo "go_hold_d m0+passes rc $rc $(date -Is)" >> "$K/image.txt"
"$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1
exit $rc
