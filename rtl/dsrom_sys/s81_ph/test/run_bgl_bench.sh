#!/bin/bash
# run_bgl_bench.sh OUT CASE : lockstep bench of the 8-leaf dsfd_vm_bgq28h against the flat dsfd_vm_bgr (Verilator >= 5.050).
#   gold | gold_s2 | stress        random stimulus, exact (expect PASS)
#   trace                          PRODUCTION trace: the master gate's tp case records slice 0's request bus, replayed here
#   cov_refuse                     too short to cover: must print COVERAGE_REFUSED + FAIL
#   mut_RELAY | mut_ID | mut_J0 | mut_ORDER | mut_MASK    mutants (expect FAIL)
# Prints "BGL_<case>: PASS|FAIL|BUILD_FAIL".  Run from the repo root.
set -u
OUT=$1; C=$2; R=$(pwd); mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=$(which verilator)
T=rtl/dsrom_sys/s81_ph
case $C in
  gold) A="";; gold_s2) A="-GSEED=2 -GGRP=3";; stress) A="-GRATE=3";; cov_refuse) A="-GNCYC=300";;
  trace) A="-GTRACE=1";; mut_*) A="+define+OT_VMBGL_${C/mut_/MUT_} -GNCYC=40000";; *) echo "BGL_$C: unknown case"; exit 2;;
esac
P=""
if [ "$C" = trace ]; then
  VERILATOR=$V python3 tools/s81_vm/s81_vm_gate.py one tp_trace --out "$OUT/master" > "$OUT/master.out" 2>&1 \
    || { echo "BGL_$C: BUILD_FAIL (master tp_trace)"; tail -5 "$OUT/master.out"; exit 1; }
  P="+trace=$(cd "$OUT/master" && pwd)/bg_trace.txt"
fi
$V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -j 8 --top-module tb_dsfd_vm_bgl_lockstep --Mdir "$OUT/obj_$C" \
   +define+OT_VMBGL_FLOPMEM $A $R/$T/test/tb_dsfd_vm_bgl_lockstep.sv $R/$T/vm/dsfd_vm_bgl.sv $R/$T/vm/dsfd_vm_bgq_sys.sv \
   > "$OUT/build_$C.log" 2>&1 || { echo "BGL_$C: BUILD_FAIL"; grep -m8 -i error "$OUT/build_$C.log"; exit 1; }
"$OUT/obj_$C/Vtb_dsfd_vm_bgl_lockstep" $P > "$OUT/run_$C.log" 2>&1
grep -E "^(RESULT|MISMATCH|COVERAGE|TRACE)" "$OUT/run_$C.log" | head -8
r=$(grep -x -E 'PASS|FAIL' "$OUT/run_$C.log" | tail -1); echo "BGL_$C: ${r:-FAIL}"
[ "$r" = PASS ]
