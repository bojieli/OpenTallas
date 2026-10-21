#!/bin/bash
set -euo pipefail
mkdir -p ../sector_native2
$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys -Q -T -s results/rtl/hbm_qcore_r16_write_1021/sector_native2.ys > ../sector_native2/synth.log 2>&1
args=(); for f in libs/*.lib;do args+=(--liberty "$f");done
python3 tools/ref_tile/native_census.py --netlist ../sector_native2/mapped.v --top ot_hbm_su_qcore_r13_sec --kit qcore_r16_actual_sector7 --out ../sector_native2/native.json "${args[@]}" > ../sector_native2/native.log 2>&1
