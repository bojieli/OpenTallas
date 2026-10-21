#!/bin/bash
# DRIVE-S81-GUPROP 10-20: gather maps (98 / 84 frames, GU_PROP) -> SW consumer bench vectors for EVERY consumer beat leaf
# (G 0..62) -> tb_vs_guprop on Verilator 5.050 (m0), gather-map mutants srcoff / gswap, overlapped issue (ovl, measurement),
# RTL negative control VS_MUT=1.  usage (lane root on the fleet): run_bench.sh OUT
set -uo pipefail; cd "$(dirname "$0")"; O=${1:-bench}; mkdir -p $O/vec
./run_gather.sh 3R,4L 1 $O/g98gp > /dev/null; ./run_gather.sh 1R,3R,4L,6L 1 $O/g84gp > /dev/null
grep -h GATHER_RC $O/g98gp.log $O/g84gp.log
GEN="python3 root/tools/s81_dv/layer_prog/vs/gen_guprop_bench.py --fixtures fixtures/L0"
for G in $(seq 0 62); do
  $GEN --map $O/g98gp.json --G $G --out $O/vec/f98_G$G >> $O/gen.log 2>&1 || echo "GEN_FAIL f98 $G"
  $GEN --map $O/g84gp.json --G $G --out $O/vec/f84_G$G >> $O/gen.log 2>&1 || echo "GEN_FAIL f84 $G"
done
# mutants / ovl on the consumers with the most source slices (+ one shared-slot leaf)
SEL=$(python3 -c "
import json; m=json.load(open('$O/g98gp.json')); s={}
for r in m['records']: s.setdefault(r['G'], set()).add(r['src_sid'])
g=sorted(s, key=lambda G: (-len(s[G]), G)); print(' '.join(map(str, sorted(set(g[:4] + [58])))))")
echo "SEL $SEL" > $O/sel.txt
for G in $SEL; do
  for mu in srcoff gswap; do $GEN --map $O/g98gp.json --G $G --mutant $mu --out $O/vec/${mu}_f98_G$G >> $O/gen.log 2>&1; done
  $GEN --map $O/g98gp.json --G $G --issue ovl --out $O/vec/ovl_f98_G$G >> $O/gen.log 2>&1
done
B=root/tools/s81_dv/layer_prog/vs/run_guprop_bench.sh
J=8 $B root $O/run 0 $O/vec/f98_G* $O/vec/f84_G* $O/vec/srcoff_* $O/vec/gswap_* $O/vec/ovl_* > $O/run_m0.txt 2>&1
J=8 $B root $O/run 1 $(for G in $SEL; do echo $O/vec/f98_G$G; done) > $O/run_m1.txt 2>&1
echo "M0 PASS $(grep -c 'PASS$' $O/run_m0.txt) FAIL $(grep -c 'FAIL$' $O/run_m0.txt) | M1 PASS $(grep -c 'PASS$' $O/run_m1.txt) FAIL $(grep -c 'FAIL$' $O/run_m1.txt)"
echo BENCH_RC 0
