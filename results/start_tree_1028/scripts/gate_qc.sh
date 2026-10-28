#!/bin/bash
# START-TREE-1: bind + die STA (gate form) on QC t6 with --start-tree clock (estimate inputs, no build)
MT=/srv/opentallas-scratch2/claude/wt/start-tree-1/tools/die_plan; T=/srv/opentallas-scratch2/claude/die-qc9-1028/ca/t6; PR=$T/proof
PL=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/event/qc_k2b_phase12.json; O=/srv/opentallas-scratch2/claude/start-tree-1/qc
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
cd $O
python3 $MT/count_align_bind.py $T/grp_spice_xing_lpo.json --from-ocv --parts ocv --samples 500 $F --start-tree clock --out bind_clock.json > bind_clock.log 2>&1; echo "bind rc $?" > gate_rc.txt
python3 $MT/die_sta_related.py $PR --plan $PL --out sta_clock --corner TT --corner FF --clock-ocv table --clock-droop shared \
  --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice \
  --count-align bind_clock.json --count-align-key region > sta_clock.log 2>&1; echo "sta rc $?" >> gate_rc.txt
echo DONE $(date) >> gate_rc.txt
