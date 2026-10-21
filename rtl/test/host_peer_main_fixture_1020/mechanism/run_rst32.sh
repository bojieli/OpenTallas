#!/bin/bash
set -eu
V=/opt/verilator-5.050/bin/verilator;[ -x "$V" ] || V=$(command -v verilator)
for case in exact mutant;do
 flags=();[ "$case" != mutant ] || flags+=(-DOT_RST32_MUT)
 "$V" --binary --timing -Wno-fatal -j 4 --top-module tb_rst32 --Mdir "obj_rst32_$case" "${flags[@]}" rtl/lib/ot_rst_relay.sv rtl/test/host_peer_main_fixture_1020/mechanism/tb_rst32.sv > "build_rst32_$case.log" 2>&1
 set +e;"obj_rst32_$case/Vtb_rst32" > "run_rst32_$case.log" 2>&1;rc=$?;set -e
 cat "run_rst32_$case.log"
 if [ "$case" = exact ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];grep -q 'RST32 FAIL' "run_rst32_$case.log";fi
done
