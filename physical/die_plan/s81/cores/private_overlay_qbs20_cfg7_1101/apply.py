#!/usr/bin/env python3
"""Apply only the pinned physical QBS20/CFG7 view overlay to an owned source root."""
import argparse,hashlib,json,pathlib,shutil
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--backup',required=True);a.add_argument('--receipt',required=True);o=a.parse_args()
root=pathlib.Path(o.root).resolve();here=pathlib.Path(__file__).resolve().parent;backup=pathlib.Path(o.backup)
m=json.loads((here/'manifest.json').read_text())
for rel,h in m['files'].items():
 assert digest(here/rel)==h, 'pinned overlay hash mismatch:'+rel
plan=root/'physical/die_plan/s81/plan_h2_2249.json'
assert digest(plan)==m['plan_sha256'], 'parent plan changed'
p=json.loads(plan.read_text());t=p['partition_types'][m['parent_type']];hits={}
for c in t['hard_cores']:
 mod=c['module']
 if mod not in m['modules']:continue
 dest=(root/c['lib']).parent
 assert dest.resolve().is_relative_to(root),'overlay cannot write outside owned root'
 if str(dest) in hits:continue
 spec=m['modules'][mod];hits[str(dest)]=spec
 for name in spec['overlay_files']:
  src=here/mod/name;dst=dest/name
  old=backup/dst.relative_to(root)
  if dst.exists() and not old.exists():old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,old)
  if dst.is_symlink():dst.unlink()
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
lef_hits={}
for c in t['hard_cores']:
 mod=c['module']
 if mod not in m['modules']:continue
 src=here/mod/m['modules'][mod]['lef_file'];dst=root/c['lef']
 assert dst.resolve().is_relative_to(root),'LEF overlay outside owned root'
 if str(dst) in lef_hits:continue
 old=backup/dst.relative_to(root)
 if dst.exists() and not old.exists():old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,old)
 if dst.is_symlink():dst.unlink()
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 lef_hits[str(dst)]=digest(dst)
assert len(hits)==2 and len(lef_hits)==2,'expected two exact library and LEF view directories'
pathlib.Path(o.receipt).write_text(json.dumps(dict(manifest_sha256=digest(here/'manifest.json'),plan_sha256=digest(plan),destinations=hits,lef_files=lef_hits),indent=2)+'\n')
print('APPLIED pinned QBS20/CFG7 actual-view overlay',len(hits),'directories; parent plan unchanged')
