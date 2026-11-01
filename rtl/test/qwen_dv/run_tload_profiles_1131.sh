#!/bin/bash
# Current body 0/0 vs 1/1 plus metadata-defined extra input/output/reset contract.
set -eu
R=$(pwd)
O=${1:?output directory}
mkdir -p "$O";O=$(cd "$O" && pwd)
mkdir -p "$O/models" "$O/rtl"
cp rtl/qwen_dv/{qfd_dv_slice_tload.sv,qfd_dv_table_rom_loader.sv,qfd_dv_vm.sv} "$O/rtl/"
for n in ot_rom_4096x266_m8 ot_sram_1r1w_1024x256_m2_r2c2 ot_sram_1r1w_128x256_m1_r2c2 ot_sram_1r1w_256x256_m2_r2c2; do cp "physical/asap7_memory_macros_v2/$n/$n.v" "$O/models/"; done
cp rtl/test/qwen_dv/tb_qfd_dv_tload_profiles_1131.sv "$O/tb.sv"
python3 results/qc_tload_protocol_1131/prepare_fixture.py --out "$O/fx"
cd "$O"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --version
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_qfd_dv_slice_tload -Mdir obj models/*.v rtl/*.sv tb.sv > build.log 2>&1
for p in 0 1 4; do obj/Vtb_qfd_dv_slice_tload +PROFILE=$p +OT_ROM_DIR="$O/fx" +EXPECTED="$O/fx/expected.hex" > profile$p.log 2>&1; grep -q TLOAD_JOIN_PASS profile$p.log; done
for p in 2 3; do set +e; obj/Vtb_qfd_dv_slice_tload +PROFILE=$p +OT_ROM_DIR="$O/fx" +EXPECTED="$O/fx/expected.hex" > mutant$p.log 2>&1; rc=$?; set -e; test "$rc" -ne 0; grep -q TLOAD_EDGE_MISMATCH mutant$p.log; done
echo TLOAD_PROTOCOL_PROFILES_PASS > result.txt
