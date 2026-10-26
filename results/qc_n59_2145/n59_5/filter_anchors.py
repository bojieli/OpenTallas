"""PATH-QC-N59-5: keep the anchors whose register exists (by normalised name) in the kit's own Yosys netlist; report the
rest by family.  Usage: filter_anchors.py anchors.tcl 1_2_yosys.v out.tcl out.json"""
import json,re,sys
from collections import Counter
a,v,o,j=sys.argv[1:5]
norm=lambda n:n.replace('\\','')
fam=lambda n:re.sub(r'\$_.*','',re.sub(r'\[\d+\]','[]',norm(n)))
regs=set()
rx=re.compile(r'^\s*((?:DFF|SDF|ASYNC_DFF)\w*)\s+(\S+)\s*\(')
for l in open(v):
    m=rx.match(l)
    if m:regs.add(norm(m[2].lstrip('\\')))
keep=[];miss=Counter();remapped=0
for l in open(a):
    m=re.match(r'\s*\{\{(.*)\} ([\d.]+) ([\d.]+)\}',l)
    if not m:continue
    # a name with '/' is a register inside a keep_hierarchy cell (not in the flat module body of 1_2_yosys.v):
    # kept here, resolved by findInst on the ODB (n59_reach405.tcl errors on a miss, never skips)
    collapsed=m[1].replace('/', '.')
    if norm(m[1]) not in regs and '/' in m[1] and norm(collapsed) in regs:
        # Exact instance match after the opt-in register-wrapper flatten; no alias inference.
        keep.append(l.replace(m[1],collapsed,1).rstrip('\n'));remapped+=1
    elif norm(m[1]) in regs or '/' in m[1]:keep.append(l.rstrip('\n'))
    else:miss[fam(m[1])]+=1
open(o,'w').write('\n'.join(keep)+'\n')
r=dict(netlist_regs=len(regs),exact_flatten_remaps=remapped,kept=len(keep),missing=sum(miss.values()),missing_families=miss.most_common(40))
json.dump(r,open(j,'w'),indent=1);print(json.dumps(r)[:1500])
