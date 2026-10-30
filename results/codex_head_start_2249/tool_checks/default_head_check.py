import importlib.util,json,sys,hashlib
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-head-start-2249')
w=Path('/srv/opentallas-scratch2/claude/wt/codex-head-start-2249');sys.path[:0]=[str(w/'tools/die_plan')]
import count_align_bind as CAB,clock_landings as CL,landing_place as LP,schema
def old(name):
    s=importlib.util.spec_from_file_location(name,r/(name+'_before.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
OC,OL,OP=old('count_align_bind'),old('clock_landings'),old('landing_place')
src=Path('/srv/opentallas-scratch2/claude/die-head-36/src25q/src25q2')
p=json.load(open(src/'source_plan.json'));t=json.load(open(src/'source_sidecar.json'))
assert all('landing_reader_start' not in ty.get('clock',{}) for ty in p['partition_types'].values())
old_ties=OC.strap_ties(t['count_aligned'],p);new_ties=CAB.strap_ties(t['count_aligned'],p)
assert old_ties==new_ties
old_manifest=OL.Landings(p,t).manifest();new_manifest=CL.Landings(p,t).manifest();assert old_manifest==new_manifest
P=schema.Plan(p,src/'source_plan.json');rows={}
for tn in p['partition_types']:
    a=OP.tcl(P,tn);b=LP.tcl(P,tn);assert a==b,tn
    rows[tn]=hashlib.sha256(a.encode()).hexdigest()
rep=dict(scope='actual HEAD src25q2 defaults: canonical strap values, initial landing manifest and per-type physical placement hook bytes',
         strap_types=len(new_ties['types']),strap_instances=len(new_ties['instances']),placement_types=len(rows),
         verdict='BYTE_IDENTICAL',placement_sha256=rows,enabled_reader_start=False)
(r/'default_head.json').write_text(json.dumps(rep,indent=1));print(json.dumps({k:v for k,v in rep.items() if k!='placement_sha256'}))
