#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd)
pids=()
for c in TT FF; do
 docker run --rm --memory=4g --cpus=4 -v "$K:/work" -e OT_CORNER="$c" -e ODB=/work/run/results/asap7/hd_elemB_rb/base/5_1_grt.odb -e OT_POSTCTS_GRT=1 -e OT_VCLK_TT=250 -e OT_VCLK_FF=170 -e LAYER_PARASITICS_FILE=/work/setRC_fit.tcl openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/head1309_grt_stats_native.tcl' > "$K/grt_native_stats_$c.log" 2>&1 &
 pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
((status == 0)) || exit "$status"
for c in TT FF; do
 grep -E '^(HEAD_|OT_POSTCTS|OT_PAIR)' "$K/grt_native_stats_$c.log"
done
