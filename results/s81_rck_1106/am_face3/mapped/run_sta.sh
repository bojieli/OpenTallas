#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/codex-s81-rck-1106
cd "$W/am_map_fa"
python3 sta_prepare.py
for top in old_am new_am; do
 docker run --rm --memory 4g --cpus 2 -v "$W":/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -p 'read_json /work/am_map_fa/$top.json; hierarchy -top $top; write_verilog -noattr -noexpr -norename /work/am_map_fa/$top.mapped.v'" > "$top.export.log" 2>&1
 for corner in TT FF; do
  docker run --rm --memory 4g --cpus 2 -e OT_CORNER="$corner" -v "$W":/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 2 -exit /work/am_map_fa/$top.sta.tcl" > "$top.$corner.sta.log" 2>&1
 done
done
