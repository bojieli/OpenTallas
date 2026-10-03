"""Independent source service/interval audit, no scheduler import."""
import gzip
import hashlib
import json
from pathlib import Path
B=Path(__file__).resolve().parent

def proof():
    raw=(B/'run_r4/calendars.json.gz').read_bytes();runs=json.loads(gzip.decompress(raw));out={}
    for name,run in runs.items():
        events=run['events'];ids={r['id']:r for r in events};assert len(events)==len(ids)
        resources={}
        for r in events:
            assert r['duration']>0 and r['end']-r['start']==r['duration']
            assert r['resource_release']>r['start']
            for p in r['depends_on']:assert ids[p]['end']<=r['start']
            resources.setdefault((tuple(r['resource']),r['seat']),[]).append(r)
        for rows in resources.values():
            rows.sort(key=lambda r:r['start'])
            for a,b in zip(rows,rows[1:]):assert a['resource_release']<=b['start']
        SMs={}
        for j in run['jobs']:
            assert len(j['children'])==16 and j['R14_LEN']==1 and j['R14_BEAT']==0
            assert sorted(c['first'] for c in j['children'])==list(range(16))
            assert len({c['stack'] for c in j['children']})==4
            assert all(c['sectors']==1 for c in j['children'])
            SMs.setdefault(j['SM'],[]).append(j)
            rows=[r for r in events if r['id'].startswith(j['name']+':')]
            for kind in ('R14_allocate','command_bus','backend_read','R14_return_arb','R14_lookup','W2_restore','held_return','return_data','response_capture','R14_reverse_lookup','child_reverse'):
                assert sum(r['kind']==kind for r in rows)==16
            assert sum(r.get('payload_bytes',0) for r in rows if r['kind']=='response_capture')==512
            assert sum(r['kind']=='common_ACK' for r in rows)==1
            for kind in ('fragment_credit_reserve','stage_store_ACK','stage_credit_return'):
                assert sum(r['kind']==kind for r in rows)==8
            assert sum(r['kind']=='child_tuple_assign' for r in rows)==16
            assert sum(r['duration'] for r in rows if r['kind'].startswith('W6_'))==19
            assert all(r['parent55']==j['parent55'] for r in rows)
            assert all(c['end']==j['retire'] for c in j['physical_context_quarantine'])
            for r in rows:
                if r['kind'] in ('R14_lookup','R14_reverse_lookup'):assert r['native_CORE_or_client_edges']==12
                if r['kind']=='R14_return_arb':assert r['native_CORE_or_client_edges']==7
        for rows in SMs.values():
            rows.sort(key=lambda j:j['begin'])
            for a,b in zip(rows,rows[1:]):assert a['retire']<=b['begin']
        assert all(sum(tuple(r['resource'])==('command_bus',stack) for r in events)==16 for stack in range(4))
        #W2 reserve->accepted local terminal occupies a real16-row/client
        #pool. Physical quarantine continues to the parent drain after this.
        W2={}
        contexts={}
        for j in run['jobs']:
            for child in j['children']:
                n=child['first'];reserve=ids[j['name']+':W2_reserve.child'+str(n)]
                accepted=ids[j['name']+':held_return.sector'+str(n)]
                W2.setdefault(child['physical_PC'],[]).extend([(reserve['start'],1),(accepted['end'],-1)])
                contexts.setdefault(child['physical_PC'],[]).extend([(reserve['start'],1),(j['retire'],-1)])
        peaks={}
        for banks,capacity,label in ((W2,16,'W2_perPC_client'),(contexts,128,'R14_context_perPC')):
            peak=0
            for edges in banks.values():
                live=0
                for time,delta in sorted(edges,key=lambda p:(p[0],p[1])):
                    live+=delta;peak=max(peak,live);assert 0<=live<=capacity
                assert live==0
            peaks[label]=peak
        out[name]=dict(events=len(events),parents=len(run['jobs']),sector_children=16*len(run['jobs']),
                       last_retire=run['last_retire'],resource_overlap=False,capacity_peaks=peaks)
    model=json.loads((B/'run_r4/model.json').read_bytes())
    assert model['W2_composition']['p_wr_done_ready_required'] and model['p_wr_done_ready_REQUIRED']
    assert model['W2_composition']['W2_model_costs']['full_wrapper_variant']['protected_state_bits_per_PC']==9144
    assert model['cost_inputs']['pipeline_two_seats_38stages_144lanes_increment_bits']==1575936
    assert model['conservative_whole_command_inventory']['conservative_whole_command_gross_protected_bits']==940464
    assert model['conservative_whole_command_inventory']['conservative_whole_command_gross_raw_bits']==748500
    assert model['matched_prior_W2_debit'] is None and not model['whole_program_composed']
    return dict(schema='INDEPENDENT_SOURCE_CONNECTOR_R7_PROOF',verdict='PASS_PROSPECTIVE_CONTROLS_ONLY',
                artifact_sha256=hashlib.sha256(raw).hexdigest(),runs=out,
                actual_caller_full16_quarantine_installed=False,whole_token_ns=None)

if __name__=='__main__':
    raw=(json.dumps(proof(),sort_keys=True,indent=2)+'\n').encode();target=B/'run_r4/proof.json'
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    print(raw.decode(),end='')
