from pathlib import Path
import json,hashlib,shutil,re
R=Path('/srv/opentallas-scratch/claude/codex-tok-head-b-connected-2100')
OLD=Path('/srv/opentallas-scratch/claude/codex-tok-s81-head-2000')
SRC=Path('/srv/opentallas-scratch/claude/stw-s81-head-h10/h10m')
A=Path('/srv/opentallas-scratch/claude/codex-s81-head-a7-portable')
R.mkdir(parents=True,exist_ok=True)
lines=(OLD/'b_resolve/files_b_full.f').read_text().splitlines()
incs=[Path(x[len('+incdir+'):]) for x in lines if x.startswith('+incdir+')]
files=[Path(x) for x in lines if x and not x.startswith('+')]
files += [SRC/'bind/bind/die.v']
for d in incs:
 for pat in ['*.vh','*.svh','*.h','*.inc','*.sv','*.v']:
  files.extend(d.glob(pat))
def mapped(p):
 return R/'inputs'/str(p).lstrip('/')
for d in incs:mapped(d).mkdir(parents=True,exist_ok=True)
manifest=[]
for f in sorted(set(files)):
 if not f.is_file():raise RuntimeError('missing real input '+str(f))
 dst=mapped(f);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
 manifest.append(dict(original=str(f),staged=str(dst.relative_to(R)),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
new=[]
for x in lines:
 if x.startswith('+incdir+'):
  new.append('+incdir+'+str(mapped(Path(x[len('+incdir+'):]))))
 elif x:new.append(str(mapped(Path(x))))
(R/'files_b_full.f').write_text('\n'.join(new)+'\n')
(R/'bind').mkdir(exist_ok=True)
for name in ['die.v','port_bind.json']:shutil.copy2(SRC/'bind/bind'/name,R/'bind'/name)
shutil.copytree(OLD/'tools',R/'tools',dirs_exist_ok=True)
(R/'img').mkdir(exist_ok=True)
for name in ['golden.json','xa.hex','xb.hex','xb_beats.hex']:
 if (A/'img'/name).exists():shutil.copy2(A/'img'/name,R/'img'/name)
(R/'out').mkdir(exist_ok=True)
for name in ['a.json','rec.hex']:
 shutil.copy2(A/'out_compat'/name,R/'out'/name)
for name in ['gold','a_mut']:
 shutil.copytree(A/'out_compat'/name,R/'out'/name,dirs_exist_ok=True)
shutil.copy2(OLD/'b_resolve/resolve_b.json',R/'resolve_b.json')
(R/'source_identity.json').write_text(json.dumps(dict(source='materialized authoritative H10 strict bind; numerical bundles replaced only by existing CUT-A-verified face replay',full_token=False,files=manifest),indent=1)+'\n')
print('self-contained B staged',len(manifest),'source/header files')
