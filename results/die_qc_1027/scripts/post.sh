#!/bin/bash
# DIE-QC post: measured crossing margins (current ring + count-aligned) + main die STA related pairs on the routed clock
set -u
W=/srv/opentallas-scratch2/claude/wt/qc-sliceclk-1027; D=/srv/opentallas-scratch2/claude/die-qc-1027
R=/srv/opentallas-scratch2/claude/qc-sliceclk-1027/fs/regions.json; PLAN=$W/physical/die_plan/qwen_compute/die_plan_sliceclk.json
log(){ echo "$* $(date)" >> $D/chain.log; }
cd $D
python3 -I $W/tools/s81_head/landed_phase_ocv.py /srv/opentallas-scratch2/claude/qc-sliceclk3-1027/lpo/crossings_plan.json $D --tools $W/tools/die_plan --out $D/lpo_routed.json > $D/lpo_routed.log 2>&1; log "lpo rc $?"
python3 -I $D/ca_qc.py $D/lpo_routed.json $R /srv/opentallas-scratch2/claude/qc-sliceclk3-1027/ca $D/qc_routed_ca > $D/ca_routed.log 2>&1; log "ca rc $?"
python3 -I $D/mk_proof.py $D $R $D/proof > $D/proof.log 2>&1; log "proof rc $?"
for HB in none HB4; do
  ~/.local/bin/ot-run --mem 32 --threads 4 --hosts localhost --dir $D --priority die -- python3 -I $W/tools/die_plan/die_sta_related.py $D/proof --plan $PLAN --out $D/sta_$HB --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $D/proof/droop_regions.json --hold-buffers $HB > $D/sta_$HB.log 2>&1; log "sta $HB rc $?"
done
log POST_DONE
