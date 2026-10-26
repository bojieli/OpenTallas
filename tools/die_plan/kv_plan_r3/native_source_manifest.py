#!/usr/bin/env python3
"""Resolve the actual bound leaf library using canonical bind-verify preferences."""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import bind_elab as E
p=argparse.ArgumentParser(description=__doc__);p.add_argument('recipe');p.add_argument('bound');p.add_argument('--out',required=True);a=p.parse_args();r=json.load(open(a.recipe));base=Path(a.recipe).resolve().parent/r['base'];base=base.resolve();O=Path(a.bound);rep=json.load(open(O/'bind_report.json'));files=rep['files'];cells=[f for f in files if Path(f).name=='bind_cells.sv'];idx=E.module_index(r.get('rtl_roots',['rtl']),r.get('files',[])+rep.get('extra_lib',[])+cells,str(base));prefer=[str(base/f) if not Path(f).is_absolute() else f for f in r.get('prefer',[])]+rep.get('extra_lib',[]);leaf=set()
for f in files:
 if f.endswith('_bound_top.sv') or f in cells:continue
 t=Path(f).read_text(errors='replace');mods=set(re.findall(r'^module\s+(\w+)',t,re.M));leaf.update(set(re.findall(r'^\s+(\w+)\s+(?:#\(.*?\)\s+)?u_\w+\s*\(',t,re.M))-mods)
selected={};missing=[];todo=sorted(leaf)
while todo:
 m=todo.pop()
 if m in selected or m in missing:continue
 f,_=E.pick(idx,m,prefer)
 if f is None:missing.append(m);continue
 selected[m]=str(f);todo.extend(sorted(E.instantiated(E.module_body(f,m),idx)))
# Generated infrastructure lives in bind.f or explicit kept primitive, not indexed leaf roots.
generated=set()
for f in files:
 if Path(f).is_file():generated.update(re.findall(r'^module\s+(\w+)',Path(f).read_text(errors='replace'),re.M))
missing=sorted(set(missing)-generated)
ordered=[]
for f in [selected[m] for m in sorted(selected)]+files:
 if f not in ordered:ordered.append(f)
out=dict(schema='opentallas.bound_native_source_selection.v1',scope='canonical bind_verify module_index/pick with recipe prefer + actual extra_lib',recipe=str(Path(a.recipe).resolve()),bound=str(O.resolve()),module_files=selected,files=ordered,include_dirs=sorted({str(Path(f).parent) for f in ordered}),missing=missing)
Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(modules=len(selected),files=len(ordered),include_dirs=len(out['include_dirs']),missing=missing)));assert not missing
