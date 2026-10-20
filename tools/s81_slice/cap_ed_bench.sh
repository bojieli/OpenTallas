#!/bin/bash
# cap_ed_bench.sh <outdir> <DM>  -- LEAD2-S81/TOK2 10-19: ot_s81sl_cap_ed bench (tb_s81sl_cap_ed, DX = 24); DM != 24 = RTL mutant
set -u; O=$1; DM=${2:-24}; mkdir -p $O
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x $V ] || V=verilator
$V --version > $O/verilator.version
$V --binary --timing -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GDM=$DM --top-module tb_s81sl_cap_ed -Mdir $O/obj \
  rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv \
  rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_cap_ed.sv > $O/build.log 2>&1 || { echo "BUILD_FAILED"; exit 3; }
$O/obj/Vtb_s81sl_cap_ed > $O/run.log 2>&1; cat $O/run.log | grep -E "^TB_CAP_ED"
grep -q "^TB_CAP_ED PASS" $O/run.log
