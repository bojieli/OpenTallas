#!/usr/bin/env python3
"""Read-only, streaming VCD acceptance recorder. Never manufactures event edges.

Bindings name exact clock/valid/payload nets at each actual consumer. VM writer
output offers must not be substituted for accepted enables at the VM sink.
Full geometry/source/run pins accompany the waveform; no HDL build is launched.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

KINDS={'phase_accept','cfg_accept','vm_request_accept','activation_capture',
       'root_return_accept','writer_accept','phase_retire'}

def binary(value):
    if any(c in value.lower() for c in 'xz'):raise ValueError('unknown active event data')
    return int(value,2)

def extract(states,field):
    value=binary(states[field['signal']]);lo=field.get('lsb',0)
    return (value>>lo)&((1<<field['width'])-1)

def record(vcd,bindings,out):
    initial_hash=file_hash(vcd)
    definitions=bindings['events']
    if {e['kind'] for e in definitions}!=KINDS:raise ValueError('missing real consumer event binding')
    if not bindings.get('writer_sink_bound'):raise ValueError('writer offer is not sink acceptance')
    if not bindings.get('whole_phase_geometry_bound'):raise ValueError('whole phase geometry unbound')
    if bindings.get('input_class')!='ACTUAL_RUNTIME_VCD':raise ValueError('not an actual runtime trace declaration')
    wanted={e[k] for e in definitions for k in ['clock','valid','reset_n']}
    wanted.update(f['signal'] for e in definitions for f in e['fields'].values())
    signals={};codes={};scope=[];time=0;states={};changes={};counts=Counter();events=0;tick_ps=None
    def flush(target):
        nonlocal events
        before=states.copy();after=dict(states);after.update(changes)
        for e in definitions:
            c=e['clock']
            if before.get(c)=='0' and after.get(c)=='1':
                if binary(before.get(e['reset_n'],'x'))==0:continue
                if binary(before.get(e['valid'],'x'))==0:continue
                fields={k:extract(before,f) for k,f in e['fields'].items()}
                event=dict(kind=e['kind'],time_ps=time*tick_ps,clock=c,
                           basis='actual_VCD_pre_consumer_rising_edge',binding_id=e['id'],**fields)
                target.write(json.dumps(event,sort_keys=True)+'\n');counts[e['kind']]+=1;events+=1
        states.update(changes);changes.clear()
    with Path(vcd).open() as src,Path(out).open('x') as target:
        header=True;timescale_text='';reading_timescale=False
        for line in src:
            line=line.strip()
            if header:
                if line.startswith('$scope'):scope.append(line.split()[2])
                elif line.startswith('$upscope'):scope.pop()
                elif line.startswith('$var'):
                    p=line.split();name='.'.join(scope+[p[4]])
                    if name in wanted:
                        signals[name]=int(p[2]);codes.setdefault(p[3],[]).append(name)
                if line.startswith('$timescale'):reading_timescale=True
                if reading_timescale:
                    timescale_text+=' '+line
                    if '$end' in line:
                        match=re.search(r'\$timescale\s+(\d+)\s*(ps|ns|us|ms|s)\s+\$end',timescale_text)
                        if not match:raise ValueError('unsupported timescale')
                        tick_ps=int(match[1])*{'ps':1,'ns':1000,'us':1000000,'ms':1000000000,'s':1000000000000}[match[2]]
                        reading_timescale=False
                if line.startswith('$enddefinitions'):
                    if wanted-set(signals):raise ValueError('missing exact VCD signals: '+','.join(sorted(wanted-set(signals))))
                    if tick_ps is None:raise ValueError('missing timescale')
                    for e in definitions:
                        for k in ['clock','valid','reset_n']:
                            if signals[e[k]]!=1:raise ValueError('non-scalar acceptance control')
                        for f in e['fields'].values():
                            if f['width']<=0 or f.get('lsb',0)+f['width']>signals[f['signal']]:raise ValueError('payload width mismatch')
                    header=False
                continue
            if not line or line.startswith('$'):continue
            if line.startswith('#'):
                flush(target);newtime=int(line[1:])
                if newtime<time:raise ValueError('waveform time reversal')
                time=newtime;continue
            if line[0] in 'bB':value,code=line[1:].split()
            elif line[0] in '01xXzZ':value,code=line[0],line[1:]
            else:continue
            for name in codes.get(code,[]):
                if name in changes and changes[name]!=value and any(name==e['clock'] for e in definitions):
                    raise ValueError('ambiguous multiple clock transitions at same timestamp')
                changes[name]=value
        if header:raise ValueError('incomplete VCD header')
        flush(target)
    final_hash=file_hash(vcd)
    if initial_hash!=final_hash:raise ValueError('waveform changed during extraction')
    missing=sorted(k for k in KINDS if not counts[k])
    return {'basis':'ACTUAL_RUNTIME_WAVEFORM_OBSERVATIONS_ONLY','events':events,'counts':dict(counts),
            'missing_event_classes':missing,'all_event_classes_observed':not missing,
            'complete_phase_qualified':False,'conservation_and_owner_retirement':'separate source-bound validation required; presence of event classes alone is insufficient',
            'offered_profile_used':False,'physical_clock_credit':False,'numerical_or_fulltoken_qualification':False,
            'vcd_sha256':final_hash,'bindings_sha256':file_hash(bindings['bindings_path']) if bindings.get('bindings_path') else None}

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--vcd',type=Path,required=True);p.add_argument('--bindings',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output directory required')
    a.out.mkdir()
    try:
        bindings=json.loads(a.bindings.read_text());bindings['bindings_path']=str(a.bindings)
        result=record(a.vcd,bindings,a.out/'events.jsonl');(a.out/'record.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    except Exception as error:
        pins={}
        for name,path in [('vcd',a.vcd),('bindings',a.bindings)]:
            try:pins[name+'_sha256']=file_hash(path)
            except Exception as pin_error:pins[name+'_pin_error']=str(pin_error)
        (a.out/'failure.json').write_text(json.dumps({'exception_type':type(error).__name__,'exception':str(error),**pins},indent=2)+'\n');raise
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
