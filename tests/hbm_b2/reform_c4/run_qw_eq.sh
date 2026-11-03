#!/bin/bash
# usage: run_qw_eq.sh REPO WORK  -> positive EQ + 4 mutants (all must FAIL)
set -u
R=$(cd "$1" && pwd -P); W=$(mkdir -p "$2" && cd "$2" && pwd -P); H=$(cd "$(dirname "$0")" && pwd -P)
cd "$W"
git -C "$R" show origin/main:rtl/hbm_accel/generic/qw/ot_hgi_qw_dec.sv | sed 's/module ot_hgi_qw_dec\b/module ot_hgi_qw_dec_old/; s/ot_hgi_quant_decode u_dec/ot_hgi_quant_decode_old u_dec/' > old_qw.sv
git -C "$R" show origin/main:rtl/hbm_accel/generic/ot_hgi_quant_decode.sv | sed 's/module ot_hgi_quant_decode\b/module ot_hgi_quant_decode_old/; s/ot_hgi_fp4qdq bq/ot_hgi_fp4qdq_old bq/' > old_qd.sv
git -C "$R" show origin/main:rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv | sed 's/module ot_hgi_fp4qdq\b/module ot_hgi_fp4qdq_old/' > old_bq.sv
DEPS="$R/rtl/lib/ot_rst_relay.sv $R/physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv $R/physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv $(ls $R/rtl/hdc/ot_hdc_{delay,fastfp,fastfp_lat,fp32_add_lat,fp32_f12,fp32_mul_lat,sfu}.sv) $(git -C $R ls-files rtl | grep '/ot_hdc_prefix.sv$' | head -n 1 | sed "s#^#$R/#")"
NEW_QW=$R/rtl/hbm_accel/generic/qw/ot_hgi_qw_dec.sv; NEW_QD=$R/rtl/hbm_accel/generic/ot_hgi_quant_decode.sv; NEW_BQ=$R/rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv
run() { # name expect qw qd bq
  iverilog -g2012 -o $1.vvp -s tb $H/tb_qw_eq.sv $3 $4 $5 old_qw.sv old_qd.sv old_bq.sv $DEPS > $1.comp.log 2>&1 || { echo "$1 COMPILE_FAIL $(head -n 3 $1.comp.log)"; return; }
  out=$(timeout 1800 vvp -n $1.vvp +seed=7 2>&1 | grep -E "QW_EQ|MISMATCH" | tail -n 1)
  echo "$1 expect=$2: $out"
}
run pos pass $NEW_QW $NEW_QD $NEW_BQ
sed 's/localparam integer AL=14-BQS6;/localparam integer AL=14;/' $NEW_QD > mut_pipe14.sv; run mut_pipe14 fail $NEW_QW mut_pipe14.sv $NEW_BQ
sed 's/{s6a_sgn\[i\], be\[7:0\], rn\[6:0\]}/{s5_sgn[i], be[7:0], rn[6:0]}/' $NEW_BQ > mut_sgn.sv; run mut_sgn fail $NEW_QW $NEW_QD mut_sgn.sv
sed 's/+ s6a_qs\[b\] - 11/+ s5_qs[b] - 11/' $NEW_BQ > mut_qs.sv; run mut_qs fail $NEW_QW $NEW_QD mut_qs.sv
sed 's/fault <= s6a_v \&\& s6a_nf;/fault <= s6a_v \&\& s5_nf;/' $NEW_BQ > mut_nf.sv; run mut_nf fail $NEW_QW $NEW_QD mut_nf.sv
