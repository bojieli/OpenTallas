#!/bin/bash
# Actual generated physical native, canonical keep hook and per-kept-leaf library mapping.
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/yosys-0.68/bin:$PATH
root=$(pwd)
mkdir -p native
top=ot_qfd_tt_ctlm_static_hr_safe32_native32_1r
{
 for lib in "$root"/libs/*.lib; do printf 'read_liberty -lib %s\n' "$lib"; done
 printf 'read_verilog -sv -DSYNTHESIS candidate/native32_1r_param.v candidate/native32_helpers.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v\n'
 printf 'hierarchy -check -top %s\ntcl physical/common_flow/ot_keep_regs.tcl\nsynth -noabc -top %s -flatten\n' "$top" "$top"
 printf 'dfflibmap -liberty %s/libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib\nabc' "$root"
 for family in SIMPLE INVBUF AO OA; do printf ' -liberty %s' "$root"/libs/asap7sc7p5t_${family}_RVT_TT_*.lib; done
 printf '\nopt_clean -purge\nautoname\nwrite_verilog -noattr %s/native/mapped.v\nstat\n' "$root"
} > native/run.ys
yosys -ql native/synth.log native/run.ys
args=()
for lib in "$root"/libs/*.lib; do args+=(--liberty "$lib"); done
python3 tools/ref_tile/native_census.py --netlist native/mapped.v --top "$top" --out native/census.json "${args[@]}" > native/census.log 2>&1
cat native/census.log
