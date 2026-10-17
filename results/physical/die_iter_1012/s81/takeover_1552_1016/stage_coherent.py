from pathlib import Path
import os,json,hashlib
root=Path('/srv/opentallas-scratch/codex/s81-die-1552');base=root/'source_2305beec7';out=root/'source_3f21ae39b'
assert not out.exists();out.mkdir()
for child in base.iterdir():(out/child.name).symlink_to(child)
def ensure(path):
 if path==out:return
 ensure(path.parent)
 if path.is_symlink():
  target=path.resolve();path.unlink();path.mkdir()
  for child in target.iterdir():(path/child.name).symlink_to(child)
 elif not path.exists():path.mkdir()
manifest=json.loads((root/'gen_closure_manifest.json').read_text());actual={}
for rel in manifest:
 target=out/rel;ensure(target.parent)
 if target.is_symlink():target.unlink()
 assert not target.exists(),target
 source=root/'generator_3f21ae39b.py' if rel=='tools/dsrom_s81_fulldie.py' else base/rel
 os.link(source.resolve(),target)
 actual[rel]=hashlib.sha256(target.read_bytes()).hexdigest()
p=out/'SOURCE_SHA';p.unlink();p.write_text('3f21ae39b coherent compact dependency closure; immutable base79ab/guard/status/contacts plus current native capture views\n')
(root/'coherent_manifest_3f21.json').write_text(json.dumps(actual,indent=1)+'\n')
print('MATERIALIZED_COMPACT_CLOSURE',len(actual),'hardlinked files',sum((out/p).stat().st_size for p in actual),'bytes')
