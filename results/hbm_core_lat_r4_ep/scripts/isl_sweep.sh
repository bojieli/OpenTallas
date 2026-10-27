#!/bin/bash
# HBM-CORE-LAT-R4 hfd_ep_static: plan-model sweep of island sets x tree structures on one GEO (plan geometry only, UNCHECKED).
# usage: isl_sweep.sh GEO OUTDIR ISLFILE(name|x,y;x,y;x,y;x,y per line) "SPLITS:SMAX ..." [extra htree args]
G=$(readlink -f $1); O=$2; IF=$(readlink -f $3); CFG=$4; shift 4; X="$@"
R3=/srv/opentallas-scratch2/claude/hbm-core-lat-r3-ep; W=$(cd $(dirname $0)/../../.. && pwd)
mkdir -p $O; cd $O; echo "{\"seg_um\": {}}" > asb.json
while IFS="|" read nm isl; do [ -z "$nm" ] && continue; for c in $CFG; do ( s=${c%%:*}; m=${c##*:}; t=${nm}_s$(echo $s | tr , _)_m$m
  python3 $W/tools/die_plan/core_infra_htree.py $G $t.tcl --libtt $R3/lib/invbuf_tt.lib --libff $R3/lib/invbuf_ff.lib --splits $s --smax $m --islands "$isl" $X > $t.log 2> $t.err || { echo "$t HTREE_FAIL $(tail -1 $t.err)"; exit; }
  l=$(OT_PHYS_FIT=$W/results/model_refit3_1026/uf_phys3_v1.json python3 $W/results/qc_su_prog_l1_1026/phys_gate.py $t.tcl asb.json $G $R3/lib $t.pred.json 2>&1 | tail -1)
  h=$(python3 -c "import json;d=json.load(open(\"$t.tcl.json\"));p=d[\"pred\"];print(\"ht TT %.1f w%.1f FF %.1f w%.1f L %s rep %s wire %.0f cells %d\"%(p[\"TT\"][\"mean\"],p[\"TT\"][\"window\"],p[\"FF\"][\"mean\"],p[\"FF\"][\"window\"],d[\"level_len_um\"],d[\"repeaters_per_edge\"],d[\"path_wire_um\"],d[\"n_cells\"]))")
  echo "$t | $l | $h" ) & done; wait; done < $IF
