#!/bin/bash
set -eu
ROOT=$PWD;OUT=$ROOT/out_p192_1;mkdir -p "$OUT"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for case_name in exact mutant_addr mutant_bypass;do
 defs=();[ "$case_name" != mutant_addr ] || defs+=(-DOT_MUT_MEMM)
 [ "$case_name" != mutant_bypass ] || defs+=(-DOT_CDC_IBMEM_MUT_NOBYPASS)
 "$V" --version > "$OUT/version.txt"
 "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_safe -Mdir "$OUT/obj_$case_name" -j 4 -o sim "${defs[@]}" $(cat rtl/test/host_cdc_safe_1020/sources.f) > "$OUT/$case_name.build.log" 2>&1 || { tail -30 "$OUT/$case_name.build.log";exit 2; }
 set +e
 "$OUT/obj_$case_name/sim" > "$OUT/$case_name.log" 2>&1
 rc=$?
 set -e
 if [ "$case_name" = exact ];then [ "$rc" = 0 ] && grep -q '^PASS HOST_CDC_SAFE' "$OUT/$case_name.log";else [ "$rc" != 0 ] && grep -q '^FAIL' "$OUT/$case_name.log";fi
 tail -3 "$OUT/$case_name.log"
done
