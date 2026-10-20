#!/bin/bash
set -eu
R=/srv/opentallas-scratch/codex/kv-ahub6
B=/srv/opentallas-scratch/claude/ref_gate/qkd_ahub_g4a-20261019-215713
W=$R/control_work_v7
sed -n 's/.*Executing Liberty frontend: //p' "$W"/logs/asap7/*/base/1*log | sort -u > "$W/actual_liberties.txt"
cp "$R/tools/ref_tile/native_census.py" "$W/native_census.py"
cp "$R/tools/textbook_lint.py" "$W/textbook_lint.py"
docker run --rm -e PYTHONPATH=/work -v "$B/src:/src:ro" -v "$W:/work" openroad/orfs:asap7lock bash -lc 'set -eu; args=();while IFS= read -r x;do args+=(--liberty "$x");done < /work/actual_liberties.txt; python3 /work/native_census.py --netlist /work/results/asap7/opentallas_qkd_ahub_static_dw_g3_lp_asap7_ref_gate/base/1_2_yosys.v --top qkd_ahub_static_dw_g3_lp "${args[@]}" --out /work/mandatory_native.json'
