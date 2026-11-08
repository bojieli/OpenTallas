#!/usr/bin/env bash
# DIE-HBM-92-SU-IDX 11-08 lock-step: as-built ot_hbm_idx_score_hcol_h0 (bind base, DELIVERED_RESET=1) vs the staged
# wires-only glue ot_hbm_idx_score_hcol_h0__p6glue around ot_hbm_idx_score_hcol_h0_ra/_rb (rgn.sv @c4237519789).
#   run.sh BASE GLUE_DIR OUT    BASE = bind base checkout (asbuilt "base"), GLUE_DIR = staged p37su_idx_sources
# S: masters with their seam face flop (ra cs/cf out, rb cs/cf in: seam_models.sv) must PASS;
# P: plain core sources (no seam face) must FAIL (ra pays the 2 seam face flops back inside).
set -u
T=$1; G=$2; O=$3; H=$(cd "$(dirname "$0")" && pwd); R=$H/../..; V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
mkdir -p "$O"; cd "$O" || exit 1
for f in rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_delivered3.sv rtl/hdc/ot_hdc_delay.sv \
  rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv \
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_next/bind/ot_hnx_idx_hcol_plan.sv; do cp "$T/$f" "lib_$(basename $f)"; done
sed -e "s/module ot_hbm_idx_score_hcol_h0_ra /module ot_hbm_idx_score_hcol_h0_ra__core /" \
    -e "s/module ot_hbm_idx_score_hcol_h0_rb /module ot_hbm_idx_score_hcol_h0_rb__core /" "$G/ot_hbm_idx_score_hcol_h0_rgn.sv" > rgn_core.sv
python3 -I "$R/lockstep_gen.py" "$H/spec.json" tb.sv
for v in S P; do
  if [ $v = S ]; then X="rgn_core.sv $H/seam_models.sv"; else X="$G/ot_hbm_idx_score_hcol_h0_rgn.sv"; fi
  rm -rf obj_$v; $V --binary -j 16 -Wno-fatal -Wno-lint -Wno-style --top-module tb -Mdir obj_$v -o sim tb.sv lib_*.sv $X \
    "$G/ot_hbm_idx_score_hcol_h0__p6glue.sv" > build_$v.log 2>&1 || { tail -20 build_$v.log; exit 2; }
  obj_$v/sim > sim_$v.log 2>&1; echo "$v: $(grep LOCKSTEP sim_$v.log)"
done
