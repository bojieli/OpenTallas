#!/bin/bash
# closure-loop RE-STA (flow-hold 2026-10-07): re-time a routed block's EXISTING 6_final.odb/.spef/.sdc under a corrected
# sign-off SDC (no re-route).  The routed ORFS dir is never written: its 6_final.* are hard-linked into a scratch ORFS dir.
# usage: resta_hold.sh <orfs_dir> <out_dir> <src_root> <mode: ref|post> <sdc (repo-relative to src_root)> [macro ...]
#   ref : tools/w18/corner_sta_ref.py --extra-sdc (Qwen die masters)      post: tools/w18/corner_sta.py --post-sdc
set -euo pipefail
O=$1; OUT=$2; SRC=$3; MODE=$4; SDC=$5; shift 5
B=$(ls -d $O/results/asap7/*/base | head -1); N=$(basename $(dirname $B))
mkdir -p $OUT/orfs/results/asap7/$N/base
for f in 6_final.odb 6_final.spef 6_final.sdc; do ln -f $B/$f $OUT/orfs/results/asap7/$N/base/$f 2>/dev/null || cp $B/$f $OUT/orfs/results/asap7/$N/base/$f; done
M=(); for m in "$@"; do M+=(--macro $m); done
cd $SRC
if [ $MODE = ref ]; then
  python3 tools/w18/corner_sta_ref.py --orfs-dir $OUT/orfs --extra-sdc $SDC "${M[@]}" --output $OUT/corner_sta.json > $OUT/sta.log 2>&1
else
  python3 tools/w18/corner_sta.py --orfs-dir $OUT/orfs --post-sdc $SDC "${M[@]}" --output $OUT/corner_sta.json > $OUT/sta.log 2>&1
fi
python3 -c "import json;d=json.load(open('$OUT/corner_sta.json'));print('RESTA', d['setup_ss']['worst_slack_ps'], d['hold_ff']['worst_slack_ps'], 'in2reg', d['hold_ff'].get('worst_input_to_reg_slack_ps'), 'out', d['hold_ff'].get('worst_output_port_slack_ps'), 'r2r', d['hold_ff'].get('worst_reg_to_reg_slack_ps'))"
