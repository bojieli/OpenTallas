#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mut=${1:-0};v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary --timing -j 2 -Wno-fatal --top-module tb_hbm_b2_peer_lease -GMUT="$mut" --Mdir "obj_$mut" ot_hbm_b2_peer_lease.sv tb_hbm_b2_peer_lease.sv > "build_$mut.log" 2>&1 || { tail -25 "build_$mut.log";exit 2; }
set +e
./obj_$mut/Vtb_hbm_b2_peer_lease > "run_$mut.log" 2>&1
rc=$?
set -e
cat "run_$mut.log"
if [ "$rc" -ne 0 ];then exit "$rc";fi
grep -q '^NATIVE_PEER_LEASE PASS' "run_$mut.log"
