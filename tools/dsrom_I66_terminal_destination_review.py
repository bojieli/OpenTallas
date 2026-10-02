"""Independent terminal I66 root/write/visibility review; never runs hardware."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

SOURCE='3bc652fe5851e77de2086788ed2a1008d4a244b1'
IDENTITY=dict(stage=0,rank=0,phase=10,key_word=2149580800,reset_era=0)
ORACLE=0x45a00000


def review(events,record):
    if record.get('source_commit')!=SOURCE or not record.get('finish_monotonic'):
        raise ValueError('exact terminal source required')
    if not any(s['name']=='runtime' and s['returncode']==0 for s in record['stages']):
        raise ValueError('actual runtime exit0 required')
    roots={};writes={};visible={};counts=Counter();bounds={};retire=None;drain=None;last=-1
    for e in events:
        if any(e.get(k)!=v for k,v in IDENTITY.items()) or e['edge']<last:
            raise ValueError('source event identity/order')
        last=e['edge'];k=e['kind'];n=e['edge'];counts[k]+=1
        if k.startswith('FAIL'):raise ValueError('actual source fault')
        bounds.setdefault(k,[n,n])[1]=n
        if k=='root_row_accept':
            row=e['b']
            if row in roots or not 0<=row<576 or not 0<=e['a']<128 or e['c']!=ORACLE:
                raise ValueError('root conservation/oracle')
            roots[row]=(n,e['a'])
        elif k=='VM_write_accept':
            row=e['b']-398720
            if row in writes or roots.get(row)!=(n-1,e['a']) or e['c']!=ORACLE:
                raise ValueError('native writer dependency')
            writes[row]=n
        elif k=='final_destination_visible':
            row=e['a']-398720
            if row in visible or writes.get(row)!=n or e['c']!=ORACLE:
                raise ValueError('actual sink visibility')
            visible[row]=n
        elif k=='phase_retire':
            if len(visible)!=576 or n<=max(visible.values()):
                raise ValueError('retirement before complete visibility')
            retire=n
        elif k=='all_source_root_writer_drained':
            if retire is None or n<=retire or len(visible)!=576 or (e['a'],e['b'],e['c'])!=(102400,576,576):
                raise ValueError('source drain fence')
            drain=n
    required={'op_accept':1,'phase_accept':1,'EID_VM_read_accept':1,
              'VM_write_accept':576,'final_destination_visible':576,'root_row_accept':576}
    if any(counts[k]!=v for k,v in required.items()) or drain is None:
        raise ValueError('complete accepted event census')
    return dict(source_commit=SOURCE,dependency_verdict='PASS_DIRECTED_I66_ROOT_DESTINATION_DRAIN',
        original_wrapper_verdict=record['result'],original_calibration=record['calibration'],
        event_counts=dict(counts),event_edge_bounds=bounds,
        measured_source_edges=dict(op_accept=bounds['op_accept'][0],phase_accept=bounds['phase_accept'][0],
            last_root=max(n for n,p in roots.values()),last_destination_visible=max(visible.values()),
            adapter_retire=retire,observer_stable_drain=drain),
        op_to_last_visible_edges=max(visible.values())-bounds['op_accept'][0],
        op_to_adapter_retire_edges=retire-bounds['op_accept'][0],
        startup_spine_idle_not_phase_completion=True,
        observer_stable_drain_not_natural_kernel_latency=True,
        simulated_functional_cycles_not_physical_time=True,
        prediction_calendar_admitted=False,physical_fit=False,fulltoken_rate=False,
        scope='Isolated L0.I66 synthetic unit coefficients/input, real arithmetic and sink. No payload, fullcore/coll_busy, transport or SSFF qualification.')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('immutable evidence')
    raw=(a.run_dir/'record.json').read_bytes();r=json.loads(raw)
    journal=a.run_dir/'actual.jsonl';h=sha(journal)
    if h!=r['actual_journal_sha256'] or sha(a.run_dir/'gate')!=r['binary_sha256']:
        raise ValueError('actual executable/journal pins')
    with journal.open() as f:result=review((json.loads(l) for l in f),r)
    if sha(journal)!=h or (a.run_dir/'record.json').read_bytes()!=raw:
        raise ValueError('live evidence changed')
    result.update(actual_journal_sha256=h,binary_sha256=r['binary_sha256'],
                  terminal_record_sha256=hashlib.sha256(raw).hexdigest(),
                  reviewer_sha256=sha(__file__))
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
