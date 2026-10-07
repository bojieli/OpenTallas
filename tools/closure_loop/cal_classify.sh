#!/bin/bash
# cal_classify.sh <ORFS results base glob>: why a CTS-only calibrate run left no 4_1_cts.odb.  Prints ONE line
#   CALIBRATE_FAIL class=<class> detail=<first matching log line>
# classes: cts_segv_macro_reg_sinks | cts_segv | rsz_max_buffer | odb_dont_touch | est_parasitics | oom | nickname |
#          synth_or_place (failed before CTS) | flow_error | unknown
G=$1
B=$(ls -d $G 2>/dev/null | tail -1)
R=${G%%/work/orfs/*}                         # route dir (route_view.sh layout)
L=$(ls -d ${G/\/results\//\/logs\/} 2>/dev/null | tail -1)
logs="$(ls $L/*.log 2>/dev/null) $R/run.log"
hit() { grep -h -m1 -E "$1" $logs 2>/dev/null | head -1 | cut -c1-200; }
cls=unknown; d=""
if   d=$(hit "nickname-tag"); [ -n "$d" ]; then cls=nickname
elif d=$(hit "separateMacroRegSinks"); [ -n "$d" ]; then cls=cts_segv_macro_reg_sinks
elif d=$(hit "Signal 11|Segmentation fault"); [ -n "$d" ]; then cls=cts_segv
elif d=$(hit "RSZ-0060"); [ -n "$d" ]; then cls=rsz_max_buffer
elif d=$(hit "ODB-0370"); [ -n "$d" ]; then cls=odb_dont_touch
elif d=$(hit "EST-0104"); [ -n "$d" ]; then cls=est_parasitics
elif d=$(hit "Killed|Cannot allocate memory|std::bad_alloc|out of memory|exit code 137"); [ -n "$d" ]; then cls=oom
elif [ -z "$B" ] || [ ! -f "$B/3_place.odb" ]; then cls=synth_or_place; d=$(hit "ERROR|FAILED")
else d=$(hit "\[ERROR|FAILED"); [ -n "$d" ] && cls=flow_error
fi
echo "CALIBRATE_FAIL class=$cls detail=$d"
