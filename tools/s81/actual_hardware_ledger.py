#!/usr/bin/env python3
"""Fail-closed inventory of required S81 operations against actual RTL and emitted die.

An alias/partial graph is not a whole die. This gate requires the emitted die,
canonical shape receipt, and successful die_port_bind record pinned to that die.
The ledger enumerates source ports even when adoption or native evidence is absent.
It does not infer functionality, static semantics or physical qualification from a
module name, source parser, declaration, passing component test, or CLOSED status.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as bind

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(requirements, manifest, die=None, bind_record=None, shape=None):
    req=json.loads(requirements.read_text())
    files,defs,_=bind.load_manifest(str(manifest))
    defines={v.split('=',1)[0]:v.partition('=')[2] for v in defs}
    # Explicit requirement paths expose candidates omitted by the build manifest.
    paths=list(dict.fromkeys(files+[x['source'] for x in req['operations'] if x.get('source')]))
    idx={}
    for name in paths:
        p=Path(name);p=p if p.is_absolute() else ROOT/p
        if p.exists():
            for mod in bind.parse_modules(bind.preprocess(p.read_text(),defines),str(p)):
                idx[mod.name]=mod
    emitted=Counter()
    if die and die.exists():
        emitted.update(m for m,_,_,_ in bind.parse_die(die)[3] if m!='__assign__')
    reasons=[]
    if not die or not die.exists(): reasons.append('missing_emitted_canonical_die')
    shape_record=json.loads(shape.read_text()) if shape and shape.exists() else {}
    shape_data=shape_record.get('observed',{})
    if not (shape_record.get('schema')=='opentallas.s81.observed-shape.v1' and shape_record.get('status')=='OBSERVED_SOURCE_AND_CONSTRUCTION_SHAPE' and die and die.exists() and shape_record.get('die_sha256')==sha(die)):
        reasons.append('canonical_shape_observation_missing_invalid_or_not_die_pinned')
    for role in ('die','plan','stage_map','sequencer_source'):
        ev=shape_record.get('evidence',{}).get(role,{})
        ep=Path(ev.get('path','__missing__'))
        if not ep.is_file() or sha(ep)!=ev.get('sha256'):
            reasons.append('canonical_shape_evidence_missing_or_stale:'+role)
    for k,v in req['canonical'].items():
        if shape_data.get(k)!=v:reasons.append('canonical_'+k+'_unproven')
    # A gate record must hash the exact generated netlist; a generic PASS is weak evidence.
    br=json.loads(bind_record.read_text()) if bind_record and bind_record.exists() else {}
    if not (die and die.exists() and br.get('verdict')=='PASS' and br.get('die_sha256')==sha(die)):
        reasons.append('whole_die_port_gate_missing_or_not_pinned_pass')
    rows=[]
    for item in req['operations']:
        row=dict(item);name=item.get('module');mod=idx.get(name);fail=[]
        if not mod:fail.append('actual_source_module_missing')
        else:
            row['source_sha256']=sha(Path(mod.path))
            row['source']=str(Path(mod.path).relative_to(ROOT))
            row['ports']={n:{'direction':d[0],'bits':mod.width(n,mod.env())}for n,d in mod.ports.items()}
            if mod.port_parse_errors:fail.append('source_header_parse_error')
            if any(p['bits'] is None for p in row['ports'].values()):fail.append('unevaluated_port_width')
            if not any(Path(f).resolve()==Path(mod.path).resolve() for f in files):fail.append('source_not_selected_in_manifest')
        for pn,width in item.get('required_ports',{}).items():
            actual=row.get('ports',{}).get(pn,{}).get('bits')
            if actual!=width:fail.append('required_port_width:'+pn+':'+str(actual)+'!='+str(width))
        for d in item.get('required_defines',[]):
            if d not in defines:fail.append('missing_build_define:'+d)
        row['emitted_die_instances']=emitted[name]
        if not emitted[name]:fail.append('required_master_not_in_emitted_die')
        if 'static_semantics_evidence' in item:
            p=ROOT/(item.get('static_semantics_evidence') or '__missing__')
            if not p.is_file():fail.append('static_semantics_evidence_missing')
        if 'native_clock_delivery_evidence' in item:
            p=ROOT/(item.get('native_clock_delivery_evidence') or '__missing__')
            if not p.is_file():fail.append('native_clock_delivery_evidence_missing')
        # Source-level evidence may never automatically qualify a native implementation.
        row['native_qualified']=False
        row['binding_findings']=fail
        row['verdict']='FAIL' if fail else 'PORTS_BOUND_PHYSICAL_QUALIFICATION_UNPROVEN'
        rows.append(row)
    reasons += ['operation:'+r['operation'] for r in rows if r['binding_findings']]
    return {'schema':'opentallas.s81.actual-hardware-ledger.v1','verdict':'FAIL' if reasons else 'PORTS_BOUND_NATIVE_AUDIT_REQUIRED',
            'release_qualified':False,'scope':req['scope'],'requirements_sha256':sha(requirements),
            'manifest_sha256':sha(manifest),'die_sha256':sha(die) if die and die.exists() else None,
            'canonical_required':req['canonical'],'canonical_observed':shape_data,
            'failures':reasons,'operations':rows}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--requirements',type=Path,default=ROOT/'physical/s81_die_rtl/required_operations.json')
    ap.add_argument('--manifest',type=Path,default=ROOT/'physical/s81_die_rtl/layer1.f')
    ap.add_argument('--die',type=Path);ap.add_argument('--port-bind',type=Path);ap.add_argument('--shape',type=Path)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    r=audit(a.requirements,a.manifest,a.die,a.port_bind,a.shape)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    for x in r['operations']:print(x['operation'],x['module'],len(x.get('ports',{})),'ports',','.join(x['binding_findings']) or x['verdict'])
    print(r['verdict'],len(r['failures']),'missing requirements')
    return 1 if r['failures'] else 0
if __name__=='__main__':raise SystemExit(main())
