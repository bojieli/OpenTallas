#!/bin/bash
set -eu
O=${1:?output};S=rtl/dsrom_sys/s81_ph;mkdir -p "$O"
for variant in base mdata mhash;do
 define=;case $variant in mdata)define=-DOT_VM_SCATTER_LANE_MUT_DATA;;mhash)define=-DOT_VM_SCATTER_LANE_MUT_HASH;;esac
 iverilog -g2012 $define -s tb_dsfd_vm_static_scatter_lane -o "$O/$variant" "$S/vm/dsfd_vm_static_scatter.sv" "$S/vm/dsfd_vm_static_scatter_lane.sv" "$S/test/tb_dsfd_vm_static_scatter_lane.sv" > "$O/build_$variant.log" 2>&1
 if [ "$variant" = base ];then
  for mode in 0 1 2;do vvp "$O/base" +mode=$mode > "$O/base_$mode.log" 2>&1;grep -q 'TB_VM_SCATTER_LANE PASS' "$O/base_$mode.log";done
 else
  if vvp "$O/$variant" +mode=0 > "$O/$variant.log" 2>&1;then echo "MUTANT ESCAPED $variant";exit 1;fi
  grep -q 'TB_VM_SCATTER_LANE FAIL' "$O/$variant.log"
 fi
done
grep -h TB_VM_SCATTER_LANE "$O"/*.log
echo 'STATIC_SCATTER_LANE_GATE PASS actual4lanes twoedges 3modes 2mutants'
