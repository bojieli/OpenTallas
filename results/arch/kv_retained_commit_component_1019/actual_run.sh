#!/usr/bin/env bash
set -euo pipefail
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
mkdir -p actual_out
/usr/bin/time -v "$V" --binary --timing -Wno-fatal -j 8 --top-module actual_ingress_reset_tb --Mdir actual_out/obj -f results/arch/kv_retained_commit_component_1019/actual_files.txt >actual_out/build.log 2>&1
/usr/bin/time -v actual_out/obj/Vactual_ingress_reset_tb >actual_out/trace.log 2>&1
cat actual_out/trace.log
du -sh actual_out/obj

/usr/bin/time -v "$V" --binary --timing -Wno-fatal -j 8 --top-module actual_ingress_reset_tb -GING_MUT=1 --Mdir actual_out/mut_obj -f results/arch/kv_retained_commit_component_1019/actual_files.txt >actual_out/mut_build.log 2>&1
set +e
actual_out/mut_obj/Vactual_ingress_reset_tb >actual_out/mut_ingress_bypass.log 2>&1
mut_rc=$?
set -e
if [ "$mut_rc" = 0 ] || ! grep -Eq "RESERVED_CSR_RESTART|RESERVATION_EXCLUSION_MISSING" actual_out/mut_ingress_bypass.log; then
 echo "FAIL ingress bypass mutant was not causally caught";exit 1
fi
echo "PASS causal ingress admission bypass mutant"
cat actual_out/mut_ingress_bypass.log
