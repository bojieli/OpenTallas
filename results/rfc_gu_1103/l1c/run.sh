#!/bin/bash
# usage: run.sh <repo root> <workdir> [MUT define: 1 = OT_RF_MUT_L1C] -> L1C_RF PASS / FAIL
R=$1; T=$2; M=${3:-0}; V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$(cd "$(dirname "$0")" && pwd); mkdir -p $T; DEF=""; [ "$M" = 1 ] && DEF="-DOT_RF_MUT_L1C"
cd $T && $V --cc --exe --build -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $DEF --top-module tb_l1c_rf -Mdir obj$M \
  $R/rtl/lib/ot_rst_relay.sv $R/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_sel.sv $R/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1c.sv \
  $D/tb_l1c_rf.sv $D/tb_l1c_rf.cpp -CFLAGS -O1 > build$M.log 2>&1 || { echo "L1C_RF FAIL build"; tail -5 build$M.log; exit 1; }
./obj$M/Vtb_l1c_rf +CYC=${CYC:-200000} | tail -6
