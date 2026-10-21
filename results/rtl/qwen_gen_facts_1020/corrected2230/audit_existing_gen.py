"""Diagnose existing immutable GEN facts using actual emitted clock wiring.
No GEN or netlist rewrite. Retains original reports; derived fixes are explicit.
"""
import argparse, collections, copy, hashlib, json, re
from pathlib import Path
from types import SimpleNamespace
from gen_safety_facts import relay_chains
from gen_check import check_facts, status_line

ap=argparse.ArgumentParser();ap.add_argument('--gen',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args();s=a.gen;o=a.out;o.mkdir(parents=True,exist_ok=True)
f=json.loads((s/'out/case/gen_safety_facts.json').read_text())
model=json.loads((s/'out/rom_tp8b.json').read_text())
by={i['n']:SimpleNamespace(master=i['m'],kind='reset_rep' if i['m'].startswith('qfd_rst_rep') else ('relay' if i['m'].startswith(('qfd_rly','qfd_land')) else 'block')) for i in model['insts']}
v=(s/'out/case/die.v').read_text()
ports={}
for line in v.splitlines():
 m=re.match(r'\s+\w+\s+(\w+)\s+\(',line)
 if m: ports[m[1]]=dict(re.findall(r'[.]([A-Za-z0-9_]+)[(]([^)]*)[)]',line))
original=check_facts(f);derived=copy.deepcopy(f)
resolutions=[];kept=[]
for c in derived['crossings']:
 for side in ('src_region','dst_region'):
  r=c[side]
  if not r.startswith('UNDRIVEN:io_collective/'):
   continue
  cp=r.split('/',1)[1];m=re.fullmatch(r'(\w+)(?:\[(\d+)\])?',cp);assert m,cp
  expr=ports['io_collective'][m[1]]
  values=expr.strip('{}').split(',');bit=int(m[2] or 0)
  assert bit<len(values),(cp,expr)
  physical=values[-1-bit].strip();root=re.sub(r'\[0\]$','',physical).removeprefix('n_')
  assert derived['regions'].get(root,{}).get('root'),(cp,root)
  resolutions.append(dict(bus=c['id'],side=side,related_pin=cp,emitted_port=m[1],emitted_value=expr,physical_bit_net=physical,resolved_region=root))
  c[side]=root
 if c['id']=='rst_fwd':
  assert c['dst']=='rs_bump' and by['rs_bump'].master=='qfd_rstsync'
  assert ports['rs_bump']['arst_n']=='n_rst_fwd'
  derived['reset_landings'].append(dict(id=c['id'],src=['ckb_rom','rs'],dst=['rs_bump','arst_n'],landing='rs_bump',kind='package_reset_synchronizer',evidence='actual qfd_rstsync.arst_n; existing qwen_landed_pairs RESET_SYNC class'))
  continue
 if c['src_region']==c['dst_region']:
  continue
 kept.append(c)
derived['crossings']=kept
# The prior facts already stitch data relay lanes. Stitch the remaining actual
# qfd_rst_rep q0..q7 branches too; all input pin coordinates are retained.
derived['wires']=relay_chains(derived['wires'],by)
report=check_facts(derived)
assert not derived['centroid_only_segments']
bad=[c for c in derived['crossings'] if not c.get('landing')]
reset=[c for c in bad if c['id'].startswith(('rst_field','rst_seq','rst_io'))]
for c in reset:
 net='n_'+c['id']
 c['actual_src_ports']=[p for p,n in ports[c['src']].items() if n==net]
 c['actual_dst_ports']=[p for p,n in ports[c['dst']].items() if n==net]
files=['src/SOURCE_COMMIT','src/tools/qwen_rom_fulldie_b3r2.py','src/tools/qwen_split/gen_safety_facts.py','src/tools/qwen_split/reset_sync_contract.py','out/case/die.v','out/case/reset_sync.json','out/case/gen_safety_facts.json','out/case/fwd_lanes.json','gen_safety_report.json','reset_audit.log']
diagnosis=dict(scope='Post-GEN audit of actual corresponding-bit facts and actual emitted netlist wiring; remaining failures preserved, no die qualification',gen=str(s),input_sha256={p:hashlib.sha256((s/p).read_bytes()).hexdigest() for p in files},exporter_source_commit='3fe1d74c8',centroid_only_segments=len(derived['centroid_only_segments']),channels=len(derived['channels']),actual_reset_landings=len(derived['reset_landings']),source_synchronous_clocks=len(derived['source_synchronous_clocks']),alias_resolutions=resolutions,package_sync_correction='rst_fwd -> actual qfd_rstsync rs_bump/arst_n',reset_counts=dict(crossings=len(reset),unique_buses=len({c['id'] for c in reset}),source_repeaters=len({c['src'] for c in reset}),destinations=len({c['dst'] for c in reset})),regional_reset_targets=reset,other_unlanded=[c for c in bad if c not in reset])
(o/'original_report.json').write_text(json.dumps(original,indent=1)+'\n')
(o/'derived_report.json').write_text(json.dumps(report,indent=1)+'\n')
(o/'diagnosis.json').write_text(json.dumps(diagnosis,indent=1)+'\n')
(o/'derived_facts.json').write_text(json.dumps(derived,separators=(',',':'))+'\n')
print(status_line(report));print('ACTUAL_BIT_GEOMETRY centroid_only=0 channels='+str(len(derived['channels'])))
