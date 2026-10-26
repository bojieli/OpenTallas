#!/bin/bash
set -euo pipefail
O=${1:?output};mkdir -p "$O"
trap 'printf "%s\n" "$?" > "$O/exit"' EXIT
D=physical/hbm_accel_die_views/vm/checker9
MUT=(); if [[ ${VM_CK_MUT:-} == IGNORE ]]; then MUT=(-DMUT_CK_IGNORE); fi
verilator --binary --timing -j 8 --unroll-count 16 -Wno-fatal "${MUT[@]}" --top-module tb_vm_ck4 -Mdir "$O/obj" -o sim "$D/vm_ck4.sv" "$D/tb_vm_ck4.sv" > "$O/build.log" 2>&1
"$O/obj/sim" > "$O/run.log" 2>&1
cat "$O/run.log"
grep -q 'VM_CK4 PASS cases=' "$O/run.log"
