#!/usr/bin/env bash
# S81U-1: dsdv_gunit whole-unit bench (Verilator) vs tools/hdc_golden_v41 (router + HC coefficients) + 5 mutants that
# must FAIL (1 bias not added, 4 route_scale skipped, 5 HC group association, 6 HC root order, 7 rsqrt eps dropped).
# Prints GUNIT_GATE PASS/FAIL.  usage: run_gunit_bench.sh [workdir] [cases]
set -u
U=$(cd "$(dirname "$0")/.." && pwd); R=$(cd "$U/../../../.." && pwd)
T=${1:-$(mktemp -d)}; N=${2:-8}; mkdir -p "$T"
SRC="rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv
 rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41x/ot_dsrom_divc.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv
 rtl/hdc/v41/ot_hdc_select_tree.sv rtl/hdc/v41x/ot_dsrom_su_bias_select.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
 rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_tail_static.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_tail_unit_static.sv rtl/dsrom_sys/s81_dv/unit/ot_dsdv_vstop.sv
 rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_rt.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_hcf.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit.sv
 rtl/dsrom_sys/s81_dv/unit/test/tb_dsdv_gunit.sv"
python3 -I "$U/test/gunit_vectors.py" "$T/gv.hex" "$N" 1017 || { echo "GUNIT_GATE FAIL vectors"; exit 1; }
MUTS="0 1 4 5 6 7"
for m in $MUTS; do
  ( cd "$T" && verilator --cc --exe --build -j 6 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DMUT=$m \
      --top-module tb_dsdv_gunit -Mdir "obj$m" $(for f in $SRC; do echo "$R/$f"; done) "$U/test/tb_dsdv_gunit.cpp" \
      -CFLAGS -O1 > "build$m.log" 2>&1; echo $? > "build$m.rc" ) &
done
wait
bad=0
for m in $MUTS; do
  [ "$(cat "$T/build$m.rc")" = 0 ] || { echo "GUNIT_GATE FAIL build MUT=$m"; tail -5 "$T/build$m.log"; exit 1; }
  out=$(cd "$T" && "./obj$m/Vtb_dsdv_gunit" +N=$N +SEED=7 | grep '^GUNIT'); echo "MUT=$m: $out"
  if [ $m = 0 ]; then echo "$out" | grep -q '^GUNIT PASS' || bad=1; else echo "$out" | grep -q '^GUNIT PASS' && bad=1; fi
done
[ $bad = 0 ] && echo "GUNIT_GATE PASS ($N golden cases, mutants 1/4/5/6/7 detected)" || echo "GUNIT_GATE FAIL"
exit $bad
