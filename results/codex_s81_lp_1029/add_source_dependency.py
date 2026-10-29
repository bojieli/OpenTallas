#!/usr/bin/env python3
"""Complete a selected parent source list with an exact missing canonical file; reject module overrides."""
import hashlib,json,re,shutil,sys
from pathlib import Path
src,dst,root=map(Path,sys.argv[1:4]);rel=sys.argv[4];f=root/rel;assert not dst.exists(),dst;assert f.is_file(),f
mod=re.compile(r'(?m)^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+([A-Za-z_][A-Za-z_0-9$]*)')
def modules(text):return {m.group(1) for m in mod.finditer(re.sub(r'//[^\n]*','',text))}
known=set().union(*(modules(p.read_text()) for p in (src/'rtl').iterdir()));added=modules(f.read_text());assert added and not (known&added),('Source would override selected module',known&added)
shutil.copytree(src/'rtl',dst/'rtl');d=json.load(open(src/'sources.json'));fs=(src/'sources.f').read_text().splitlines();q=dst/'rtl'/('extra_'+f.name);shutil.copyfile(f,q);fs.append('/out/rtl/'+q.name)
d['files'].append(dict(path=str(f),snapshot=str(q.relative_to(dst)),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size));d.setdefault('restored_source_dependencies',[]).append(dict(file=rel,modules=sorted(added),cause='Actual current Yosys hierarchy missing module; complete explicit canonical implementation source, no module override or RTL edits'))
(dst/'sources.json').write_text(json.dumps(d,indent=1)+'\n');(dst/'sources.f').write_text('\n'.join(fs)+'\n');print(json.dumps(d['restored_source_dependencies'][-1]))
