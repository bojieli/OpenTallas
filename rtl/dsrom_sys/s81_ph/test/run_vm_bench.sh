#!/bin/bash
# run.sh <tag> [verilator defines...] : build the VM gate under Verilator
set -u
tag=$1; shift
mkdir -p obj_$tag
verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -j 8 --top-module tb_ot_s81ph_vm_mem "$@" \
  --Mdir obj_$tag rtl/dsrom_sys/s81_ph/test/tb_ot_s81ph_vm_mem.sv rtl/dsrom_sys/s81_ph/vm/ot_s81ph_vm_mem.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v > build_$tag.log 2>&1 || { echo BUILD_FAIL; grep -m20 -i error build_$tag.log; exit 1; }
echo BUILD_OK
