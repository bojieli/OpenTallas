#!/bin/bash
# A2P-HC: build NQ4 m0 / NQ2 m0 / NQ2 mut4, run P1/P2/P8/G22 per NQ, mutant on NQ2 P1. Run from the repo root (src).
set -u
S=$PWD; O=${1:?out}; mkdir -p $O
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V(){ echo "$(date -Is) $*" >> $O/verdict.txt; }
build(){ # name nq mut
  python3 tools/hbm_hc_eng_build.py --objdir $O/obj_$1 --nq $2 --mutant $3 --jobs 8 > $O/build_$1.log 2>&1
  [ -x $O/obj_$1/Vtb_hbm_hc_eng_static ] && V "build $1 OK" || V "build $1 FAILED"
}
build nq4 4 0 & build nq2 2 0 & build nq2m4 2 4 & wait
run(){ # bin dir -> PASS?
  ( cd $2 && $O/obj_$1/Vtb_hbm_hc_eng_static $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log )
  grep -h "HC_ENG_DONE\|HC_ENG PASS\|HC_ENG FAIL\|FAULT\|MISMATCH\|watchdog\|RUN_RC" $2/run.log | head -8 | sed "s|^|  $1/$(basename $2): |" >> $O/verdict.txt
  grep -q "HC_ENG PASS" $2/run.log
}
gen(){ python3 tools/rtl_hbm_hc_eng_static_gate.py --run $1 "${@:2}" >> $O/gen.log 2>&1; }
for nq in 4 2; do
  for P in 1 2 8; do d=$O/nq${nq}_p$P; gen $d --mode full --npos $P --raw0 137 --rs 104 --nq $nq; (run nq$nq $d && V "NQ$nq P$P PASS" || V "NQ$nq P$P FAIL") & done
  d=$O/nq${nq}_g22; gen $d --mode g22 --nq $nq; (run nq$nq $d && V "NQ$nq G22 PASS" || V "NQ$nq G22 FAIL") &
done
d=$O/nq2_p1_mut4; gen $d --mode full --npos 1 --raw0 137 --rs 104 --nq 2; (run nq2m4 $d && V "NQ2 MUT4 unexpectedly PASS (escape)" || V "NQ2 MUT4 FAIL as expected") &
d=$O/nq2_p1_mutq3; gen $d --mode full --npos 1 --raw0 137 --rs 104 --nq 2
python3 - $d/prog.mem <<'PY'
# schedule mutant: the first x ingest event of client 1 names client 2 (absent on the half die) -> must fault
import sys; p=sys.argv[1]; L=open(p).read().split()
for i,w in enumerate(L):
    v=int(w,16)
    if (v>>20)&1 and ((v>>21)&3)==1 and not (v>>23)&1:
        v=(v & ~(3<<21)) | (2<<21); L[i]='%064x'%v; break
open(p,'w').write('\n'.join(L)+'\n')
PY
(run nq2 $d && V "NQ2 CLIENT2 EVENT unexpectedly PASS (escape)" || V "NQ2 CLIENT2 EVENT FAIL as expected") &
wait
V "chain done"
cat $O/verdict.txt
