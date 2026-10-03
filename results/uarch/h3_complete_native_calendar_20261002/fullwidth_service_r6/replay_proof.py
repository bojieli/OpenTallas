"""Independent interval/ownership audit; no producer scheduler imports."""
import gzip
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent

def check_run(run):
    events = run['events']; jobs = run['jobs']
    by_id = {e['id']: e for e in events}
    assert len(by_id) == len(events)
    grouped = {}
    for e in events:
        assert e['end'] - e['start'] == e['duration'] > 0
        assert e['resource_release'] > e['start']
        for parent in e['depends_on']:
            assert by_id[parent]['end'] <= e['start']
        assert e['owner55'] >> 9 == e['owner46']
        assert e['backend_generation4'] == e['owner46'] & 15
        assert e['backend_PT35'] == (e['owner46'] >> 4) & ((1 << 35) - 1)
        assert e['physical_PC'] == e['owner46'] >> 39
        assert 0 <= e['seat'] < e['capacity']
        grouped.setdefault((tuple(e['resource']),e['seat']),[]).append(e)
    for rows in grouped.values():
        rows.sort(key=lambda e:e['start'])
        for a,b in zip(rows,rows[1:]):
            assert a['resource_release'] <= b['start']
    SMs = {}; slots = {}
    for job in jobs:
        SMs.setdefault(job['requester_SM'],[]).append(job)
        owner=job['owner46']
        key=(owner>>39,(owner>>36)&7,job['W2_private_slot'])
        assert 0<=job['W2_private_slot']<16
        slots.setdefault(key,[]).append(job)
        rows=[e for e in events if e['id'].startswith(job['occurrence']+':')]
        assert len(rows)==61
        for kind in ('backend_read','return_data','response_capture'):
            children=[e for e in rows if e['kind']==kind]
            assert len(children)==16
            assert sum(e['payload_bytes'] for e in children)==512
        for kind in ('both_RF_copies','old_sector_read'):
            assert sum(e['payload_bytes'] for e in rows if e['kind']==kind)==1024
        assert sum(e['kind']=='common_ACK' for e in rows)==1
        assert sum(e['kind']=='all_copies_drain' for e in rows)==1
        assert max(e['end'] for e in rows)==job['all_copies_drain_end']==job['retire']
    for group in (SMs,slots):
        for rows in group.values():
            rows.sort(key=lambda j:j['admit'])
            for a,b in zip(rows,rows[1:]):
                assert a['retire']<=b['admit']
    return dict(events=len(events), jobs=len(jobs), last_retire=run['summary']['last_retire'],
                incremental_edges=run['summary']['incrementally_paid_edges'],
                wraps=run['summary']['modulo16_wraps'])


def proof():
    result={};hashes={}
    for name in ('prospective_calendars.json.gz','contending_32SM_calendars.json.gz'):
        raw=(BASE/'final'/name).read_bytes();hashes[name]=hashlib.sha256(raw).hexdigest()
        result[name]={k:check_run(v) for k,v in json.loads(gzip.decompress(raw)).items()}
    model=json.loads((BASE/'final/model.json').read_bytes())
    assert model['fields']['W4_W6_bits']==55
    assert model['W2_minimum']['total_raw_bits']==466944
    assert not model['production_admitted'] and model['whole_token_ns'] is None
    assert model['policy']['drain_source_export'] is None
    return dict(schema='INDEPENDENT_FULLWIDTH_PROSPECTIVE_INTERVAL_PROOF_R6',
                verdict='PASS_MODEL_INTERVALS_ONLY', calendars=result, artifact_sha256=hashes,
                resource_overlap=False, premature_owner_reuse=False, missing_sector_children=False,
                installed_quiescence_proved=False, actual_production_calls=0,
                actual_caller_map_supplied=False, whole_program_qualified=False)

if __name__=='__main__':
    data=(json.dumps(proof(),sort_keys=True,indent=2)+'\n').encode()
    target=BASE/'final/proof.json'
    if target.exists():
        assert target.read_bytes()==data
    else:
        target.write_bytes(data)
    print(data.decode(),end='')
