import json,re,hashlib,sys,collections,gzip
from pathlib import Path
from functools import lru_cache
root=Path.cwd();stage=(sys.argv[1] if len(sys.argv)>1 else 'synth_kept_742');src=root/stage/'mapped.json';d=json.loads(src.read_text());m=d['modules']['ot_s81ph_native_guarded_mux'];roles={};libs=[]
def blocks(s,k):
 for q in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',s):
  a=i=q.end();depth=1
  while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
  yield q[1].strip('" '),s[a:i-1]
for lp in sorted((Path.home()/'.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT*.lib*')):
 libs.append({'path':str(lp),'sha256':hashlib.sha256(lp.read_bytes()).hexdigest()});s=gzip.open(lp,'rt').read()if lp.suffix=='.gz'else lp.read_text()
 for name,body in blocks(s,'cell'):
  pins={}
  for pn,pb in blocks(body,'pin'):
   dr=re.search(r'\bdirection\s*:\s*(\w+)',pb);fn=re.search(r'\bfunction\s*:\s*"([^"]+)"',pb)
   pins[pn]={'direction':dr[1]if dr else None,'function':fn[1]if fn else None,'clock':bool(re.search(r'\bclock\s*:\s*true',pb))}
  ins=[n for n,z in pins.items()if z['direction']=='input'];outs=[z for z in pins.values()if z['direction']=='output'];fn=outs[0]['function']if len(outs)==1 else None
  roles[name]={'pins':pins,'unary':len(ins)==1 and len(outs)==1 and fn is not None and re.sub(r'[()\s]','',fn)in[ins[0],'!'+ins[0],ins[0]+"'"]}
loads=collections.defaultdict(list);drivers=[];trans={};unknown=[]
for cn,c in m['cells'].items():
 role=roles.get(c['type'])
 if role is None:unknown.append(c['type']);continue
 out=[];inp=[]
 for pn,bits in c['connections'].items():
  pr=role['pins'].get(pn)
  if pr is None:raise RuntimeError('unknown pin '+c['type']+'/'+pn)
  for bi,net in enumerate(bits):
   if not isinstance(net,int):continue
   key=cn+'/'+pn+('['+str(bi)+']'if len(bits)>1 else '')
   if pr['direction']=='output':drivers.append((key,net,c['type']));out.append(net)
   elif pr['direction']=='input':loads[net].append((key,pr['clock']));inp.append(key)
 if role['unary']:
  if len(out)!=1:raise RuntimeError('unaryoutputs '+cn)
  for key in inp:trans[key]=out[0]
for pn,p in m['ports'].items():
 for i,net in enumerate(p['bits']):
  if not isinstance(net,int):continue
  key='PORT/'+pn+('['+str(i)+']'if len(p['bits'])>1 else '')
  if p['direction']=='input':drivers.append((key,net,'PORT'))
  else:loads[net].append((key,False))
@lru_cache(None)
def ends(net):
 out=set()
 for key,clock in loads[net]:
  if key in trans:out.update(ends(trans[key]))
  elif not clock:out.add(key)
 return frozenset(out)
rows=[{'driver':key,'master':typ,'data_loads':len(ends(net)),'endpoints':sorted(ends(net))}for key,net,typ in drivers]
res={'schema':'opentallas.native_mapped_all_driver_census.v1','mapped_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'lib_sources':libs,'unknown_masters':sorted(set(unknown)),'cell_count':len(m['cells']),'max_data_loads':max(z['data_loads']for z in rows),'over32':[z for z in rows if z['data_loads']>32],'sequential_cells':sum('DFF'in c['type']for c in m['cells'].values()),'reset_leaf_drivers':[z for z in rows if 'relay_q'in z['driver']],'raw_reset_drivers':[z for z in rows if z['driver']=='PORT/rst_n'],'scope':'Mapped all-driver data/reset census, transparent unary buffers collapsed, clocks excluded only by pinned Liberty clock:true. No placement/reach/PG qualification.'}
(root/stage/'census.json').write_text(json.dumps(res,indent=2));print('MAPPED_CENSUS',res['cell_count'],'MAX',res['max_data_loads'],'OVER32',len(res['over32']),'UNKNOWN',res['unknown_masters']);
for z in sorted(res['over32'],key=lambda z:-z['data_loads'])[:12]:print(z['driver'],z['data_loads'])
