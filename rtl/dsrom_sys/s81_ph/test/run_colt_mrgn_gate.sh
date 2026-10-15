#!/bin/bash
# run_colt_mrgn_gate.sh <src root> <out dir>: F5 collector gate: dsfd_colt_mrgn NQ 4 lockstep with the CLOSED
# dsfd_colt_mrg (PASS), NQ 1 exact frame/DONE stream (PASS, 2 seeds), MUT 1 (no DONE) FAIL; full-RTL lint of the
# 1-stack die master dsfd_bk_collector_c1.
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
SRC=$1; OUT=$2; mkdir -p $OUT
F="$SRC/rtl/dsrom_sys/s81_ph/ot_s81ph_col_tile.sv $SRC/rtl/dsrom_sys/s81_ph/dsfd_colt_mrgn.sv $SRC/rtl/dsrom_sys/s81_ph/test/tb_colt_mrgn.sv"
FCLK=$(cd $SRC && python3 tools/die_port_bind.py none --closure ot_fwd_clk_inv | tr '\n' ' ')
v=PASS
run() { l=$1; want=$2; shift 2
  verilator --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_colt_mrgn "$@" --Mdir $OUT/$l -o tb $FCLK $F > $OUT/build_$l.log 2>&1 \
    || { echo "$l BUILD_FAIL"; grep -m3 Error $OUT/build_$l.log; v=FAIL; return; }
  $OUT/$l/tb > $OUT/run_$l.log 2>&1; r=$(grep TB_COLT_MRGN $OUT/run_$l.log | tail -1); echo "$l: $r (want $want)"
  case "$r" in *" $want") ;; *) v=FAIL;; esac
}
run nq4_lockstep PASS -GNQ=4
run nq1 PASS -GNQ=1
run nq1_s2 PASS -GNQ=1 -GSEED=11
run nq1_mut1 FAIL -GNQ=1 -GMUT=1
FL=$(cd $SRC && python3 tools/die_port_bind.py none -f physical/s81_die_rtl/layer1.f --closure dsfd_bk_collector_c1 | tr '\n' ' ')
verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module dsfd_bk_collector_c1 $FL > $OUT/lint_c1.log 2>&1 \
  && echo "dsfd_bk_collector_c1 full-RTL lint PASS" || { echo "lint FAIL"; grep -m5 Error $OUT/lint_c1.log; v=FAIL; }
echo "COLT_MRGN_GATE $v"; [ $v = PASS ]
