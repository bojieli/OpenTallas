import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_I66_fullscope_native_hooks as M


def line(kind,edge=500,rank=0,**changes):
    s=M.schema();f={k:0 for k in s['event_fields'][kind]};f.update(changes)
    return f'{M.PREFIX} {s["regions"][kind]} {edge} {rank} {kind} '+' '.join(f'{k}={v:x}' for k,v in f.items())


def test_exact_all18_source_phases_and_six_native_W2_not_consumer_count():
    r=M.model()
    assert r['primary_range']==[66,105] and r['total_GU0_phases']==18
    assert r['captured_phase_count']==12 and r['native_W2_phase_count']==6
    assert r['native_W2']==[79,84,89,94,97,100]
    last=r['W2_consumers'][-1]
    assert last['pc']==100 and last['obase']==415488
    assert last['uses']==[dict(pc=105,operand='c',read_nin=1280)]
    assert all(x['actual_writer_count'] is None and not x['intercept_576_seats'] for x in r['W2_consumers'])
    assert not any(x['writer_count_inferred_from_consumer'] for x in r['W2_consumers'])


def test_first_W2_frame_is_operand_A_then_five_C_not_six_C():
    w=M.model()['W2_consumers']
    assert [x['obase'] for x in w]==[400448,403456,406464,409472,412480,415488]
    assert [(x['uses'][0]['pc'],x['uses'][0]['operand']) for x in w]==[
        (101,'a'),(101,'c'),(102,'c'),(103,'c'),(104,'c'),(105,'c')]


def test_source_tail_I106_not_assigned_to_I100_by_address_stride():
    m=M.model()
    assert m['beyond105']['pc106_reads_other_VM_base']==418496
    assert m['beyond105']['pc106_owner_not_assigned_to_I100']
    assert m['beyond105']['pc107_source_collective_wait']==31
    assert m['beyond105']['collection_stop_PC'] is None


def test_exact_inverse_no_PC_cyclestop_or_drives_and_native_last_retirement():
    t=M.generate();body=M.block()
    assert M.inverse(t)==M.N.sha((M.N.INPUT/'runtime_wrapper.sv.txt').read_bytes())
    assert 'parameter integer I66_OBSERVE = 0' in t
    assert '.ret_p_last' in body and 'vector_done' in body and '$strobe' in body
    assert 'root_sample' in body and 'for (genvar s = 0; s < ROM_R' in body
    assert '>=105' not in body and '<=105' not in body and '$finish' not in body
    assert 'force ' not in body and 'packet_ACK' not in body
    assert 'I66HOOK ' not in body


@pytest.mark.parametrize('old,new',[(".host_entry(14'd0)",".host_entry(14'd66)"),
    ('dut.u_tile.u_core.g_rom.r_v[s]','dut.r_v[s]'),
    ('saved_retire_seq = dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p_seq','saved_retire_seq = 0')])
def test_modified_engine_scope_or_counter_fabrication_rejects_inverse(old,new):
    text=M.generate();assert old in text
    with pytest.raises(ValueError):M.inverse(text.replace(old,new))


def test_true_W2_raw_rows_above576_are_not_treated_as_capture_seats():
    r=M.parse([line('root_sample',row=1279,root=127,error=0,fp32=0x3f800000),
               line('VM',address=416767,root=127,value=0x3f800000)])
    assert r[0]['fields']['row']==1279 and r[1]['fields']['address']==416767


def test_POST105_actual_read_tag_retirement_rows_survive_parse_no_EOF_PASS():
    events=[line('SU_shape',pc=105,nin=1280,cbase=415488,seq=255),
            line('read',edge=550,port=1023,src=0,address=415488,value=17),
            line('Xtag',edge=552,cw_width=196,cw=255<<58),
            line('vector_retire',edge=590,seq=255,last=1),
            line('vector_done',edge=590,seq=255,cr_dseq=255)]
    parsed=M.parse(events)
    assert parsed[-1]['edge']==590 and parsed[-1]['region']=='post'
    assert (parsed[2]['fields']['cw']>>58)&255==255
    assert all('fulltoken' not in e and 'context' not in e for e in parsed)


@pytest.mark.parametrize('bad',[
    lambda:line('vector_done',seq=3,cr_dseq=2),
    lambda:line('read',src=1),lambda:line('read',port=1024),
    lambda:line('root_sample',root=128),lambda:line('Xtag',cw_width=195),
    lambda:line('Xtag',cw_width=196,cw=1<<196),
    lambda:line('SU_shape',seq=256),lambda:line('clock',rank=4),
    lambda:line('vector_done').replace(' post ',' pre '),
    lambda:line('SU_shape').replace('pc=0','pc=1 pc=2'),
    lambda:line('clock').replace('sim_time_ns=0','sim_time_ns=NaN'),
    lambda:line('rom_accept').replace(' obase=0',''),
    lambda:line('clock')+' generation=0',
    lambda:line('root_sample')+' credit_return=1'])
def test_invalid_native_schema_and_fabricated_provider_fields_rejected(bad):
    with pytest.raises(ValueError):M.parse([bad()])


def test_wrong_reset_region_or_counter_order_rejected():
    with pytest.raises(ValueError):M.parse([line('clock',edge=42),line('clock',edge=41)])
    with pytest.raises(ValueError):M.parse(['I66HOOK pre 0 0 read port=0'])


def test_repeated_eval_cannot_duplicate_source_accept_or_native_port_event():
    for event in [line('rom_accept'),line('read'),line('VM'),line('vector_done')]:
        with pytest.raises(ValueError,match='repeated'):M.parse([event,event])
    # Different real lanes/roots on the same source edge are legitimate.
    assert len(M.parse([line('read',port=0),line('read',port=1)]))==2
    assert len(M.parse([line('VM',root=0),line('VM',root=1)]))==2


def test_legacy130_source_plan_is_explicitly_not_launchable_or_exact_selected_core():
    import json
    p=json.loads((M.OUT/'run_source_plan.json').read_text())
    assert len(p['baseline_source_candidates'])==130 and not p['missing_native_source_paths']
    assert p['default_ROM_PHW']==6 and not p['source_closure_complete']
    assert p['selected_core_required'].endswith('/ckvsel/ot_hdc_core_v41x.sv')
    assert all(x['sha256']!=p['selected_core_sha256'] for x in p['actual_selected_core_mismatch'])
    assert p['compiled_binary'] is None and not p['compiler_executed']
