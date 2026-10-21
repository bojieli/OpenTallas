import json,subprocess,os,hashlib,re
from pathlib import Path
root=Path(__file__).parent
manifest=json.loads((root/'source_manifest.json').read_text())
for name,expected in manifest['files'].items():
 actual=hashlib.sha256((root/name).read_bytes()).hexdigest()
 if actual!=expected:raise SystemExit('PREFIX_SOURCE_BINDING_FAIL '+name+' '+actual)
print('PREFIX_SOURCE_BINDING_PASS',len(manifest['files']),flush=True)
template=(root/'model_body.tcl').read_text();libs=json.loads((root/'macro_libs.json').read_text())
image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
subprocess.run(['docker','image','inspect',image],check=True,stdout=subprocess.DEVNULL)
rows=[]
for case in ['baseline','candidate']:
 for corner in ['tt','ff']:
  reads='\n'.join('read_liberty '+p for p in libs if p.endswith('_'+corner+'.lib'))
  script=template
  replacements={'@CORNER_UPPER@':corner.upper(),'@CORNER@':corner,'@CASE@':case,'@MACRO_LIB_READS@':reads,'@DATABASE@':'/input/3_place.odb' if corner=='tt' else '/out/'+case+'.odb','@BUILD@':'1' if corner=='tt' else '0','@ALL_MACRO_LIBS@':' '.join(libs)}
  for a,b in replacements.items():script=script.replace(a,b)
  path=root/(case+'_'+corner+'.tcl');path.write_text(script)
  log=root/(case+'_'+corner+'.log')
  cmd=['docker','run','--rm','--user',str(os.getuid())+':'+str(os.getgid()),'--memory','16g','--memory-swap','16g','--cpus','1','-v',str(root/'src')+':/src:ro','-v',str(root/'input')+':/input:ro','-v',str(root)+':/out',image,'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-threads','1','-no_init','-exit','/out/'+path.name]
  with log.open('w') as out:rc=subprocess.call(cmd,stdout=out,stderr=subprocess.STDOUT)
  print('PREFIX_MODEL_EXIT',case,corner,rc,flush=True)
  text=log.read_text();print('\n'.join(l for l in text.splitlines() if l.startswith(('E2_PREFIX_','B0_PERIMETER','B0_WRITE','Error:'))),flush=True)
  rows.append(dict(case=case,corner=corner,rc=rc,log=log.name,sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
  (root/'execution_receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
  if rc:raise SystemExit(rc)
print('PREFIX_MODELS_COMPLETED_DIAGNOSTIC_ONLY',flush=True)
