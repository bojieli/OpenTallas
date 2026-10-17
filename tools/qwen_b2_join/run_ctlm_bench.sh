#!/bin/bash
set -eu
out=$1
mkdir -p "$out"
sha256sum $(cat tools/qwen_b2_join/controller_sources.f) > "$out/source.sha256"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for mut in 0 1; do
 opt="";if [ "$mut" = 1 ];then opt=-DOT_QFD_B2_AM_MUT;fi
 "$VL" --binary --timing -j 8 -O1 -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -DOT_QFDS_LU=53 -DOT_QFDS_LS=376 $opt -Wno-fatal -Wno-TIMESCALEMOD -Irtl/hdc --top-module tb_b2_ctlm --Mdir "$out/obj$mut" -f tools/qwen_b2_join/controller_sources.f > "$out/build$mut.log" 2>&1
 if "$out/obj$mut/Vtb_b2_ctlm" > "$out/run$mut.log" 2>&1;then test "$mut" = 0;else test "$mut" = 1;fi
done
cat "$out/run0.log"
