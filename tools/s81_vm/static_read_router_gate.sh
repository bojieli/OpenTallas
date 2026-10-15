#!/bin/bash
set -euo pipefail
S=${1:?flat snapshot};O=${2:?outdir};mkdir -p "$O"
F=("$S/dsfd_vm_static_read_leaf.sv" "$S/dsfd_vm_static_read_quartets.sv" "$S/dsfd_vm_static_read_valid.sv" "$S/dsfd_vm_static_read_valid_quartets.sv" "$S/dsfd_vm_static_read_router.sv" "$S/dsfd_vm_static_read_quartets_p.sv" "$S/dsfd_vm_static_read_valid_quartets_p.sv" "$S/dsfd_vm_static_read_router_p.sv" "$S/tb_dsfd_vm_static_read_router.sv")
# VM_READ_PIPE=2: the pin-registered router (dsfd_vm_static_read_router_p, L14)
P=(); [ "${VM_READ_PIPE:-1}" != 2 ] || P=(-DOT_VM_NATIVE_READ_PINREG)
for name in base select su1 early;do
 d=();case $name in select)d=(-DOT_VM_READ_MUT_SELECT);;su1)d=(-DOT_VM_READ_MUT_SU1);;early)d=(-DOT_VM_READ_MUT_EARLY);;esac
 iverilog -g2012 "${P[@]}" "${d[@]}" -s tb_dsfd_vm_static_read_router -o "$O/$name" "${F[@]}"
done
for seed in 1 2;do vvp "$O/base" +mode=0 +seed=$seed > "$O/base_s$seed.log";grep -q 'READ_ROUTER PASS mode0 ' "$O/base_s$seed.log";done
for mode in 1 2 3;do vvp "$O/base" +mode=$mode > "$O/fault_m$mode.log";grep -q "READ_ROUTER PASS mode$mode " "$O/fault_m$mode.log";done
for name in select su1 early;do vvp "$O/$name" +mode=0 > "$O/mut_$name.log";grep -q 'READ_ROUTER FAIL mode0 ' "$O/mut_$name.log";done
echo 'STATIC_READ_ROUTER_GATE PASS'
