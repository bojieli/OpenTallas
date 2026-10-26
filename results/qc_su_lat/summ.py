import sys,collections,statistics,glob,os,json
d=sys.argv[1]
out={}
for c in ("TT","FF"):
  f=os.path.join(d,"lat_%s.tsv"%c)
  if not os.path.exists(f): print(c,"missing"); continue
  rows=[l.rstrip("\n").split("\t") for l in open(f) if l.strip()]
  a=sorted(float(r[1]) for r in rows); dd=collections.Counter(int(r[2]) for r in rows)
  pin=[float(r[1]) for r in rows if r[0].startswith(("ot_fcap","ot_pin","u_pin","pi_","po_")) ]
  q=lambda p:a[int(p*(len(a)-1))]
  print(c,"n",len(a),"min %.1f p10 %.1f mean %.1f p90 %.1f max %.1f"%(a[0],q(.1),statistics.mean(a),q(.9),a[-1]),"depth",sorted(dd.items()))
  out[c]=dict(n=len(a),min=a[0],mean=statistics.mean(a),max=a[-1])
json.dump(out,open(os.path.join(d,"summary.json"),"w"))
