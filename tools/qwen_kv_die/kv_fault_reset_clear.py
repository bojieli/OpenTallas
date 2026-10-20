#!/usr/bin/env python3
"""Full proposed graph reset/clear model, with explicit unqualified root epochs.

This is a cycle model, not an RTL/CDC/physical receipt. Conservative transport
ages are copied from the candidate and must be replaced by actual phases.
"""
import argparse,collections,hashlib,json,random
from pathlib import Path

def simulate(c,p,m,offsets,mode='normal',pulse=None):
    roots={tuple(l['root_details']['output_bit']):l['root_details']['id'] for l in m['loads']}
    target={t['node']:t for t in p['targets']};source={s['id']:s for s in p['source_clears']}
    ops={n['id']:n for n in c['nodes']};ops.update({n['id']:n for n in c['transports']})
    state={s['id']:1 for s in c['sources']};state.update({n:1 for n in ops})
    pipes={n['id']:collections.deque([1]*(n['latency_cycles']-1)) for n in c['transports']}
    source_kinds={s['id']:s for s in c['sources']}
    def low(t,r,d):return 20+offsets[r]+d<=t<20+offsets[r]+d+128
    sink=c['sink'];last_release=max(20+offsets[t['root_id']]+t['depth']+128 for t in p['targets'])
    first_pulse=last_release+8
    finish=first_pulse+c['max_leaf_latency_bound']+8 if pulse else last_release+c['max_leaf_latency_bound']+8
    observations=[];resurrection=[];cleared=set()
    # A missing reset on the final collector is the exact missing branch mutant.
    for t in range(finish):
        new={}
        for name,s in source.items():
            root=roots.get(tuple(s['root_bit']))
            if root is None:raise ValueError('Source reset root not traced: '+name)
            active=bool(pulse==name and t==first_pulse)
            reset=low(t,root,s['depth'])
            if mode=='missing_source_clear' and name==c['sources'][0]['id']:reset=False
            if reset:value=0;cleared.add(name)
            elif name not in cleared:value=1
            elif source_kinds[name]['sticky']:value=state[name] or active
            else:value=active
            new[name]=int(value)
        for name,n in ops.items():
            if 'source' in n:
                q=pipes[name]
                if q:value=q.popleft();q.append(state[n['source']])
                else:value=state[n['source']]
                new[name]=value;continue
            r=target[name];depth=r['depth']
            if mode=='early_sink' and name==sink:depth=r['inherited_depth']
            reset=low(t,r['root_id'],depth)
            if mode=='missing_sink_reset' and name==sink:reset=False
            if mode=='missing_presticky_reset' and n['kind']=='sticky' and name!=sink:reset=False
            if reset:new[name]=0
            else:new[name]=state[n['a']] | state[n['b']]
        state=new
        if t>=last_release+2 and not pulse and state[sink]:resurrection.append(t)
        if pulse and t>=first_pulse and state[sink]:observations.append(t)
    if pulse:
        if not observations:raise AssertionError('Source pulse lost: '+pulse)
        if observations[0]>first_pulse+c['max_leaf_latency_bound']+2:raise AssertionError('Source pulse late: '+pulse)
        return dict(source=pulse,pulse_cycle=first_pulse,observed_cycle=observations[0])
    if resurrection:raise AssertionError('STALE_FAULT_RESURRECTION at '+str(resurrection[0]))
    return dict(last_new_reset_release=last_release,checked_until=finish,clear=True)

def main():
    a=argparse.ArgumentParser();a.add_argument('--dir',type=Path,required=True);v=a.parse_args();d=v.dir
    c=json.loads((d/'candidate.json').read_text());p=json.loads((d/'reset_branch_candidate.json').read_text());m=json.loads((d/'reset_loads.json').read_text())
    roots=sorted({t['root_id'] for t in p['targets']});skew=p['diagnostic_root_assert_skew_cycles'];rng=random.Random(1019)
    schedules=[dict.fromkeys(roots,0),{r:skew for r in roots},{r:(j%2)*skew for j,r in enumerate(roots)}]+[{r:rng.randrange(skew+1) for r in roots} for _ in range(8)]
    # Make the final sink's root earliest and every other root latest.
    sinkroot=next(t['root_id'] for t in p['targets'] if t['node']==c['sink'])
    schedules.append({r:0 if r==sinkroot else skew for r in roots})
    clear_cases=[simulate(c,p,m,s) for s in schedules]
    mutants=[]
    for mode in ('early_sink','missing_sink_reset','missing_presticky_reset','missing_source_clear'):
        detected=None
        for j,s in enumerate(schedules):
            try:simulate(c,p,m,s,mode)
            except AssertionError as e:detected=dict(mode=mode,schedule=j,witness=str(e));break
        if detected is None:raise AssertionError('RESET_MUTANT_NOT_DETECTED '+mode)
        mutants.append(detected)
    # Reset/clear is followed by every logical source, including all four pulse
    # sources before the sticky source cells and the old upstream hub input.
    pulses=[simulate(c,p,m,schedules[-1],pulse=s['id']) for s in c['sources']]
    result=dict(schema='opentallas.kv_fault_reset_clear_model.v1',qualified_release=False,status='FULL_GRAPH_CYCLE_MODEL_PASS_CONDITIONAL_ON_ROOT_AND_SOURCE_CONTRACTS',reset_schedules=len(schedules),roots=len(roots),source_pulses=len(pulses),diagnostic_root_assert_skew_cycles=skew,clear_cases=clear_cases,mutants=mutants,pulses=pulses,input_hashes={f:hashlib.sha256((d/f).read_bytes()).hexdigest() for f in ('candidate.json','reset_branch_candidate.json','reset_loads.json')},unqualified=['Common full-cycle clock model: no native phase/calendar receipt','Root assertion skew is a diagnostic hypothesis, not measured','All source clear-on-local-reset is assumed; old existing_ufh upstream reset graph still needs its own receipt','Transport delays are conservative candidate ages, not installed native lane proof','POR unknown startup, host reset hold/admission, branch clock/STA and whole STATUS path still required'])
    (d/'reset_clear_model.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('pulses','clear_cases')}))
if __name__=='__main__':main()
