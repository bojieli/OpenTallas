#!/usr/bin/env python3
"""Read-only verify real make/compiler/linker cgroups, no process mutation."""
from pathlib import Path
import json,time,datetime
b=Path.cwd();target=593819;seen={}
with (b/'build_process_membership.jsonl').open('x',buffering=1) as f:
 while Path('/proc',str(target)).exists():
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    cwd=(p/'cwd').resolve()
    if cwd not in [b,b/'obj']:continue
    argv=(p/'cmdline').read_bytes().split(b'\0');name=Path(argv[0].decode()).name
    if name not in ['make','cc1plus','collect2','ld','ld.bfd','x86_64-linux-gnu-ld','ar']:continue
    if name in seen:continue
    cg=(p/'cgroup').read_text();parent=[l for l in (p/'status').read_text().splitlines() if l.startswith('PPid:')]
    r=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),role=name,pid=int(p.name),PPid=parent,cwd=str(cwd),argv=[x.decode() for x in argv if x],proc_cgroup=cg)
    seen[name]=r;f.write(json.dumps(r)+'\n')
   except (OSError,ValueError):pass
  time.sleep(.5)
(b/'build_process_membership_summary.json').write_text(json.dumps(dict(scope='Actual sampled native build process memberships; missing roles are not inferred',observed=seen),indent=2)+'\n')
