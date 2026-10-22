from pathlib import Path
import os,subprocess,json,tarfile,hashlib
b=Path.cwd();a=b/'pytest_runtime902.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='db0143f7bfd98f8a7dc733594840ea8d445bfe6aacd6bc8f9036bbb61611e291'
with tarfile.open(a)as t:t.extractall(b/'runtime902')
e=dict(os.environ,PYTHONPATH=str(b/'runtime902')+':'+str(b/'final/tools'),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
r={}
for n,c in [('pytest',['/usr/bin/python3','-m','pytest','--version']),('numpy',['/usr/bin/python3','-c','import sys,numpy;print(sys.version);print(numpy.__version__)'])]:
 p=subprocess.run(c,env=e,capture_output=True,text=True);r[n]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
(b/'runtime_preflight.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit(0 if all(v['returncode']==0 for v in r.values())else 1)
