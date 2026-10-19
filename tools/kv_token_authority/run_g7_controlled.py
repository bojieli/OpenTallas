#!/usr/bin/env python3
"""One immutable exact-original-u1 continuation; never mutates original objects."""
import hashlib,json,re,shlex,shutil,subprocess,sys
from pathlib import Path
from identity_verdict import parse_verdict
root=Path(__file__).resolve().parent
old=Path('/srv/opentallas-scratch/claude/kv-tok/veh/g7/WSQK')
run=root/'controlled_u1';obj=run/'obj'
if run.exists():raise SystemExit('REFUSED: immutable continuation already exists')
run.mkdir();obj.mkdir()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def stage(name,state,**kw):
 (run/f'{name}.json').write_text(json.dumps({'stage':name,'state':state,**kw},indent=2)+'\n')
def call(name,cmd,cwd):
 stage(name,'RUNNING',argv=cmd)
 with (run/f'{name}.log').open('wb') as f:r=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
 stage(name,'TERMINAL',returncode=r.returncode,argv=cmd)
 if r.returncode:raise SystemExit(f'{name} failed rc{r.returncode}; preserve logs')
call('audit',[sys.executable,str(root/'audit_reuse.py'),'--manifest',str(root/'original_g7_manifest.json'),'--out',str(run/'reuse_audit.json')],root)
audit=json.loads((run/'reuse_audit.json').read_text());assert audit['status']=='PASS'
# Copy complete frozen child compilation directories; no hardlinks/symlinks.
for q in sorted((old/'run/obj').glob('V*')):
 if q.is_dir():shutil.copytree(q,obj/q.name,copy_function=shutil.copy2,symlinks=False)
for name,pin in audit['reusable_files'].items():
 q=Path(name);copied=obj/q.relative_to(old/'run/obj')
 if sha(copied)!=pin['sha256']:raise SystemExit(f'copied reusable object mismatch: {q}')
call('fixture',[sys.executable,str(root/'repair_g7_fixture.py'),'--driver',str(old.parent.parent/'tools/qwen_layerbench/drive_qwk_slice_attn_mu.svh'),'--tb',str(old/'run/tb_qwk_stk_WS.sv'),'--out',str(run/'fixture')],root)
fixture=run/'fixture'
for name in ['g7_identity_bind.svh','g7_fault_bind.svh','authority.svh','kva_authority_path.sv','kva_identity_scoreboard.sv']:
 shutil.copy2(root/name,fixture/name)
args=shlex.split((old/'run/obj/Vtb_qwk_stk_WS__hierMkArgs.f').read_text())
for i,x in enumerate(args):
 if x==str(old/'run/tb_qwk_stk_WS.sv'):args[i]=str(fixture/'tb_qwk_stk_WS.sv')
 elif x=='-Mdir':args[i+1]=str(obj)
 elif x.startswith('+define+SLICE_DRIVE='):args[i]='+define+SLICE_DRIVE="'+str(fixture/'drive_qwk_slice_attn_mu.svh')+'"'
args=['+incdir+'+str(fixture),str(fixture/'kva_authority_path.sv'),str(fixture/'kva_identity_scoreboard.sv')]+args
argfile=run/'top_args.f';argfile.write_text('\n'.join(json.dumps(x) for x in args)+'\n')
verilator='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
call('frontend',[verilator,'-f',str(argfile)],obj)
# Immutable library-only include: make must never regenerate an original child.
hier=(old/'run/obj/Vtb_qwk_stk_WS_hier.mk').read_text().split('hier_build:',1)[0]
(obj/'Vtb_qwk_stk_WS_hier.mk').write_text(hier+'\nendif\n')
call('compile',['make','-f','Vtb_qwk_stk_WS.mk','-j4','Vtb_qwk_stk_WS'],obj)
for name,pin in audit['reusable_files'].items():
 q=Path(name)
 if sha(q)!=pin['sha256'] or sha(obj/q.relative_to(old/'run/obj'))!=pin['sha256']:raise SystemExit(f'reused child changed: {q}')
cases=(old/'run/cases.txt').read_text().splitlines();selected=[l for l in cases if l.startswith('u1 ')]
if len(selected)!=1:raise SystemExit('unique original u1 required')
cmd=[str(obj/'Vtb_qwk_stk_WS'),'+verilator+rand+reset+2','+verilator+seed+1','+verilator+error+limit+1000000']+shlex.split(selected[0])[1:]
stage('simulation','RUNNING',argv=cmd)
with (run/'u1.log').open('wb') as f:r=subprocess.run(cmd,cwd=run,stdout=f,stderr=subprocess.STDOUT)
passed,reason=parse_verdict((run/'u1.log').read_text(),r.returncode)
verdict={'application_pass':passed,'reason':reason}
stage('simulation','TERMINAL',returncode=r.returncode,application_verdict=verdict,argv=cmd)
print(json.dumps(verdict,indent=2));raise SystemExit(0 if verdict['application_pass'] else 1)
