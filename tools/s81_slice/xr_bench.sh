#!/bin/bash
# xr_bench.sh <outdir> [base|hops|row|porder|nocol] [SEED] [HB 0|1] [NC] [raw]  (cwd = repo root): S81-SLICE control-plane
# bench (ot_s81sl_xr1 / ot_s81sl_xr3 vs the transaction model, tb_s81sl_xr.sv).  base must PASS; the mutants must FAIL.
# Exit 0 = the expected verdict.  A 6th argument 'raw' reports a mutant's own verdict (exit 1 on FAIL: an expect=fail bench).
set -u; O=$1; M=${2:-base}; S=${3:-1}; H=${4:-0}; N=${5:-6000}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
DEF=""; case $M in hops) DEF="+define+OT_S81SL_XR_MUT_HOPS";; row) DEF="+define+OT_S81SL_XR_MUT_ROW";;
  porder) DEF="+define+OT_S81SL_XR_MUT_PORDER";; nocol) DEF="+define+OT_S81SL_XR_MUT_NOCOL";; base) ;; *) echo "BAD_MODE $M"; exit 2;; esac
[ "${XR_FOREG:-0}" = 1 ] && DEF="$DEF +define+OT_S81SL_XR_FOREG"   # XR6 fallback build (dedicated fault output flop)
srcs="rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xr.sv"
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GHB=$H -GSEED=$S -GNC=$N --top-module tb_s81sl_xr \
  -Mdir $O/obj $srcs --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
  || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_xr > $O/run.log 2>&1
grep -E "MISMATCH" $O/run.log | head -8; grep -E "^XRB|^XRILL" $O/run.log; grep -E "^XRFAULT .*fault=[^1]" $O/run.log
if [ "$M" = base ]; then grep -q '^PASS' $O/run.log && { echo "PASS xr base hb=$H seed=$S"; exit 0; }; echo "FAIL xr"; exit 1; fi
[ "${6:-}" = raw ] && { grep -q '^PASS' $O/run.log && exit 0; exit 1; }
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
