#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?outdir}"); M=${2:-0}; mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mapfile -t SRCS < <(python3 -c 'import json;print("\n".join(json.load(open("physical/ref_tile/dscoll_lane_w_s12g/spec.json"))["sources"]))')
D=(-DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF -DOT_COLL_REACH8 -DOT_COLL_REACH8N -DOT_S81PH_COLL_TF_CLEANUP)
case "$M" in 0) ;;5) D+=(-DOT_COLL_REACH_MUT_LR);;6) D+=(-DOT_COLL_REACH_MUT_LO);;7) D+=(-DOT_COLL_REACH_MUT_RT);;8) D+=(-DOT_COLL_REACH_MUT_WL);;*) exit 2;;esac
for N in physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1; do SRCS+=("$N/$(basename "$N").v");done
"$V" --version
"$V" --binary --timing -j "${J:-4}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-MULTIDRIVEN "${D[@]}" -GCORE_CRED=12 --top-module tb_coll_reach7 --Mdir "$O/obj" "${SRCS[@]}" rtl/dsrom_sys/s81_ph/test/tb_coll_reach7.sv > "$O/build.log" 2>&1 || { tail -35 "$O/build.log";exit 3;}
set +e
"$O/obj/Vtb_coll_reach7" > "$O/run.log" 2>&1
rc=$?
set -e
tail -20 "$O/run.log"
echo "sim exit $rc"
grep -q '^COLL_REACH7 PASS' "$O/run.log"
