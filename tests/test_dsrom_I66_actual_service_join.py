"""Real retained journal calibration and adversarial future packet API tests."""
import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_actual_service_join as J


@pytest.fixture(scope='module')
def actual():
    return J.S.events('r2_PASS')


def test_actual_accepted_calibration_and_finite_phase_only_bound(actual):
    r = J.measured_cone(actual)
    assert r['calibrated_events'] == 322308
    assert r['measured_counts']['VM_read_accept'] == 80
    assert r['measured_counts']['final_destination_visible'] == 576
    assert r['source_specific_finite_service']['measured_op_edges'] == 412
    assert r['source_specific_finite_service']['measured_phase_edges'] == 407
    assert r['source_specific_finite_service']['reserved_local_last_publication'] == 420
    assert not r['current_program'] and not r['fulltoken']
    assert r['remote_service_bound'] is None
    assert all(e['ACK'] is None for e in r['reservation']['events'])


@pytest.mark.parametrize('mutation', ['late_cfg', 'early_retire', 'wrong_owner', 'wrong_epoch', 'duplicate_row', 'wrong_value', 'ordinal', 'bool_identity', 'extra_category'])
def test_actual_journal_mutants_rejected_before_any_input_mutation(actual, mutation):
    events = list(actual)
    kind = {'late_cfg':'cfg_element_write_accept', 'early_retire':'phase_retire',
            'duplicate_row':'final_destination_visible', 'wrong_value':'root_row_accept'}.get(mutation, 'op_accept')
    index = next(i for i, e in enumerate(events) if e['kind'] == kind)
    e = events[index] = dict(events[index])
    if mutation == 'late_cfg': e['edge'] += 1
    elif mutation == 'early_retire': e['edge'] = 420
    elif mutation == 'wrong_owner': e['stage'] = 1
    elif mutation == 'wrong_epoch': e['reset_era'] = 1
    elif mutation == 'duplicate_row': e['a'] += 1
    elif mutation == 'wrong_value': e['c'] ^= 1
    elif mutation == 'ordinal': e['ordinal'] += 1
    elif mutation == 'bool_identity': e['rank'] = False
    else: e['kind'] = 'busy_is_progress'
    before = dict(e)
    with pytest.raises(ValueError): J.measured_cone(events)
    assert e == before


def samples():
    # Fake callback packets test schema only, never native runtime evidence.
    ident = J.R.demand_example()['input']['calendar']['identity']
    template = dict.fromkeys(J.BITS, 0)
    template.update(identity=ident, pc=66, st=7, d_unit=3, qe_mode=0,
                    X_ROM=1, FULL_SHAPE=1, adapter_st=0, key_hit=1,
                    rom_vre=0, rom_vaddr=366688, rom_vq=0, phase_accept=0,
                    phase=10, key_word=2149580800)
    s = [dict(template, edge=i) for i in range(21,28)]
    s[0].update(st=6, waited=1, unit_ready=1, q_gate=1, kv_gate=1, m0_gate=1)
    s[1].update(qe_go=1, rom_q_go=1, rom_ready=1)
    s[2].update(rom_vre=1, adapter_st=1)
    s[3].update(adapter_st=2)
    s[4].update(adapter_st=3)
    s[6].update(phase_accept=1)
    return ident, s


def test_source_correct_registered_origin_and_no_invented_collbusy_gate():
    ident, s = samples()
    s[0]['coll_busy'] = 1
    assert J.admission(s, ident) == dict(core_issue_edge=21, adapter_accept_edge=22, phase_accept_edge=27)


@pytest.mark.parametrize('mutation', ['allfalse', 'stale', 'missing', 'keymiss', 'fault', 'eid', 'bool', 'float', 'phase'])
def test_admission_rejects_stale_or_false_gate_and_key_miss(mutation):
    ident, s = samples()
    if mutation == 'allfalse':
        for k in ['waited','unit_ready','q_gate','kv_gate','m0_gate']: s[0][k]=0
    elif mutation == 'stale': s[1]['identity'] = dict(ident, generation=2)
    elif mutation == 'missing': del s[2]
    elif mutation == 'keymiss': s[4]['key_hit']=0
    elif mutation == 'fault': s[3]['adapter_fault']=1
    elif mutation == 'eid': s[3]['rom_vq']=383
    elif mutation == 'bool': s[0]['unit_ready']=True
    elif mutation == 'float': s[0]['q_gate']=1.0
    else: s[6]['phase']=11
    old=copy.deepcopy(s)
    with pytest.raises(ValueError): J.admission(s, ident)
    assert s == old


def fake_provider_packets(plan):
    # Test-double ledger exercises proposed API. No simulated hardware claim.
    bound=J.R.compose(plan['calendar'],plan['events'],plan['domains'])
    ident=plan['calendar']['identity']; packets=[]
    for e in bound['reservation']['events']:
        packets.append(dict(kind='capture',id=e['id'],edge=e['visible'],identity=ident,bits=e['bits']))
        if e['kind']=='result': packets.append(dict(kind='publish',id=e['id'],edge=e['visible'],identity=ident,bits=e['bits'],row=e['row'],address=e['address']))
        if e['ACK'] is not None: packets.append(dict(kind='ACK',id=e['id'],edge=e['ACK'],identity=ident))
    packets.append(dict(kind='source_idle',edge=plan['calendar']['source_idle_edge'],identity=ident))
    packets.append(dict(kind='operation_retire',edge=bound['successful_completion_edge'],identity=ident))
    packets.sort(key=lambda p: (p['edge'], {'capture':0,'publish':1,'ACK':2,'source_idle':3,'operation_retire':4}[p['kind']]))
    return [dict(p,ordinal=i) for i,p in enumerate(packets)]


def test_provider_observer_join_is_finite_but_only_api_test_double():
    plan=J.R.demand_example()['input']; packets=fake_provider_packets(plan)
    r=J.provider_join(plan,packets)
    assert r['finite_conditional_bound']==435 and not r['fulltoken']


@pytest.mark.parametrize('mutation',['late_ACK','missing_ACK','wrong_generation','wrong_row','early_retire','busy','double_capture','same_edge_ACK','bool_identity','repeat_idle'])
def test_provider_causal_negative_controls_sticky(mutation):
    plan=J.R.demand_example()['input']; packets=fake_provider_packets(plan)
    idx=next(i for i,p in enumerate(packets) if p['kind']=='ACK')
    if mutation=='late_ACK': packets[idx]['edge']+=1
    elif mutation=='same_edge_ACK': packets[idx]['edge']-=1
    elif mutation=='missing_ACK': del packets[idx]
    elif mutation=='wrong_generation': packets[idx]['identity']=dict(packets[idx]['identity'],generation=2)
    elif mutation=='bool_identity': packets[idx]['identity']=dict(packets[idx]['identity'],generation=True)
    elif mutation=='wrong_row': next(p for p in packets if p['kind']=='publish')['row']+=1
    elif mutation=='early_retire': packets[-1]['edge']=420
    elif mutation=='busy': packets[idx]['kind']='busy'
    elif mutation=='repeat_idle': packets.insert(-1,dict(next(p for p in packets if p['kind']=='source_idle'),id='invented_second_idle'))
    else: packets.insert(1,dict(packets[0]))
    for i,p in enumerate(packets): p['ordinal']=i
    old=copy.deepcopy(packets)
    with pytest.raises(ValueError): J.provider_join(plan,packets)
    assert packets==old


@pytest.fixture
def provenance(tmp_path):
    # Fully explicit artificial files: unit tests are NOT build qualification.
    i=J.P.OUT/'inputs';word=J.S.load(i/'I66_current_patched_word.json')['word_hex']
    programs={}; plus={}; fields={}; hashes={}
    for rank in map(str,range(4)):
        d=tmp_path/rank;d.mkdir();p=d/'prog.hex';p.write_text('0\n'*66+word+'\n')
        programs[rank]=str(p);plus[rank]=['+DIR='+str(d),'+OT_ROM_DIR='+str(d)]
        for name in ['spine_phase.hex','spine_keys.hex','spine_stream.hex']: (d/name).write_text('0\n')
        fields[rank]=str(d);hashes[rank]={name:J.S.sha(d/name) for name in ['spine_phase.hex','spine_keys.hex','spine_stream.hex']}
    params=dict(FULL_SHAPE=1,X_ROM=1,ROM_PHW=10,ROM_R=128,ROM_BST=17,logical_NP=4096,NBF=724,ROM_FBW=1632)
    sources=dict(core=str(i/'core.sv.txt'),spine=str(i/'runtime_spine.sv.txt'),wrapper=str(i/'runtime_wrapper.sv.txt'))
    binary=tmp_path/'binary';binary.write_bytes(b'artificial enrollment test')
    journal=tmp_path/'trace.json';journal.write_text('{}')
    compile_record=dict(binary_sha256=J.S.sha(binary),parameters=params,source_sha256={k:J.S.sha(Path(v)) for k,v in sources.items()},source_files={v:J.S.sha(Path(v)) for v in sources.values()})
    compile_path=tmp_path/'compile.json';compile_path.write_text(json.dumps(compile_record))
    qualification=dict(scope='CURRENT_PHW10_FULLPROGRAM',parameters=params,source_files=compile_record['source_files'],program_sha256={k:J.S.sha(Path(p)) for k,p in programs.items()},field_image_sha256=hashes)
    q=tmp_path/'qualification.json';q.write_text(json.dumps(qualification))
    runtime=dict(scope='CURRENT_PHW10_FULLPROGRAM',binary_sha256=J.S.sha(binary),compile_manifest_sha256=J.S.sha(compile_path),rank_plusargs=plus,journal_sha256=J.S.sha(journal))
    rt=tmp_path/'runtime.json';rt.write_text(json.dumps(runtime))
    return dict(parameters=params,binary_path=str(binary),binary_sha256=J.S.sha(binary),compile_manifest_path=str(compile_path),compile_manifest_sha256=J.S.sha(compile_path),qualification_path=str(q),qualification_sha256=J.S.sha(q),runtime_receipt_path=str(rt),runtime_receipt_sha256=J.S.sha(rt),source_paths=sources,program_paths=programs,program_sha256=qualification['program_sha256'],enrolled_plusargs=plus,field_image_paths=fields,field_image_sha256=hashes,journal_path=str(journal))


def test_static_plus_actual_loader_enrollment_test_double(provenance):
    assert J.current_enrollment(provenance)['accepted_origin'] is None


@pytest.mark.parametrize('mutation',['wrong_basename','actual_missing_DIR','duplicate_DIR','historical_cone','missing_source','full_program_changed','field_changed','journal_changed','bool_parameter'])
def test_current_enrollment_adversarial_identity_and_runtime_inputs(provenance,mutation):
    def change(which, fn):
        path=Path(provenance[which+'_path']);m=J.S.load(path);fn(m);path.write_text(json.dumps(m));provenance[which+'_sha256']=J.S.sha(path)
    if mutation=='wrong_basename':
        old=Path(provenance['program_paths']['0']);new=old.with_name('different.hex');old.rename(new);provenance['program_paths']['0']=str(new)
    elif mutation=='actual_missing_DIR': change('runtime_receipt',lambda m:m['rank_plusargs']['0'].pop(0))
    elif mutation=='duplicate_DIR': change('runtime_receipt',lambda m:m['rank_plusargs']['0'].append('+DIR=/wrong'))
    elif mutation=='historical_cone': change('runtime_receipt',lambda m:m.update(scope='PHW10_OLDER_CORE_NATIVE_CONE_ONLY'))
    elif mutation=='missing_source': change('qualification',lambda m:m['source_files'].pop(provenance['source_paths']['core']))
    elif mutation=='full_program_changed': change('qualification',lambda m:m['program_sha256'].update({'0':'0'*64}))
    elif mutation=='field_changed': change('qualification',lambda m:m['field_image_sha256']['0'].update({'spine_stream.hex':'0'*64}))
    elif mutation=='bool_parameter': provenance['parameters']['X_ROM']=True
    else: Path(provenance['journal_path']).write_text('{"fabricated":true}')
    with pytest.raises(ValueError): J.current_enrollment(provenance)


def paired_test_enrollment(provenance, tmp_path):
    # Complete API test double with explicit qualified phase-plan binding.
    # This is not a measured current-program journal or compiled observer.
    plan=J.R.demand_example()['input']
    plan['calendar']['source_phase_accept_edge']=27
    pp=tmp_path/'plan.json';pp.write_text(json.dumps(plan))
    ident, core=samples()
    trace=dict(core_samples=core,provider_packets=fake_provider_packets(plan))
    journal=Path(provenance['journal_path']);journal.write_text(json.dumps(trace))
    rtpath=Path(provenance['runtime_receipt_path']);rt=J.S.load(rtpath)
    rt['journal_sha256']=J.S.sha(journal);rtpath.write_text(json.dumps(rt));provenance['runtime_receipt_sha256']=J.S.sha(rtpath)
    qpath=Path(provenance['qualification_path']);q=J.S.load(qpath)
    pred=J.S.A/'prediction_r2'
    q['qualified_service_plans']={'0':dict(plan_sha256=J.S.sha(pp),source_calendar_path=str(pred/'prediction.json'),source_calendar_sha256=J.S.sha(pred/'prediction.json'),phase_source_path=str(pred/'img/spine_phase.hex'),phase_source_sha256=J.S.sha(pred/'img/spine_phase.hex'))}
    q['callback_source_files']={provenance['source_paths']['wrapper']:J.S.sha(Path(provenance['source_paths']['wrapper']))}
    qpath.write_text(json.dumps(q));provenance['qualification_sha256']=J.S.sha(qpath)
    return pp


def test_complete_current_enrollment_and_reserved_api_join_test_double(provenance,tmp_path):
    plan=paired_test_enrollment(provenance,tmp_path)
    r=J.current_join(provenance,plan)
    assert r['origin']['adapter_accept_edge']==22
    assert r['service']['finite_conditional_bound']==435
    assert not r['fulltoken']


@pytest.mark.parametrize('mutation',['unqualified_phase','changed_plan','changed_calendar_pin','changed_origin','callback_uncompiled'])
def test_current_join_requires_reviewed_exact_phase_plan_and_compiled_observer(provenance,tmp_path,mutation):
    pp=paired_test_enrollment(provenance,tmp_path)
    qpath=Path(provenance['qualification_path']);q=J.S.load(qpath)
    if mutation=='unqualified_phase': q['qualified_service_plans']={}
    elif mutation=='changed_plan':
        p=J.S.load(pp);p['domains']['shared']['bits_per_edge']+=1;pp.write_text(json.dumps(p))
    elif mutation=='changed_calendar_pin': q['qualified_service_plans']['0']['source_calendar_sha256']='0'*64
    elif mutation=='changed_origin':
        p=J.S.load(pp);p['calendar']['source_phase_accept_edge']=26;pp.write_text(json.dumps(p));q['qualified_service_plans']['0']['plan_sha256']=J.S.sha(pp)
    else: q['callback_source_files']={'uncompiled.sv':'0'*64}
    qpath.write_text(json.dumps(q));provenance['qualification_sha256']=J.S.sha(qpath)
    with pytest.raises(ValueError): J.current_join(provenance,pp)
