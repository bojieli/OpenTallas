#!/bin/bash
# redesign-hbm 2026-10-09: coarse clock-gating lockstep of the attention quad (ot_attn_tile_m6h1q CG 1): four gated quads
# (ot_attn_tile_m6h1x HALF 2) against ot_hdc_v41x_attn_tile_l, every output every cycle, with ACT busy / IDLE fully idle
# windows so the gates close.  Run in the source root:  cg_lockstep.sh <outdir> <tag> [-G params ...]
#   positive: -GCG=1 -GIDLE=300 -GACT=200   (TILERLOCK ... mismatches=0, gated_quad0 > 0)
#   mutants : add -GMUTCG=1 (wake 2 edges late) or -GHOLDQ=0 (no drain hold): must FAIL
set -u; O=$1; t=$2; shift 2; mkdir -p $O
VL=$( [ -x $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator ] && echo $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator || echo verilator)
$VL --cc --exe --build -j ${J:-16} -O1 -CFLAGS -O1 -MAKEFLAGS OPT_SLOW=-O0 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-PINMISSING \
  --top-module tb_hdc_v41x_attn_tile_m6h1r_lockstep --prefix Vtb -Mdir $O/$t -GHALF=2 -GNCYC=${NCYC:-12000} "$@" \
  rtl/test/tb_hdc_v41x_attn_tile_m6h1r_lockstep.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m8_phys.sv \
  rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv \
  rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv \
  rtl/hdc/ot_hdc_cg.sv rtl/hbm_accel/cg/ot_cg_tile.sv rtl/test/hdc_v41_harness.cpp > $O/$t.build.log 2>&1 || { tail -20 $O/$t.build.log; echo "QCG BUILD_FAIL"; exit 2; }
$O/$t/Vtb > $O/$t.run 2>&1; rc=$?
cat $O/$t.run | grep -E "TILERLOCK|MISMATCH" | head -6
g=$(sed -n 's/.*gated_quad0=\([0-9]*\).*/\1/p' $O/$t.run)
if [ $rc = 0 ] && grep -q "mismatches=0" $O/$t.run && [ "${g:-0}" -gt 0 ]; then echo "QCG_PASS gated_quad0=$g"; exit 0; fi
echo "QCG_FAIL rc=$rc gated_quad0=${g:-0}"; exit 1
