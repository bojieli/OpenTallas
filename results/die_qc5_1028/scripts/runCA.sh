#!/bin/bash
# DIE-QC-4: count-aligned crossing chain on a clock-first run (KV-4/KV-5 recipe): landed_phase_ocv (main) -> ca_spice
# (CA plan, region crossings only, spice x1.0485/x1.0552) -> count_align_bind v2 -> main die_sta_related --count-align
# --clock-cal spice --cppr-lca on an UNSCALED proof.  usage: runCA.sh KITNAME NDR
set -u
B=/srv/opentallas-scratch2/claude/die-qc5-1028; K=$B/$1; N=$2; R=$K/CA_$N; MT=/srv/opentallas-scratch2/claude/wt/die-qc5-1028/tools
PLAN=${PLAN:-/srv/opentallas-scratch2/claude/wt/die-qc4-1028/physical/die_plan/qwen_compute/die_plan_sliceclk.json}; MAP=${MAP:-$B/regions_grp.json}
log(){ echo "CA $1 $N: $2 $(date)" >> $B/chain.log; }
mkdir -p $R/lpo $R/sc; ln -sfn ../../clk $R/lpo/clk; ln -sfn ../../clk $R/sc/clk
for C in TT FF; do ln -sfn ../../c1_${N}_$C $R/lpo/out_$C; ln -sfn ../../c1_${N}_$C $R/sc/out_$C; done
python3 -I $MT/s81_head/landed_phase_ocv.py $PLAN $R/lpo --tools $MT/die_plan --out $R/lpo.json > $R/lpo.log 2>&1; log $1 "lpo rc $?"
cd $R && python3 -I $B/ca_spice.py $R/lpo.json $MAP $R/grp_spice 1.0485 1.0552 --mc 2000 > $R/ca.log 2>&1; log $1 "ca rc $?"
python3 -I $MT/die_plan/count_align_bind.py $R/grp_spice_xing_lpo.json --from-ocv --parts ocv --scale 1.0 --samples 2000 --out $R/grp_spice_bind.json > $R/bind.log 2>&1; log $1 "bind rc $?"
if [ ! -s $R/grp_spice_bind.json ]; then   # INFO bind: the plan-FAIL crossings dropped (never a gate number)
  python3 -I $B/info_drop.py $R/grp_spice_xing_lpo.json $R/grp_spice_ca.json $R/grp_spice_xing_lpo_INFO.json >> $R/bind.log 2>&1
  python3 -I $MT/die_plan/count_align_bind.py $R/grp_spice_xing_lpo_INFO.json --from-ocv --parts ocv --scale 1.0 --samples 2000 --out $R/grp_spice_bind.json >> $R/bind.log 2>&1; log $1 "bind INFO (plan FAIL dropped) rc $?"
fi
python3 -I $B/mk_proof.py $R/sc $MAP $R/proof > $R/proof.log 2>&1; log $1 "proof rc $?"
for HB in none HB4; do
  python3 -I $MT/die_plan/die_sta_related.py $R/proof --plan $PLAN --out $R/sta_$HB --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $R/proof/droop_regions.json --hold-buffers $HB --cppr-lca --clock-cal spice --count-align $R/grp_spice_bind.json --count-align-key region > $R/sta_$HB.log 2>&1; log $1 "sta $HB rc $?" &
done; wait
