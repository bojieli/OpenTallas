from pathlib import Path
import shlex,json,hashlib
r=Path('/srv/opentallas-scratch2/claude/codex-ds-service-hier-0340')
a=r/'fs/home/ubuntu/scratch-root/claude/tok-ds-2/build_v1c3/obj/Vs81p_svc_lo_dsdv_svc_rs_w___05Ft1_9__hierMkArgs.f'
tokens=shlex.split(a.read_text());out=[]
for i,x in enumerate(tokens):
 if i and tokens[i-1]=='-Mdir':x=str(r/'out')
 else:
  for root in ['/srv/opentallas-scratch2/','/home/ubuntu/scratch-root/']:
   x=x.replace(root,str(r/'fs')+root)
 if i and tokens[i-1]=='--build-jobs':x='1'
 out.append(x)
out.extend(['--hierarchical-params-file',str(r/'empty_types.sv')])
(r/'candidate_args.f').write_text('\n'.join(json.dumps(x) for x in out)+'\n')
(r/'empty_types.sv').write_text('// Compatibility trigger for integer/default-only library substitution. No type declarations.\n')
files=[p for p in (r/'fs').rglob('*') if p.is_file()]
(r/'staged_readset.json').write_text(json.dumps([dict(path=str(p.relative_to(r/'fs')),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files],indent=2)+'\n')
