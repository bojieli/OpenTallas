#!/usr/bin/env bash
# Usage: run.sh <fresh out dir>   (run from the repo/worktree root)
set -euo pipefail
O=${1:?out};mkdir -p "$O"
V=verilator;[ ! -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] || V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version >"$O/verilator_version.txt"
H=rtl/dsrom_sys/s81_dv/hostb;T=tools/s81_dv/hostctx_1021
python3 -I $T/gen_vectors.py "$O/vec" >"$O/gen.log"
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_hostb_stage_hbc -Mdir "$O/obj" \
 rtl/lib/ot_reset_sync.sv $H/dsdv_hostb_hold.sv $H/dsdv_hostb_crc512.sv $H/dsdv_hostb_rx.sv $H/dsdv_hostb_tx.sv \
 $H/dsdv_hostb_stage.sv $H/dsdv_hbc1_loader.sv $H/dsdv_hbc1_affine_book.sv $H/dsdv_hostb_stage_hbc.sv $T/tb_hostb_stage_hbc.sv \
 --build-jobs 4 >"$O/build.log" 2>&1 || { tail -40 "$O/build.log"; exit 1; }
rc=0
for m in 0 1 2 3 4 5;do "$O/obj/Vtb_hostb_stage_hbc" +VEC="$O/vec" +MODE=$m >"$O/mode$m.log" 2>&1 || rc=1;grep -E "RESULT|PASS|FAIL|Error" "$O/mode$m.log";done
exit $rc
