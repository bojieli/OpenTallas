#!/bin/bash
set -eu
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version | tee verilator.txt;grep -q '5.050' verilator.txt
mkdir -p out
for mut in 0 1 2;do
 O="$PWD/out/obj_m$mut"
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_sysface_accepted_ctx -GMUT=$mut --Mdir "$O" rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv rtl/qwen_split/qfd_sys_face_accepted_mu_ctx.sv rtl/test/qwen_split/tb_sysface_accepted_ctx.sv > out/build_m$mut.log 2>&1
 set +e
 "$O/Vtb_sysface_accepted_ctx" > out/run_m$mut.log 2>&1;r=$?
 set -e
 cat out/run_m$mut.log
 if [ "$mut" = 0 ];then test "$r" = 0;grep -q ACCEPTCTX_PASS out/run_m$mut.log;else test "$r" != 0;grep -q ACCEPTCTX_FAIL out/run_m$mut.log;fi
done
echo ACCEPTCTX_MATRIX_PASS
