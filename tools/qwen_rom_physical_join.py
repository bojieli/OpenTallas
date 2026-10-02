#!/usr/bin/env python3
"""Join retained Qwen physical records to the actual connected runtime pins.

This is verification preparation, not physical closure. Historical defaults are
read from each record's commit and checked against the record's source hash.
No P&R command is launched, and failed records remain unchanged.
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def defaults(text, top):
    header = re.search(r'\bmodule\s+' + re.escape(top) + r'\s*#\s*\((.*?)\)\s*\(', text, re.S)
    if not header:
        raise ValueError('Cannot bind module parameter header')
    return {name:int(value) for name,value in re.findall(r'parameter\s+integer\s+(\w+)\s*=\s*(\d+)',header[1])}


def flags(values):
    return {m[1]:int(m[2]) for value in values if (m:=re.fullmatch(r'-G(\w+)=(\d+)',value))}


def join_record(record, runtime, root=ROOT):
    d=record['design'];top=d['top']; commit=record['git']['commit']
    sources={s['path']:s['sha256'] for s in d['sources']}
    historical={}; current={}; connected={}
    module_text=None
    for path,pin in sources.items():
        p=root/path
        current[path]=p.is_file() and digest(p.read_bytes())==pin
        connected[path]=runtime.get('source_sha256_at_capture',{}).get(path)==pin
        proc=subprocess.run(['git','show',f'{commit}:{path}'],cwd=root,capture_output=True)
        historical[path]=proc.returncode==0 and digest(proc.stdout)==pin
        if historical[path] and re.search(rb'\bmodule\s+'+top.encode()+rb'\b',proc.stdout):
            module_text=proc.stdout.decode()
    effective=defaults(module_text,top) if module_text else {}
    overrides=d.get('parameters',{})
    unknown=sorted(set(overrides)-set(effective))
    effective.update(overrides)
    blocks=runtime.get('params',{})
    runtime_defaults={}
    if 'tile' in top:
        item=runtime.get('files',{}).get('source/rtl/hdc/ot_qwen_rom_tile.sv')
        if item:
            raw=base64.b64decode(item['base64'],validate=True)
            if digest(raw)!=runtime['source_sha256_at_capture']['rtl/hdc/ot_qwen_rom_tile.sv']:
                raise ValueError('Runtime source snapshot hash mismatch')
            runtime_defaults=defaults(raw.decode(),'ot_qwen_rom_tile_logic')
    wanted=dict(runtime_defaults,**flags(blocks.get('tile' if 'tile' in top else 'die',[])))
    if 'G' in wanted:wanted['GT']=wanted.pop('G')
    unjoined_parameters=sorted(set(effective)-set(wanted))
    parameter_differences={k:dict(physical=effective[k],runtime=wanted[k]) for k in sorted(effective.keys() & wanted.keys()) if effective[k]!=wanted[k]}
    reasons=[]
    if record.get('status')!='pass' or d.get('closed') is not True:reasons.append('raw physical verdict is not closed PASS')
    if record.get('corner',{}).get('name')!='SS':reasons.append('cell corner is not SS; ORFS WC label does not relabel TT cells')
    if d.get('clock_uncertainty_ns')!=0.060 or d.get('clock_uncertainty_hold_ns')!=0.025:reasons.append('uncertainty policy mismatch')
    if abs(record.get('target_clock_period_ns',0)-1/1.2)>0.000001:reasons.append('not the 1.2 GHz target')
    if parameter_differences:reasons.append('parameters differ from connected runtime (KV-local address defaults are dormant in host-global-KV mode)')
    if unjoined_parameters:reasons.append('physical arithmetic/top parameters have no connected-runtime parameter counterpart')
    if unknown:reasons.append('unknown/unbound physical parameter overrides')
    if not all(historical.values()):reasons.append('historical source pin recovery incomplete')
    if not all(current.values()):reasons.append('historical sources differ from intake source')
    logic=[p for p in sources if p.startswith('rtl/')]
    if not logic or not all(connected[p] for p in logic):reasons.append('RTL sources differ from connected runtime')
    # Even a local matched SS PASS lacks contextual FF, hub, macro and die proof.
    reasons.append('contextual FF hold, macro clk-to-q, hub routing and actual-element die power join required')
    return dict(top=top,commit=commit,status=record.get('status'),closed=d.get('closed'),
                corner=record.get('corner',{}).get('name'),period_ns=record.get('target_clock_period_ns'),
                setup_uncertainty_ns=d.get('clock_uncertainty_ns'),hold_uncertainty_ns=d.get('clock_uncertainty_hold_ns'),
                effective_parameters=effective,unjoined_parameters=unjoined_parameters,runtime_effective_parameters=wanted,parameter_differences=parameter_differences,unknown_overrides=unknown,
                historical_source_checks=historical,current_source_checks=current,connected_runtime_source_checks=connected,
                error=record.get('error'),product_closure=False,blockers=reasons)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package',type=Path,required=True)
    ap.add_argument('--verification',type=Path,required=True)
    ap.add_argument('--record',type=Path,action='append',required=True)
    ap.add_argument('--result',type=Path,required=True)
    a=ap.parse_args()
    if a.result.exists():ap.error('Refusing to overwrite evidence')
    p=json.loads(a.package.read_text());v=json.loads(a.verification.read_text())
    if v['package_sha256']!=digest(a.package.read_bytes()):ap.error('Runtime package/verification mismatch')
    runtime=dict(p,params=v['params'])
    rows={str(path.resolve().relative_to(ROOT)):dict(record_sha256=digest(path.read_bytes()),**join_record(json.loads(path.read_text()),runtime)) for path in a.record}
    result=dict(schema='opentallas.qwen-rom-physical-source-join.v1',status='blocked',adoption=False,
                verifier_sha256=digest(Path(__file__).read_bytes()),runtime_package_sha256=digest(a.package.read_bytes()),
                records=rows,claim_boundary='Source/parameter join and preserved failures only; no physical or rate qualification.')
    a.result.parent.mkdir(parents=True,exist_ok=True)
    with a.result.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:dict(status=r['status'],differences=r['parameter_differences'],blockers=r['blockers']) for k,r in rows.items()},indent=2))


if __name__=='__main__':main()
