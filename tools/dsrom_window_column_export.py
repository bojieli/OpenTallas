#!/usr/bin/env python3
"""Export routed WINDOW columns under their fixed-width parent macro names."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--orfs-dir',type=Path,required=True)
    p.add_argument('--width',type=int,choices=(128,256),required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--reuse-export',action='store_true')
    a=p.parse_args()
    name=f'ot_dsrom_window_column_{a.width}'
    out=a.out.resolve()
    if not a.reuse_export:
        subprocess.run([sys.executable,str(ROOT/'tools/hbm_fmax_attn_abstract.py'),
                        '--orfs-dir',str(a.orfs_dir.resolve()),'--name',name,
                        '--out',str(out)],check=True)
    record=json.loads((out/'abstract.json').read_text())
    record['physical_top']='ot_dsrom_window_column'
    record['physical_parameter']={'WIDTH':a.width}
    record['parent_cell']=name
    record['rename']='Only LEF MACRO/END and Liberty cell names; all pins/arcs/geometry unchanged.'
    record['before_rename_sha256']=record['files']
    for suffix in ('.lef','_ss.lib','_ff.lib'):
        f=out/(name+suffix)
        s=f.read_text()
        if suffix=='.lef':
            s,n=re.subn(r'(?m)^(MACRO|END) ot_dsrom_window_column\s*$',lambda m:m.group(1)+' '+name,s)
            if n!=2:raise RuntimeError(f'unexpected LEF cell count: {n}')
        else:
            s,n=re.subn(r'(cell\s*\(\s*"?)ot_dsrom_window_column("?\s*\))',lambda m:m.group(1)+name+m.group(2),s)
            if n!=1:raise RuntimeError(f'unexpected Liberty cell count: {n}')
        temporary=f.with_name(f.name+'.renamed')
        temporary.write_text(s)
        temporary.replace(f)
    record['files']={f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                     for f in sorted(out.iterdir()) if f.suffix in ('.lef','.lib')}
    (out/'abstract.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':main()
