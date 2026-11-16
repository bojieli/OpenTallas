import glob,collections,sys
S=sys.argv[1]
rows={}
allr=[]
for f in glob.glob(S+"/scan_*.tsv"):
    for l in open(f):
        p=l.rstrip("\n").split("\t")
        if len(p)<15 or p[0].startswith("ERR"): continue
        age=float(p[5]); k=(p[1],p[3])
        allr.append(p)
        if k not in rows or age<float(rows[k][5]): rows[k]=p
print("types",len(rows), collections.Counter(k[0] for k in rows))
def f(x):
    try: return float(x)
    except: return None
# kits with repair flag
print("== kits with OT_TT_SETUP_REPAIR and a TT gate (all attempts)")
for p in sorted(allr,key=lambda p:(p[1],p[3])):
    if p[10]!="-" and f(p[6]) is not None:
        print("  ",p[1],p[3][:44],p[4],"age",p[5],"setup",p[6],"ttH",p[7],"ffH",p[8],p[9],p[11],p[12],p[13])
print("== repair flag kits without gate yet:",sum(1 for p in allr if p[10]!="-" and f(p[6]) is None), collections.Counter((p[1],p[11]) for p in allr if p[10]!="-" and f(p[6]) is None).most_common(25))
print("== latest kit per type, age<=6h, with route log or gate")
x=collections.Counter()
for k,p in sorted(rows.items()):
    su=f(p[6]); r=p[12]
    rc="noroute" if not r.strip() else ("0255" if "DRT-0255" in r else ("drc0" if "drv=0 " in r and "TMP" not in r else ("running" if "TMP" in r else "other")))
    sb="nogate" if su is None else ("ok" if su>=-42 else ("near" if su>=-80 else ("mid" if su>=-150 else "far")))
    x[(k[0],rc,sb)]+=1
    if float(p[5])<=3.0 and (su is not None or r.strip()):
        print("  ",p[0],k[0],k[1][:46],p[2][:14],p[4],"age",p[5],"setup",p[6],"ffH",p[8],p[10],p[11],r,p[13],p[14][:150])
print("== cross (die,route,setup)")
for k,v in sorted(x.items()): print("  ",k,v)
print("== all 0255 latest")
for k,p in sorted(rows.items()):
    if "DRT-0255" in p[12]: print("  ",k[0],k[1][:46],p[2][:14],p[4],"age",p[5],"setup",p[6],p[10],p[12],p[13])
print("== routed other (drv>0 finished)")
for k,p in sorted(rows.items()):
    r=p[12]
    if r.strip() and "TMP" not in r and "DRT-0255" not in r and "drv=0 " not in r: print("  ",k[0],k[1][:46],p[4],"age",p[5],"setup",p[6],r,p[14][:200])
