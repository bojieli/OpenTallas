import re,sys
D,FF=sys.argv[1],sys.argv[2]
pos={};typ={}
sec=None
nets={}
cur=None;buf=[]
rx=re.compile(r'^\s*- (\S+) (\S+) .*?(?:PLACED|FIXED) \( (-?\d+) (-?\d+) \)')
pr=re.compile(r'\( (\S+) (\S+) \)')
with open(D) as f:
  for line in f:
    if line.startswith('COMPONENTS'): sec='C';continue
    if line.startswith('END COMPONENTS'): sec=None;continue
    if line.startswith('NETS') or line.startswith('SPECIALNETS'): sec='N' if line.startswith('NETS') else 'S';continue
    if line.startswith('END NETS'): sec=None;continue
    if sec=='C':
      m=rx.match(line)
      if m: pos[m.group(1)]=(int(m.group(3))/1000,int(m.group(4))/1000);typ[m.group(1)]=m.group(2)
    elif sec=='N':
      s=line.strip()
      if s.startswith('- '):
        cur=s.split()[1];nets[cur]=[]
      if cur is not None and ('+ ROUTED' in s or '+ USE' in s and not s.startswith('(')):
        pass
      if cur is not None and not s.startswith('NEW') and '+ ROUTED' not in s:
        for a,b in pr.findall(s.split('+ ROUTED')[0]):
          if not a.startswith('-') and not a[0].isdigit() and a!='*' : nets[cur].append((a,b))
      if s.endswith(';'): cur=None
# map driver pin -> net
drv={}
for n,pins in nets.items():
  for c,p in pins: drv[(c,p)]=n
out=[]
for l in open(FF):
  t=l.rstrip('\n').split('\t')
  if len(t)<5: continue
  ff=t[0].replace('\\','')
  key=None
  for k in (t[0],ff):
    if k in pos: key=k
  if key is None: continue
  n=drv.get((key,'QN'))
  if not n: continue
  fx,fy=pos[key]
  for c,p in nets[n]:
    if c==key or c=='PIN' or c not in pos: continue
    x,y=pos[c];d=abs(x-fx)+abs(y-fy)
    if d>40: out.append((d,key,c,typ[c],x,y,fx,fy,t[1]))
out.sort(reverse=True)
print('outliers >40um:',len(out))
for o in out[:25]: print('%.1f %s -> %s %s (%.1f,%.1f) ff(%.1f,%.1f) face %s'%o)
# trace bout flops: QN -> buf/inv chain -> PIN
outp={}
for p in ('Y',):
  pass
res=[]
for l in open(FF):
  t=l.rstrip('\n').split('\t')
  if len(t)<5 or '/q' not in t[0] or not t[0].startswith('u_bout'): continue
  key=t[0] if t[0] in pos else t[0].replace('\\','')
  if key not in pos: continue
  c,pin=key,'QN';L=0.0;chain=[];px,py=pos[key];ok=False
  for _ in range(12):
    n=drv.get((c,pin))
    if not n: break
    sinks=[(a,b) for a,b in nets[n] if a!=c]
    if any(a=='PIN' for a,b in sinks): ok=True;break
    if len(sinks)!=1: break
    a,b=sinks[0]
    if a not in pos or not re.match(r'(BUF|INV|HB)',typ[a]): break
    x,y=pos[a];L+=abs(x-px)+abs(y-py);px,py=x,y;chain.append(a);c,pin=a,'Y'
  if ok:
    res.append((L,key,len(chain),pos[key],t[4]))
res.sort(reverse=True)
print('bout chains traced',len(res),' >50um:',sum(1 for r in res if r[0]>50),' >200um:',sum(1 for r in res if r[0]>200))
for r in res[:15]: print('%.1f %s hops %d ff %s port %s'%r)
