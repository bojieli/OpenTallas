#!/usr/bin/env bash
# S81/PORTFIX-FLT (2026-10-25): tb_bk_sel_vmtx_fault on the real dsdv_bk_sel_vmtx (Verilator 5.050), plus two negative
# controls built from sed copies of dsdv_idx_l20s.sv: nor (vm_fault dropped from the sticky OR) and sel (fault port = the
# bk_sel fault only, the pre-PORTFIX single-cause port).  (The vmux collision flag is itself sticky, so a non-sticky fq
# is not observable from this cause.)
# Usage (cwd = repo root): run_bk_sel_fault.sh OUTDIR   ->  BK_SEL_FAULT_GATE PASS / FAIL
set -u
O=$(realpath -m "${1:?outdir}"); mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
I=rtl/dsrom_sys/s81_dv/idx
SRC="physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
rtl/common/ot_fwd_link_stage.sv rtl/hdc/ot_hdc_prefix.sv rtl/dsrom_sys/s81_glue/ot_s81_rly.sv
rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_dv/unit/ot_dsdv_vstop.sv
rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_v.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_g.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bksel_c.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_sel.sv $I/dsdv_idx_tree.sv rtl/lib/ot_rst_relay.sv"
( sha256sum $SRC $I/dsdv_idx_l20s.sv $I/test/tb_bk_sel_vmtx_fault.sv; $VL --version ) > "$O/sources.sha256"
sed 's/fq <= fq | sel_f | ef | mf | vm_fault | tx_st\[0\];/fq <= fq | sel_f | ef | mf | tx_st[0];/' $I/dsdv_idx_l20s.sv > "$O/l20s_nor.sv"
sed 's/assign vo_n = vn; assign fault = fq;/assign vo_n = vn; assign fault = sel_f;/' $I/dsdv_idx_l20s.sv > "$O/l20s_sel.sv"
for m in nor sel; do cmp -s $I/dsdv_idx_l20s.sv "$O/l20s_$m.sv" && { echo "sed $m did not apply"; exit 2; }; done
bad=0
one() { n=$1; exp=$2; l20=$3
  $VL --binary --timing -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE --top-module tb_bk_sel_vmtx_fault $SRC $l20 $I/test/tb_bk_sel_vmtx_fault.sv -Mdir "$O/$n" \
    > "$O/build_$n.log" 2>&1 || { echo "$n: BUILD FAIL"; grep -m8 %Error "$O/build_$n.log"; bad=1; return; }
  "$O/$n/Vtb_bk_sel_vmtx_fault" > "$O/$n.log" 2>&1; v=$(grep -m1 -E '^(PASS|FAIL) bk_sel_fault' "$O/$n.log")
  echo "$n: $v"; grep -E '^(ERR|OK) ' "$O/$n.log" | head -4 | sed 's/^/  /'
  echo "$v" | grep -q "^$exp " || { echo "  $n: expected $exp"; bad=1; }
}
one base PASS $I/dsdv_idx_l20s.sv; one nor FAIL "$O/l20s_nor.sv"; one sel FAIL "$O/l20s_sel.sv"
[ $bad = 0 ] && echo "BK_SEL_FAULT_GATE PASS" || echo "BK_SEL_FAULT_GATE FAIL"; exit $bad
