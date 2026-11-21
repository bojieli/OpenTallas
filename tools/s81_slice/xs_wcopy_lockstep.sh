#!/bin/bash
# xs_wcopy_lockstep.sh OUT [1] (cwd = repo root): OT_S81SL_XS_WCOPY lockstep of ot_s81sl_xs with vs without the define   mut=1 builds the gate with a broken mask half (negative control, must FAIL)
set -u; O=$(realpath -m $1); MUT=${2:-0}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
VROOT=$($V -V | sed -n 's/^ *VERILATOR_ROOT *= *//p' | head -1)
X=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv
{ echo '`define OT_S81SL_XS_WCOPY'; sed -e 's/^module ot_s81sl_xs #/module ot_s81sl_xs_wc #/' -e 's/OT_S81SL_XS_MUT_/OT_S81SL_XS_WCNOMUT_/g' $X; echo '`undef OT_S81SL_XS_WCOPY'; } > $O/ot_s81sl_xs_wc.sv
[ $MUT = 1 ] && sed -i 's/{128{!fg0\[1\] || !fg0\[0\]}}/{128{!fg0[1] || fg0[0]}}/' $O/ot_s81sl_xs_wc.sv
grep -q '^module ot_s81sl_xs_wc' $O/ot_s81sl_xs_wc.sv || { echo rename failed; exit 3; }
CAL="rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv"
MAC="physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
S="rtl/lib/ot_rst_relay.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv $CAL rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv $MAC rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs_ctl.sv $X $O/ot_s81sl_xs_wc.sv"
D=rtl/dsrom_sys/s81_dv/slice/test
$V --cc -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --prefix Vtb --top-module tb_s81sl_xs_wcopy --Mdir $O/obj +define+DSFD_PQ_STATIC_X2 $S $D/tb_s81sl_xs_wcopy.sv > $O/verilate.log 2>&1 || { echo BUILD_FAILED; tail -8 $O/verilate.log; exit 3; }
make -C $O/obj -f Vtb.mk -j8 Vtb__ALL.a OPT_FAST=-O1 OPT_SLOW=-O0 > $O/make.log 2>&1 || { echo BUILD_FAILED make; tail -5 $O/make.log; exit 3; }
g++ -std=c++20 -O1 -I$VROOT/include -I$VROOT/include/vltstd -I$O/obj $D/tb_s81sl_xs_wcopy.cpp $O/obj/Vtb__ALL.a $VROOT/include/verilated.cpp $VROOT/include/verilated_threads.cpp -pthread -o $O/tb > $O/link.log 2>&1 || { echo BUILD_FAILED link; tail -5 $O/link.log; exit 3; }
$O/tb
