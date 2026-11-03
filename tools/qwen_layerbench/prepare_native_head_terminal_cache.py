#!/usr/bin/env python3
"""Copy an authenticated terminal pilot cache without PCH, archive or executable.
Run only after source/resource review, into a NEW independent cache directory.
"""
import argparse,hashlib,json,shlex,shutil
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pilot',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--controller-status',type=Path,required=True);p.add_argument('--controller-log',type=Path,required=True);a=p.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert 'OT_RUN_RC=0' in a.controller_status.read_text();log=a.controller_log.read_text();assert 'PASS_NATIVE_B_PILOT_GATE' in log and 'RAN' in log
assert sha(a.pilot/'SHA256SUMS')=='b9b915112ac5752994a458fdce56d2cc33d2f3363dc9fe5bde9c393a71ba84d6'
assert not a.cache.exists()and a.pilot.resolve() not in a.cache.resolve().parents
# Source hashes also guard terminal inputs, rather than trusting directory names.
for line in (a.pilot/'SHA256SUMS').read_text().splitlines():
 digest,name=line.split(None,1);name=name.lstrip('*');assert sha(a.pilot/name)==digest
assert (a.pilot/'contexts/tile0/baseline.log').read_text().find('PASS_NATIVE_B_PILOT tile=0 ')>=0
assert (a.pilot/'contexts/tile639/baseline.log').read_text().find('PASS_NATIVE_B_PILOT tile=639 ')>=0
obj=a.pilot/'obj';a.cache.mkdir(parents=True);files={};external={}
for f in sorted(obj.iterdir()):
 if f.is_file()and f.suffix in {'.cpp','.h','.d','.mk','.o'}:
  shutil.copyfile(f,a.cache/f.name);files[f.name]=sha(f);assert sha(a.cache/f.name)==files[f.name]
for f in sorted(a.cache.glob('*.d')):
 for dep in shlex.split(f.read_text().replace('\\\n',' ').split(':',1)[1]):
  path=Path(dep)
  if path.is_absolute():external[str(path)]=sha(path)
config=[x for x in files if x.endswith('.mk')];assert config
m=dict(terminal_status='PASS_OT_RUN_RC0',pilot_packet_sha256=sha(a.pilot/'SHA256SUMS'),source_pilot=str(a.pilot.resolve()),compiler_log_sha256=sha(a.pilot/'compiler_version.log'),files=files,external_dependencies=external,configuration_files=config,proof_hashes={str(x):sha(x)for x in [a.controller_status,a.controller_log]},excluded='PCH/archives/ELF; normal make may rebuild all native objects')
(a.cache/'cache_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(dict(copied_files=len(files),copied_bytes=sum((a.cache/f).stat().st_size for f in files),manifest_sha256=sha(a.cache/'cache_manifest.json'))))
