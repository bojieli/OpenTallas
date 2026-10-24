#!/bin/bash
# TOK-DS/COMP 10-24: rstop (ot_s81sl_rstopt_xo) egress bench + latency probe on main RTL. run_rstop_1024.sh WT OUT
set -uo pipefail
WT=$1; O=$2; mkdir -p $O
cd $WT
git rev-parse HEAD > $O/main_sha.txt
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
for M in none xooff xoall xonoflag tiercol; do
  ( J=3 bash tools/s81_slice/rstopt_xo_bench.sh $O $M > $O/bench_$M.log 2>&1; echo "rc $?" >> $O/bench_$M.log ) &
done
( python3 tools/s81_dv/tokfunc/rstop_lat_tb.py rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_xo.sv $O/tb_rstop_lat.sv > $O/lat_patch.log 2>&1 \
  && $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_s81sl_rstop_xo -Mdir $O/obj_lat \
    rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv $O/tb_rstop_lat.sv --build-jobs 4 > $O/build_lat.log 2>&1 \
  && $O/obj_lat/Vtb_s81sl_rstop_xo > $O/run_lat.log 2>&1; echo "rc $?" >> $O/run_lat.log ) &
wait
for d in $O/obj_*; do echo "== $d"; python3 -I $WT/tools/verilator_nba_guard.py $d; echo "rc $?"; done > $O/nba.txt 2>&1
sha256sum rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_xo.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_sid.sv tools/s81_slice/rstopt_xo_bench.sh tools/s81_dv/tokfunc/rstop_lat_tb.py $O/tb_rstop_lat.sv > $O/sources.sha256
echo DONE
