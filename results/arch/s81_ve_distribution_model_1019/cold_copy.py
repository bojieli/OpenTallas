"""Symbolic OLD-store proof of shared-next-state pointer-copy mechanism."""
import json,math
from pathlib import Path
P=Path(__file__).resolve().parent
cases=0;checks=0;bad_mutant=None
for N in range(1,27):
    codes=1<<max(1,(N-1).bit_length());D=N+2
    for a0 in range(codes):
        for b0 in range(codes):
            cases+=1;a=a0;b=b0;din=('stale_din',);mem=[('stale',k) for k in range(N)]
            for edge in range(1,2*D+1):
                old=mem[b] if b<N else ('invalid',)
                if a<N:mem[a]=din
                din=('input',edge)
                nxt=0 if a>=N-1 else a+1
                a=b=nxt # every replica D is the SAME function of canonical Q
                if edge>=D:
                    assert old==('input',edge-D+1),(N,a0,b0,edge,old)
                    checks+=1
    if bad_mutant is None and N>1:
        a=0;b=1;din=('stale_din',);mem=[('stale',k) for k in range(N)]
        for edge in range(1,2*D+1):
            old=mem[b]
            mem[a]=din;din=('input',edge)
            a=0 if a>=N-1 else a+1;b=0 if b>=N-1 else b+1
            if edge>=D and old!=('input',edge-D+1):
                bad_mutant=dict(rows=N,write_initial=0,read_initial=1,edge=edge,expected=['input',edge-D+1],actual=old,reason='Independently advancing unreset replicas retain distinct offsets; write/read ownership split corrupts first qualified data.');break
assert bad_mutant
out=dict(rows_tested=list(range(1,27)),all_initial_write_read_pointer_code_pairs=cases,qualified_OLD_checks=checks,shared_canonical_next_state='PASS',independent_feedback_mutant=bad_mutant,mechanism='All copies receive identical combinational next-state function of one canonical counter vector. Arbitrary power-up copies converge at edge1. Writes of first required din begin edge2, hence output valid at edgeD=N+2 without a reset or extra edge.',limitations='Ring mechanism only. No production source edit or first-use/valid/occupied-reset comparator; mapping must preserve common D and coherent write/read address ownership. No simulation initialization relied upon.')
(P/'cold_copy.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
