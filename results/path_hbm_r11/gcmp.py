import json,sys
A=json.load(open(sys.argv[1])); B=json.load(open(sys.argv[2]))
ga=A.get("gates",A); gb=B.get("gates",B)
for k in ga:
  sa=json.dumps({kk:vv for kk,vv in ga[k].items() if not isinstance(vv,(list,dict))} if isinstance(ga[k],dict) else ga[k])[:230]
  sb=json.dumps({kk:vv for kk,vv in gb.get(k,{}).items() if not isinstance(vv,(list,dict))} if isinstance(gb.get(k),dict) else gb.get(k))[:230]
  print(k,"\n  R10s1",sa,"\n  R11A ",sb)
