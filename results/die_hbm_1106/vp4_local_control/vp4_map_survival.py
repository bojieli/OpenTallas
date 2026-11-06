import json,re
from pathlib import Path
p=Path('.')
m=json.load(open(p/'mapped_local_ctrl.json'))['modules']['ot_hgi_dma_back_static_vp4_controller']
n={k:v for k,v in m['netnames'].items() if re.fullmatch(r'G_COMMAND_CTRL\[\d+\]\.G_LOCAL\.(flags|valid_q)',k)}
d={}
for k,c in m['cells'].items():
 if 'DFF' not in c['type']:continue
 for pn,bs in c['connections'].items():
  if pn in ('Q','QN'):
   for b in bs:d.setdefault(b,[]).append((k,c['type']))
inv={c['connections']['Y'][0]:c['connections']['A'][0] for c in m['cells'].values() if c['type'].startswith('INV') and 'Y' in c['connections']}
for nn in n.values():
 for bit in nn['bits']:
  src=bit;seen=set()
  while src in inv and src not in seen:
   seen.add(src);src=inv[src]
  if src!=bit:d[bit]=d.get(src,[])
r={k:{'bits':v['bits'],'drivers':[d.get(b,[]) for b in v['bits']]}for k,v in n.items()}
bits={b for v in n.values()for b in v['bits']};drvs={x[0] for b in bits for x in d.get(b,[])}
s={'source_groups':17,'named_vectors':len(n),'local_bits':sum(len(v['bits'])for v in n.values()),'distinct_bits':len(bits),'distinct_ff_drivers':len(drvs),'all_single_ff_driver':all(len(d.get(b,[]))==1 for b in bits),'std_cells':len(m['cells']),'seq_cells':sum('DFF' in c['type']for c in m['cells'].values()),'local_drivers':r}
(p/'mapped_survival.json').write_text(json.dumps(s,indent=2)+'\n');print({k:v for k,v in s.items()if k!='local_drivers'})
assert s['local_bits']==119 and s['distinct_ff_drivers']==119 and s['all_single_ff_driver']
