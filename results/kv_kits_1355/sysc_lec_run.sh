#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-kits-1355/sysc_fix
WT=/srv/opentallas-scratch2/claude/wt/codex-kv-kits-1355
sudo docker run --rm --name codex-kv-sysc-lecfix-1355 --cpus 8 --memory 64g --memory-swap 64g -v "$R/kit":/work -v "$WT/tools/die_plan":/src -w /work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /src/lec.py /work --netlist /work/run/results/asap7/dp_kv3_sys_c/base/1_2_yosys.v --out /work/lec_fix" > "$R/lec_fix.log" 2>&1
