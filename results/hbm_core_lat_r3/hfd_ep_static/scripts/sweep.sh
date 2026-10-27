#!/bin/bash
# HBM-CORE-LAT-R3: plan-model sweep of core_infra_htree structures on one GEO (plan geometry only, UNCHECKED).
# usage: sweep.sh GEO OUTDIR "SPLITS:SMAX ..." [extra htree args]
G=$(readlink -f $1); O=$2; shift 2; CFG=$1; shift; X="$@"
D=/srv/opentallas-scratch2/claude/hbm-core-lat-r3-ep; W=/srv/opentallas-scratch2/claude/wt/hbm-core-lat-r3-ep
mkdir -p $O; cd $O; echo '{"seg_um": {}}' > asb.json
for c in $CFG; do ( s=${c%%:*}; m=${c##*:}; t=s$(echo $s | tr , _)_m$m
  python3 $W/tools/die_plan/core_infra_htree.py $G $t.tcl --libtt $D/lib/invbuf_tt.lib --libff $D/lib/invbuf_ff.lib --splits $s --smax $m $X > $t.log 2> $t.err || { echo "$t HTREE_FAIL $(tail -1 $t.err)"; exit; }
  l=$(OT_PHYS_FIT=$W/results/model_refit3_1026/uf_phys3_v1.json python3 $W/results/qc_su_prog_l1_1026/phys_gate.py $t.tcl asb.json $G $D/lib $t.pred.json 2>&1 | tail -1)
  h=$(python3 -c "import json;d=json.load(open('$t.tcl.json'));p=d['pred'];print('ht TT %.1f w%.1f FF %.1f w%.1f stages %s L %s rep %s wire %.0f cells %d'%(p['TT']['mean'],p['TT']['window'],p['FF']['mean'],p['FF']['window'],d['stages_per_path'],d['level_len_um'],d['repeaters_per_edge'],d['path_wire_um'],d['n_cells']))")
  echo "$t | $l | $h" ) & done; wait
