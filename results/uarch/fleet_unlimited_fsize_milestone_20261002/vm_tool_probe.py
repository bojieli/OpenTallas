"""Read-only installed native tool fingerprints; no compiler invocation on inputs."""
import json,subprocess,hashlib,os
from pathlib import Path
out={}
for name,path in [('compiler','/usr/bin/g++'),('make','/usr/bin/make'),('prlimit','/usr/bin/prlimit'),('linker','/usr/bin/ld')]:
 p=Path(path);r=subprocess.run([path,'--version'],text=True,capture_output=True,timeout=5)
 out[name]={'path':path,'resolved':str(p.resolve()),'version':r.stdout.splitlines()[0]if r.stdout else r.stderr.splitlines()[0],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
c=subprocess.check_output(['/usr/bin/g++','-print-prog-name=cc1plus'],text=True).strip();p=Path(c);out['cc1plus']={'path':c,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for name in ['libstdc++.so','libgcc_s.so']:
 c=subprocess.check_output(['/usr/bin/g++','-print-file-name='+name],text=True).strip();p=Path(c)
 out[name]={'path':c,'resolved':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()if p.is_file()else None}
out['host_machine']=os.uname().machine
print(json.dumps(out))
