#!/bin/bash
# DIE-HEAD-11: CA gate (START-TREE-1 --start-tree clock --start-clean width) on a rebuilt die clock run dir G
# Usage: run_ca_inv.sh <G (clk/, out_TT|FF/arr_*.txt, plan_rs_fb1.json)> <outdir>
set -eu
G=$1; O=$2; mkdir -p $O
W=/srv/opentallas-scratch2/claude/wt/die-head-1; ST=/srv/opentallas-scratch2/claude/die-head-10/st1src
MAP=/srv/opentallas-scratch2/claude/die-head-3/part/map_part.json
J=$W/physical/die_plan/s81_head/die_plan_root_sp5.json
IDREG=/srv/opentallas-scratch2/claude/die-head-7/sta_qc5/bind_idreg.json
I=/srv/opentallas-scratch2/claude/die-head-11/inv
echo START $(date) G=$G
python3 $I/mk_proof.py $G $MAP $G/proof --tree-path > $G/mk_proof.log 2>&1
python3 $W/tools/s81_head/landed_phase_ocv.py $G/plan_rs_fb1.json $G --tools $W/tools/die_plan --out $G/landed_ocv.json > $G/landed_ocv.log 2>&1
python3 /srv/opentallas-scratch2/claude/nc-headpart/scripts/spice_scale.py $G/landed_ocv.json $G/ocv_spice.json
P=$G/proof
cd $ST/tools/die_plan
python3 count_align_plan.py $G/ocv_spice.json --mc-chips 2000 --start-skew 57.5,89.7 --sta-proof $P --sta-plan $J \
  --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $P/droop_regions.json \
  --sta-core-latency-ff 202.5 --start-tree clock --start-clean width --out $O/plan.json > $O/plan.log 2>&1
python3 count_align_bind.py $O/plan.json --parts region --out $O/bind.json > $O/bind.log 2>&1
python3 -c "import json,sys;b=json.load(open(sys.argv[1]));b['parts']=json.load(open(sys.argv[2]))['parts'];json.dump(b,open(sys.argv[3],'w'))" \
  $O/bind.json $IDREG $O/bind_idreg.json
python3 die_sta_related.py $P --plan $J --out $O/sta --corner TT --corner FF --core-latency-ff 202.5 \
  --droop-regions $P/droop_regions.json --count-align $O/bind_idreg.json --count-align-key region --clock-cal spice \
  --cppr-lca --clock-ocv table --clock-droop shared > $O/sta.log 2>&1
grep COUNT-ALIGN $O/sta.log
echo END $(date)
