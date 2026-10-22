#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
src=(rtl/hdc/v41x/ot_hbm_idx_col8_sram_face.sv rtl/hdc/v41x/ot_hbm_idx_col8_sram_landed.sv rtl/hdc/v41x/ot_hbm_idx_col8_landed.sv rtl/common/landed_parent/ot_pl_land_physical.sv rtl/hdc/v41x/ot_hbm_idx_chunk_rt_c.sv rtl/hdc/v41x/ot_hidx_rst_tree_3e_f32.sv rtl/hdc/v41x/col8_parent_1021/pair_hard_interfaces.v physical/asap7_memory_macros/ot_sram_1r1w2c_64x516_m1/ot_sram_1r1w2c_64x516_m1_bb.v)
args=();for p in "${src[@]}";do args+=(--source "$p");done
macro=(--macro-view ot_sram_1r1w2c_64x516_m1=physical/asap7_memory_macros/ot_sram_1r1w2c_64x516_m1)
for i in 0 1 2;do macro+=(--macro-view "ot_hidx_score_pair8_r$i=physical/ref_tile/hidx_score_pair8_r$i/views/ot_hidx_score_pair8_r$i");done
macro+=(--macro-view ot_hidx_score_pair8_r3=physical/ref_tile/hidx_col8_standin_r3/views/ot_hidx_score_pair8_r3)
sha256sum "${src[@]}" > "$out/source_receipt.txt"
export OT_ORFS_NUM_CORES=8 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top ot_hidx_col8_sram_face_col "${args[@]}" --clock-port ctl --clock-period-ns 0.833333 --stages pnr --pnr-stop-after floorplan --die-area 0 0 907.2 907.2 --core-area 2.16 2.16 905.04 905.04 "${macro[@]}" --macro-place-halo 5.4 5.4 --orfs-corner WC --hold-corners WC,BC --routing-layers M2 M5 --step-tcl PRE_FLOORPLAN=tools/ref_tile/native_census.tcl --orfs-var OT_NATIVE_KIT=hidx_column_native_1021 --orfs-var NUM_CORES=8 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir "$out/work" --output "$out/physical.json" > "$out/flow.log" 2>&1
