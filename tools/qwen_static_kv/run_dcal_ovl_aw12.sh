#!/bin/bash
set -eu
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version | tee verilator.txt
grep -q '5.050' verilator.txt
D=rtl/qwen_sys/d2d_static_20261015
for trunc in 0 1; do
 O=out/obj_t${trunc};mkdir -p "$O"
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -I"$D" --top-module tb_kv_dcal_ovl_aw12 -GTRUNC=$trunc --Mdir "$PWD/$O" physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v "$D/ot_qwen_d2d_cal_seq.sv" "$D/ot_qwen_d2d_ovl_seq.sv" "$D/qkd_d2d_cal_seq_ovl_bootcfg.sv" rtl/test/qwen_split/tb_kv_dcal_ovl_aw12.sv > out/build_t${trunc}.log 2>&1
 set +e
 "$O/Vtb_kv_dcal_ovl_aw12" +MUT=$((trunc*7)) > out/run_t${trunc}.log 2>&1
 r=$?
 set -e
 cat out/run_t${trunc}.log
 if [ "$trunc" = 0 ]; then test "$r" = 0;grep -q KDCALAW12_PASS out/run_t0.log;else test "$r" != 0;grep -q 'static TX/RX start edge mismatch' out/run_t1.log;fi
done
bash tools/qwen_static_kv/run_dcal_ovl_bc.sh "$PWD/out/legacy" 0 > out/legacy.log 2>&1
echo AW12_MATRIX_PASS
