from pathlib import Path
import os,json,hashlib,sys
base=Path('/srv/opentallas-scratch/codex/s81-die-1552/source_3f21ae39b')
payload=Path(sys.argv[1]);out=Path(sys.argv[2]);ref=sys.argv[3]
assert not out.exists();out.mkdir()
for child in base.iterdir():(out/child.name).symlink_to(child)
def ensure(path):
 if path==out:return
 ensure(path.parent)
 if path.is_symlink():
  target=path.resolve();path.unlink();path.mkdir()
  for child in target.iterdir():(path/child.name).symlink_to(child)
 elif not path.exists():path.mkdir()
old=json.loads((base.parent/'coherent_manifest_3f21.json').read_text())
overrides={str(p.relative_to(payload)):p for p in payload.rglob('*') if p.is_file()}
actual={};total=0
for rel in sorted(set(old)|set(overrides)):
 target=out/rel;ensure(target.parent)
 if target.is_symlink() or target.exists():target.unlink()
 source=overrides.get(rel,base/rel)
 os.link(source.resolve(),target)
 actual[rel]=hashlib.sha256(target.read_bytes()).hexdigest();total+=target.stat().st_size
p=out/'SOURCE_SHA';p.unlink();p.write_text(ref+' coherent corrected diagnostic successor\n')
(out/'consumed_source_sha256.json').write_text(json.dumps(actual,indent=1)+'\n')
print(json.dumps(dict(source=ref,files=len(actual),bytes=total,root=str(out),overrides=sorted(overrides))))
