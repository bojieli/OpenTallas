#!/usr/bin/env python3
"""Combine native bound file lists without masking conflicting shared module definitions."""
import argparse,hashlib,json,re
from pathlib import Path

def stage(lists,top,out,models=()):
    out.mkdir(exist_ok=False,parents=True);seen={};modules={};files=[];dups=[];conflicts=[];omitted=[]
    for fl in lists:
        for raw in fl.read_text().splitlines():
            raw=raw.strip()
            if not raw or raw.startswith('#'):continue
            if raw.startswith(('+','-')):raise ValueError(f'unsupported file-list directive: {raw}')
            p=Path(raw);p=p if p.is_absolute() else fl.parent/p
            p=p.resolve();data=p.read_bytes();sha=hashlib.sha256(data).hexdigest()
            if sha in seen:dups.append(dict(file=str(p),same_as=str(seen[sha])));continue
            defs={m.decode() for m in re.findall(rb'^\s*(?:module|primitive)\s+(\w+)',data,re.M)}
            if defs and defs<=set(models) and re.search(rb'\(\*\s*blackbox\s*\*\)',data):
                # Only explicit declaration-only physical abstracts may yield to functional models.
                clean=re.sub(rb'//[^\n]*',b'',data)
                body=re.sub(rb'module\b[\s\S]*?\);',b'',clean)
                body=re.sub(rb'\(\*[\s\S]*?\*\)|`timescale[^\n]*|endmodule|\s',b'',body)
                if body:raise ValueError(f'blackbox contains behavior: {p}')
                omitted.append(dict(file=str(p),modules=sorted(defs)));continue
            seen[sha]=p;files.append(p)
            for mod in re.findall(rb'^\s*(?:module|primitive)\s+(\w+)',data,re.M):
                n=mod.decode()
                if n in modules:conflicts.append(dict(module=n,first=str(modules[n]),second=str(p)))
                else:modules[n]=p
    report=dict(files=len(files),modules=len(modules),duplicates=dups,conflicts=conflicts,physical_blackboxes_replaced_by_models=omitted,
                scope='Source staging only. Distinct definitions of one shared module are never silently selected.')
    (out/'sources.json').write_text(json.dumps(report,indent=1)+'\n')
    for row in omitted:
        if not set(row['modules'])<=set(modules):raise ValueError('missing explicit functional model')
    if conflicts:raise ValueError(f'{len(conflicts)} conflicting shared module definitions; see sources.json')
    (out/'files.f').write_text('\n'.join(str(p) for p in files+[top.resolve()])+'\n')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--files',type=Path,action='append',required=True);p.add_argument('--model-module',action='append',default=[]);p.add_argument('--top',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=stage(a.files,a.top,a.out,a.model_module);print('PAIR_SOURCES_STAGED',r['files'],r['modules'])
