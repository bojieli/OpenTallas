#!/usr/bin/env python3
"""Prepare a die-owner review candidate from full current-parent mapped cell receipts. No canonical writes."""
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);out=Path(sys.argv[2]);assert out.resolve()!=p.resolve()
d=json.load(open(p));updates=[]
for file in map(Path,sys.argv[3:]):
 r=json.load(open(file));assert not r['unmapped_cells'],file
 targets=[(n,t) for n,t in d['partition_types'].items() if t.get('module')==r['module']];assert len(targets)==1,(r['module'],targets)
 n,t=targets[0];old=t.get('cells');new=r['mapped_std_cells'];assert isinstance(new,int) and new>0
 t['cells']=new
 t['note']=t.get('note','')+f'; current full bound parent mapped standard cells {new} (including all landed/monitor/reset/FT logic), source graph {r["source_graph_commit"]}; measured receipt {file.name}; physical SRAM macro cells excluded; no extra landing estimate'
 updates.append(dict(type=n,old_explicit_cells=old,measured_complete_cells=new,cap=r['cap_verdict'],macro_instances=r['macro_instances'],module=r['module']))
out.write_text(json.dumps(d,indent=1)+'\n');print(json.dumps(dict(scope='DIE OWNER REVIEW CANDIDATE, no canonical plan adoption',updates=updates)))
