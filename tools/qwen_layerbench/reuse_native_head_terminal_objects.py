#!/usr/bin/env python3
"""Conservatively copy dependency-identical terminal objects; normal make follows.

No hardlinks, timestamp overrides, PCH/archive/ELF reuse, or forced make stamps.
A cache must already be an immutable copy authenticated by cache_manifest.json.
"""
import argparse,hashlib,json,shlex,shutil
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--obj',type=Path,required=True);p.add_argument('--compiler-log',type=Path,required=True);a=p.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((a.cache/'cache_manifest.json').read_text());assert m['terminal_status']=='PASS_OT_RUN_RC0' and m['pilot_packet_sha256']=='b9b915112ac5752994a458fdce56d2cc33d2f3363dc9fe5bde9c393a71ba84d6'
assert sha(a.compiler_log)==m['compiler_log_sha256']
for name,digest in m['files'].items():
 path=Path(name);assert not path.is_absolute()and '..' not in path.parts
 assert sha(a.cache/path)==digest,('CACHE_HASH',name)
# These encode flags, include directories, generated group inventory and build ABI.
# Any difference declines reuse entirely, preserving the ordinary build fallback.
configs=m['configuration_files'];compatible=all((a.obj/f).is_file()and sha(a.obj/f)==m['files'][f]for f in configs)
reused=[];declined=[]
for name,digest in m['files'].items():
 if not name.endswith('.o'):continue
 dep=name[:-2]+'.d';ok=compatible and dep in m['files']
 if ok:
  text=(a.cache/dep).read_text().replace('\\\n',' ');dependencies=shlex.split(text.split(':',1)[1]);assert dependencies
  for f in dependencies:
   path=Path(f)
   # External toolchain/runtime inputs have separately pinned hashes.
   if path.is_absolute():
    ok=ok and str(path)in m['external_dependencies'] and path.is_file() and sha(path)==m['external_dependencies'].get(str(path))
   else:
    ok=ok and '..' not in path.parts and f in m['files'] and (a.obj/path).is_file() and sha(a.obj/path)==m['files'].get(f)
   if not ok:break
 if ok:
  shutil.copyfile(a.cache/name,a.obj/name)
  shutil.copyfile(a.cache/dep,a.obj/dep)
  reused.append(name)
 else:declined.append(name)
r=dict(reused_objects=reused,declined_objects=declined,normal_make_required=True,note='ordinary copy natural timestamps; existing make/PCH/header dependency rules may rebuild any copied object')
(a.obj/'cache_reuse_receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
