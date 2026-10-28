#!/bin/bash
# DIE-KV-13 INFO: DIE-KV-12 ca.sh chain on the inverter tree with MEASURED fall arrivals (proof_fall from grt13.sh + tta_fall.py)
# and the FLOW-GEN-1 6672c5921 planner/bind/gate (git archive fg1/, NOT main: COORD 09:38 says it goes to FLOW-ONEMODEL-1).
# phase only.  INFO: the gate of record waits for FLOW-ONEMODEL-1 on main.
set -u
T=inv_r150; R=/srv/opentallas-scratch2/claude/die-kv-13-1028; R12=/srv/opentallas-scratch2/claude/die-kv-12-1028
W=/srv/opentallas-scratch2/claude/wt/die-kv-6/tools; S=$R/fg1/tools/die_plan
L=/srv/opentallas-scratch2/claude/die-kv-2-1027/l128; PL=/srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json
K5=/srv/opentallas-scratch2/claude/die-kv-5-1027
cd $R || exit 1; P=$R/proof_fall
cp $R12/proof_inv_r150/mesh.json $R12/proof_inv_r150/droop_regions.json $P/
mkdir -p lpo_$T; ln -sfn $R12/clk_$T lpo_$T/clk; ln -sfn $R/out_${T}_TT lpo_$T/out_TT; ln -sfn $R/out_${T}_FF lpo_$T/out_FF
python3 $W/s81_head/landed_phase_ocv.py $PL lpo_$T --tools $S --out lpo_$T.json > lpo_$T.log 2>&1; echo LPO_RC $? $(date -Is)
mkdir -p ca_$T; cd ca_$T; cp $K5/split/ca_spice.py .; cp $S/count_align_plan.py .
python3 -I ca_spice.py $R/lpo_$T.json $L/land128_regions.json ${T}_spice 1.0485 1.0552 --mc 2000 2>&1 | tail -n 2
STA="--sta-proof $P --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $P/droop_regions.json --sta-core-latency-ff 202.5"
python3 $S/count_align_bind.py ${T}_spice_xing_lpo.json --from-ocv --parts ocv $STA --start-tree clock --start-clean phase --samples 500 --out st_phase_bind_parts.json > st_phase_bind.log 2>&1; echo BIND_RC $? $(date -Is)
mkdir -p $R/sta_fall_phase; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $R/sta_fall_phase/ 2>/dev/null
python3 $S/die_sta_related.py $P --plan $PL --out $R/sta_fall_phase --clock-cal spice --cppr-lca --count-align $R/ca_$T/st_phase_bind_parts.json --count-align-key region --clock-ocv table --clock-droop shared --droop-regions $P/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 > $R/sta_fall_phase.log 2>&1; echo STA_RC $? $(date -Is)
grep "COUNT-ALIGN TT\|COUNT-ALIGN FF" $R/sta_fall_phase.log | cut -c1-260
