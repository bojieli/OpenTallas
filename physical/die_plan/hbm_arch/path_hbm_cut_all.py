"""Probe: every partition cut segment over the limit (G0 check_cuts reports only the worst per line).
Usage: cut_all.py <tools/die_plan dir> <out.json> <plan.json>..."""
import sys,json,inspect,hashlib,collections
sys.path.insert(0,sys.argv[1]);import schema as S,check as C
src=inspect.getsource(C.check_cuts)
src=src.replace("            if loc:\n","            ALL.extend((orient,c,x) for x in loc)\n            if loc:\n",1)
src=src.replace("            for p, q, w in segs:\n                a, b","            for p, q, w, *_ in segs:\n                a, b",1)
src=src.replace("segs.append((p, q, w))","segs.append((p, q, w, lid))")
assert "ALL.extend" in src
ns=C.__dict__;ns['ALL']=[];exec(src,ns)
res={}
for pp in sys.argv[3:]:
  ns['ALL'].clear();P=S.Plan(S.load(pp),pp);geo={lid:C.lane_geometry(P,lid) for lid in P.lanes};R=C.Report()
  out=ns['check_cuts'](P,R,geo);lim=P.budgets['cut_ratio_max']
  bad=sorted([dict(orient=o,at=c,part=x[1],ratio=round(x[0],4),bits=x[2],tracks=round(x[3])) for o,c,x in ns['ALL'] if x[0]>lim+1e-9],key=lambda d:-d['ratio'])
  # lanes crossing each bad segment
  for d in bad[:12]:
    r=P.rect(d['part']);lo,hi=((r[1],r[3]) if d['orient']=='vertical' else (r[0],r[2]));c=d['at'];lanes=collections.Counter()
    for lid,(pts,_,_) in geo.items():
      w=P.ports[P.lanes[lid]["ports"][0]]["width"]
      for p,q in zip(pts,pts[1:]):
        a,b=(p[0],q[0]) if d['orient']=='vertical' else (p[1],q[1]);y=p[1] if d['orient']=='vertical' else p[0]
        if min(a,b)<c-1e-6 and max(a,b)>c+1e-6 and lo-1e-6<=y<=hi+1e-6:lanes[lid]+=w
    d['lanes']=lanes.most_common(12)
  res[pp]=dict(sha256=hashlib.sha256(open(pp,'rb').read()).hexdigest(),n_over=len(bad),over=bad,worst_full=out['worst_full'],errors=[i['msg'] for i in R.items if i['level']=='ERROR'])
  print(pp,len(bad),[(d['part'],d['at'],d['ratio']) for d in bad[:10]],flush=True)
json.dump(res,open(sys.argv[2],'w'),indent=1)
