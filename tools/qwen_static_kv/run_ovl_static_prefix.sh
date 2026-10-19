#!/bin/bash
set -eu
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version | tee verilator.txt;grep -q '5.050' verilator.txt
mkdir -p out
for mut in 0 1 2;do
 O="$PWD/out/obj_m$mut"
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_ovl_static_prefix -GMUT=$mut --Mdir "$O" rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_ovl_seq.sv rtl/test/qwen_split/tb_ovl_static_prefix.sv > out/build_m$mut.log 2>&1
 set +e
 "$O/Vtb_ovl_static_prefix" > out/run_m$mut.log 2>&1;r=$?
 set -e
 cat out/run_m$mut.log
 if [ "$mut" = 0 ];then test "$r" = 0;grep -q STATICPREFIX_PASS out/run_m$mut.log;else test "$r" != 0;grep -q STATICPREFIX_FAIL out/run_m$mut.log;fi
done
echo STATICPREFIX_MATRIX_PASS
