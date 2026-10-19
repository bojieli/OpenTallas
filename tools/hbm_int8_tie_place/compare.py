import json,re,sys
from pathlib import Path
r=Path(sys.argv[1]);src=json.load(open(r/'safe_mapped.json'))['modules']['ot_smh_int8_tile_safe']
alias={}
for n,p in src['ports'].items():
 for k,b in enumerate(p['bits']):alias[n+(f'[{k}]' if len(p['bits'])>1 else '')]=b
def normalize(raw):
 m=next(iter(raw['modules'].values()));meta=m['net_metadata'];nets={};ties={}
 for c in m['cells'].values():
  if c['type'] in ('TIEHIx1_ASAP7_75t_R','TIELOx1_ASAP7_75t_R'):
   for p,b in c['connections'].items():
    if c['port_directions'][p]=='output':ties[b[0]]='1' if c['type'].startswith('TIEHI') else '0'
 for k,v in meta.items():
  n=v['name'];k=int(k)
  if k in ties:nets[k]=ties[k]
  elif n in alias:nets[k]=alias[n]
  elif re.fullmatch(r'n[0-9]+',n):nets[k]=int(n[1:])
  elif n=='one_':nets[k]='1'
  elif n=='zero_':nets[k]='0'
 out={}
 for n,c in m['cells'].items():
  if n not in src['cells']:continue
  d={p:[nets[x] for x in b] for p,b in c['connections'].items() if c['pin_signal_types'][p] not in ('POWER','GROUND')}
  out[n]=dict(type=c['type'],connections=d)
 assert set(out)==set(src['cells'])
 for n,c in out.items():assert c=={k:src['cells'][n][k] for k in ('type','connections')},(n,c,src['cells'][n])
 return m
summ=[]
for name in ('before','after_ties','placed'):
 m=normalize(json.load(open(r/name/'raw.json')));summ.append(dict(stage=name,ordinary_cells=len(src['cells']),extra_cells=len(m['cells'])-len(src['cells']),all_ordinary_connections_exact=True))
(r/'connectivity_identity.json').write_text(json.dumps(summ,indent=2)+'\n');print(json.dumps(summ))
