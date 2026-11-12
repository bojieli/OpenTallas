#!/usr/bin/env python3
"""Collect actual BF replay gates and issue an opt-in source-bound measurement."""
from pathlib import Path
import collections
import hashlib
import json
import re
import sys


def collect(run,extra_positive=()):
    run=Path(run);manifest=json.loads((run/'manifest.json').read_text());source=Path(manifest['source'])
    if any(not re.fullmatch(r'[a-z0-9_]+',name) for name in extra_positive):raise ValueError('invalid extra replay name')
    positive_names=('full','tail','router',*extra_positive)
    checks={}
    shapes={}
    for name in (*positive_names,'descriptor_fault','payload_fault'):
        path=run/'replay'/name/'check.json'
        checks[name]=json.loads(path.read_text()) if path.exists() else dict(pass_=False,errors=['missing completed checker'])
        if name in positive_names:
            meta=json.loads((run/'replay'/name/'meta.json').read_text())
            if meta['shape'].split('|')[0]!=manifest['master']+'_'+manifest['variant']:
                raise ValueError('replay is not the selected source frame class')
            shapes[name]={k:meta[k] for k in ('op','nrows','seg','nseg','field_phase','die_frame')}
    positives=all(checks[n].get('pass') for n in positive_names)
    controls=all(checks[n].get('pass') is False and checks[n].get('errors') and checks[n].get('summary',{}).get('end')
                 for n in ('descriptor_fault','payload_fault'))
    def trace(path):
        return collections.Counter(l for l in path.read_text().splitlines() if l.startswith(('BFI ','BFPV ','RET ')))
    lockstep=trace(run/'walker.log')==trace(run/'replay/full/run.log')
    native_path=Path(manifest.get('native_family_check',str(run.parent/'native_family/check.json')))
    native=json.loads(native_path.read_text())
    family=manifest.get('native_family_hold') is True and native.get('status')=='PASS' and native.get('pulse_family_fault_caught')
    result=dict(status='PASS' if positives and controls and lockstep and family else 'FAIL',
                scope='BF-active as-built frame return composition; Q outputs held quiescent',
                clock_ps=833,static_replay=positives,controls_caught=bool(controls),trace_lockstep=lockstep,
                native_family_hold=bool(family),payload_skew_edges=manifest['payload_skew_edges'],
                xo_forwarding_qualification=manifest.get('xo_forwarding_qualification','CHECKED'),
                tested_shapes=shapes,
                cases={n:dict(passed=c.get('pass'),errors=c.get('errors',[])[:12],end=c.get('summary',{}).get('end')) for n,c in checks.items()},
                production_enabled=False,added_cycles=0)
    (run/'check.json').write_text(json.dumps(result,indent=2)+'\n')
    if result['status']!='PASS':return 1
    measured=json.loads((run/'measure.json').read_text())
    hashes=dict(manifest['source_sha256'])
    # the canonical plan-kit path is a required pin (xs_bf.qualify_asbuilt_measurement); a frame root's schedule may
    # name the kit by ext/<path> instead, and prepare.py then required both paths to hold the same bytes
    for name in ('rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv',
                 f'rtl/dsrom_sys/s81_dv/frame_lp/plan/{manifest["master"]}_l4_lp_plan_kit.sv'):
        hashes[name]=hashlib.sha256((source/name).read_bytes()).hexdigest()
    if manifest.get('plan_kit_sha256') not in (None,hashes[name]):
        raise ValueError('plan kit changed since prepare: '+name)
    for line in (source/'tools/s81_dv/frame_bench.f').read_text().splitlines():
        line=line.strip()
        if line.startswith('+incdir+'):
            directory=source/line[len('+incdir+'):]
            for header in directory.rglob('*'):
                if header.is_file() and header.suffix in ('.vh','.svh'):
                    hashes[str(header.relative_to(source))]=hashlib.sha256(header.read_bytes()).hexdigest()
            continue
        if not line or line.startswith(('#','+')):continue
        hashes[line]=hashlib.sha256((source/line).read_bytes()).hexdigest()
    # S81-FRAME-FIX-1 11-11: a --bound-plan schedule is measured only on a bench carrying the same seam depths
    sched=json.loads(Path(manifest['schedule']).read_text())
    bound=manifest.get('bound_plan')
    if (sched.get('bound_plan') or {}).get('plan_sha256')!=(bound or {}).get('plan_sha256') or \
            (bound is not None and bound['seam_depths']!=sched['bound_plan']['seam_depths']):
        raise ValueError('bench seam depths differ from the schedule bound plan')
    for rec in measured.values():
        if rec.get('leaf_ret_corr'):raise ValueError('as-built record carries a leaf return correction: '+rec['key'])
        rec['asbuilt_source_qualification']=dict(status='PASS_STATIC_REPLAY',clock_ps=833,
            payload_control_caught=not checks['payload_fault']['pass'],one_edge_control_caught=not checks['descriptor_fault']['pass'],
            source_sha256=hashes,schedule_sha256=hashlib.sha256(Path(manifest['schedule']).read_bytes()).hexdigest(),
            scope=result['scope'],trace_lockstep=True,cases=shapes,
            binding=manifest['hard_cfg_parameters'],idle_q_assumption=manifest['idle_q_assumption'],native_family_hold=True,
            payload_skew_edges=manifest['payload_skew_edges'],validated_ops=['attn.wo_a','ffn.router'],
            xo_forwarding_qualification=result['xo_forwarding_qualification'],bound_plan=bound)
    (run/'candidate_measurements.json').write_text(json.dumps(measured,indent=2)+'\n')
    return 0


if __name__=='__main__':sys.exit(collect(sys.argv[1],sys.argv[2:]))
