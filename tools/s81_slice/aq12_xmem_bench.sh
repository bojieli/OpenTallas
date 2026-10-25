#!/bin/bash
# aq12_xmem_bench.sh <outdir> [base|mutxptr] [N]  (cwd = repo root): S81-TILES2 2026-10-17 equivalence bench of
# the vq-only fork ot_s81sl_aq12x (xd = x delayed 12) against the shared ot_dsrom_aq12 (flop line), side by
# side on one random stimulus, every output every cycle; and ot_s81sl_vq AQ_XMEM 2 (one-macro sub-beat ring) vs 0.
# base must PASS; mutxptr (xd one cycle short) mutvq2 (vq AQ_XMEM 2 ring one row short) and mutwreg (vq macro write address misaligned with its registered data, S81-VQFIX) must FAIL.
# Prints PASS/FAIL aq12_xmem_eq; exit 0 on PASS.
set -u; O=$1; M=${2:-base}; N=${3:-20000}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
DEF=""; [ "$M" = mutxptr ] && DEF="+define+OT_AQ12_MUT_XPTR"; [ "$M" = mutvq2 ] && DEF="+define+OT_VQ_MUT_XPTR"; [ "$M" = mutwreg ] && DEF="+define+OT_VQ_MUT_WREG"
srcs="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_hbm_norm_split.sv rtl/hdc/v41x/ot_hbm_norm_split_p.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/dsrom_sys/s81_dv/slice/test/tb_aq12_xmem_eq.sv"
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GN=$N --top-module tb_aq12_xmem_eq -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_aq12_xmem_eq > $O/run.log 2>&1
grep -E "MISMATCH" $O/run.log | head -5; grep -E "^SUMMARY" $O/run.log
grep -q '^PASS aq12_xmem_eq' $O/run.log && { echo "PASS aq12_xmem_eq $M"; exit 0; }; echo "FAIL aq12_xmem_eq $M"; exit 1
