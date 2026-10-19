#!/bin/bash
# LAYERBENCH smoke of one cut die slice (tools/qwen_layerbench/slice_cut.py output dir): generate the smoke bench,
# build with Verilator 5.050 (the closure daemon's pin), run twice from two random initial states (reset completeness:
# the two output folds must match), report SMOKE_PASS / SMOKE_FAIL.
# SMOKE_UNRESET_OK = regex of outputs allowed to differ between the two initial states (declared, with a reason, in the record)
# usage: [BENCH_FILES="neighbour-replay RTL files"] [BENCH_DEFS="+define+..."] run_smoke.sh SLICE_DIR WORK [DRIVE_SVH|-] [MUT] [plusargs...]
set -u
SL=$(readlink -f "$1"); W=$(mkdir -p "$2" && readlink -f "$2"); DRV=${3:--}; MUT=${4:-0}; shift 4 2>/dev/null || shift $#
H=$(cd "$(dirname "$0")" && pwd)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
TOP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['top'])" $SL/slice.json)
[ -f $W/tb_$TOP.sv ] && cp $W/tb_$TOP.sv $W/tb_prev.sv
python3 $H/slice_smoke.py $SL/slice.json --out $W/tb_$TOP.sv || exit 2
DEF=""; [ "$DRV" != "-" ] && DEF="+define+SLICE_DRIVE=\"$(readlink -f $DRV)\" +incdir+$(dirname $(readlink -f $DRV))"
O=$W/obj_m$MUT
verilator --version > $W/verilator.version
if [ -x $O/Vtb_$TOP ] && cmp -s $W/tb_$TOP.sv $W/tb_prev.sv && [ -z "${SMOKE_REBUILD:-}" ]; then echo "reusing $O (bench unchanged)" >> $W/build_m$MUT.log; else
/usr/bin/time -f "%e s %M KB" -o $W/build_m$MUT.time verilator --binary --timing -j 16 -O1 -Wno-fatal -Wno-lint -Wno-style \
    -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN --x-assign unique --x-initial unique \
    --top-module tb_$TOP -GMUT=$MUT -Mdir $O $DEF ${BENCH_DEFS:-} -f $SL/$TOP.f ${BENCH_FILES:-} $W/tb_$TOP.sv > $W/build_m$MUT.log 2>&1; fi
if [ ! -x $O/Vtb_$TOP ]; then echo "SMOKE_BUILD_FAIL $TOP (see $W/build_m$MUT.log)"; grep -m20 -E '%Error' $W/build_m$MUT.log; exit 3; fi
rc=0
for s in 1 2; do
    $O/Vtb_$TOP +verilator+rand+reset+2 +verilator+seed+$s "$@" > $W/run_m${MUT}_s$s.log 2>&1; echo "exit $?" >> $W/run_m${MUT}_s$s.log
done
grep -hE 'SMOKE_(PASS|FAIL)|%Error|%Warning|Assertion|\$error' $W/run_m${MUT}_s1.log | head -5
python3 - $W/run_m${MUT}_s1.log $W/run_m${MUT}_s2.log > $W/reset_det_m$MUT.txt <<'PY'
import re, sys
import os
OK = re.compile(os.environ.get('SMOKE_UNRESET_OK', r'(?!)'))   # declared (and reasoned in the record) unreset data outputs
def rd(f):
    out, ph = {}, 'idle'
    for l in open(f):
        if l.startswith('SMOKE_FOLD programme'): ph = 'programme'
        m = re.match(r'SMOKE_OFOLD (\S+) (\S+) act (\d+)', l)
        if m: out[(ph if (ph, m.group(1)) not in out else 'programme', m.group(1))] = m.group(2)
    return out
a, b = rd(sys.argv[1]), rd(sys.argv[2])
if not a: print('RESET_DET NO_TRACE'); sys.exit(0)
diff = sorted({p for k, p in a if a[(k, p)] != b.get((k, p))})
ctl = [p for p in diff if not OK.fullmatch(p)]
print(f'RESET_DET ports {len({p for _, p in a})} nondet {len(diff)} undeclared_nondet {len(ctl)}')
for p in diff: print(('  UNDECLARED ' if p in ctl else '  declared   ') + p)
PY
head -1 $W/reset_det_m$MUT.txt
grep -q 'undeclared_nondet 0' $W/reset_det_m$MUT.txt && echo "SMOKE_RESET_DETERMINISTIC $TOP (every output, except the declared SMOKE_UNRESET_OK ones listed in reset_det_m$MUT.txt)" || { echo "SMOKE_RESET_NONDETERMINISTIC $TOP"; grep UNDECLARED $W/reset_det_m$MUT.txt | head -12; rc=1; }
grep -q SMOKE_PASS $W/run_m${MUT}_s1.log && grep -q SMOKE_PASS $W/run_m${MUT}_s2.log || rc=1
[ $rc = 0 ] && echo "SMOKE_RESULT PASS $TOP MUT=$MUT" || echo "SMOKE_RESULT FAIL $TOP MUT=$MUT"
exit $rc
