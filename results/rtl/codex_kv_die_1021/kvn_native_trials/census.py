import pathlib,hashlib,json,subprocess,collections
p=pathlib.Path.cwd(); s=p/'qkd_kvn_ctx_ovl_rope.sv'; y=pathlib.Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'
script=f'read_verilog -sv {s}; hierarchy -check -top qkd_kvn_ctx_ovl_rope; synth -top qkd_kvn_ctx_ovl_rope -noabc; write_json generic.json; stat'
r=subprocess.run([str(y),'-Q','-T','-p',script],capture_output=True,text=True);(p/'synthesis.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
m=json.loads((p/'generic.json').read_text())['modules']['qkd_kvn_ctx_ovl_rope'];loads=collections.defaultdict(list);drivers=collections.defaultdict(list);names=collections.defaultdict(list)
for name,n in m['netnames'].items():
 for b in n['bits']:
  if isinstance(b,int):names[b].append(name)
for n,c in m['cells'].items():
 for pn,bs in c['connections'].items():
  for b in bs:
   if not isinstance(b,int):continue
   if c['port_directions'][pn]=='output':drivers[b].append((n,pn))
   elif pn not in ('C','CLK'):loads[b].append((n,pn))
for n,c in m['ports'].items():
 for b in c['bits']:
  if isinstance(b,int):
   if c['direction']=='input' and n!='ck':drivers[b].append(('@PORT',n))
   elif c['direction']=='output':loads[b].append(('@PORT',n))
rows=sorted([dict(bit=b,names=names[b],drivers=d,loads=len(loads[b])) for b,d in drivers.items() if not any(n=='@PORT' and pn=='ck' for n,pn in d)],key=lambda r:-r['loads'])
rec=dict(source_sha256=hashlib.sha256(s.read_bytes()).hexdigest(),source_commit=None,scope='generic scalar technology-map before ABC/buffers; diagnostic native-driver lower bound only',layout=False,limits=dict(max_driver_pins=32),over32=[r for r in rows if r['loads']>32],top=rows[:40],cells=len(m['cells']))
(p/'census.json').write_text(json.dumps(rec,indent=2));print('KVN_GENERIC_NATIVE',rec['cells'],'max',rows[0]['loads'],'over32',len(rec['over32']));print(json.dumps(rows[:4],indent=2))
