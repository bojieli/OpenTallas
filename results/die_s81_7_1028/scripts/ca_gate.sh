#!/bin/bash
# DIE-S81-7 gate CA + die STA in the COORD 03:4x REQUIRED form (DIE-QC-5 4edf8acf6c: scale_clock scales tree nodes,
# --count-align-key region), DIE-KV-4/QC-4 recipe: landed_phase_ocv (lpo_$V.json from post.sh) -> ca_spice.py (per-corner
# spice TT x1.0485 / FF x1.0552) -> count_align_bind --from-ocv -> die_sta_related --count-align --clock-cal spice
# --cppr-lca, key region (gate) and key part (old, to count untimed crossings).  usage: ca_gate.sh V
set -u
V=${1:?}; WT=/srv/opentallas-scratch2/claude/wt/die-s81-7; MT=$WT/tools; O=/srv/opentallas-scratch2/claude/die-s81-7
PL=/srv/opentallas-scratch2/claude/die-s81-5/plan_s5.json; MAP=/srv/opentallas-scratch2/claude/die-s81-5/feed/map_part.json
R=$O/CA_$V; PR=$O/proof_$V; mkdir -p $R
cd $R && python3 -I $WT/results/die_s81_7_1028/scripts/ca_spice.py $O/lpo_$V.json $MAP $R/sp 1.0485 1.0552 --mc 2000 > $R/ca.log 2>&1; echo CA_RC $?
tail -c 1200 $R/ca.log; echo
python3 -I $MT/die_plan/count_align_bind.py $R/sp_xing_lpo.json --from-ocv --parts ocv --scale 1.0 --samples 2000 --out $R/bind.json > $R/bind.log 2>&1; echo BIND_RC $?
tail -c 1500 $R/bind.log; echo
for KEY in region part; do for HB in none HB4; do
  python3 -I $MT/die_plan/die_sta_related.py $PR --plan $PL --out $R/sta_${KEY}_$HB --cppr-lca --clock-ocv table --clock-droop shared \
    --clock-cal spice --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers $HB --landing-window-ps 416.5 \
    --count-align $R/bind.json --count-align-key $KEY > $R/sta_${KEY}_$HB.log 2>&1; echo "STA_RC $KEY $HB $?" &
done; done; wait
for f in $R/sta_*.log; do echo "== $f"; grep -E "pairs|SUMMARY|count.align|unbound" $f | cut -c1-600; done
echo CA_GATE_DONE $(date)
