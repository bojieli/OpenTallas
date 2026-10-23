#!/usr/bin/env bash
# STW-S81c-TOK4-BAND 10-22: banded gunit l1f behaviour proof = the dsdv_gunit golden bench (run_gunit_bench.sh, unchanged
# vectors / mutants) with every dsdv_gunit_l1f replaced by the lockstep shim (banded flat parent drives, current RTL
# compared on every edge).  usage: run_l1f_band_lsw.sh WORKDIR [cases] [muts]
# Prints L1F_LSW PASS iff MUT 0 is GUNIT PASS with 0 mismatches (live edges > 0) and every other MUT still FAILs the golden
# with 0 lockstep mismatches (the mutant hits both copies alike).
set -u
U=$(cd "$(dirname "$0")/.." && pwd); R=$(cd "$U/../../../.." && pwd)
T=$(mkdir -p "$1" && cd "$1" && pwd); N=${2:-8}; MUTS=${3:-"0 1"}
sed 's/^module dsdv_gunit_l1f #(/module dsdv_gunit_l1f_ref #(/' "$U/dsdv_gunit_l1f.sv" > "$T/l1f_ref.sv"
grep -q "module dsdv_gunit_l1f_ref" "$T/l1f_ref.sv" || { echo "L1F_LSW ERROR rename"; exit 2; }
REL=$(python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$T/l1f_ref.sv" "$R")
# BANDMUT=1 (the kit's expect=fail mutant): the BANDED copy alone runs MUT 1 (bias forced 0), the reference stays MUT 0
# -> the lockstep must report mismatches and the script must print L1F_LSW FAIL.
SHIM=rtl/dsrom_sys/s81_dv/unit/test/dsdv_gunit_l1f_lsw.sv
if [ "${BANDMUT:-0}" != 0 ]; then
  sed 's/dsdv_gunit_l1f_bp #(.MUT(MUT))/dsdv_gunit_l1f_bp #(.MUT(1))/' "$R/$SHIM" > "$T/l1f_lsw_bandmut.sv"
  grep -q 'dsdv_gunit_l1f_bp #(.MUT(1))' "$T/l1f_lsw_bandmut.sv" || { echo "L1F_LSW ERROR bandmut sed"; exit 2; }
  SHIM=$(python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$T/l1f_lsw_bandmut.sv" "$R")
  echo "L1F_LSW BANDMUT=1: banded copy MUT 1, reference MUT 0"
fi
sed -e "s#rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1f.sv#$REL rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1f_band.sv $SHIM#" \
    -e 's#^U=.*#U='"$U"'; R='"$R"'#' -e "s#| grep '^GUNIT')#| grep '^GUNIT'; true)#g" "$U/test/run_gunit_bench.sh" > "$T/bench.sh"
grep -q "l1f_lsw" "$T/bench.sh" || { echo "L1F_LSW ERROR bench rewrite"; exit 2; }
bash "$T/bench.sh" "$T/w" "$N" "$MUTS" > "$T/bench.out" 2>&1; cat "$T/bench.out"
bad=0
for m in $MUTS; do
  o=$(cd "$T/w" && "./obj$m/Vtb_dsdv_gunit" +N=$N +SEED=7 2>&1)
  nm=$(echo "$o" | grep -c "GUNIT_LSW.*MISMATCH"); nl=$(echo "$o" | grep "GUNIT_LSW.*checked" | awk '{s+=$6} END {print s+0}')
  g=$(echo "$o" | grep -c '^GUNIT PASS')
  echo "L1F_LSW_CASE MUT=$m golden_pass=$g lockstep_mismatch_lines=$nm live_edges=$nl"
  echo "$o" | grep "GUNIT_LSW" | head -6
  [ "$nm" = 0 ] && [ "$nl" -gt 0 ] || bad=1
  if [ $m = 0 ]; then [ "$g" -ge 1 ] || bad=1; else [ "$g" = 0 ] || bad=1; fi
done
if [ "${BANDMUT:-0}" != 0 ]; then
  # the expect=fail mutant: FAIL only when the lockstep really ran (live edges) and saw the band differ; a build / vector
  # error is an ERROR, never a detected mutant
  if [ "${nm:-0}" -gt 0 ] && [ "${nl:-0}" -gt 0 ]; then echo "L1F_LSW FAIL band mutant caught ($nm mismatch lines, $nl live edges)"; exit 1; fi
  echo "L1F_LSW ERROR band mutant not caught or bench did not run (mismatch lines ${nm:-0}, live edges ${nl:-0})"; exit 2
fi
[ $bad = 0 ] && echo "L1F_LSW PASS" || echo "L1F_LSW FAIL"; exit $bad
