#!/bin/bash
# TOK-QK/S8A 2-slice proof: build tb_s8dbg (N=2 qfd_dv_s8_flat, s8die source list, s8 kit defines) with the FIXED
# qfd_dv_s8_suvm_rp1 (claude/tok-qk-s8a-1024 dd2d80455, src/), then run the calibrate stimulus on
#   fix  (obj_fix)            -> must PASS check_n2.py
#   orig (s8exp/dbg/obj, unfixed suvm_rp1 = old alignment mutant) -> must FAIL
#   wf3  (s8exp/dbg/obj_wf3, the what-if) -> fix log must equal it line for line (lockstep)
set -u
A=/srv/opentallas-scratch2/claude/tok-qw/s8a; E=/srv/opentallas-scratch2/claude/tok-qw/s8exp; T=$E/tree
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd $T; t0=$(date +%s)
if [ ! -x $A/obj_fix/Vtb ]; then
verilator --cc --exe --build -O1 -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --x-assign 0 --x-initial 0 \
  +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM +define+OT_QFD_UP4_CK_ENTRIES \
  --top-module tb_s8dbg --prefix Vtb -GN=2 -GDBG=1 -CFLAGS -O0 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
  -Mdir $A/obj_fix rtl/test/qwen_dv/main2.cpp $(cat $A/src/files_fix.txt) $E/dbg/src/tb_s8dbg.sv > $A/build_fix.log 2>&1
echo "build rc=$? $(( $(date +%s)-t0 )) s" | tee -a $A/timing.txt
fi
cd $A
for v in fix:$A/obj_fix orig:$E/dbg/obj wf3:$E/dbg/obj_wf3; do n=${v%%:*}; o=${v#*:}
  $o/Vtb +EV=$E/dbg/cal.ev +LOG=$A/n2_$n.log +NCYC=2268 > $A/n2_$n.out 2>&1; echo "$n sim rc=$?" | tee -a $A/timing.txt
  python3 -I $A/check_n2.py $T $A/n2_$n.log > $A/n2_$n.check.json; echo "$n $(cut -c1-200 $A/n2_$n.check.json)"
done
cmp $A/n2_fix.log $A/n2_wf3.log && echo "LOCKSTEP fix == wf3 log ($(wc -l < $A/n2_fix.log) lines)" || echo "LOCKSTEP MISMATCH"
