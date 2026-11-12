#!/usr/bin/env bash
# CLAND-SLEW-1 (GEN-CLASS-1 11-12) lock-step bench: ot_dp_clk_landing_ca / _cas DSREP=1 (gold) vs DSREP=8 (gate),
# W 65 / 568 (the hd_spn_wshim_rx link_i dataflow ring).  Each normal build must PASS; the mutant (last read-select copy
# never turns on) must FAIL.  Writes out/result_ca.txt; exit 0 = all as expected.  Needs verilator (>= 5.0) + perl:
#   docker run --rm --memory 8g -v $REPO:$REPO -w $PWD --entrypoint bash verilator/verilator:v5.032 ./run_ca.sh
set -uo pipefail
cd "$(dirname "$0")"
rtl=${RTL_DIR:-$(cd ../../../.. && pwd)/rtl/common}
mkdir -p out
cp "$rtl/ot_dp_clk_landing_ca.sv" "$rtl/ot_dp_clk_landing.sv" "$rtl/ot_meso_fifo.sv" out/
perl -pe 's/\Qot_meso_dsel_sel #(.DEPTH(DEPTH)) u_sel (.clk(clk), .align(align), .on(on),\E/ot_meso_dsel_sel #(.DEPTH(DEPTH)) u_sel (.clk(clk), .align(align), .on((r == SREP - 1) ? 1\x27b0 : on),/' \
  out/ot_meso_fifo.sv > out/ot_meso_fifo_mutant.sv
grep -q "on((r == SREP - 1)" out/ot_meso_fifo_mutant.sv || { echo "mutation site not found"; exit 2; }
rc=0; : > out/result_ca.txt
for W in 65 568; do
  for M in normal mutant; do
    fifo=out/ot_meso_fifo.sv; [ $M = mutant ] && fifo=out/ot_meso_fifo_mutant.sv
    o=out/obj_ca_${W}_$M
    verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -DTBW=$W --top-module tb_dsrep_ca -Mdir $o \
      tb_dsrep_ca.sv out/ot_dp_clk_landing_ca.sv out/ot_dp_clk_landing.sv $fifo > $o.build.log 2>&1 || { echo "W=$W $M: BUILD FAIL" | tee -a out/result_ca.txt; rc=1; continue; }
    ./$o/Vtb_dsrep_ca > $o.sim.log 2>&1
    res=$(grep -o 'TB_DSREP_CA \(PASS\|FAIL\)' $o.sim.log | tail -1)
    echo "W=$W $M: $(grep '^TB_DSREP_CA W' $o.sim.log) -> $res" | tee -a out/result_ca.txt
    if [ $M = normal ] && [ "$res" != "TB_DSREP_CA PASS" ]; then rc=1; fi
    if [ $M = mutant ] && [ "$res" != "TB_DSREP_CA FAIL" ]; then rc=1; echo "MUTANT NOT DETECTED" | tee -a out/result_ca.txt; fi
  done
done
echo "BENCH rc=$rc" | tee -a out/result_ca.txt; exit $rc
