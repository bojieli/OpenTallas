import json,sys
s=json.load(open(sys.argv[1]))['blocks']
V=[];S=[];G=[];Cr=[]
for ln in open(sys.argv[2]):
  p=ln.split()
  if len(p)==3 and p[0]=='V': V.append(int(p[1]))
  if len(p)==3 and p[0]=='S': S.append(int(p[1]))
  if len(p)==4 and p[0]=='G': G.append((int(p[1]),int(p[3])))
  if ln.startswith('CACHE_RETIRE'): Cr.append(ln)
print("n kind land nl  go_rc  G_rc | V  rs_m+rc0 | S  open_m | S->go  go-model_open")
for i,b in enumerate(s):
  rc0=b['rc0']; rm=b['rm'] or {}
  v=V[i] if i<len(V) else None; st=S[i] if i<len(S) else None; g=G[i] if i<len(G) else None
  print(i,b['kind'],b['landing'],b['nl'],b['go'],g[1] if g else None,'|',v, rm.get('reserve',0)+rc0,'|',st, rm.get('open',0)+rc0, '|', (b['go_abs']-st) if st else None, b['go']-rm.get('open',0))
