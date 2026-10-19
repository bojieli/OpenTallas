#!/usr/bin/env python3
"""Independent abstract transparent terminal-pin audit, before native mapping.

This is a design-model check only. Native mapping must independently recount
all native standard cell inputs through actual BUF/INV; never infer native PASS.
"""
import argparse,collections,json
from pathlib import Path

def audit(graph):
 m=next(iter(graph['modules'].values())); fan=collections.defaultdict(list); drivers={}; trans={}
 for name,c in m['cells'].items():
  for pin,bits in c['connections'].items():
   for k,b in enumerate(bits):
    if c['port_directions'][pin]=='input':fan[b].append((name,pin,k))
    else:assert b not in drivers;drivers[b]=(name,pin)
  if c['type'] in ['$_NOT_','BUFx2_ASAP7_75t_R']:
   trans[name]=c['connections']['Y'][0]
 for name,p in m['ports'].items():
  if p['direction']=='output':
   for k,b in enumerate(p['bits']):fan[b].append(('@'+name,'',k))
 def terminal(b,seen=frozenset()):
  assert b not in seen,'transparent cycle'
  return sum(terminal(trans[n],seen|{b}) if n in trans else 1 for n,p,k in fan[b])
 clocks={b for n,c in m['cells'].items() for p,bb in c['connections'].items() if p in ['C','clk','rclk','wclk'] for b in bb}
 roots={b:('TOP',name) for name,p in m['ports'].items() if p['direction']=='input' for b in p['bits']}
 roots.update({b:d for b,d in drivers.items() if d[0] not in trans})
 rows=[{'net':b,'driver':d,'terminal_pins':terminal(b)} for b,d in roots.items() if isinstance(b,int) and b not in clocks]
 rows.sort(key=lambda r:-r['terminal_pins']);bad=[r for r in rows if r['terminal_pins']>32]
 return {'scope':'abstract source only; native census required','status':'FAIL' if bad else 'PASS','roots':len(rows),'max':max((r['terminal_pins'] for r in rows),default=0),'over32':bad,'top20':rows[:20]}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('graph');ap.add_argument('--out',required=True);a=ap.parse_args()
 result=audit(json.loads(Path(a.graph).read_text()));Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['status']=='PASS'
