#!/usr/bin/env python3
"""Exercise source-profile derivation against real L2 operation IDs.

Route and absolute row dates here are explicitly synthetic unit-test inputs.
They never qualify the current physical die or replace real CAP producers.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import kv_program_builder as B


def run(root):
    root=Path(root)
    binding=json.loads((root/'binding.json').read_text())
    binding['source_root']=str(root/'source')
    binding['native_command_epoch_seq_edge']=0
    schedule=json.loads((root/'schedule.json').read_text())
    expected=json.loads((root/'selected_groups.json').read_text())['groups']
    groups=B.selected_groups(schedule)
    assert {g['kind']:set(g['covers']) for g in groups}=={k:set(v['covers']) for k,v in expected.items()}
    class TestRoute:
        die_sha='TEST_ONLY_ROUTE'
    # Source edge arithmetic is tested independently of production routing.
    B.ctl_path=lambda die,inst:dict(edges=9,path=[],scope='TEST_ONLY_ROUTE')
    args=(TestRoute(),schedule,binding)
    ledger=dict(die_v_sha256=TestRoute.die_sha,clock_epoch_identity='TEST_ONLY_EPOCH',
                producers={},receipt_root=str(root),edge_convention='native_command_epoch_relative_sampled_edges',
                native_command_epoch_seq_edge=0,context=0,job_ids={g['owner']:i for i,g in enumerate(groups)})
    tr=root/'transport.json';unit=root/'unit.json'
    missing=B.build(*args,ledger,tr,unit)
    assert missing['status']=='PARTIAL' and not missing['jobs'] and len(missing['missing'])==4
    assert missing['source_timing_derivation']['capture_offset']==19
    assert not missing['calendar_qualified'] and not missing['production_enabled']
    caught=[]
    def expect(name,fn):
        try:fn()
        except ValueError as exc:caught.append(dict(case=name,error=str(exc)))
        else:raise AssertionError('missed '+name)
    wrong=deepcopy(binding);wrong['die_v_sha256']='WRONG'
    expect('different_die',lambda:B.build(TestRoute(),schedule,wrong,ledger,tr,unit))
    wrong=deepcopy(binding);wrong['parameters']['KV_CP']=0
    expect('disabled_pool',lambda:B.build(TestRoute(),schedule,wrong,ledger,tr,unit))
    wrong=deepcopy(binding);wrong['source_hashes']['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_bank.sv']='0'*64
    expect('unmeasured_bank_source',lambda:B.build(TestRoute(),schedule,wrong,ledger,tr,unit))
    wrong=deepcopy(binding);wrong['parameters']['HARD_RQ']=1-binding['parameters'].get('HARD_RQ',0)
    expect('wrong_reduce_source_selection',lambda:B.build(TestRoute(),schedule,wrong,ledger,tr,unit))
    wrong=deepcopy(binding);wrong['source_hashes']['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv']='0'*64
    expect('unbound_native_write_pipeline',lambda:B.build(TestRoute(),schedule,wrong,ledger,tr,unit))
    cp=next(g for g in groups if g['kind']=='CP');owner=cp['owner']
    record=dict(status='PASS',producer_kind='TEST_ONLY_SYNTHETIC_SOURCE',clock_epoch_identity='TEST_ONLY_EPOCH',
        edge_convention='native_command_epoch_relative_sampled_edges',native_command_epoch_seq_edge=0,
        rows=[dict(lo=0,hi=511,ready_edge=20,release_edge=10000,producer='TEST_ONLY_CAP',
                   source_receipt='TEST_ONLY_CAP_RECEIPT',format='fp32')])
    (root/'test_rows.json').write_text(json.dumps(record))
    selected=deepcopy(ledger);selected['producers'][owner+'::input_rows']=dict(record,
        receipt_path='test_rows.json',receipt_sha256=B.sha(root/'test_rows.json'))
    actual=B.build(*args,selected,tr,unit)
    assert len(actual['jobs'])==1 and len(actual['missing'])==3
    job=actual['jobs'][0];capture=job['issue']+19
    assert job['first_output_write_edge']==capture+139 and job['output_ready_edge']==capture+392
    assert job['residency'][0]['ready_edge']==20 and job['residency'][0]['last_read_edge']==capture+378
    changed=deepcopy(selected);changed['producers'][owner+'::input_rows']['rows'][0]['ready_edge']=0
    expect('ledger_changed_without_source_receipt',lambda:B.build(*args,changed,tr,unit))
    other=deepcopy(record);other['native_command_epoch_seq_edge']=100
    (root/'other_rows.json').write_text(json.dumps(other))
    changed=deepcopy(selected);changed['producers'][owner+'::input_rows']=dict(other,
        receipt_path='other_rows.json',receipt_sha256=B.sha(root/'other_rows.json'))
    expect('source_rows_from_another_command_epoch',lambda:B.build(*args,changed,tr,unit))
    changed=deepcopy(selected);changed['clock_epoch_identity']='OTHER_EPOCH'
    expect('row_dates_cast_to_other_epoch',lambda:B.build(*args,changed,tr,unit))
    changed=deepcopy(ledger);changed['edge_convention']='absolute_receiver_edges'
    expect('absolute_dates_used_as_native_issue_ages',lambda:B.build(*args,changed,tr,unit))
    cn=next(g for g in groups if g['kind']=='CN');co=cn['owner']
    selected=deepcopy(ledger)
    for suffix,ranges in [('input_rows',[(692,819)]),('parameters',[(672,691)]),
                          ('gain_upload_rows',[(528,531),(896,1023)])]:
        rec=dict(status='PASS',producer_kind='TEST_ONLY_SYNTHETIC_SOURCE',clock_epoch_identity='TEST_ONLY_EPOCH',
            edge_convention='native_command_epoch_relative_sampled_edges',native_command_epoch_seq_edge=0,
            rows=[dict(lo=lo,hi=hi,ready_edge=20,release_edge=10000,producer='TEST_ONLY_CAP',
                       source_receipt='TEST_ONLY_CAP_RECEIPT',format='fp32') for lo,hi in ranges])
        if suffix=='gain_upload_rows':
            rec.update(gain_bank_release_edge=10000,writes=[dict(issue=1,row=528,mask=15,
                word128='0',producer='TEST_ONLY_GAIN',role='gain',commit_edge=10)])
        path=root/(suffix+'.json');path.write_text(json.dumps(rec))
        selected['producers'][co+'::'+suffix]=dict(rec,receipt_path=path.name,receipt_sha256=B.sha(path))
    native=B.build(*args,selected,tr,unit)
    assert [j['kind'] for j in native['jobs']]==['GK','CN']
    assert len(native['jobs'][0]['writes'])==1 and not native['jobs'][1]['writes']
    short=deepcopy(selected);key=co+'::gain_upload_rows';rec=deepcopy(short['producers'][key])
    rec.pop('receipt_path');rec.pop('receipt_sha256');rec['gain_bank_release_edge']=1000
    path=root/'short_gain.json';path.write_text(json.dumps(rec))
    short['producers'][key]=dict(rec,receipt_path=path.name,receipt_sha256=B.sha(path))
    expect('gain_lease_expires_before_consumer',lambda:B.build(*args,short,tr,unit))
    ko=next(g['owner'] for g in groups if g['kind']=='KV')
    relative=dict(schema='opentallas.s81.native_producer_ledger.v1',run_id='TEST_ONLY_PARTIAL_SOURCE',
        source_relative_only=True,edge_convention='replay_native_command_epoch_relative_sampled_edges',
        physical_projection_applied=False,physical_epoch_mapping=None,native_clock_domain='TEST_ONLY',source_sha256={},
        row_availability=[dict(instance='TEST_DEST',row=row,known_mask=15,ready_edge=300,
            intended_consumer_owner=ko,future_consumer_release_edge=None) for row in (692,693)])
    constraints=B.relative_constraints(schedule,relative)
    kv=next(g for g in constraints['groups'] if g['kind']=='KV')
    assert kv['observed_input_values']==8 and kv['missing_input_values']==504
    assert kv['complete_input_ready_edge'] is None and constraints['native_command_epoch_seq_edge'] is None
    assert not constraints['jobs'] and not constraints['production_enabled']
    changed=deepcopy(relative);changed['physical_projection_applied']=True
    expect('unproved_component_to_physical_projection',lambda:B.relative_constraints(schedule,changed))
    result=dict(status='PASS',scope='ACTUAL_L2_IDS_AND_MEASURED_SOURCE_PROFILE_WITH_SYNTHETIC_ROUTE_AND_ROW_DATES',
        builder_sha256=B.sha(B.__file__),schedule_sha256=B.sha(root/'schedule.json'),
        selected_operations=sum(len(g['covers']) for g in groups),
        source_profile=missing['source_timing_derivation'],missing_producers=missing['missing'],
        causal_refusals=caught,calendar_qualified=False,production_enabled=False)
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS actual L2 operation coverage and source-profile derivation;',len(caught),'causal refusals; production remains unbound')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();run(a.root)
