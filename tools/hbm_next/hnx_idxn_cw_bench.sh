#!/bin/bash
# HBM-NEXT-UNITS IDXQ 2026-10-19: ot_hnx_idxn_calendar CW=1 (bypass) and CW=2 (no-bypass 3-row ring) vs CW=0 lockstep (tb_hnx_idxn_cw).
# Fleet (Verilator 5.050), from a bundle root:  tools/hbm_next/hnx_idxn_cw_bench.sh OUT
#  f<N>      compiled IDXN frame (--score-chain 14), N = 1/2/4/6 rows, pitch 232 (the row II)          -> PASS
#  f6p<P>    frame, 6 rows, pitch 233 / 236 / 300                                                   -> PASS
#  f8h<H>    frame, 8 rows, pitch 232, start phase H = 0..7 (every phase has one bypass row)         -> PASS
#  r<S>/s<S> random 2,048-word frames (dense / 1-in-8 sparse words), 6 rows, pitches 232 / 233 / 237     -> PASS
#  m1 m2 m3  CW=1 ring bypass off (8 rows 232 phase 3) / ring slot pinned 0 / head row 0 dropped (6 rows 233) -> FAIL
#  m4 m5 m6  CW=2 ring write slot pinned 0 / shared head rows 0-1 dropped / ring read slot pinned 0 (6 rows 233) -> FAIL
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null) $(verilator --version)"
SRC=(rtl/hbm_next/idxn/ot_hnx_idxn_calendar.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/hbm_next/idxn/tb/tb_hnx_idxn_cw.sv)
sha256sum "${SRC[@]}" tools/hbm_next/hnx_idxn_calendar.py tools/hbm_idx_static_calendar.py tools/hbm_next/hnx_idxn_cw_bench.sh > $O/sources.sha256
python3 tools/hbm_next/hnx_idxn_calendar.py $O/cal --score-chain 14 > $O/cal.log 2>&1 || { V "calendar FAILED"; cat $O/cal.log; exit 1; }
L=$(python3 -c "import json;print(json.load(open('$O/cal/frame/calendar.json'))['length'])")
python3 - "$O" <<'PY'
import random, sys
o = sys.argv[1]
for s in (1, 2, 3):
    for kind in ('r', 's'):
        rnd = random.Random(1000 * s + (kind == 's'))
        w = [rnd.getrandbits(32) if (kind == 'r' or rnd.random() < 0.125) else 0 for _ in range(2048)]
        open(f'{o}/{kind}{s}.hex', 'w').write('\n'.join(f'{x:08x}' for x in w) + '\n')
PY
d=$O/obj; rm -rf $d
verilator --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_idxn_cw -Mdir $d -o Vc "${SRC[@]}" > $O/build.log 2>&1
V "build rc=$? bin=$( [ -x $d/Vc ] && echo ok || echo MISSING) frame length $L"
[ -x $d/Vc ] || { tail -30 $O/build.log | tee -a $O/verdict.txt; exit 1; }
run(){ # tag hex len want plusargs...
  local t=$1 h=$2 ln=$3 want=$4; shift 4; local od=$O/run_$t; rm -rf $od; mkdir -p $od; cp $h $od/cal.hex
  ( cd $od && $d/Vc +LEN=$ln "$@" > run.log 2>&1; echo RUN_RC=$? >> run.log )
  local got=PASS; grep -q 'IDXN_CW PASS' $od/run.log || got=FAIL
  local ok=OK; [ "$got" = "$want" ] || ok=UNEXPECTED
  V "$t [$ok want $want got $got]: $(grep -h 'IDXN_CW rows\|CWBAD\|CW2BAD' $od/run.log | head -3 | tr '\n' ' ')"; rm -f $od/cal.hex
}
F=$O/cal/frame/calendar_instructions.hex
for n in 1 2 4 6; do run f$n $F $L PASS +ROWS=$n +PITCH=232 & done
for p in 233 236 300; do run f6p$p $F $L PASS +ROWS=6 +PITCH=$p & done
for h in 0 1 2 3 4 5 6 7; do run f8h$h $F $L PASS +ROWS=8 +PITCH=232 +PHASE=$h & done
wait
i=0; for s in 1 2 3; do for k in r s; do p=$((232 + (i % 3) * 2 + (i % 2))); i=$((i+1)); run $k$s $O/$k$s.hex 2048 PASS +ROWS=6 +PITCH=$p & done; done
run m1 $F $L FAIL +ROWS=8 +PITCH=232 +PHASE=3 +MUT=1 &
for m in 2 3 4 5 6; do run m$m $F $L FAIL +ROWS=6 +PITCH=233 +MUT=$m & done
wait
rm -rf $d
V "SUMMARY unexpected=$(grep -c UNEXPECTED $O/verdict.txt)"
V done
