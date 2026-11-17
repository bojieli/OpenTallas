#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/qc-types-r/aliasprep
for i in 1 2 3 4 5 6 7;do
 rc=0
 docker run --rm -v "$R":/out openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -s /out/sat_$i.ys" > "$R/sat_$i.log" 2>&1 || rc=$?
 echo "$rc" > "$R/sat_$i.rc"
 if [ "$i" -lt 7 ];then [ "$rc" -eq 0 ] || exit 2;else [ "$rc" -ne 0 ] || exit 3;fi
done
python3 -I "$R/cutpoint_proof.py" summarize
