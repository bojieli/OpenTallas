import json,collections,functools
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/codex-qc-a0-2157');j=json.loads((r/'native_flat.json').read_text());m=j['modules']['ot_qwen_tile_lsl'];cells=m['cells'];cons=collections.defaultdict(list)
for n,c in cells.items():
 for p,d in c['port_directions'].items():
  if d=='input':
   for b in c['connections'][p]:cons[b].append((n,p))
@functools.lru_cache(None)
def cap(b):
 q=set()
 for n,p in cons[b]:
  c=cells[n]
  if c['type'].startswith('DFF'):q.add((n,p))
  else:
   for pp,d in c['port_directions'].items():
    if d=='output':
     for bb in c['connections'][pp]:q|=cap(bb)
 return frozenset(q)
ports={}
for n,p in m['ports'].items():
 if p['direction']=='input'and n not in ('clk','rst_n'):
  ports[n]=[{'bit':i,'first_capture_ff_count':len(cap(b))}for i,b in enumerate(p['bits'])]
o={'status':'actual native source first-state census; no physical F6/timing credit','ports':ports,'summary':{n:{'bits':len(v),'min_capture':min(x['first_capture_ff_count']for x in v),'max_capture':max(x['first_capture_ff_count']for x in v)}for n,v in ports.items()}}
inv=collections.defaultdict(list)
for n,p in m['ports'].items():
 if p['direction']=='input'and n not in ('clk','rst_n'):
  for i,b in enumerate(p['bits']):
   for c in cap(b):inv[c].append(n+'['+str(i)+']')
o['capture_map']={n+('['+str(i)+']' if len(p['bits'])>1 else ''):next(iter(cap(b)))[0] for n,p in m['ports'].items() if p['direction']=='input'and n not in ('clk','rst_n') for i,b in enumerate(p['bits'])}
o['shared_first_capture']={str(k):v for k,v in inv.items()if len(v)>1}
print(o['summary'],'shared_capture',len(o['shared_first_capture']));Path('/srv/opentallas-scratch/claude/wt/codex-qc-a0-2157/results/qc_a0_2157/rawfault_cut/input_capture_census.json').write_text(json.dumps(o,indent=2))
