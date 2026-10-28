import json,sys
D=sys.argv[1]
for g in sys.argv[2:]:
  o=json.load(open("%s/ocv_%s.json"%(D,g))); print(D,g, {C:(o[C]["nominal_spread"],o[C]["ocv_inclusive_spread"],o[C]["worst_pair"]) for C in o})
  d=json.load(open("%s/trunk_%s.json"%(D,g))); CI={k:v for k,v in d["summary"]["child_ins"].items()}
  G=json.load(open(D+"/"+d["cl"])); r2c={r.replace("\\",""):c["name"] for c in G["clusters"] for r in c["regs"]}
  for C,ci in (("TT",0),("FF",1)):
    R={}
    for l in open("%s/arr_r%s_%s.txt"%(D,g,C)):
      p=l.split()
      if not p or p[0]!="S" or p[2].startswith("ICG"): continue
      i=p[1].rsplit("/",1)[0].replace("\\","")
      if p[2] in CI: nm=i; v=float(p[4])+CI[p[2]][ci]
      else:
        nm=r2c.get(i); v=float(p[4])
        if nm is None: continue
      R.setdefault(nm,[]).append(v)
    mids=sorted(((min(v)+max(v))/2,n) for n,v in R.items()); w=sorted((max(v)-min(v),n) for n,v in R.items())
    print("  %s mid spread %.1f (%s %.1f .. %s %.1f) cluster width max %.1f (%s) median %.1f insertion max %.1f"%(C,mids[-1][0]-mids[0][0],mids[0][1][-12:],mids[0][0],mids[-1][1][-12:],mids[-1][0],w[-1][0],w[-1][1][-12:],w[len(w)//2][0],max(max(v) for v in R.values())))
