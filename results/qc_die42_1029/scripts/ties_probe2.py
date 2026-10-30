import json,sys,collections,bisect
sys.path.insert(0,"/srv/opentallas-scratch2/claude/die-qc41/src_pc/tools/die_plan")
import die_clock_128 as C128
d=sys.argv[1]; wires=json.load(open(d+"/fixed_wires.json")); pg=json.load(open(d+"/pg_rects.json"))
nd=dict(width=.08,space=.32,rf=.5,cf=1.15)
drawn=[];src=[]
for wi,w in enumerate(wires):
  for si,(seg,mode,ext) in enumerate(zip(w["segs"],w.get("shield_modes") or [C128.DRAWN]*len(w["segs"]),w.get("shield_ext") or [None]*len(w["segs"]))):
    if mode==C128.DRAWN: drawn.append(tuple(seg)+(ext,)); src.append((wi,si))
st=C128.shield_stripes(drawn,nd)
ties=C128.shield_ties(st,pg,nd["width"])
print({k:(len(v) if hasattr(v,"__len__") else v) for k,v in ties.items()})
# VSS perp lines
vss={L:sorted(((r[2]+r[4])/2 if L=="M9" else (r[3]+r[5])/2, r[3] if L=="M9" else r[2], r[5] if L=="M9" else r[4]) for r in pg if r[0]=="VSS" and r[1]==L) for L in ("M8","M9")}
cat=collections.Counter(); rows=[]
for k in ties["untied"]:
  L,x0,y0,x1,y1=st[k]; wi,si=src[k//2]; w=wires[wi]; seg=drawn[k//2]
  c,a,b=(y0,min(x0,x1),max(x0,x1)) if L=="M8" else (x0,min(y0,y1),max(y0,y1))
  P="M9" if L=="M8" else "M8"; cs=[q[0] for q in vss[P]]
  i=bisect.bisect_left(cs,(a+b)/2); near=[q for q in vss[P][max(0,i-2):i+2]]
  dn=min([abs(q[0]-a) if q[0]<a else (abs(q[0]-b) if q[0]>b else 0) for q in near] or [None])
  inside=[q for q in near if a<=q[0]<=b]
  why="no_perp_in_span" if not inside else ("perp_not_covering_c" if all(not(q[1]<=c<=q[2]) for q in inside) else "?")
  cat[(L,why,seg[5] is None)]+=1
  rows.append(dict(k=k,L=L,c=round(c,4),span=[round(a,4),round(b,4)],len=round(b-a,3),net=w["name"],seg=si,nseg=len(w["segs"]),ext=seg[5],why=why,dist_perp=dn,stacks=len(w.get("stacks",[]))))
print(cat)
json.dump(rows,open(sys.argv[2],"w"),indent=0)
for r in rows[:30]: print(r)
lc=collections.Counter(round(r["len"],1) for r in rows); print(lc.most_common(10))
print(collections.Counter(r["net"].rsplit("_",1)[0][:8] for r in rows).most_common(10))
