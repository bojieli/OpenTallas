#!/bin/bash
# DIE-QC-11: START-TREE-1 --start-tree clock (91c2e9fec3, exported tools) on trial8 BUILT arrivals: plan phase + width, bind, die STA (FF hold with --hold-buffers none)
MT=/srv/opentallas-scratch2/claude/die-qc11-1028/st_tools/tools/die_plan; T=/srv/opentallas-scratch2/claude/die-qc10-1028/ca/t8; PR=$T/proof
PL=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/event/qc_k2b_phase12.json; O=/srv/opentallas-scratch2/claude/die-qc11-1028/st8
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
cd $O
for M in phase width; do python3 $MT/count_align_plan.py $T/grp_spice_xing_lpo.json $F --start-tree clock --start-clean $M --mc-chips 300 --out plan_$M.json > plan_$M.log 2>&1; echo "plan $M rc $? $(date)" >> rc.txt; done
python3 $MT/count_align_bind.py $T/grp_spice_xing_lpo.json --from-ocv --parts ocv --samples 500 $F --start-tree clock --out bind_clock.json > bind_clock.log 2>&1; echo "bind rc $? $(date)" >> rc.txt
python3 $MT/die_sta_related.py $PR --plan $PL --out sta_clock --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align bind_clock.json --count-align-key region > sta_clock.log 2>&1; echo "sta rc $? $(date)" >> rc.txt
echo DONE $(date) >> rc.txt
