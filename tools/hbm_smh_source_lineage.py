#!/usr/bin/env python3
"""Check whether changed source modules can be referenced by the actual SM roots.

This is a conservative lexical closure after Verilog preprocessing: it includes
all generate branches and any occurrence of a known module name in a body.
It establishes source lineage, not a new numerical or formal correctness gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
ROOTS=['ot_hbm_accel_smh']+['ot_hbm_accel_smh_'+p for p in
    ('front_s','front_c','front_n','tile_e','tile_w','be_e','be_w')]


def git_bytes(commit,path):
    return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)


def module_bodies(text):
    text=re.sub(r'/\*.*?\*/',' ',text,flags=re.S)
    text=re.sub(r'//[^\n]*',' ',text)
    return {name:body for name,body in re.findall(r'\bmodule\s+(\w+)\b(.*?)\bendmodule\b',text,flags=re.S)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old',required=True)
    p.add_argument('--new',required=True)
    p.add_argument('--inventory',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    paths=json.loads(a.inventory.read_text())['paths']
    old={q:git_bytes(a.old,q) for q in paths}
    new={q:git_bytes(a.new,q) for q in paths}
    changed=[q for q in paths if old[q]!=new[q]]
    changed_modules=set()
    for q in changed:
        if q.endswith(('.sv','.v')):
            changed_modules.update(module_bodies(old[q].decode()))
            changed_modules.update(module_bodies(new[q].decode()))
    modes={}
    with tempfile.TemporaryDirectory(prefix='smh-source-lineage-') as td:
        temp=Path(td)
        for q,data in new.items():
            f=temp/q;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
        sources=[q for q in paths if q.endswith(('.sv','.v'))]
        for mode,defines in (('bench',['OT_SMH']),('physical',['SYNTHESIS'])):
            output=temp/(mode+'.sv')
            cmd=['iverilog','-E','-g2012']+['-D'+d for d in defines]+['-o',str(output)]+sources
            proc=subprocess.run(cmd,cwd=temp,capture_output=True,text=True)
            if proc.returncode:raise RuntimeError(proc.stderr)
            mods=module_bodies(output.read_text())
            edges={n:set(re.findall(r'\b\w+\b',body)) & (mods.keys()-{n}) for n,body in mods.items()}
            roots={}
            for root in ROOTS:
                pending=[root];seen=set()
                while pending:
                    n=pending.pop()
                    if n in seen:continue
                    seen.add(n);pending.extend(edges[n]-seen)
                roots[root]=dict(reachable_modules=sorted(seen),changed_modules_reachable=sorted(seen&changed_modules))
            modes[mode]=dict(defines=defines,preprocessed_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),roots=roots)
    non_rtl_changed=[q for q in changed if not q.endswith(('.sv','.v'))]
    passed=not non_rtl_changed and not any(row['changed_modules_reachable'] for m in modes.values() for row in m['roots'].values())
    record=dict(schema='opentallas.hbm.smh.source_module_lineage.v1',status='pass' if passed else 'fail',
        old_commit=subprocess.check_output(['git','rev-parse',a.old],cwd=ROOT,text=True).strip(),
        new_commit=subprocess.check_output(['git','rev-parse',a.new],cwd=ROOT,text=True).strip(),
        changed_files=changed,changed_modules=sorted(changed_modules),non_RTL_changes_unqualified=non_rtl_changed,modes=modes,
        source_hashes={q:dict(old=hashlib.sha256(old[q]).hexdigest(),new=hashlib.sha256(new[q]).hexdigest()) for q in paths},
        method='Conservative module-name reference closure after preprocessing, includes all parameter generate branches',
        scope='Source lineage only; numerical gate scope and real SRAM model/physical contracts remain separate',
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'],changed)
    return not passed


if __name__=='__main__':
    raise SystemExit(main())
