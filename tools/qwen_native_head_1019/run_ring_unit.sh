#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p ring_unit
verilator --binary --timing -j 8 -Wno-fatal --top-module tb_head_ring --Mdir ring_unit/obj rtl/test/qwen_dv/tb_head_ring.sv rtl/qwen_dv/qfd_dv_head_native_b64.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v >ring_unit/build.log 2>&1
ring_unit/obj/Vtb_head_ring | tee ring_unit/positive.log
verilator --binary --timing -j 8 -Wno-fatal +define+OT_HEAD_RING_AGE_MUT --top-module tb_head_ring --Mdir ring_unit/mut_obj rtl/test/qwen_dv/tb_head_ring.sv rtl/qwen_dv/qfd_dv_head_native_b64.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v >ring_unit/mut_build.log 2>&1
set +e
ring_unit/mut_obj/Vtb_head_ring >ring_unit/age_mut.log 2>&1
rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo MUTANT_UNEXPECTED_PASS; exit 7; fi
grep -q HEAD_RING_AGE_FAIL ring_unit/age_mut.log
cat ring_unit/age_mut.log
