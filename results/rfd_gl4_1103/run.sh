#!/bin/bash
# usage: [OLAT=2] run.sh <repo root> <workdir> [1 = mutant OT_RF_MUT_L4, 2 = OT_RFD_MUT_L4F posedge out face] -> L4_RF PASS / FAIL
R=$1; T=$2; M=${3:-0}; V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$(cd "$(dirname "$0")" && pwd); mkdir -p $T; DEF=""; [ "$M" = 1 ] && DEF="-DOT_RF_MUT_L4"; [ "$M" = 2 ] && DEF="-DOT_RFD_MUT_L4F"; DEF="$DEF -DOLAT_N=${OLAT:-2}"
cd $T && $V --cc --exe --build -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $DEF --top-module tb_l4_rf -Mdir obj$M \
  $R/rtl/lib/ot_rst_relay.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_sfu.sv $R/rtl/hdc/ot_hdc_fastfp.sv $R/rtl/hdc/ot_hdc_fastfp_lat_f12.sv \
  $R/rtl/hdc/ot_hdc_fp32_f12.sv $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hdc/ot_hdc_prefix.sv \
  $R/rtl/hdc/v41x/ot_dsrom_su_norm.sv $R/rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sfu.sv \
  $R/rtl/hdc/v41x/ot_dsrom_divc.sv $R/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_pass.sv $R/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l4.sv \
  $D/tb_l4_rf.sv $D/tb_l4_rf.cpp -CFLAGS -O1 > build$M.log 2>&1 || { echo "L4_RF FAIL build"; grep -m5 -i error build$M.log; exit 1; }
./obj$M/Vtb_l4_rf +CYC=${CYC:-200000} | tail -6
