#!/bin/bash
# DIE-QC-6 freeze-gate re-run on K2 with MESO-START-2 tools (fbb34b6aac, carries DIE-QC-5 STA fixes) + --tree-parent x3
# (COORD 03:36), event plan 40b05f16d753 for STA, --count-align-key region, --clock-cal spice, --cppr-lca. usage: runG.sh TAG
set -u
B=/srv/opentallas-scratch2/claude/die-qc6-1028; C=/srv/opentallas-scratch2/claude/die-qc4-1028/K2/CA_2w2s
PLAN=/srv/opentallas-scratch2/claude/die-qc4-1028/plan_grpP/event/qc_grpP_event.json
MT=/srv/opentallas-scratch2/claude/wt/meso-start-2/tools/die_plan; O=$B/$1; mkdir -p $O; X=$C/grp_spice_xing_lpo.json
TP="--tree-parent c_W0_tn_10=c_W0_tn_00__a22__0 --tree-parent c_E4_tn_10=c_E4_tn_00__a22__0 --tree-parent c_W0_bn_10=c_W0_bn_00__a22__0"
python3 -I $MT/count_align_plan.py $X $TP --out $O/plan.json > $O/plan.log 2>&1; echo "plan rc $? $(date)" >> $O/chain.log
python3 -I $MT/count_align_bind.py $X --from-ocv --parts ocv --samples 2000 $TP --out $O/bind.json > $O/bind.log 2>&1; echo "bind rc $? $(date)" >> $O/chain.log
for HB in none HB4; do
  python3 -I $MT/die_sta_related.py $C/proof --plan $PLAN --out $O/sta_$HB --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $C/proof/droop_regions.json --hold-buffers $HB --cppr-lca --clock-cal spice --count-align $O/bind.json --count-align-key region > $O/sta_$HB.log 2>&1; echo "sta $HB rc $? $(date)" >> $O/chain.log &
done; wait; echo DONE >> $O/chain.log
