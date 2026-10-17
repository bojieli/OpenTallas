import json,hashlib
from pathlib import Path
import pinreg_audit as P
v=Path('/srv/opentallas-scratch/claude/closure-loop/hep_static_w5e_1016-w5e-314f4f068/record/views/hfd_ep_static')
ins=json.loads((v/'insertion.json').read_text()); out={'job':'hep_static_w5e_1016-w5e-314f4f068','sha256':{},'corners':{}}
for corner in ('tt','ff','ss'):
 p=v/f'hfd_ep_static_{corner}.lib'; out['sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
 lib=P.parse_lib(p); refs=P.clock_refs(lib,ins,corner); metrics=P.pin_metrics(lib,refs)
 launch=sorted([(m['out'],n) for n,m in metrics.items() if m['dir']=='output' and m['out'] is not None],reverse=True)
 capture=sorted([(m['inp'],n) for n,m in metrics.items() if m['dir']=='input' and m['inp'] is not None],reverse=True)
 out['corners'][corner]={'refs':refs,'launch_max':launch[0], 'capture_max':capture[0], 'outputs':len(launch),'inputs':len(capture),'launch_over_220':[x for x in launch if x[0]>220],'capture_over_190':[x for x in capture if x[0]>190],'comb':[n for n,m in metrics.items() if m['comb']], 'all_port_metrics':metrics}
out['sha256']['insertion.json']=hashlib.sha256((v/'insertion.json').read_bytes()).hexdigest()
Path('hep5e_audit.json').write_text(json.dumps(out,indent=2)+'\n')
for c,r in out['corners'].items():print(c, {k:v for k,v in r.items() if k!='all_port_metrics'})
