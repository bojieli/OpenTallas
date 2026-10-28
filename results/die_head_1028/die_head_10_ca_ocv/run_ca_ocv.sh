#!/bin/bash
# DIE-HEAD-10 plan event CA-OCV-K: replan HEAD K/DEPTH with the OCV-inclusive bound, bind, gate (clock_variation table + none info)
# Usage: run_ca_ocv.sh <repo> <outdir>
set -eu
W=$1; O=$2; mkdir -p $O
C5=/srv/opentallas-scratch2/claude/die-head-5; P=$C5/sta_ival/proof
J=/srv/opentallas-scratch2/claude/wt/die-head-1/physical/die_plan/s81_head/die_plan_root_sp5.json
IDREG=/srv/opentallas-scratch2/claude/die-head-7/sta_qc5/bind_idreg.json
cd $W/tools/die_plan
python3 count_align_plan.py $C5/sta/ocv_spice.json --mc-chips 2000 --start-skew 57.5,89.7 --sta-proof $P --sta-plan $J \
  --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $P/droop_regions.json \
  --sta-core-latency-ff 202.5 --out $O/plan_ocv.json > $O/plan_ocv.log 2>&1
python3 count_align_bind.py $O/plan_ocv.json --parts region --out $O/bind_ocv.json > $O/bind_ocv.log 2>&1
python3 -c "import json,sys;b=json.load(open(sys.argv[1]));b['parts']=json.load(open(sys.argv[2]))['parts'];json.dump(b,open(sys.argv[3],'w'))" \
  $O/bind_ocv.json $IDREG $O/bind_ocv_idreg.json
for V in table none; do
  python3 die_sta_related.py $P --plan $J --out $O/sta_$V --corner TT --corner FF --core-latency-ff 202.5 \
    --droop-regions $P/droop_regions.json --count-align $O/bind_ocv_idreg.json --count-align-key region --clock-cal spice \
    --cppr-lca --clock-ocv $V --clock-droop shared > $O/sta_$V.log 2>&1
  grep COUNT-ALIGN $O/sta_$V.log
done
