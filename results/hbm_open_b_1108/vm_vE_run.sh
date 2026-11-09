#!/bin/bash
cd /srv/opentallas-scratch2/claude/hbm-open-b/vm_proof
for v in old new mut; do ( cd $v && timeout 1500 iverilog -g2012 -DSYNTHESIS -DOUTF=\"../$v.out\" -o ../$v.vvp ../tb.v *.sv 2> ../$v.iv.log && timeout 1500 vvp -n ../$v.vvp > ../$v.vvp.log 2>&1; echo $v rc=$? >> ../status.txt ) & done
wait
python3 -I - <<'PY'
o=[l for l in open('old.out')]; n=[l for l in open('new.out')]; m=[l for l in open('mut.out')]
d=lambda a,b:sum(x!=y for x,y in zip(a,b))
xs=sum('x' in l or 'z' in l for l in o)
print('samples',len(o),len(n),len(m),'old-vs-new mismatches',d(o,n),'old-vs-mutant',d(o,m),'lines with X',xs, 'distinct',len(set(o)))
PY
