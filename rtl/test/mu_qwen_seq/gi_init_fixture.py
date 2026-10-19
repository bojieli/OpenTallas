#!/usr/bin/env python3
"""Stage actual public F16 packet events; no synthetic programme or arithmetic."""
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
a=json.loads((p/'admission.json').read_text()); base=2000; end=base+a['H']+max(x['init'] for x in a['boundaries'].values())+200
es=[(base-334,0,(1<<42)|(777<<18)|5)]
for repeat in range(2):
 for x in a['active_units']:
  if x['user']==0:
   t=base+repeat*a['H']+x['time']
   if t<end: es.append((t,1,(1<<42)|(x['stage']<<36)|(777<<18)|5))
 for us,b in a['boundaries'].items():
  u=int(us); t=base+repeat*a['H']+b['load_slot']['bank_load']
  if t<end:
   record=(1<<128)|(0x4d43<<112)|(1<<(108+u-1))|(((1000+100*repeat+u)<<18|7)<<(36*(u-1)))
   es.append((t-2,2,record))
   es.append((t-1,3,0))  # ordinary user0 record immediately restores receiver
(out/'events.txt').write_text(''.join(f'{t} {k} {v:033x}\n' for t,k,v in sorted(es)))
(out/'limits.txt').write_text(f'{end}\n')
