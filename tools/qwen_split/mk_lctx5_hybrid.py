"""SQC-SYSFACE 10-22: derive qfd_sys_face_lctx5_hybrid from Codex qfd_sys_face_lctx4_bounded (c22e52bbf).
Same netlist graph, same 93 ports, same FFs/edges/ROMs.  Only the hierarchy attribute changes:
 * a generic cell is KEPT (keep_hierarchy helper, unchanged) iff another cell of the same type has identical inputs
   (deliberate same-D/C/R FF copies and Boolean publication copies of the load-bounding construction) -> they
   cannot be merged back by opt_merge/ABC;
 * every other cell is emitted flat (assign / always) so ABC optimises the comb logic for delay (lctx4 kept every
   2-input gate as its own module: generic depth 85, a 60-gate serial OR prefix chain -> cannot meet 833 ps).
"""
import re,sys,collections
src,out=sys.argv[1],sys.argv[2]
t=open(src).read()
CELL=re.compile(r'^\(\* keep_hierarchy="yes" \*\) qfd_lctx_full32_(\w+) #\(\.ID\((\d+)\)\) (\w+)\((.*?)\);\n',re.M)
cells=[(m.group(1),m.group(2),m.group(3),dict(re.findall(r"\.(\w+)\(([^)]+)\)",m.group(4))),m.group(0)) for m in CELL.finditer(t)]
COMM={'and','or','xor'}
def key(ty,c):
    if ty in COMM: return (ty,tuple(sorted((c['A'],c['B']))))
    if ty=='not': return (ty,c['A'])
    if ty=='mux': return (ty,c['A'],c['B'],c['S'])
    return (ty,c['C'],c['D'],c.get('R'))
grp=collections.Counter(key(ty,c) for ty,_,_,c,_ in cells)
import os
KEEPFF=os.environ.get('LCTX5_KEEP_FF','0')=='1'
FO=collections.Counter(v for _,_,_,c,_ in cells for k,v in c.items() if k not in('Y','Q'))
FOMAX=int(os.environ.get('LCTX5_KEEP_FO','0') or 0)
def keep(ty,c):
    if grp[key(ty,c)]>1: return True
    if KEEPFF and ty.startswith(('dff','sdff')): return True
    o=c.get('Y',c.get('Q'))
    return FOMAX>0 and FO[o]>=FOMAX
kept=flat=0; ffregs=[]; body=[]
EXPR={'and':'{A} & {B}','or':'{A} | {B}','xor':'{A} ^ {B}','not':'~{A}','mux':'{S} ? {B} : {A}'}
for ty,i,name,c,line in cells:
    if keep(ty,c): body.append(line); kept+=1; continue
    flat+=1
    if ty in EXPR: body.append(f"assign {c['Y']} = {EXPR[ty].format(**c)};\n"); continue
    q=c['Q']; ffregs.append(q)
    if ty=='dff_p': body.append(f"always @(posedge {c['C']}) r_{q} <= {c['D']};\n")
    elif ty=='dff_pn0': body.append(f"always @(posedge {c['C']} or negedge {c['R']}) if(!{c['R']}) r_{q} <= 1'b0; else r_{q} <= {c['D']};\n")
    elif ty=='dff_pn1': body.append(f"always @(posedge {c['C']} or negedge {c['R']}) if(!{c['R']}) r_{q} <= 1'b1; else r_{q} <= {c['D']};\n")
    elif ty=='sdff_pp0': body.append(f"always @(posedge {c['C']}) if({c['R']}) r_{q} <= 1'b0; else r_{q} <= {c['D']};\n")
    else: raise SystemExit('unknown '+ty)
    body.append(f"assign {q} = r_{q};\n")
first=CELL.search(t).start(); last=list(CELL.finditer(t))[-1].end()
assert t[first:last].count('keep_hierarchy')==len(cells)
regdecl=''.join('reg '+', '.join('r_'+q for q in ffregs[k:k+64])+';\n' for k in range(0,len(ffregs),64))
new=t[:first]+regdecl+''.join(body)+t[last:]
new=new.replace('module qfd_sys_face_lctx4_bounded','module qfd_sys_face_lctx5_hybrid',1).replace('LCTX4 is fixed','LCTX5 is fixed')
hdr='// SQC-SYSFACE 10-22 qfd_sys_face_lctx5_hybrid: derived from qfd_sys_face_lctx4_bounded (c22e52bbf) by tools/qwen_split/mk_lctx5_hybrid.py;\n// identical graph; keep_hierarchy only on duplicate-input cells (copies), all other cells flat for ABC.\n'
open(out,'w').write(hdr+new)
print(f'cells {len(cells)} kept {kept} flat {flat} ff_flat {len(ffregs)} dup_groups {sum(1 for v in grp.values() if v>1)}')
print('kept by type',collections.Counter(ty for ty,_,_,c,_ in cells if keep(ty,c)))
