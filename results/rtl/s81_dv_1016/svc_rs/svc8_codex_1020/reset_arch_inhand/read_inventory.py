import collections,hashlib,json,re
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/s81-svc8-1020');O=R/'out_codex_reset_arch_model';O.mkdir(exist_ok=True)
p=R/'out_codex_predecode_native/map/flat.json';j=json.load(p.open())['modules']['ot_s81svc8_hgrp_s81'];cells=j['cells'];ledger=json.load((R/'out_codex_predecode_resume2/bound/bounded.v.ledger.json').open())
net=j['netnames'];resetbits={n:net[n]['bits']for n in ['rst_n','rl0','rl1','rst_l','ov']};bits={x for bs in resetbits.values()for x in bs};candidates=[]
for name,c in cells.items():
 if c['type'].startswith(('DFF','INV')) and any(set(v)&bits for port,v in c['connections'].items()if c['port_directions'][port]=='output'):
  candidates.append({'name':name,'type':c['type'],'connections':c['connections'],'attributes':c.get('attributes')})
# Trace inversions from logical rl0/rl1/ov back to actual QN registers.
flops={}
for logical in ['rl0','rl1','ov']:
 pending=set(net[logical]['bits']);seen=set();found=[]
 while pending-seen:
  wave=pending-seen;seen|=wave
  for name,c in cells.items():
   out={v for port,vs in c['connections'].items()if c['port_directions'][port]=='output'for v in vs}
   if not wave&out:continue
   if c['type'].startswith('DFF'):found.append(name)
   elif c['type'].startswith(('INV','BUF')):
    pending|={v for port,vs in c['connections'].items()if c['port_directions'][port]=='input'for v in vs}
 flops[logical]=found
copies=collections.Counter(ledger['origins'].values());details={}
for logical,names in flops.items():
 details[logical]=[{'original_cell':n,'cell':cells[n],'mapped_copies_including_original':copies[n],'mapped_instance_keys':[k for k,v in ledger['origins'].items()if v==n]}for n in names]
consumers=[]
for name,c in cells.items():
 for port,vs in c['connections'].items():
  if c['port_directions'][port]=='input'and set(vs)&set(net['rl1']['bits']):consumers.append({'cell':name,'type':c['type'],'port':port,'retained_copies':copies[name]})
area={};libsources=[]
for f in sorted((R/'out_codex_predecode_native/map/lib').glob('*.lib')):
 text=f.read_text();libsources.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 for m in re.finditer(r'\bcell\s*\(\s*(\S+?)\s*\)\s*\{\s*area\s*:\s*([\d.eE+-]+)',text):area[m[1]]=float(m[2])
result={'status':'SOURCE_ARCHITECTURE_MODEL_ONLY','source_json_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_ledger_sha256':hashlib.sha256((R/'out_codex_predecode_resume2/bound/bounded.v.ledger.json').read_bytes()).hexdigest(),'logical_net_bits':resetbits,'reset_flops':details,'rl1_original_consumer_roles':dict(collections.Counter(x['port']for x in consumers)),'rl1_consumer_retained_loads_by_port':{port:sum(x['retained_copies']for x in consumers if x['port']==port)for port in sorted({x['port']for x in consumers})},'rl1_consumers':consumers,'area_um2':{k:area.get(k)for k in ['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R']},'area_sources':libsources}
(O/'actual_reset_inventory.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['rl1_consumers','area_sources','reset_flops']},indent=2));print('RESET_COPIES',{k:[x['mapped_copies_including_original']for x in v]for k,v in details.items()},flush=True)
