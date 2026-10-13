#!/bin/bash
# el1013-idx-tiles: transaction-exact equivalence of ot_hgi_idx_index_wt (tiled) vs ot_hgi_idx_index_w (flat), plus the
# mutants that must FAIL.  usage: run_idxw_equiv.sh ROOT OUT [NFR=300] [SEEDS="1 2 3"]   -> OUT/SUMMARY
#   base   MUT=0 with the reference at DL=2 (as shipped) and DL=4 (same landing depth as the tiled leaf): must PASS
#   MUT    1 2 (inherited), 11 (divider stage), 12 (regional pointer copy), 13 (credit seam): must FAIL
set -uo pipefail
# Exit status (fixed 10-13): 0 only when every build succeeded, every base line is PASS and every mutant line is FAIL.
# ROOT and OUT are made absolute first: the builds run inside OUT/<tag>, so a relative ROOT used to break every source
# path, no simulation ran, SUMMARY held empty verdicts and the script still returned 0.
R=$(realpath "$1"); OUT=$(realpath -m "$2"); NFR=${3:-300}; SEEDS=${4:-"1 2 3"}; mkdir -p "$OUT"
[ -f "$R/rtl/hbm_accel/generic/idx/tb_hgi_idxw_equiv.sv" ] || { echo "IDXW_EQUIV GATE FAIL: no sources under ROOT $R"; exit 2; }
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$R/rtl/hbm_accel/generic/idx
SRC="$D/tb_hgi_idxw_equiv.sv $D/ot_hgi_idx_index_w.sv $D/ot_hgi_idx_index_wt.sv $D/ot_hgi_idxw_lane.sv $D/ot_hgi_idxw_qcore.sv
 $D/ot_hgi_idxw_keep.sv $D/ot_hgi_idxw_beat.sv $D/ot_hgi_idxw_wr.sv"
build() { # tag MUT RDL
  ( mkdir -p $OUT/$1 && cd $OUT/$1 && $V --binary --timing -O2 -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKANDNBLK \
      -Wno-MULTIDRIVEN --top-module tb_hgi_idxw_equiv -GMUT=$2 -GRDL=$3 -Mdir obj $SRC > build.log 2>&1; echo $? > build.exit )
}
build base 0 2; build base_rdl4 0 4
for m in 1 2 11 12 13; do build mut$m $m 2; done
: > $OUT/SUMMARY
for t in base base_rdl4 mut1 mut2 mut11 mut12 mut13; do
  for s in $SEEDS; do
    n=$NFR; case $t in mut*) n=$((NFR / 5 > 20 ? NFR / 5 : 20));; esac
    ( cd $OUT/$t && [ "$(cat build.exit)" = 0 ] && ./obj/Vtb_hgi_idxw_equiv +NFR=$n +SEED=$s > run_s$s.log 2>&1
      echo "$t seed=$s $(grep -E '^IDXW_EQUIV (PASS|FAIL)' run_s$s.log | head -1) | $(grep IDXW_EQUIV_STATS run_s$s.log)" > line_s$s ) &
  done
done
wait
cat $OUT/*/line_s* > $OUT/SUMMARY
cat $OUT/SUMMARY
rc=0
for t in base base_rdl4 mut1 mut2 mut11 mut12 mut13; do
  [ "$(cat $OUT/$t/build.exit 2>/dev/null)" = 0 ] || { echo "IDXW_EQUIV: build of $t FAILED (see $OUT/$t/build.log)"; rc=1; }
  for s in $SEEDS; do
    v=$(grep -E '^IDXW_EQUIV (PASS|FAIL)' $OUT/$t/run_s$s.log 2>/dev/null | head -1)
    case $t in
      mut*) case "$v" in "IDXW_EQUIV FAIL"*) ;; *) echo "IDXW_EQUIV: mutant $t seed $s not killed ('$v')"; rc=1;; esac;;
      *)    case "$v" in "IDXW_EQUIV PASS"*) ;; *) echo "IDXW_EQUIV: $t seed $s did not pass ('$v')"; rc=1;; esac;;
    esac
  done
done
[ $rc = 0 ] && echo "IDXW_EQUIV GATE PASS" | tee $OUT/gate || { echo "IDXW_EQUIV GATE FAIL" | tee $OUT/gate; exit 1; }
