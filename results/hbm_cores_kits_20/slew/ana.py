import sys
def rd(f):
  d={}
  for l in open(f):
    x=l.rstrip("\n").split("\t"); d[x[0]]=x[1:]
  return d
D=sys.argv[1]
g=rd(D+"/q_grtfinal.tsv"); s=rd(D+"/q_spef.tsv"); w=rd(D+"/wl_6_final.tsv")
f=lambda v: float(v.split("-")[-1])
rows=[(f(g[n][0]),f(s[n][0]),float(w[n][1]),int(w[n][2])) for n in s if n in g and n in w]
def q(v): v=sorted(v); return "%.3f/%.3f/%.3f"%(v[len(v)//10],v[len(v)//2],v[9*len(v)//10])
print(D,"n",len(rows),"wireC spef/grt p10/50/90",q([r[1]/r[0] for r in rows if r[0]>0]),"spef fF/um",q([r[1]/r[2] for r in rows if r[2]>0]),"grt fF/um",q([r[0]/r[2] for r in rows if r[2]>0]), "vias/um", q([r[3]/r[2] for r in rows if r[2]>0]))
