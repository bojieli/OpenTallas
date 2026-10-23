#!/bin/bash
set -u
R=/srv/opentallas-scratch/claude/codex-qdie-2000
O=$R/qchain_status40_negative_2209
[ ! -e "$O" ] || exit 9
mkdir "$O"
cd "$R/dv2f21g5r52cxc/src" || exit 9
D2D_STATUS_OFS=40 D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 D2D_DIE_STAGES=3,3,3,3,2,2/11,11,9,9,9,9,9 bash "$R/d2d_production_current.sh" "$O/program" > "$O/fail.log" 2>&1
rc=$?
printf 'actual_exit=%s\n' "$rc" > "$O/receipt.txt"
[ "$rc" = 1 ] && grep -Fx 'C: two write captures in one cycle (TXD collision)' "$O/fail.log" || exit 8
printf 'EXPECTED_STATUS40_FAILURE_CAUGHT\n' | tee -a "$O/receipt.txt"
