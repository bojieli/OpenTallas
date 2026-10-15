#!/bin/bash
set -euo pipefail
# Component port-observation proof; run independently of native producer schedule qualification.
S=${1:?flat source snapshot};O=${2:?outdir};mkdir -p "$O"
for name in base densecount slice dlat;do
 defs=();case $name in densecount)defs=(-DOT_VMSS_MUT_DENSECOUNT);;slice)defs=(-DOT_VMSS_MUT_SLICE);;dlat)defs=(-DOT_VMSS_MUT_DLAT);;esac
 iverilog -g2012 "${defs[@]}" -s tb_dsfd_vm_seq_sparse -o "$O/$name" "$S/dsfd_vm_seq_static.sv" "$S/tb_dsfd_vm_seq_sparse.sv"
done
for m in 0 1 2 3 4 5 6 7 8 9;do
 vvp "$O/base" +mode=$m > "$O/base_mode$m.log"
 grep -q "SPARSE PASS mode$m " "$O/base_mode$m.log"
done
for name in densecount slice dlat;do
 vvp "$O/$name" +mode=0 > "$O/mut_$name.log"
 grep -q 'SPARSE FAIL mode0 ' "$O/mut_$name.log"
done
echo 'SPARSE_ENGINE_GATE PASS'
