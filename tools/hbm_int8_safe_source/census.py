import json,re,sys,collections,hashlib
from pathlib import Path
p=Path(sys.argv[1]); j=json.loads(p.read_text()); m=j['modules']['ot_smh_int8_tile_safe']; cells=m['cells']; roots={}; sinks=collections.defaultdict(list); forward={}
def kind(t):return 'ff' if re.search('DFF|SDFF',t) else 'comb'
for n,c in cells.items():
 t=c['type']; pd=c.get('port_directions',j['modules'].get(t,{}).get('ports',{})); trans=bool(re.match('BUF|INV',t)); ins=[]; outs=[]
 for pin,bits in c['connections'].items():
  d=pd[pin]; d=d['direction'] if isinstance(d,dict) else d
  for i,b in enumerate(bits):
   x={'name':n+'/'+pin,'pin':pin,'master':t,'kind':kind(t)}
   if d=='input':sinks[b].append(x); ins.append(b)
   elif d=='output':outs.append(b); roots[b]=x
 if trans:
  assert len(ins)==1 and len(outs)==1,(n,ins,outs)
  forward[n]=outs[0]
for n,pd in m['ports'].items():
 for i,b in enumerate(pd['bits']):
  x={'name':n+'['+str(i)+']','kind':'input' if pd['direction']=='input' else 'output','pin':n,'master':None}
  if pd['direction']=='input':roots[b]=x
  else:sinks[b].append(x)
def ends(b,seen):
 assert b not in seen,('cycle',b)
 r=[]
 for x in sinks[b]:
  n=x['name'].rsplit('/',1)[0]
  if n in forward:r.extend(ends(forward[n],seen|{b}))
  else:r.append(x)
 return r
allroots=[]
for b,x in roots.items():
 n=x['name'].rsplit('/',1)[0]
 if n in forward or x['kind']=='input' and x['pin']=='clk':continue
 e=ends(b,set());allroots.append(dict(x,bit=b,loads=len(e),endpoints=e))
unknown=[b for b in sinks if b not in roots and b not in ('0','1','x','z')]
constants={str(b):ends(b,set()) for b in ('0','1') if b in sinks}
inputs=[x for x in allroots if x['kind']=='input']
outputs={e['name']:x for x in allroots for e in x['endpoints'] if e['kind']=='output'}
summary={'mapped_json_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'roots':len(allroots),'counts':dict(collections.Counter(x['kind'] for x in allroots)),'max_loads':max(x['loads'] for x in allroots),'unsafe_roots':len([x for x in allroots if x['loads']>32]),'unknown_bits':unknown,'input_non_ff':[x for x in inputs if any(e['kind']!='ff' for e in x['endpoints'])],'output_non_ff':{n:x for n,x in outputs.items() if x['kind']!='ff'},'constant_endpoints':{b:len(e) for b,e in constants.items()},'constant_note':'Literal constants require real per-sink tie repair in physical netlist; no physical tie or placement claim','clock_FF_contacts':sum(1 for c in cells.values() if kind(c['type'])=='ff')}
Path(sys.argv[2]).write_text(json.dumps(dict(summary=summary,unsafe=[x for x in allroots if x['loads']>32],all_roots=allroots,constant_endpoints=constants),indent=2)+'\n');print(json.dumps(summary,indent=2))
