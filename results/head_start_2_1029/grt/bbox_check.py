#!/usr/bin/env python3
"""HEAD-START-2: LL-vs-centre assertion on the imported ODB (GEOM-55 cond.) + overlap census on ACTUAL bboxes.
usage: bbox_check.py bbox_TT.txt ctree.tcl physical_lc.json start_overlay.json out.json"""
import json,re,sys,math,collections
bbf,ctcl,phf,ovf,out=sys.argv[1:6]
act={}
for l in open(bbf):
    n,o,*v=l.split();act[n]=(o,tuple(map(float,v)))
exp={}
for m in re.finditer(r"place_inst -name (\S+) -location \{([-\d.]+) ([-\d.]+)\}(?: -orientation (\S+))?",open(ctcl).read()):
    exp['ck_'+m[1]]=(m[4] or 'R0',float(m[2]),float(m[3]))
ph=json.load(open(phf));names=json.load(open(ovf))['cell_names']
for k,c in ph['cells'].items():exp[names[k]]=(c.get('orient','R0'),*c['xy_um'])
for d in ph['stage_clock_drivers'].values():exp[d['inst']]=(d.get('orient','R0'),*d['xy_um'])
miss=[n for n in exp if n not in act];bad=[];orient=[]
for n,(o,x,y) in exp.items():
    if n not in act:continue
    ao,b=act[n]
    if abs(b[0]-x)>1e-3 or abs(b[1]-y)>1e-3:bad.append((n,o,x,y,b[:2]))
    if ao!=o:orient.append((n,o,ao))
bins=collections.defaultdict(list);B=4.0;R=list(act.items())
for i,(n,(o,b)) in enumerate(R):
    for gx in range(math.floor(b[0]/B),math.floor(b[2]/B)+1):
        for gy in range(math.floor(b[1]/B),math.floor(b[3]/B)+1):bins[gx,gy].append(i)
ov=set()
for ids in bins.values():
    for k,i in enumerate(ids):
        a=R[i][1][1]
        for j in ids[k+1:]:
            c=R[j][1][1]
            if min(a[2],c[2])-max(a[0],c[0])>1e-6 and min(a[3],c[3])-max(a[1],c[1])>1e-6:ov.add((min(i,j),max(i,j)))
rowbad=sum(1 for n,(o,b) in R if abs(b[1]/.27-round(b[1]/.27))>1e-4)
r=dict(insts=len(act),expected=len(exp),missing=len(miss),ll_mismatch=len(bad),orient_mismatch=len(orient),actual_overlaps=len(ov),off_row=rowbad,
       examples=dict(ll=bad[:10],orient=orient[:10],overlap=[(R[i][0],R[j][0]) for i,j in sorted(ov)[:10]],missing=miss[:10]))
r['verdict']='PASS' if not (miss or bad or orient or ov or rowbad) else 'FAIL'
json.dump(r,open(out,'w'),indent=1);print(json.dumps({k:v for k,v in r.items() if k!='examples'}))
