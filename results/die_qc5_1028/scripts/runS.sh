#!/bin/bash
# DIE-QC-4 die STA (main die_sta_related --cppr-lca, table OCV, shared droop per region, spice-scaled clock) on RD/proof. usage: runS.sh RD [HB4]
set -u
RD=$1; HB=${2:-none}; W=/srv/opentallas-scratch2/claude/wt/die-qc4-1028; PLAN=${PLAN:-$W/physical/die_plan/qwen_compute/die_plan_sliceclk.json}
M=lca; [ $HB = HB4 ] && M=lcaHB4
python3 -I /srv/opentallas-scratch2/claude/wt/die-qc5-1028/tools/die_plan/die_sta_related.py $RD/proof --plan $PLAN --out $RD/sta_$M --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $RD/proof/droop_regions.json --hold-buffers $HB --cppr-lca > $RD/sta_$M.log 2>&1
echo "sta $RD $M rc $? $(date)" >> /srv/opentallas-scratch2/claude/die-qc5-1028/chain.log
