#!/bin/bash
# el1011-q-kvd 2026-10-12: sim_nhb_fp_lat_nr_dpi.sv (the bench stand-in for ot_hdc_fp32_add_lat_nr) against the REAL
# ot_hdc_fp32_add_lat_nr, through rtl/test/tb_hdc_add_lat_nr.sv: the real unit is renamed to the TB's reference
# (ot_hdc_fp32_add_lat), the stand-in is the DUT.  Random normals / subnormals / signed zeros / inf / NaN /
# near-cancellation pairs with valid gaps and a mid-run reset; every valid (y, err) and the valid sequence must match.
# Negative control: NEG=1 builds the stand-in with nhb_fadd's operands swapped to a - b semantics (must FAIL).
#   run_nr_standin_equiv.sh OUT [LATS="3 4 5 6 7"] [N=200000]
set -u
OUT=$1; LATS=${2:-"3 4 5 6 7"}; N=${3:-200000}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
W=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
awk '/^module ot_hdc_fp32_add_lat_nr /{s=1} s{print} s&&/^endmodule/{s=0}' $W/hdc/ot_hdc_fp32_add_lat_nr.sv \
  | sed 's/^module ot_hdc_fp32_add_lat_nr /module ot_hdc_fp32_add_lat /' > $OUT/real_as_ref.sv
awk '/^module ot_hdc_fp32_add_lat_nr /{s=1} !s{print} s&&/^endmodule/{s=0}' $W/hdc/ot_hdc_fp32_add_lat_nr.sv \
  | awk '/^module ot_hdc_fp32_add_lat_sel /{s=1} !s{print} s&&/^endmodule/{s=0}' > $OUT/nr_rest.sv
awk '/^module ot_hdc_lzc32/,/^endmodule/' $W/hdc/ot_hdc_fastfp.sv > $OUT/lzc32.sv
sed 's/yl\[0\] <= nhb_fadd(a, b, e);/yl[0] <= nhb_fadd(a, b ^ 32'"'"'h80000000, e);/' $W/test/nearhbm/sim_nhb_fp_lat_nr_dpi.sv > $OUT/standin_neg.sv
grep -q "b ^ 32'h80000000" $OUT/standin_neg.sv || { echo "FAIL: negative-control edit did not apply"; exit 3; }
rc=0
for neg in 0 1; do
  SI=$W/test/nearhbm/sim_nhb_fp_lat_nr_dpi.sv; [ $neg = 1 ] && SI=$OUT/standin_neg.sv
  for L in $LATS; do
    d=$OUT/n${neg}_l$L
    $VL --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hdc_add_lat_nr -GLAT=$L -GN=$N \
      --Mdir $d -o Vt $W/test/tb_hdc_add_lat_nr.sv $OUT/real_as_ref.sv $OUT/nr_rest.sv $SI $OUT/lzc32.sv \
      $W/hdc/ot_hdc_prefix.sv $W/test/nearhbm/sim_nhb_fp_lat_dpi.cpp > $d.build.log 2>&1 || { echo "BUILD_FAIL neg=$neg LAT=$L"; rc=3; continue; }
    r=$($d/Vt | grep -E "^(PASS|FAIL)")
    echo "neg=$neg $r"
    if [ $neg = 0 ]; then case "$r" in PASS*) ;; *) rc=1;; esac
    else case "$r" in FAIL*) ;; *) rc=1;; esac; fi
  done
done
[ $rc = 0 ] && echo "EQUIV PASS (stand-in == real _nr; negative control caught)" || echo "EQUIV FAIL rc=$rc"
exit $rc
