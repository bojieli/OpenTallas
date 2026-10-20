from pathlib import Path
import subprocess,json,hashlib,os,datetime
B=Path.cwd();rows=json.loads((B/'cases.json').read_text());image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29';jobs=sorted({str(Path(r['orfs_dir']).parents[3]) for r in rows});paths=sorted({f['path'] for r in rows for f in r['files'] if f['exists']})
def hashes():return {p:dict(size=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for p in paths}
pre=hashes();(B/'inputs_before.json').write_text(json.dumps(pre,indent=2));inspect=json.loads(subprocess.check_output(['docker','image','inspect',image]));assert inspect[0]['Id']==image; (B/'frozen_image_inspect.json').write_text(json.dumps(inspect,indent=2))
base=['docker','run','--rm','--user',str(os.getuid())+':'+str(os.getgid()),'-v',str(B)+':/stage']
for job in jobs:base+=['-v',job+':'+job+':ro']
rcs=[]
for entry,args,log in [('python3',['/stage/capture_image.py'],'capture_image.log'),('/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',['-no_init','-exit','-python','/stage/native_graph.py'],'native_graph.log')]:
 cmd=base+['--entrypoint',entry,image]+args
 with (B/log).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 rcs.append(dict(command=cmd,returncode=r.returncode,log=log));print('PREFLIGHT_STEP',entry,r.returncode,flush=True)
 if r.returncode:break
post=hashes();(B/'inputs_after.json').write_text(json.dumps(post,indent=2));(B/'preflight_execution.json').write_text(json.dumps(dict(scope='ROOT07:40 currentfrozenimageprospectiveONLY; nohistoricalimageproof; ORIGINALRO_NO_EXPORT_YET',source='6586b0856',source35sha256='578418117d3547dc46dcf08c119533d1fc36db122a7a8c22f44cf6d4ae7b82b3',steps=rcs,original_inputs_unchanged=pre==post),indent=2));assert pre==post
if (B/'native_preflight_summary.json').exists():print((B/'native_preflight_summary.json').read_text())
raise SystemExit(next((x['returncode'] for x in rcs if x['returncode']),0))
