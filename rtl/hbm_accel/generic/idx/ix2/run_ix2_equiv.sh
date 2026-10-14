#!/bin/bash
# ix2 equivalence + divide benches.  usage: run_ix2_equiv.sh ROOT OUT [build|run|all]
#   build: Verilator binaries for MUT 0..3 (equiv) and MUT 0 / 3 (divide);  run: seeds 1..3 x 100 frames at MUT 0,
#   seed 1 x 40 frames for each mutant (must FAIL), divide exhaustive, latency at round trip 8 and 16.
set -uo pipefail
# Exit status: 0 only when every binary built, MUT 0 passes every seed, every mutant fails and the divide check passes
# (a failed build is a gate failure, never a silent pass).  ROOT / OUT are made absolute.
R=$(realpath "$1"); OUT=$(realpath -m "$2"); WHAT=${3:-all}; mkdir -p "$OUT"
[ -f "$R/rtl/hbm_accel/generic/idx/ix2/tb_hgi_idx_ix2_equiv.sv" ] || { echo "IX2 GATE FAIL: no sources under ROOT $R"; exit 2; }
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$R/rtl/hbm_accel/generic/idx
IX2="$D/ix2/ot_hgi_idx_ix2_lane.sv $D/ix2/ot_hgi_idx_ix2_kp.sv $D/ix2/ot_hgi_idx_ix2_qa.sv $D/ix2/ot_hgi_idx_ix2_pk.sv
 $D/ix2/ot_hgi_idx_ix2_wp.sv $D/ix2/ot_hgi_idx_ix2_ct.sv $D/ix2/ot_hgi_idx_ix2.sv"
if [ "$WHAT" != run ]; then
  for m in 0 1 2 3; do
    $V --binary --timing -O2 -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-BLKANDNBLK -Wno-MULTIDRIVEN -Wno-CMPCONST \
      --top-module tb_hgi_idx_ix2_equiv -GMUT=$m -Mdir $OUT/eq$m $IX2 $D/ot_hgi_idx_index_w.sv $D/ix2/tb_hgi_idx_ix2_equiv.sv \
      > $OUT/eq$m.build.log 2>&1 &
  done
  for m in 0 3; do
    $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-BLKSEQ --top-module tb_hgi_idx_ix2_div -GMUT=$m -Mdir $OUT/div$m \
      $D/ix2/ot_hgi_idx_ix2_kp.sv $D/ix2/tb_hgi_idx_ix2_div.sv > $OUT/div$m.build.log 2>&1 &
  done
  wait
fi
if [ "$WHAT" != build ]; then
  for s in 1 2 3; do $OUT/eq0/Vtb_hgi_idx_ix2_equiv +SEED=$s +FRAMES=100 > $OUT/eq0.s$s.log 2>&1 & done
  for m in 1 2 3; do $OUT/eq$m/Vtb_hgi_idx_ix2_equiv +SEED=1 +FRAMES=40 > $OUT/eq$m.s1.log 2>&1 & done
  for rt in 8 16; do $OUT/eq0/Vtb_hgi_idx_ix2_equiv +SEED=5 +FRAMES=6 +MEAS=$rt > $OUT/lat$rt.log 2>&1 & done
  for m in 0 3; do $OUT/div$m/Vtb_hgi_idx_ix2_div > $OUT/div$m.log 2>&1 & done
  wait
  grep -h "IX2EQ MUT\|IX2DIV\|IX2LAT" $OUT/eq*.s*.log $OUT/div?.log $OUT/lat*.log > $OUT/SUMMARY
  cat $OUT/SUMMARY
fi
rc=0
for m in 0 1 2 3; do [ -x $OUT/eq$m/Vtb_hgi_idx_ix2_equiv ] || { echo "IX2: build eq$m FAILED ($OUT/eq$m.build.log)"; rc=1; }; done
for m in 0 3; do [ -x $OUT/div$m/Vtb_hgi_idx_ix2_div ] || { echo "IX2: build div$m FAILED ($OUT/div$m.build.log)"; rc=1; }; done
if [ "$WHAT" != build ]; then
  for s in 1 2 3; do grep -q "IX2EQ MUT=0 .*PASS" $OUT/eq0.s$s.log 2>/dev/null || { echo "IX2: MUT 0 seed $s did not pass"; rc=1; }; done
  for m in 1 2 3; do grep -q "IX2EQ MUT=$m .*FAIL" $OUT/eq$m.s1.log 2>/dev/null || { echo "IX2: mutant $m not killed"; rc=1; }; done
  grep -q "IX2DIV.*PASS" $OUT/div0.log 2>/dev/null || { echo "IX2: divide check did not pass"; rc=1; }
  grep -q "IX2DIV.*FAIL" $OUT/div3.log 2>/dev/null || { echo "IX2: divide mutant not killed"; rc=1; }
fi
[ $rc = 0 ] && echo "IX2 GATE PASS" | tee $OUT/gate || { echo "IX2 GATE FAIL" | tee $OUT/gate; exit 1; }
