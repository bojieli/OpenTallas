#!/usr/bin/env bash
# DIE-S81-85 11-09 iqf__t1 DSREP lock-step bench: ot_dp_clk_landing DSREP=1 (gold) vs DSREP=4 (gate), W 513 / 514,
# default and S81 CLAND_WCHK + CLAND_LOCAL_ON forms.  Each normal build must PASS; the mutant build (a text copy of
# ot_meso_fifo.sv whose LAST read-select copy never turns on) must FAIL.  Writes out/result.txt; exit 0 = all as expected.
# Needs verilator (>= 5.0) and perl on PATH.  Fleet hosts (no verilator on the host), with a memory cap:
#   docker run --rm --memory 8g -v $REPO:$REPO -w $PWD --entrypoint bash verilator/verilator:v5.032 ./run.sh
set -uo pipefail
cd "$(dirname "$0")"
rtl=${RTL_DIR:-$(cd ../../../.. && pwd)/rtl/common}
mkdir -p out
cp "$rtl/ot_dp_clk_landing.sv" "$rtl/ot_meso_fifo.sv" out/
# mutant: the last select copy's .on is tied low
perl -pe 's/\Qot_meso_dsel_sel #(.DEPTH(DEPTH)) u_sel (.clk(clk), .align(align), .on(on),\E/ot_meso_dsel_sel #(.DEPTH(DEPTH)) u_sel (.clk(clk), .align(align), .on((r == SREP - 1) ? 1\x27b0 : on),/' \
  out/ot_meso_fifo.sv > out/ot_meso_fifo_mutant.sv
grep -q "on((r == SREP - 1)" out/ot_meso_fifo_mutant.sv || { echo "mutation site not found"; exit 2; }
rc=0; : > out/result.txt
for form in default wchk; do
  defs=""; [ $form = wchk ] && defs="-DOT_S81_CLAND_WCHK -DOT_S81_CLAND_LOCAL_ON"
  for W in 513 514; do
    for M in normal mutant; do
      fifo=out/ot_meso_fifo.sv; [ $M = mutant ] && fifo=out/ot_meso_fifo_mutant.sv
      o=out/obj_${form}_${W}_$M
      verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -DTBW=$W $defs --top-module tb_dsrep -Mdir $o \
        tb_dsrep.sv out/ot_dp_clk_landing.sv $fifo > $o.build.log 2>&1 || { echo "form=$form W=$W $M: BUILD FAIL" | tee -a out/result.txt; rc=1; continue; }
      ./$o/Vtb_dsrep > $o.sim.log 2>&1
      res=$(grep -o 'TB_DSREP \(PASS\|FAIL\)' $o.sim.log | tail -1)
      echo "form=$form W=$W $M: $(grep '^TB_DSREP W' $o.sim.log) -> $res" | tee -a out/result.txt
      if [ $M = normal ] && [ "$res" != "TB_DSREP PASS" ]; then rc=1; fi
      if [ $M = mutant ] && [ "$res" != "TB_DSREP FAIL" ]; then rc=1; echo "MUTANT NOT DETECTED" | tee -a out/result.txt; fi
    done
  done
done
echo "BENCH rc=$rc" | tee -a out/result.txt; exit $rc
