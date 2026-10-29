#!/bin/bash
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/codex-head-start-0828
R=/srv/opentallas-scratch2/claude/codex-head-start-0828/hk5_leaf2
T=/srv/opentallas-scratch2/claude/codex-head-ca-0840
H=/srv/opentallas-scratch2/claude/head-start-4
mkdir -p "$R"
python3 "$W/tools/s81_head/head_start_leaf_frames.py" "$T/ca2/region_ocv.json" --regions "$T/inputs/regions.json" --out "$R/leaf_ocv.json" > "$R/leaf_ocv.log"
python3 "$W/tools/s81_head/head_start_capture_sites.py" "$T/inputs/plan.json" "$T/ca2/proof/tap_arrivals_TT.json" --out "$R/capture" > "$R/capture.log"
python3 "$W/tools/die_plan/count_align_plan.py" "$R/leaf_ocv.json" --corner TT_droop-regions_corelat450,FF_droop-regions_corelat380 --sta-proof "$T/ca2/proof" --sta-plan "$R/capture/plan.json" --sta-clock-cal spice_cell --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$T/ca2/proof/droop_regions.json" --sta-core-latency-ff 380 --sta-ca-ring "$H/ca_ring_hd_tile_dh20.json" --sta-clock-cell inv --start-tree clock --start-leaf-origins --start-capture-taps "$R/capture/capture_taps.json" --start-clean width --start-max-hop-um 360 --start-retime-max 64 --mc-chips 2000 --out "$R/plan.json" > "$R/plan.log" 2>&1
python3 "$W/tools/s81_head/head_start_leaf_bind.py" "$R/plan.json" --table "$T/ca2/table.json" --regions "$T/inputs/regions.json" --die "$R/capture/plan.json" --out "$R/bind" > "$R/bind.log"
python3 "$W/tools/die_plan/start_stage_emit.py" emit "$R/bind/bind.json" "$T/ca2/proof" --ctree "$T/fresh/clk" --plan "$R/capture/plan.json" --out "$R/stages" > "$R/stages.log"
python3 "$W/tools/die_plan/reset_tree.py" offsets "$R/capture/plan.json" --out "$R/reset_offsets.json" > "$R/reset_offsets.log"
python3 "$W/tools/s81_head/head_start_reset_exports.py" "$R/capture/plan.json" "$R/reset_offsets.json" "$R/stages/start_stages.json" --out "$R/exports0.json" > "$R/exports.log"
python3 - "$W" "$R" <<'PY'
import json,sys
from pathlib import Path
w,r=map(Path,sys.argv[1:]);sys.path.insert(0,str(w/'tools/s81_head'))
from head_start_reset_aliases import reuse_existing
x=reuse_existing(json.load(open(r/'exports0.json')),json.load(open(r/'reset_offsets.json')))
(r/'exports.json').write_text(json.dumps(x,indent=1)+'\n')
settle=max(74,x['summary']['max_relative_raw_release']+4)
(r/'settle.txt').write_text(str(settle)+'\n')
print(json.dumps(x['summary']), 'settle',settle)
PY
python3 "$W/tools/s81_head/head_start_local_reset.py" "$R/stages" "$R/exports.json" --settle "$(cat "$R/settle.txt")" --out "$R/provider" > "$R/provider.log"
