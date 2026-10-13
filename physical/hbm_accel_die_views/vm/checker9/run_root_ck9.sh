#!/bin/bash
set -euo pipefail
O=${1:?output};mkdir -p "$O"
trap 'printf "%s\n" "$?" > "$O/exit"' EXIT
D=physical/hbm_accel_die_views/vm/checker9
TB=${VM_CK_TB:-tb_vm_root_ck9}
MUT=();if [[ ${VM_CK_MUT:-} == IGNORE ]];then MUT=(-DMUT_CK_IGNORE);fi
if [[ ${VM_CK_BASELINE:-} == 1 ]];then MUT+=(-DVM_CK_BASELINE);fi
verilator --binary --timing -j 8 --unroll-count 8192 -Wno-fatal "${MUT[@]}" --top-module "$TB" -Mdir "$O/obj" -o sim "$D/vm_ck4.sv" "$D/vm_ck4_state.sv" "$D/vm_root_ctl9.sv" "$D/vm_root_ck9.sv" "$D/$TB.sv" physical/hbm_accel_die_views/vm/tiles/ot_hfd_vm_root_x.sv > "$O/build.log" 2>&1
"$O/obj/sim" > "$O/run.log" 2>&1
cat "$O/run.log"
if [[ "$TB" == tb_vm_root_rate ]];then grep -q "VM_ROOT_RATE PASS" "$O/run.log";else grep -q "VM_ROOT_CK9 COMPONENT PASS" "$O/run.log";fi
