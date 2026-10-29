#!/usr/bin/env python3
"""Restore one exact named physical macro dependency, never replace a different macro kind."""
import hashlib,json,shutil,sys
from pathlib import Path
src,dst,root=map(Path,sys.argv[1:4]);name=sys.argv[4];assert not dst.exists(),dst
views=[root/p/name for p in ('physical/asap7_memory_macros_v2','physical/asap7_memory_macros') if (root/p/name).is_dir()];assert len(views)==1,(name,views)
v=views[0];bb=v/(name+'_bb.v');lef=v/(name+'.lef');lib=v/(name+'_tt.lib');assert all(q.is_file() for q in (bb,lef,lib)),v
shutil.copytree(src/'rtl',dst/'rtl');d=json.load(open(src/'sources.json'));fs=(src/'sources.f').read_text().splitlines()
assert name not in d['macros'],name
f=dst/'rtl'/('extra_'+name+'_bb.v');shutil.copyfile(bb,f);fs.append('/out/rtl/'+f.name)
d['files'].append(dict(path=str(bb),snapshot=str(f.relative_to(dst)),sha256=hashlib.sha256(bb.read_bytes()).hexdigest(),bytes=bb.stat().st_size))
d['macros'][name]=dict(source=str(bb),lef=str(lef),liberty_tt=str(lib))
d.setdefault('restored_physical_dependencies',[]).append(dict(module=name,view=str(v),cause='Actual current Yosys -hierarchy -check missing module; restore exact named native physical interface, no macro replacement',interface_sha256=hashlib.sha256(bb.read_bytes()).hexdigest()))
(dst/'sources.json').write_text(json.dumps(d,indent=1)+'\n');(dst/'sources.f').write_text('\n'.join(fs)+'\n');print(json.dumps(d['restored_physical_dependencies'][-1]))
