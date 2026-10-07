#!/bin/bash
# run_kh_bench.sh [neg]: the coll-local endpoint copy equals rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv except for
# (* keep_hierarchy *) on primitive instances (exact); "neg" checks a copy with one operator changed (must MISMATCH).
D=$(dirname $0)
if [ "${1:-}" = neg ]; then
  T=$(mktemp -d); mkdir -p $T/physical/hbm_accel_die_views/coll/rtl $T/rtl/hbm_accel/tu
  cp $D/make_endpoint_kh.py $T/physical/hbm_accel_die_views/coll/rtl/; cp rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv $T/rtl/hbm_accel/tu/
  sed '0,/<= 1.b1;/s//<= 1'"'"'b0;/' $D/ot_hbm_accel_tu_endpoint_kh.sv > $T/physical/hbm_accel_die_views/coll/rtl/ot_hbm_accel_tu_endpoint_kh.sv
  cmp -s $D/ot_hbm_accel_tu_endpoint_kh.sv $T/physical/hbm_accel_die_views/coll/rtl/ot_hbm_accel_tu_endpoint_kh.sv && { echo "NEG mutant not applied"; exit 0; }
  python3 $T/physical/hbm_accel_die_views/coll/rtl/make_endpoint_kh.py check; rc=$?; rm -rf $T; exit $rc
fi
python3 $D/make_endpoint_kh.py check
