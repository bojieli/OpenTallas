import json,collections,functools
from pathlib import Path
scope=Path('/srv/opentallas-scratch2/claude/codex-hbm-xs3-model-0920');j=json.loads((scope/'flat.json').read_text());top=max(j['modules'].values(),key=lambda m:len(m.get('cells',{})));cs=top['cells'];drivers=collections.defaultdict(list);users=collections.defaultdict(list)
for n,c in cs.items():
 for p,bs in c['connections'].items():
  direction=c['port_directions'][p]
  for bit in bs:
   if isinstance(bit,int):(drivers if direction=='output' else users)[bit].append((n,p))
macros={n:c for n,c in cs.items() if c['type'].startswith('ot_sram_')}
seq=lambda c:any(s in c['type'].upper() for s in ('DFF','LATCH'))
@functools.lru_cache(None)
def back(bit):
 result=set()
 for n,p in drivers[bit]:
  c=cs[n]
  if seq(c):result.add((n,p))
  elif n not in macros:
   for q,bs in c['connections'].items():
    if c['port_directions'][q]=='input':
     for b in bs:
      if isinstance(b,int):result.update(back(b))
 return frozenset(result)
summary={}
for n,c in macros.items():
 ports={}
 for p,bs in c['connections'].items():
  if p=='clk':continue
  native=[b for b in bs if isinstance(b,int)]
  if c['port_directions'][p]=='input':
   src=set().union(*(back(b) for b in native)) if native else set();ports[p]=dict(bits=len(bs),nonconstant_bits=len(native),unique_source_ffs=len(src),source_ffs=sorted(src))
  else:
   direct=[(u,q) for b in native for u,q in users[b] if seq(cs[u])];ports[p]=dict(bits=len(bs),nonconstant_bits=len(native),direct_capture_ffs=sorted(set(direct)))
 summary[n]=ports
(scope/'actual_macro_pin_ff_adjacency.json').write_text(json.dumps(dict(scope='Source actual mapped combinational adjacency only; no physical positions, route or geometry PASS claimed',macros=summary),indent=1)+'\n')
print('XS3_ADJACENCY',len(summary),'macros',sum(len(v.get('source_ffs',[])) for p in summary.values() for v in p.values()),'sourceff-port incidences')
