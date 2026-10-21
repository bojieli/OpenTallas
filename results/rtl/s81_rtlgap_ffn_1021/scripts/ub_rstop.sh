#!/bin/bash
# RG-FFN: existing rstop_sid bench (tb_s81sl_rstop_sid) against ot_s81sl_rstopt: tb copy with the module name substituted.
set -u; S=$(pwd); O=$S/ub_rstop_$1; M=${2:-none}; mkdir -p $O; cd $S/src
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
sed 's/ot_s81sl_rstop u (/ot_s81sl_rstopt u (/' rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_sid.sv > $O/tb_s81sl_rstop_sid.sv
grep -c "ot_s81sl_rstopt u" $O/tb_s81sl_rstop_sid.sv
D=""; [ $M = tiercol ] && D="+define+OT_S81SL_RSTOP_MUT_TIERCOL"
$V --version > $O/version_$M.log
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $D --top-module tb_s81sl_rstop_sid -Mdir $O/obj_$M \
  rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt.sv $O/tb_s81sl_rstop_sid.sv --build-jobs 4 > $O/build_$M.log 2>&1 \
  || { echo "BUILD_FAILED"; grep -m8 "%Error" $O/build_$M.log; exit 3; }
$O/obj_$M/Vtb_s81sl_rstop_sid > $O/run_$M.log 2>&1
grep -E "^MISMATCH|^PASS|^FAIL" $O/run_$M.log | head -12
if [ $M = none ]; then grep -q '^PASS rstop_sid' $O/run_$M.log && { echo "BENCH_PASS rstop_sid"; exit 0; }; echo "BENCH_FAIL rstop_sid"; exit 1; fi
grep -q '^FAIL rstop_sid' $O/run_$M.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED MUT=$M (bench blind)"; exit 1
