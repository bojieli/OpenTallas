#!/bin/bash
set -euo pipefail
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in positive mutant;do
 flag=;if [ "$m" = mutant ]; then flag=-DOT_QFD_NATIVE_TREE_MUT;fi
 "$VL" --binary --timing -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -DOT_QFDS_LU=53 -DOT_QFDS_LS=376 -j 8 -O1 -Wno-fatal -Wno-TIMESCALEMOD -Irtl/hdc $flag --top-module tb_native_band_tree_tp8 --Mdir obj_$m -f native_join.f rtl/test/qwen_split/tb_native_band_tree_tp8.sv > bench_build_$m.log 2>&1
 set +e
 obj_$m/Vtb_native_band_tree_tp8 > bench_$m.log 2>&1
 rc=$?
 set -e
 echo "$rc" > bench_$m.exit
 if [ "$m" = positive ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];fi
done
