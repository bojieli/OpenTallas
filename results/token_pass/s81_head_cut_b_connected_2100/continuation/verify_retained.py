from pathlib import Path
import hashlib,json,os
R=Path.cwd()
m=json.loads((R/'retained_build_manifest.json').read_text())
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
for rel,entry in m['files'].items():
 p=R/rel
 assert p.stat().st_size==entry['bytes'] and digest(p)==entry['sha256'],rel
for path,entry in m['tools'].items():assert digest(Path(path))==entry['sha256'],path
source=json.loads((R/'source_identity.json').read_text())
for entry in source['files']:assert digest(R/entry['staged'])==entry['sha256'],entry['staged']
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  exe=(proc/'exe').resolve().name
  if exe not in ('make','g++','cc1plus','verilator_bin'):continue
  cwd=(proc/'cwd').resolve()
  assert R not in cwd.parents and cwd!=R,('duplicate writer',proc.name,exe,str(cwd))
 except (FileNotFoundError,PermissionError,ProcessLookupError):continue
print('PASS retained integrity:',len(m['files']),'generated/build files,',m['objects'],'ELF-checked retained objects,',len(source['files']),'staged sources, exact tool hashes, no duplicate writer')
