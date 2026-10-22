#!/bin/bash
# HBMb/HC-SFU 10-21: FPIPE fault-tree bench (positive + OT_SFU_FTREE_MUT_DROP13 negative control), Verilator 5.050.
set -euo pipefail
: "${OUT:?output directory required}"; mkdir -p "$OUT"; OUT=$(realpath "$OUT")
p=rtl/hbm_accel/generic/peers; m=physical/asap7_memory_macros
src=(rtl/test/hbm_accel/generic/tb_hgi_sfu_store_fault_pipe.sv $p/ot_hgi_sfu_fault_tree.sv $p/ot_hgi_sfu_static_operand_store.sv $p/ot_hgi_su_unit.sv "$m/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$m/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" "$m/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v")
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; "$v" --version
sha256sum "${src[@]}" > "$OUT/bench_inputs.sha256"
for cfg in pos mut;do
 d=();[ $cfg = mut ] && d=(-DOT_SFU_FTREE_MUT_DROP13)
 "$v" --binary --timing -j 8 -O1 -Wno-fatal "${d[@]}" --top-module tb_hgi_sfu_store_fault_pipe --Mdir "$OUT/$cfg" "${src[@]}" > "$OUT/$cfg.build.log" 2>&1
 set +e; "$OUT/$cfg/Vtb_hgi_sfu_store_fault_pipe" > "$OUT/$cfg.log" 2>&1; rc=$?; set -e
 if [ $cfg = pos ];then [ $rc = 0 ] && grep 'PASS SFU_FAULT_PIPE' "$OUT/$cfg.log" || { tail -5 "$OUT/$cfg.log"; exit 1; }
 else [ $rc != 0 ] && grep -q 'FPIPE_AGE' "$OUT/$cfg.log" && echo "SFU_FAULT_PIPE MUT_DROP13 REJECTED: $(grep -m1 FPIPE_ "$OUT/$cfg.log")" || { echo "MUT ESCAPED"; exit 1; }; fi
done
