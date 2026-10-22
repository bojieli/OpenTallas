#!/bin/bash
set -euo pipefail
O=/work/census_rr; mkdir -p $O; cd /work/src
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
cp /work/native7/cells.lib $O/cells.lib
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv -lib physical_abstracts.v; read_verilog -sv /work/out/rr/qfd_tt_ctlm_dv_np_lp.sv /work/out/rr/qfd_tt_ctlm_dv_np_helpers.sv; hierarchy -check -top qfd_tt_ctlm_dv_np_lp; synth -top qfd_tt_ctlm_dv_np_lp -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_verilog -noattr $O/mapped.v" > $O/mapped.log 2>&1
args=(--liberty "$O/cells.lib")
for f in physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_tt.lib physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_tt.lib physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_tt.lib physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr_tt.lib physical/ref_tile/qfd_tt_ctlm_dv_wtn/views/qfd_tt_ctlm_dv_wtn/qfd_tt_ctlm_dv_wtn_tt.lib; do args+=(--liberty "$f"); done
python3 tools/ref_tile/native_census.py --netlist "$O/mapped.v" --top qfd_tt_ctlm_dv_np_lp "${args[@]}" --out "$O/native.json" > "$O/native.stdout" 2>&1 || true
python3 -c "import json;d=json.load(open('$O/native.json'));print('RR_CENSUS',d.get('status',d.get('verdict')),d.get('max_dynamic_loads'))"
grep -A3 "Chip area" $O/mapped.log | head -3
