#!/usr/bin/env python3
"""Source-pin and consumer-boundary checks for the existing acceptance collector.

No DUT stimulus, golden injection, HDL build, or implicit ACK. Fixtures exercise
this checker only. Its PASS is a trace-consistency result, never hardware credit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

IDENTITY=('phase','stage','rank','shard','key','reset_era','owner')
REQUIRED={'phase_accept','cfg_accept','vm_request_accept','activation_capture',
          'root_return_accept','writer_accept','writer_visible','phase_retire'}

def normalize_events(events,observations):
    """Map reviewed binding IDs to consumer roles without touching observations.

    The original collector can record two writer_accept definitions: executed
    and final-visible. Only the pinned ID mapping distinguishes these roles.
    No new edge, timestamp, payload, identity or ACK is synthesized.
    """
    roles={x['binding_id']:x for x in observations}
    if len(roles)!=len(observations):raise ValueError('duplicate consumer binding ID')
    for event in events:
        if event['binding_id'] not in roles:raise ValueError('foreign consumer binding ID')
        role=roles[event['binding_id']]
        if event['kind']!=role['raw_kind'] or role['kind'] not in REQUIRED:
            raise ValueError('wrong consumer role mapping')
        yield dict(event,kind=role['kind'])

def verify_source_bindings(repo,bindings):
    """Verify immutable source bytes AND the reviewed source anchor per observer.

    This does not prove elaboration: current geometry and clock bindings still
    require producer review. A matching source snippet alone cannot admit a run.
    """
    if bindings.get('schema')!='DSROM_CURRENT_CONSUMER_BINDINGS_V1':
        raise ValueError('consumer binding schema missing')
    for entry in bindings['sources']:
        commit=entry['commit']
        if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
            raise ValueError('full immutable source commit required')
        data=subprocess.check_output(['git','show',commit+':'+entry['path']],cwd=repo)
        if hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise ValueError('source pin changed')
        if not entry['anchor'] or entry['anchor'].encode() not in data:
            raise ValueError('source consumer anchor missing')
    return {'source_pins_verified':True,'elaboration_qualified':False,
            'launch_admitted':False,'ACK_inferred':False}

def check_events(events,contract):
    """Check exact expected source IDs and final write readback observations.

    Input IDs, cfg addresses and row/position sets must come from the separately
    pinned source/program contract, not counts fitted from the observed trace.
    """
    identity=tuple(contract['identity'][k] for k in IDENTITY)
    expected_cfg=set(contract['cfg_addresses'])
    expected_rows={tuple(x) for x in contract['root_row_positions']}
    expected_writes={((x['row'],x['position']),x['address']) for x in contract['writes']}
    if len(expected_writes)!=len(contract['writes']) or {x[0] for x in expected_writes}!=expected_rows:
        raise ValueError('source write mapping incomplete or duplicated')
    if len(expected_cfg)!=len(contract['cfg_addresses']) or len(expected_rows)!=len(contract['root_row_positions']):
        raise ValueError('duplicate source expectation')
    kinds=set();cfg=set();roots=set();writes={};visible=set();clocktimes={}
    last_time=-1;phase_started=False;phase_retired=False
    for e in events:
        if tuple(e[k] for k in IDENTITY)!=identity:raise ValueError('foreign phase/owner identity')
        if e['kind'] not in REQUIRED:raise ValueError('foreign observation kind')
        time=e['time_ps']
        if not isinstance(time,int) or time<0 or time<last_time:raise ValueError('absolute event time reversal')
        last_time=time
        clock=e['clock']
        if clock not in contract['clocks'][e['kind']]:raise ValueError('wrong consumer clock')
        # Multiple lanes can share an edge; clock identities need not share rate.
        if time<clocktimes.get(clock,-1):raise ValueError('consumer clock reversal')
        clocktimes[clock]=time
        if e.get('basis')!='actual_VCD_pre_consumer_rising_edge':raise ValueError('offered or unbound observation basis')
        k=e['kind'];kinds.add(k)
        if phase_retired:raise ValueError('event after phase retirement')
        if k=='phase_accept':
            if phase_started:raise ValueError('duplicate phase acceptance')
            phase_started=True
        elif not phase_started:raise ValueError('event before accepted phase')
        if k=='cfg_accept':
            addr=e['cfg_address']
            if addr not in expected_cfg or addr in cfg:raise ValueError('foreign or duplicate cfg address')
            cfg.add(addr)
        if k=='root_return_accept':
            row=(e['row'],e['position'])
            if row not in expected_rows or row in roots:raise ValueError('foreign or duplicate root row/position')
            if e['fault']!=0:raise ValueError('root fault')
            roots.add(row)
        if k in {'writer_accept','writer_visible'}:
            row=(e['row'],e['position']);key=(row,e['address'])
            if key not in expected_writes:raise ValueError('foreign destination write address')
            if row not in roots:raise ValueError('write without prior matching root receipt')
            if e['collision_mask']!=0:raise ValueError('unresolved actual VM writer collision')
            if type(e['word']) is not int or not 0<=e['word']<2**32:raise ValueError('invalid actual VM word')
            if k=='writer_accept':
                if key in writes:raise ValueError('duplicate writer execution')
                writes[key]=(e['word'],time)
            else:
                if key not in writes or key in visible:raise ValueError('foreign or duplicate final visibility')
                word,write_time=writes[key]
                if time<=write_time:raise ValueError('visibility before settled memory edge')
                if e['word']!=word:raise ValueError('final VM word differs from actual executed write')
                visible.add(key)
        if k=='phase_retire':
            if not e['source_idle'] or not e['writer_drained']:raise ValueError('source retirement/drain absent')
            phase_retired=True
    if kinds!=REQUIRED:raise ValueError('missing observation class')
    if cfg!=expected_cfg or roots!=expected_rows:raise ValueError('source cfg/root coverage incomplete')
    if set(writes)!=visible or set(writes)!=expected_writes:
        raise ValueError('source final-write conservation incomplete')
    return {'status':'TRACE_SOURCE_CONSISTENCY_ONLY','cfg_words':len(cfg),'root_rows':len(roots),
            'writes_executed':len(writes),'final_visible':len(visible),'ACK_inferred':False,
            'phase_retirement_source_observed':phase_retired,'hardware_qualified':False,
            'fulltoken_or_timing_credit':False}

def main():
    parser=argparse.ArgumentParser()
    for name in ['events','contract','bindings','repo','out']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(exist_ok=False)
    try:
        paths={'events':args.events,'contract':args.contract,'bindings':args.bindings}
        pins={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in paths.items()}
        contract=json.loads(args.contract.read_text());bindings=json.loads(args.bindings.read_text())
        if contract.get('input_class') not in {'ACTUAL_RUNTIME_OBSERVER','SOURCE_SEMANTICS_FIXTURE'}:
            raise ValueError('offered profile or unspecified event provenance')
        source_result=verify_source_bindings(args.repo,bindings)
        with args.events.open() as f:
            events=(json.loads(line) for line in f)
            if 'observations' in bindings:events=normalize_events(events,bindings['observations'])
            result=check_events(events,contract)
        for k,v in paths.items():
            if hashlib.sha256(v.read_bytes()).hexdigest()!=pins[k]:raise ValueError('input changed during inspection')
        result.update(source_binding=source_result,input_sha256=pins,input_class=contract['input_class'])
        (args.out/'record.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    except Exception as error:
        (args.out/'failure.json').write_text(json.dumps({'exception_type':type(error).__name__,'exception':str(error)},indent=2)+'\n')
        raise
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
