import json,hashlib
from pathlib import Path
import pinreg_audit as P
v=Path('/srv/opentallas-scratch/claude/closure-loop/hsm_smvm_wrq_t_r4-faces4-c8e94d78d/record/views/ot_hbm_sm_vm_wr_q_t_faces4')
ins=json.loads((v/'insertion.json').read_text()); out={'job':'hsm_smvm_wrq_t_r4-faces4-c8e94d78d','sha256':{},'corners':{}}
for corner in ('tt','ff','ss'):
 p=v/f'ot_hbm_sm_vm_wr_q_t_faces4_{corner}.lib'; out['sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
 lib=P.parse_lib(p); refs=P.clock_refs(lib,ins,corner); metrics=P.pin_metrics(lib,refs)
 launch=sorted([(m['out'],n) for n,m in metrics.items() if m['dir']=='output' and m['out'] is not None],reverse=True)
 capture=sorted([(m['inp'],n) for n,m in metrics.items() if m['dir']=='input' and m['inp'] is not None],reverse=True)
 out['corners'][corner]={'refs':refs,'launch_max':launch[0], 'capture_max':capture[0], 'outputs':len(launch),'inputs':len(capture),'launch_over_220':[x for x in launch if x[0]>220],'capture_over_190':[x for x in capture if x[0]>190],'comb':[n for n,m in metrics.items() if m['comb']], 'all_port_metrics':metrics}
out['sha256']['insertion.json']=hashlib.sha256((v/'insertion.json').read_bytes()).hexdigest()
Path('writer_audit.json').write_text(json.dumps(out,indent=2)+'\n')
for c,r in out['corners'].items(): print(c, r['launch_max'],r['capture_max'],len(r['launch_over_220']),len(r['capture_over_190']),r['refs'])
