#!/bin/bash
# S81-ROMCAP 10-20: GU_MERGE (gate ++ up rows of one expert as ONE placed matrix) on the release frame u_f_0L00.
#  1. FRAME: compile the L0 field (XS + BF ops) with merge 0 / 1: phase counts, legaliser faults, max ROM fill.
#  2. BENCH: vectors of merged experts_gu phases (mixed gate/up rows, 1-row tail, next expert, last expert) + swap / shift
#     mutants; one Verilator 5.050 build of col_h9_l4 (LK 5, as bench_xsp4); xs_place.py check: bit-exact + cycle-exact.
set -u
D=/srv/opentallas-scratch/claude/s81-romcap; S=$D/src; O=$D/out; FX=$D/fixtures/L0
DR=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref
[ -e $O ] && { echo REFUSE_EXISTING_OUT; exit 2; }; mkdir -p $O
cd $S; echo "HOST $(hostname) $(python3 --version 2>&1)"
X=tools/s81_dv/layer_prog/xs_place.py
for M in 0 1; do
  OT_XS_GU_MERGE=$M python3 $X frame --frame u_f_0L00 --fixtures $FX --die-src $DR --out $O/frame_m$M > $O/frame_m$M.log 2>&1
  echo "FRAME merge=$M rc=$? $(grep XS_FRAME $O/frame_m$M.log)"
  python3 -c "
import json,collections;r=json.load(open('$O/frame_m$M/frame.json'))
c=collections.Counter(p['op'] for p in r['phases']);f=collections.Counter(p['op'] for p in r['phases'] if p.get('faults'))
print('PHASES merge=$M',dict(c),'faulty',dict(f),'nphases',r['nphases'],'maxfill',max(r['fill']),'/',r['depth'])
print('GU_PHASES merge=$M',[(p['phase'],p['mat'],p['rows'],p['calendar'],p['faults']) for p in r['phases'] if p['op']=='ffn.experts_gu'][:8])"
done
# vectors: --ops ffn.experts_gu -> field phase 0 = a_proj, 1..18 = merged gu (3 per expert)
G="OT_XS_GU_MERGE=1 python3 $X gen --frame u_f_0L00 --fixtures $FX --die-src $DR --ops ffn.experts_gu"
eval $G --out $O/vec --phase 1 3 4 18 > $O/gen.log 2>&1; echo "GEN rc=$? $(grep -c XS_PLACE_GEN $O/gen.log) vectors"; grep XS_PLACE_GEN $O/gen.log
eval $G --out $O/vec_swap --phase 1 --mutant swap > $O/gen_swap.log 2>&1; echo "GEN_SWAP rc=$?"
eval $G --out $O/vec_shift --phase 1 --mutant shift > $O/gen_shift.log 2>&1; echo "GEN_SHIFT rc=$?"
mv $O/vec_swap/p1 $O/vec/p1swap; mv $O/vec_shift/p1 $O/vec/p1shift
MASTER=col_h9 LK=5 J=16 bash tools/s81_dv/layer_prog/xs/xs_bench.sh $O/bench $O/vec/p1 $O/vec/p3 $O/vec/p4 $O/vec/p18 $O/vec/p1swap $O/vec/p1shift
for v in p1 p3 p4 p18 p1swap p1shift; do
  OT_XS_GU_MERGE=1 python3 $X check --dir $O/vec/$v --log $O/bench/run_$v.log --fixtures $FX > $O/check_$v.log 2>&1
  echo "CHECK $v rc=$? $(tail -1 $O/check_$v.log)"
done
echo ROMCAP_GUMERGE_DONE
