#!/bin/bash
# TOK-QK/S8A owner decision 13 check: the 2-slice proof with RANDOMISED initial state (--x-initial unique --x-assign unique,
# +verilator+rand+reset+2, 3 seeds) for the fixed RTL (must PASS) and the unfixed RTL (must FAIL).
set -u
A=/srv/opentallas-scratch2/claude/tok-qw/s8a; E=/srv/opentallas-scratch2/claude/tok-qw/s8exp; T=$E/tree
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd $T
for v in fix:$A/src/files_fix.txt orig:$E/dbg/src/files.txt; do n=${v%%:*}; fl=${v#*:}; t0=$(date +%s)
 [ -x $A/obj_rnd_$n/Vtb ] || { verilator --cc --exe --build -O1 -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --x-assign unique --x-initial unique \
  +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM +define+OT_QFD_UP4_CK_ENTRIES \
  --top-module tb_s8dbg --prefix Vtb -GN=2 -GDBG=1 -CFLAGS -O0 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
  -Mdir $A/obj_rnd_$n rtl/test/qwen_dv/main2.cpp $(cat $fl) $E/dbg/src/tb_s8dbg.sv > $A/build_rnd_$n.log 2>&1; echo "build $n rc=$? $(( $(date +%s)-t0 )) s" | tee -a $A/timing.txt; }
done
cd $A
for n in fix orig; do for s in 11 22 33; do
  $A/obj_rnd_$n/Vtb +verilator+rand+reset+2 +verilator+seed+$s +EV=$E/dbg/cal.ev +LOG=$A/rnd_${n}_$s.log +NCYC=2268 > $A/rnd_${n}_$s.out 2>&1
  python3 -I $A/check_n2.py $T $A/rnd_${n}_$s.log > $A/rnd_${n}_$s.check.json; echo "RND $n seed $s $(cut -c1-160 $A/rnd_${n}_$s.check.json)"
done; done
