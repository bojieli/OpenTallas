import re,sys
D=sys.argv[1]; want_insts=set(sys.argv[2].split(',')); slew_pins=sys.argv[3].split(',')
pos={};typ={};nets={};sec=None;cur=None
rx=re.compile(r'^\s*- (\S+) (\S+) .*?(?:PLACED|FIXED) \( (-?\d+) (-?\d+) \)')
pr=re.compile(r'\( (\S+) (\S+) \)')
ppos={}
with open(D) as f:
  for line in f:
    if line.startswith('COMPONENTS'): sec='C';continue
    if line.startswith('PINS'): sec='P';pcur=None;continue
    if line.startswith('END '): sec=None;continue
    if line.startswith('NETS'): sec='N';continue
    if sec=='C':
      m=rx.match(line)
      if m: pos[m.group(1)]=(int(m.group(3))/1000,int(m.group(4))/1000);typ[m.group(1)]=m.group(2)
    elif sec=='P':
      s=line.strip()
      if s.startswith('- '): pcur=s.split()[1]
      m=re.search(r'(?:FIXED|PLACED) \( (-?\d+) (-?\d+) \)',s)
      if m and pcur: ppos[pcur]=(int(m.group(1))/1000,int(m.group(2))/1000)
    elif sec=='N':
      s=line.strip()
      if s.startswith('- '): cur=s.split()[1];nets[cur]=[]
      if cur is not None and not s.startswith('NEW') and not s.startswith('+ ROUTED'):
        for a,b in pr.findall(s.split('+ ROUTED')[0]):
          if a!='*' and not a.lstrip('-').isdigit(): nets[cur].append((a,b))
      if s.endswith(';'): cur=None
pin2net={}
for n,ps in nets.items():
  for a,b in ps: pin2net[(a,b)]=n
def loc(a,b): return ppos.get(b) if a=='PIN' else pos.get(a)
outs=('Y','QN','Q','CON','SN')
for inst in want_insts:
  print('INST',inst,typ.get(inst),pos.get(inst))
  for (a,b),n in pin2net.items():
    if a==inst:
      drv=[(x,y) for x,y in nets[n] if (x=='PIN' or y in outs) and x!=inst]
      print('  pin',b,'net',n,'drv',[(x,y,typ.get(x),loc(x,y)) for x,y in drv][:2])
for sp in slew_pins:
  inst,pin=sp.rsplit('/',1)
  n=pin2net.get((inst,pin))
  if not n: print('SLEW',sp,'nonet');continue
  ps=[loc(a,b) for a,b in nets[n] if loc(a,b)]
  xs=[p[0] for p in ps];ys=[p[1] for p in ps]
  drv=[(a,typ.get(a),loc(a,b)) for a,b in nets[n] if b in outs or a=='PIN']
  print('SLEW',sp,'fanout',len(nets[n])-1,'hpwl %.0f'%((max(xs)-min(xs))+(max(ys)-min(ys))),'drv',drv[:1],'sinkloc',pos.get(inst))
# backward trace through BUF/INV from given inst pins to the first non-buffer driver
def back(inst,pin):
  path=[]
  for _ in range(15):
    n=pin2net.get((inst,pin))
    if not n: return path+[('nonet',)]
    d=[(a,b) for a,b in nets[n] if (a=='PIN') or (b in outs and a!=inst)]
    if not d: return path+[('nodrv',n)]
    a,b=d[0]
    if a=='PIN': return path+[('PORT',b,ppos.get(b))]
    path.append((a,typ.get(a),pos.get(a)))
    if not re.match(r'(BUF|INV|HB)',typ.get(a,'')): return path
    inst,pin=a,'A'
  return path
for spec in sys.argv[4].split(',') if len(sys.argv)>4 else []:
  i,p=spec.rsplit('/',1)
  t=back(i,p); print('BACK',spec,'->',t[-1],'hops',len(t))
  # one more level: inputs of that gate
  last=t[-1]
  if len(last)==3 and last[0] in pos:
    for (a,b),n in pin2net.items():
      if a==last[0] and b not in outs:
        tt=back(a,b); print('   in',b,'->',tt[-1])
if len(sys.argv)>5:
  from collections import Counter
  start=sys.argv[5].split(',')
  todo=[tuple(s.rsplit('/',1)) for s in start]; seen=set(); leaves=Counter(); ex={}; ncomb=0
  while todo:
    i,p=todo.pop()
    n=pin2net.get((i,p))
    if not n or n in seen: continue
    seen.add(n)
    d=[(a,b) for a,b in nets[n] if a=='PIN' or (b in outs and a!=i)]
    if not d: continue
    a,b=d[0]
    if a=='PIN': k='PORT:'+re.sub(r'\[\d+\]','',b); leaves[k]+=1; ex.setdefault(k,ppos.get(b)); continue
    if 'DFF' in typ.get(a,''):
      k='FF:'+re.sub(r'\\\[\d+\\\]|\[\d+\]','[]',a.split('$')[0]); leaves[k]+=1; ex.setdefault(k,pos.get(a)); continue
    if typ.get(a,'').startswith('ot_sram'): leaves['SRAM:'+a]+=1; continue
    ncomb+=1
    for (x,y),nn in [((x,y),pin2net.get((x,y))) for x,y in [(a,q) for q in ('A','B','C','D','E','A1','A2','B1','B2','C1','C2')]]:
      if nn: todo.append((x,y))
  print('CONE comb',ncomb)
  for k,v in leaves.most_common(15): print('LEAF',v,k,ex.get(k))
