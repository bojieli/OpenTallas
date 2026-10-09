#!/bin/bash
# run_lockh.sh <outdir> <pos|neg> [-G stage params]: the split attention tile (hfd_attn_half_lo + _hi) lock-stepped
# against the one-piece hfd_attn_tile_b (rtl/test/tb_hfd_attn_half_b.sv).  pos: roles 0..4 must PASS -> "ATTN_LOCKH PASS"
# (exit 0).  neg: mutants 1..5 (role 4) must each FAIL -> "ATTN_LOCKH NEG ALL CAUGHT" and exit 1 (a closure-loop
# expect=fail bench); a mutant that passes prints "MUTANT NOT CAUGHT" and exits 0.  Verilator (fleet 5.050).
O=$1; M=$2; shift 2; mkdir -p $O
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="rtl/test/tb_hfd_attn_half_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m8_phys.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/test/hdc_v41_harness.cpp"
run() { t=$1; shift
  $V --cc --exe --build -j ${J:-4} -O1 -CFLAGS -O1 -MAKEFLAGS OPT_SLOW=-O0 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb_hfd_attn_half_b --prefix Vtb -Mdir $O/$t "$@" $SRC > $O/$t.log 2>&1 && $O/$t/Vtb > $O/$t.run 2>&1; echo "$t rc=$?" >> $O/rc.txt; }
: > $O/rc.txt
if [ "$M" = neg ]; then
  for m in 1 2 3 4 5; do run m$m -GROLE=4 -GMUT=$m "$@" & done; wait
  grep -h ATTNHALF $O/m*.run | sort | uniq
  for m in 1 2 3 4 5; do grep -q "^m$m rc=0$" $O/rc.txt && { echo "MUTANT NOT CAUGHT mut=$m"; exit 0; }; done
  echo "ATTN_LOCKH NEG ALL CAUGHT"; exit 1
fi
for r in 0 1 2 3 4; do run r$r -GROLE=$r "$@" & done; wait
grep -h ATTNHALF $O/r*.run | sort | uniq
for r in 0 1 2 3 4; do grep -q "^r$r rc=0$" $O/rc.txt || { echo "role $r FAILED"; echo "ATTN_LOCKH FAIL"; exit 1; }; done
echo "ATTN_LOCKH PASS"
