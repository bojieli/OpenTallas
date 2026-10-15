#!/bin/bash
set -eu
O=${1:?output};S=rtl/dsrom_sys/s81_ph;mkdir -p "$O"
for variant in base mdata maddr;do
 define=;case $variant in mdata)define=-DOT_VM_DIRECT_SCATTER_MUT_DATA;;maddr)define=-DOT_VM_DIRECT_SCATTER_MUT_ADDR;;esac
 iverilog -g2012 $define -s tb_dsfd_vm_static_direct_scatter -o "$O/$variant" "$S/vm/dsfd_vm_static_scatter.sv" "$S/vm/dsfd_vm_static_write_capture128.sv" "$S/vm/dsfd_vm_static_scatter_b8_out.sv" "$S/test/tb_dsfd_vm_static_direct_scatter.sv" > "$O/build_$variant.log" 2>&1
 if [ "$variant" = base ];then
  for mode in 0 1 2;do vvp "$O/base" +mode=$mode > "$O/base_$mode.log" 2>&1;grep -q 'TB_VM_DIRECT_SCATTER PASS' "$O/base_$mode.log";done
 else
  if vvp "$O/$variant" +mode=0 > "$O/$variant.log" 2>&1;then echo "MUTANT ESCAPED $variant";exit 1;fi
  grep -q 'TB_VM_DIRECT_SCATTER FAIL' "$O/$variant.log"
 fi
done
grep -h TB_VM_DIRECT_SCATTER "$O"/*.log
echo 'STATIC_DIRECT_SCATTER_GATE PASS actual32capture4output twoedges 3modes 2mutants'
