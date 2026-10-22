import json,re,sys,collections
net_file,census,out=sys.argv[1:4]
cells={}  # name->(type,{pin:net})
drv={}; loads=collections.defaultdict(list); alias=collections.defaultdict(set)
cur=None
pinre=re.compile(r'\.(\w+)\((.*?)\)\s*,?\s*$')
with open(net_file) as f:
  for line in f:
    s=line.strip()
    if s.startswith('assign '):
      m=re.match(r'assign (.+?) = (.+?);',s)
      if m:
        a,b=m.group(1).strip(),m.group(2).strip()
        alias[b].add(a); alias[a].add(b)
      continue
    m=re.match(r'^(\S+_ASAP7\S*|ot_\S+|\S+_bounded)\s+(\S+)\s*\($',s)
    if m: cur=[m.group(1),m.group(2),{}]; continue
    if cur is not None:
      m=pinre.match(s)
      if m: cur[2][m.group(1)]=m.group(2).strip()
      if s.startswith(');'):
        t,n,p=cur; cells[n]=(t,p)
        for pin,net in p.items():
          if pin in ('Y','QN','Q','CON','SN','rd_out') or pin.startswith('rd'): drv[net]=(n,pin)
          else: loads[net].append((n,pin))
        cur=None
def public(n): return n.startswith('\\') or not re.match(r'^_\d+_(\[\d+\])?$',n)
def name_of(net,depth=3):
  # aliases
  for a in alias.get(net,()):
    if public(a): return a
  if depth==0: return None
  for (c,pin) in loads.get(net,[]):
    t,p=cells[c]
    if t.startswith('INV') or t.startswith('BUF'):
      o=p.get('Y')
      if o:
        if public(o): return ('~' if t.startswith('INV') else '')+o
        r=name_of(o,depth-1)
        if r: return r
  return None
d=json.load(open(census))
res=[]
for v in d['violations']:
  net=v['net']; nm=name_of(net) if not public(net) else net
  dcell=drv.get(net,(None,None))[0]
  dn=None
  if dcell and cells[dcell][0].startswith('DFF'):
    D=cells[dcell][1].get('D'); dn=D if D and public(D) else (name_of(D,1) if D else None)
  res.append(dict(net=net,loads=v['loads'],role=v['driver_role'],name=nm,dnet=dn,cell=dcell,ctype=cells[dcell][0] if dcell else None))
json.dump(res,open(out,'w'))
def norm(k):
  k=re.sub(r'\[\d+\]','[*]',k or 'None');k=re.sub(r'_\d+_','_N_',k);k=re.sub(r'\$\d+','$N',k);k=re.sub(r'\d+','#',k);return k
c=collections.Counter();m=collections.defaultdict(int)
for r in res:
  k=norm(r['name'] or ('D:'+str(r['dnet'])))
  c[k]+=1;m[k]=max(m[k],r['loads'])
for k,n in c.most_common(70): print(n,m[k],k[:220])
