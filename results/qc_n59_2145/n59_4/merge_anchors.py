"""Merge the joint-model anchors into Codex's n59_reach405.tcl (same procs/packing); matched names take the model site,
unmatched Codex entries (alias-resolved names) are kept unchanged, new names are appended."""
import re,sys
src,new,out=sys.argv[1:4]
L=open(src).read().split('\n')
i0=next(i for i,l in enumerate(L) if l.startswith('set n59r_entries {'));i1=next(i for i in range(i0+1,len(L)) if L[i]=='}')
rx=re.compile(r'\s*\{\{(.*)\} ([\d.]+) ([\d.]+)\}')
old=[rx.match(l).groups() for l in L[i0+1:i1]]
A={}
for l in open(new):
    m=rx.match(l);A[m[1]]=(m[2],m[3])
seen=set();rows=[];ov=0
for n,x,y in old:
    if n in A:rows.append((n,)+A[n]);ov+=1
    else:rows.append((n,x,y))
    seen.add(n)
add=[(n,)+A[n] for n in sorted(A) if n not in seen]
rows+=add
body=[' {{%s} %s %s}'%r for r in rows]
L=L[:i0]+['# PATH-QC-N59-4 %d Codex entries (%d moved to the joint complete-cone model), +%d new joint-model anchors'%(len(old),ov,len(add)),L[i0]]+body+L[i1:]
open(out,'w').write('\n'.join(L))
print('codex',len(old),'overridden',ov,'added',len(add),'total',len(rows))
