#!/usr/bin/env bash
# STW-S81-TOPK-VMUX (10-21): build + run tb_vmtx_lat for the G8IQ vmtx (flat dsdv_bk_sel) and vmtx' (PlanA n32 parent).
# Run from the source root.  usage: run_vmtx_lat.sh <out>.  Sources = run_idx_tree.sh's (DIEM 1 / DIEM 2 lists).
set -u -o pipefail
OUT=$1; mkdir -p "$OUT"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
BASE="physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
rtl/common/ot_fwd_link_stage.sv
rtl/hdc/ot_hdc_prefix.sv
rtl/dsrom_sys/s81_glue/ot_s81_rly.sv
rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv
rtl/dsrom_sys/s81_dv/unit/ot_dsdv_vstop.sv
rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv
rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv
rtl/hdc/v41x/ot_hdc_v41x_sel.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_v.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_g.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bksel_c.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_sel.sv
rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv
rtl/lib/ot_rst_relay.sv
rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv
rtl/dsrom_sys/s81_dv/idx/dsdv_idx_vmux_n32.sv"
PA="physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v
physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v
rtl/lib/ot_sram_showahead_1r1w.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_queue_store.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_hist_bank.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_hq_parts.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_hq_slice.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_hq_tile.sv
rtl/common/landed_parent/ot_pl_land.sv
rtl/common/landed_parent/ot_pl_land_rst_copy.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/dsdv_bk_plana_station.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/dsdv_bksel_q_pa.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_mux.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_search.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_sel_ctl.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_queue.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_packet.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_ctl.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/dsdv_bksel_c_pa_n32.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/dsdv_bk_sel_pa_n32_lp.sv
rtl/dsrom_sys/s81_dv/idx/dsdv_bk_sel_vmtx_n32.sv"
DEFS="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32 -DOT_S81PH_SEL_HQ -DOT_HARD_CHILDREN -DOT_S81PH_HQ_INPUT_RAW -DOT_S81PH_SEL_ILD -DOT_S81PH_SEL_FRPR"
for v in g8iq n32; do
  F="-DTX_SRAM=1"; S="$BASE"; [ $v = n32 ] && { F="-DLAT_N32 $DEFS"; S="$PA $BASE"; }
  ( sha256sum $S tools/s81_dv/layer_prog/bk/tb_vmtx_lat.sv; $VL --version ) > $OUT/sources_$v.sha256
  $VL --binary --timing -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE $F --top-module tb_vmtx_lat $S tools/s81_dv/layer_prog/bk/tb_vmtx_lat.sv -Mdir $OUT/obj_$v > $OUT/build_$v.log 2>&1 \
    || { tail -20 $OUT/build_$v.log; echo "LAT BUILD FAIL $v"; continue; }
  $OUT/obj_$v/Vtb_vmtx_lat > $OUT/run_$v.log 2>&1; grep VMTX_LAT $OUT/run_$v.log
done
