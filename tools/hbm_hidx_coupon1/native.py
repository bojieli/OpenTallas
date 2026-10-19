import json,re,sys,collections,hashlib
from pathlib import Path
j=json.loads(Path('out/netlist.json').read_text());m=j['modules']['hidx_coupon1'];lib=Path('out/all.lib').read_text()
def blocks(s,pat):
 for z in re.finditer(pat,s):
  a=s.index('{',z.start());d=1;b=a+1
  while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
  yield z.group(1).strip('" '),s[a+1:b-1]
scopes={n:c for n,c in m['cells'].items() if c['type']=='$scopeinfo'}
assert all(not c['connections'] for c in scopes.values())
m['cells']={n:c for n,c in m['cells'].items() if n not in scopes}
L={}
for name,body in blocks(lib,r'\bcell\s*\(\s*([^)]*)\)\s*\{'):
 pins={p:b for p,b in blocks(body,r'\bpin\s*\(\s*([^)]*)\)\s*\{')}
 ff=re.search(r'\bff\s*\(',body) is not None
 clocked=re.search(r'clocked_on\s*:\s*"([^"]+)"',body)
 clocks=set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*',clocked.group(1))) if clocked else set()
 dirs={p:re.search(r'direction\s*:\s*(\w+)',b).group(1) for p,b in pins.items()}
 ins=[p for p,d in dirs.items() if d=='input'];outs=[p for p,d in dirs.items() if d=='output']
 trans=False
 if len(ins)==1 and len(outs)==1 and not ff:
  f=re.search(r'function\s*:\s*"([^"]+)"',pins[outs[0]])
  if f:trans=re.sub(r'[\s()]','',f.group(1)) in (ins[0],'!'+ins[0],ins[0]+"'")
 caps={p:float(z.group(1)) if (z:=re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)',b)) else 0 for p,b in pins.items()}
 area=float(re.search(r'\barea\s*:\s*([0-9.eE+-]+)',body).group(1))
 L[name]=dict(pins=dirs,ff=ff,clocks=clocks,trans=trans,caps=caps,area=area)
roots={};sinks=collections.defaultdict(list);fwd={};combins={};aliases=collections.defaultdict(list)
for n,x in m['netnames'].items():
 for i,b in enumerate(x['bits']):aliases[b].append(n+'['+str(i)+']')
for n,c in m['cells'].items():
 t=c['type'];assert t in L,('non-native',n,t);mstr=L[t];ins=[];outs=[]
 for p,bits in c['connections'].items():
  assert len(bits)==1,(n,p,bits)
  b=bits[0];e=dict(name=n+'/'+p,cell=n,pin=p,master=t,kind='ff' if mstr['ff'] else 'comb',role='clock' if p in mstr['clocks'] else ('data' if mstr['ff'] else 'operand'),cap=mstr['caps'][p])
  if mstr['pins'][p]=='input':sinks[b].append(e);ins.append(b)
  elif mstr['pins'][p]=='output':
   assert b not in roots,('multiple-driver',b);roots[b]=e;outs.append(b)
 if mstr['trans']:assert len(ins)==len(outs)==1;fwd[n]=outs[0]
 if not mstr['ff']:
  for b in outs:combins[b]=ins
for n,p in m['ports'].items():
 for i,b in enumerate(p['bits']):
  e=dict(name=n+'['+str(i)+']',cell=None,pin=n,master=None,kind='input' if p['direction']=='input' else 'output',role='port',cap=0)
  if p['direction']=='input':assert b not in roots;roots[b]=e
  else:sinks[b].append(e)
def ends(b,seen=frozenset()):
 assert b not in seen,('transparent-cycle',b)
 out=[]
 for e in sinks[b]:
  if e['cell'] in fwd:out+=ends(fwd[e['cell']],seen|{b})
  else:out.append(e)
 return out
rows=[]
for b,e in roots.items():
 if e['cell'] in fwd:continue
 es=ends(b);nonclk=[x for x in es if x['role']!='clock'];clk=[x for x in es if x['role']=='clock']
 rows.append(dict(e,bit=b,aliases=aliases[b],loads=len(nonclk),clock_loads=len(clk),cap=sum(x['cap'] for x in nonclk),endpoints=es))
constants={b:ends(b) for b in ('0','1','x','z') if b in sinks}
unknown=[b for b in sinks if b not in roots and b not in constants]
assert not unknown,unknown
cache={};active=set()
def depth(b):
 if b in cache:return cache[b]
 assert b not in active,('comb-cycle',b)
 if b not in combins:return (0,[])
 active.add(b);v=max((depth(x) for x in combins[b]),key=lambda x:x[0],default=(0,[]));active.remove(b)
 cache[b]=(v[0]+1,v[1]+[roots[b]['name']]);return cache[b]
paths=[]
for b,es in sinks.items():
 if any(e['kind']=='ff' and e['role']!='clock' or e['kind']=='output' for e in es):
  d,path=depth(b);paths.append(dict(depth=d,driver=roots.get(b),endpoints=[e for e in es if e['kind'] in ('ff','output')],path=path))
ff=[(n,c,L[c['type']]) for n,c in m['cells'].items() if L[c['type']]['ff']]
summary=dict(metadata_scope_records=len(scopes),native_cells=len(m['cells']),masters=len(set(c['type'] for c in m['cells'].values())),ff=len(ff),area=sum(L[c['type']]['area'] for c in m['cells'].values()),ff_area=sum(t['area'] for _,_,t in ff),ff_clock_cap=sum(sum(t['caps'][p] for p in t['clocks']) for _,_,t in ff),roots=len(rows),max_nonclock=max(x['loads'] for x in rows),unsafe_roots=sum(x['loads']>32 for x in rows),constant_endpoints={b:len(es) for b,es in constants.items()},unknown=unknown,max_comb_levels=max(x['depth'] for x in paths),ff_counts=dict(collections.Counter(c['type'] for _,c,_ in ff)),input_loads={x['name']:x['loads'] for x in rows if x['kind']=='input'},clock_contacts=sum(x['clock_loads'] for x in rows))
packet=dict(summary=summary,all_roots=rows,constants=constants,unsafe=[x for x in rows if x['loads']>32],paths=sorted(paths,key=lambda x:-x['depth']))
Path('out/native.json').write_text(json.dumps(packet,indent=2)+'\n');Path('out/native_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
