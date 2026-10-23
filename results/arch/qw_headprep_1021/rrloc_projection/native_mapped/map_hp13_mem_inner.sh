#!/bin/bash
set -euo pipefail
O=/work/mapped_hp13_mem
G=/work/constructed2
mkdir -p "$O"
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 /work/rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv -lib mapping_abstracts.v physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v; read_verilog -sv $G/qfd_tt_ctlm_dv_hp13_rrloc_native32.sv $G/qfd_tt_ctlm_dv_hp13_rrloc_helpers.sv rtl/qwen_dv/headprep13/h16za/native32_1r_param.v rtl/qwen_dv/headprep13/h16za/native32_helpers.sv; hierarchy -check -top qfd_tt_ctlm_dv_hp13_rrloc_native32; synth -top qfd_tt_ctlm_dv_hp13_rrloc_native32 -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_verilog -noattr $O/mapped.v" > "$O/mapped.log" 2>&1
args=(--liberty "$O/cells.lib")
for f in physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_tt.lib physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_tt.lib physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_tt.lib physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_tt.lib physical/ref_tile/qfd_tt_ctlm_dv_wtn/views/qfd_tt_ctlm_dv_wtn/qfd_tt_ctlm_dv_wtn_tt.lib; do args+=(--liberty "$f"); done
python3 tools/ref_tile/native_census.py --netlist "$O/mapped.v" --top qfd_tt_ctlm_dv_hp13_rrloc_native32 "${args[@]}" --out "$O/native.json" > "$O/native.stdout" 2>&1
python3 tools/textbook_lint.py check --netlist "$O/mapped.v" --top qfd_tt_ctlm_dv_hp13_rrloc_native32 --out "$O/textbook.json" > "$O/textbook.stdout" 2>&1
python3 - <<'PY'
import json
for f in ['native','textbook']:
 d=json.load(open('/work/mapped_hp13_mem/'+f+'.json'));print(f,d.get('status',d.get('verdict')),d.get('max_dynamic_loads'),d.get('metrics'))
PY
