#!/bin/bash
set -euo pipefail
K=$1
T=/srv/opentallas-scratch2/claude/codex-qc-cores-0815/source_tools/die_plan
B=$K/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m0/base
grep -q 'CLKUNION changed_nets 0 of 106' "$K/clock_union.log"
cp "$K/eco_out/6_final.odb" "$K/eco_out/6_final.spef" "$K/eco_out/6_final.v" "$B/"
python3 -I "$T/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --ff-vclk auto --out "$K/signoff_f4k" > "$K/signoff_f4k.log" 2>&1 || SO=$?
docker run --rm --cpus 8 --memory 24g -v "$K":/work -v "$T":/tools:ro openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /tools/lec.py /work --netlist /work/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m0/base/6_final.v --out /work/lec_f4k' > "$K/lec_f4k.log" 2>&1 || LEC=$?
echo "F4K_CHAIN_DONE signoff=${SO:-0} lec=${LEC:-0} $(date -Is)" > "$K/f4k_chain.txt"
exit "${SO:-0}"
