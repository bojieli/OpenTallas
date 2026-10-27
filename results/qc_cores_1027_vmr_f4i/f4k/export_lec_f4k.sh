#!/bin/bash
set -euo pipefail
K=$1
T=/srv/opentallas-scratch2/claude/codex-qc-cores-0815/source_tools/die_plan
docker run --rm --memory 8g --cpus 2 -v "$K":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/export_logic.tcl' > "$K/export_logic.log" 2>&1
docker run --rm --cpus 8 --memory 24g -v "$K":/work -v "$T":/tools:ro openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /tools/lec.py /work --netlist /work/eco_out/6_final_logic.v --out /work/lec_f4k_logic' > "$K/lec_f4k_logic.log" 2>&1
