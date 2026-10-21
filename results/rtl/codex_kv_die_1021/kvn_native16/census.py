import pathlib,hashlib,json,subprocess,collections
p=pathlib.Path.cwd(); s=p/'qkd_kvn_ctx_ovl_rope.sv'; y=pathlib.Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'
script=f'read_verilog -sv {s}; hierarchy -check -top qkd_kvn_ctx_ovl_rope; synth -top qkd_kvn_ctx_ovl_rope -noabc; write_json generic.json; stat'
r=subprocess.run([str(y),'-Q','-T','-p',script],capture_output=True,text=True);(p/'synthesis.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
mods=json.loads((p/'generic.json').read_text())['modules'];m=mods['qkd_kvn_ctx_ovl_rope']
loads=collections.defaultdict(list);drivers=collections.defaultdict(list);names=collections.defaultdict(list);flat=[]
def walk(module,prefix,bind):
 local=mods[module]
 def net(b):return b if isinstance(b,str) else bind.get(b,(prefix,b))
 for name,n in local['netnames'].items():
  for b in n['bits']:
   if isinstance(b,int):names[net(b)].append(prefix+name)
 for name,c in local['cells'].items():
  if c['type'] in mods:
   child=mods[c['type']];cb={}
   for pn,bs in c['connections'].items():
    for b,parent in zip(child['ports'][pn]['bits'],bs):cb[b]=net(parent)
   walk(c['type'],prefix+name+'/',cb)
  else:flat.append((prefix+name,c,{pn:[net(b) for b in bs]for pn,bs in c['connections'].items()}))
walk('qkd_kvn_ctx_ovl_rope','top/',{})
parent={}
def find(b):
 parent.setdefault(b,b)
 if parent[b]!=b:parent[b]=find(parent[b])
 return parent[b]
def union(a,b):parent[find(a)]=find(b)
for n,c,con in flat:
 if c['type']=='$_NOT_':union(con['A'][0],con['Y'][0])
for n,c,con in flat:
 if c['type']=='$_NOT_':continue
 for pn,bs in con.items():
  for b in bs:
   if isinstance(b,str):continue
   b=find(b)
   if c['port_directions'][pn]=='output':drivers[b].append((n,pn))
   elif pn not in ('C','CLK'):loads[b].append((n,pn))
for n,c in m['ports'].items():
 for b in c['bits']:
  if isinstance(b,int):
   b=find(('top/',b))
   if c['direction']=='input' and n!='ck':drivers[b].append(('@PORT',n))
   elif c['direction']=='output':loads[b].append(('@PORT',n))
merged_names=collections.defaultdict(list)
for bit,ns in names.items():merged_names[find(bit)].extend(ns)
names=merged_names
rows=sorted([dict(bit=b,names=names[b],drivers=d,loads=len(loads[b])) for b,d in drivers.items() if not any(n=='@PORT' and pn=='ck' for n,pn in d)],key=lambda r:-r['loads'])
rec=dict(source_sha256=hashlib.sha256(s.read_bytes()).hexdigest(),source_commit=None,scope='hierarchy traversed into every scalar primitive; INV transparent; generic technology-map before ABC, diagnostic only',layout=False,limits=dict(max_driver_pins=32),over32=[r for r in rows if r['loads']>32],top=rows[:40],cells=len(flat))
(p/'census.json').write_text(json.dumps(rec,indent=2));print('KVN_GENERIC_NATIVE',rec['cells'],'max',rows[0]['loads'],'over32',len(rec['over32']));print(json.dumps(rows[:4],indent=2))
