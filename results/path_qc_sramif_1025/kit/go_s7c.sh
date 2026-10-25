#!/bin/bash
# btab_s7 hold retry: restore pre-hold GRT DB; FF-only GRT hold margin 5 (margin 0 left int -5.89/9, in -0.19/3 after DPL; m0 log run_hold6_m0.log)
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); HB=$K/run/results/asap7/kq_qfd_dv_s8x_btab_adj0/base
cp "$HB/5_1_grt_prehold.odb" "$HB/5_1_grt.odb"; cp "$HB/route_prehold.guide" "$HB/route.guide"
OT_S6_HOLD_MARGIN=5 "$K/hold_s6.sh"; rc=$?
echo "go_s7c hold m5 rc $rc $(date -Is)" >> "$K/image.txt"
"$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1
exit $rc
