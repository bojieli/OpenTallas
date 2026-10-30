#!/bin/bash
set -eu
F=/srv/opentallas-scratch2/claude/codex-kv-1030
O=/srv/opentallas-scratch2/claude/codex-kv-2249
cd "$F"
python3 src/tools/die_plan/start_stage_emit.py proof "$O/proof_components_data_only" --stages /srv/opentallas-scratch2/claude/die-kv-41-1029/start_wc/emitted/start_stages.json --arr TT="$O/edges_TT/arr_TT.txt" --arr FF="$O/edges_FF/arr_FF.txt" --clock-netlist /srv/opentallas-scratch2/claude/die-kv-41-1029/start_wc/emitted/ctree.v --out proof_components_loaded
cp /srv/opentallas-scratch2/claude/die-kv-41-1029/start_wc/emitted/ctree.v proof_components_loaded/
mkdir -p sta_components_loaded_spice_cell
cp -a regchar sta_components_loaded_spice_cell/
CV=()
for n in 1 2 5 6; do M=kv3_head_eighth_e$n; CV+=(--core-view "$M=/srv/opentallas-scratch2/claude/autopilot/closed/qwen_kvsys/${M}__3e7fccd216/view/$M"); done
python3 src/tools/die_plan/die_sta_related.py proof_components_loaded --plan "$O/plan_wc.json" --out sta_components_loaded_spice_cell --clock-cal spice_cell --cppr-lca --count-align nativeB_full.json --count-align-key region --clock-ocv table --clock-droop shared --droop-regions proof_components_loaded/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv "${CV[@]}" --core-insertion view --count-align-ss-scale 0 >sta_components_loaded_spice_cell.log 2>&1
