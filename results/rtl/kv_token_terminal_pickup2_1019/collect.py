import pathlib, hashlib, re, json, tarfile, io, sys, datetime
roots={'g7':'/srv/opentallas-scratch/claude/kv-tok/veh/g7/WSQK','old_qk':'/srv/opentallas-scratch/claude/codex-mu-tok-kv/old_qk_WS_r2'}
out=tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz');manifest={}
def add(name,b):
 i=tarfile.TarInfo(name);i.size=len(b);i.mtime=0;out.addfile(i,io.BytesIO(b))
for label,root in roots.items():
 p=pathlib.Path(root);m={};selected=list((p/'cut').iterdir())+[p/'run'/n for n in ['tb_qwk_stk_WS.sv','cases.txt','hier.vlt','verilator.version','run_u1.log','run_u1.time','resume_cpp_stack_20261019.u1.log','resume_cpp_stack_20261019.u1.time','resume_cpp_stack_20261019.inputs.json','resume_cpp_stack_20261019.results.json','obj/Vtb_qwk_stk_WS__verFiles.dat','obj/Vtb_qwk_stk_WS__hierMkArgs.f']]
 vf=(p/'run/obj/Vtb_qwk_stk_WS__verFiles.dat').read_text();sources=[]
 for line in vf.splitlines():
  if line.startswith('S '):
   match=re.search(r'"([^"\n]+)"$',line)
   if match:sources.append(pathlib.Path(match.group(1)))
 for q in selected+sources+[p/'run/obj/Vtb_qwk_stk_WS']:
  if not q.is_file() or str(q) in m:continue
  b=q.read_bytes();s=q.stat();m[str(q)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mtime_ns':s.st_mtime_ns}
  if q in selected or 'drive_qwk' in q.name or q.suffix=='.svh':add(label+'/files/'+str(q).lstrip('/'),b)
 for l in (p/'run/cases.txt').read_text().splitlines():
  for vec in re.findall(r'\+VEC\d+=([^ ]+)',l):
   for q in sorted(pathlib.Path(vec).iterdir()):
    if q.is_file() and str(q) not in m:
     b=q.read_bytes();m[str(q)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mtime_ns':q.stat().st_mtime_ns}
 manifest[label]={'root':root,'files':m,'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
add('manifest.json',json.dumps(manifest,indent=2).encode());out.close()
