#!/bin/bash
# DIE-QC-2 post for a run dir RD (out_TT/out_FF/clk): lpo + count-aligned + proof + die STA (region CPPR and --cppr-lca)
set -u
RD=$1; D=/srv/opentallas-scratch2/claude/die-qc2-1027
W=/srv/opentallas-scratch2/claude/wt/qc-sliceclk-1027
R=${REGIONS:-/srv/opentallas-scratch2/claude/qc-sliceclk-1027/fs/regions.json}; PLAN=$W/physical/die_plan/qwen_compute/die_plan_sliceclk.json
XP=${XPLAN:-/srv/opentallas-scratch2/claude/qc-sliceclk3-1027/lpo/crossings_plan.json}
log(){ echo "$* $(date)" >> $RD/post.log; }
cd $RD
python3 -I $W/tools/s81_head/landed_phase_ocv.py $XP $RD --tools $W/tools/die_plan --out $RD/lpo_routed.json > $RD/lpo_routed.log 2>&1; log "lpo rc $?"
python3 -I $D/ca_qc.py $RD/lpo_routed.json $R /srv/opentallas-scratch2/claude/qc-sliceclk3-1027/ca $RD/qc_routed_ca > $RD/ca_routed.log 2>&1; log "ca rc $?"
SPICE_SCALE=1.05 python3 -I $D/ca_qc.py $RD/lpo_routed.json $R $D/cap_mi $RD/qc_routed_ca_mi105 > $RD/ca_mi105.log 2>&1; log "ca_mi rc $?"
python3 -I $D/mk_proof.py $RD $R $RD/proof > $RD/proof.log 2>&1; log "proof rc $?"
for M in region lca lcaHB4; do X=""; HB=none; [ $M != region ] && X=--cppr-lca; [ $M = lcaHB4 ] && HB=HB4
  ~/.local/bin/ot-run --mem 32 --threads 4 --hosts localhost --dir $RD --priority die -- python3 -I $W/tools/die_plan/die_sta_related.py $RD/proof --plan $PLAN --out $RD/sta_$M --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $RD/proof/droop_regions.json --hold-buffers $HB $X > $RD/sta_$M.log 2>&1; log "sta $M rc $?" &
done; wait
log POST_DONE
