#!/bin/bash
set -eu
cd "$(dirname "$0")"
verilator --version > endpoint_verilator.txt
for m in 0 1 2 3 4 5; do
 verilator --binary --timing -Wno-fatal --top-module endpoint_tb -GM=$m -j 8 --Mdir obj_endpoint_$m private/qkd_host_native_token_endpoint_cancel_rc.sv endpoint_original.sv endpoint_tb.sv > endpoint_build_$m.log 2>&1
 set +e
 obj_endpoint_$m/Vendpoint_tb > endpoint_run_$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ]; then test "$rc" = 0; grep -q ENDPOINT_PASS endpoint_run_$m.log; else test "$rc" != 0; fi
 case "$m" in 1) grep -q OWNER_LOST endpoint_run_$m.log;; 2) grep -q RAWDONE_DEBT endpoint_run_$m.log;; 3) grep -q POST_POISON_ISSUE endpoint_run_$m.log;; 4) grep -q CANCEL_DRAIN_STUCK endpoint_run_$m.log;; 5) grep -q PROTOCOL_DRAIN_STUCK endpoint_run_$m.log;; esac
done
printf 'ENDPOINT_SUITE_PASS\n'
