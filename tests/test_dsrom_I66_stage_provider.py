"""Source-state software models only; fixtures do not qualify runtime or PHY."""
import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import pytest
import dsrom_I66_stage_provider as M
D=M.D


def command(eid=0):
    return D.resolve(eid,0,1,0,dict(accepted=True,address=366688,read_edge=11,response_edge=12,value=eid))


def test_source_contract_and_native_widths():
    s=M.source_contract()
    assert s['ACK_after_last_service_delivery']
    assert s['local_writer_bits']==63 and s['local_root_bits']==69
    assert s['existing_external_VM_write_bits']==512
    assert not s['exclusive_VM_bridge_arbitration_present']


@pytest.mark.parametrize('n',[1,2,73,255,256])
def test_oldstate_clean_packet_exact_edges(n):
    p=M.packet(10,n)
    assert p['collect_edges']==list(range(10,10+n))
    assert p['send_edges']==list(range(10+n,10+2*n))
    assert p['service_accept_edges']==list(range(10+2*n,10+3*n))
    assert p['RX_ACK_NBA_edge']==10+3*n-1
    assert p['TX_ACK_accept_edge']==10+3*n
    assert p['exclusive_occupied_edges']==3*n+1


def test_sink_hold_delays_ack_credit_without_any_force_ready():
    p=M.packet(0,2,blocked_delivery=[4,5,7])
    assert p['service_accept_edges']==[6,8]
    assert p['TX_ACK_accept_edge']==9
    assert p['next_packet_accept_edge']==10


def test_real_timeout_boundary_not_healthy_constantfit():
    p=M.packet(0,1,reverse_edges=1023)
    assert p['TX_ACK_accept_edge']==1026 # source ACK takes priority at timeout edge
    with pytest.raises(ValueError,match='ACK_TIMEOUT'):M.packet(0,1,reverse_edges=1024)


def test_pipe_costs_add_and_input_fullblocks():
    a=M.packet(3,9);b=M.packet(3,9,forward_edges=4,reverse_edges=3)
    assert b['exclusive_occupied_edges']==a['exclusive_occupied_edges']+7
    packets=M.input_packets(0)
    assert [p['flits'] for p in packets]==[255,255,133]
    assert [p['VM_words'] for p in packets]==[127,127,66]
    assert sum(p['exclusive_occupied_edges'] for p in packets)==1932
    assert sum(len(p['postNBA_VM_commit_edges']) for p in packets)==320


def test_header_identity_and_bounds():
    c=command(383);h=M.encode_header(c,'input',127,127)
    assert M.decode_header(h,c,'input',127,127)
    for k in ['owner_stage','phase','rank','generation','user']:
        wrong=copy.deepcopy(c);wrong[k]+=1
        with pytest.raises(ValueError):M.decode_header(h,wrong,'input',127,127)
    c['generation']=1<<32
    with pytest.raises(ValueError):M.encode_header(c,'input',0,127)


def test_all384_resolved_descriptor_preserves_arithmetic():
    for eid in range(384):
        c=command(eid);d=M.resolved_descriptor(c)
        assert d['resolved_weight_base']==2097152+eid*4096
        assert d['changed_fields']==['qe_ind','qe_wbase']
        assert d['arithmetic_fields_byteidentical']
        assert not d['physical_command_injection_port_exists']


@pytest.mark.parametrize('args',[dict(reserved_rows=575,input_visible=True,VM_exclusive=True),
                                  dict(reserved_rows=576,input_visible=False,VM_exclusive=True),
                                  dict(reserved_rows=576,input_visible=True,VM_exclusive=False)])
def test_no_ready_go_requires_capture_and_input_lease(args):
    with pytest.raises(ValueError):M.CaptureReservation(command(),**args)


def capture():
    c=M.CaptureReservation(command(),input_visible=True,VM_exclusive=True)
    # Test burst full source capacity:128 independent roots on an edge.
    for row in range(576):c.capture(row,398720+row,0x45a00000,row%128,415+row//128)
    return c


def test_held_transport_all_source_rows_captured_without_ready():
    c=capture()
    assert len(c.rows)==576 and max(c.samples.values())==1
    with pytest.raises(ValueError):c.release_payload()
    c.source_terminal(True,False)
    assert c.release_payload()==[0x45a00000]*576
    with pytest.raises(ValueError):c.complete()
    for row in range(576):c.home_commit(row,1,0)
    c.debts.add('result')
    with pytest.raises(ValueError):c.complete()
    c.debts.clear();c.complete();assert c.owner_complete


def test_stale_poison_duplicate_and_alias_do_not_publish():
    c=capture();c.source_terminal(True,False)
    with pytest.raises(ValueError):c.home_commit(0,0,0)
    c.home_commit(0,1,0)
    with pytest.raises(ValueError):c.home_commit(0,1,0)
    with pytest.raises(ValueError):c.capture(0,398720,0,0,430)
    c.fault=True
    with pytest.raises(ValueError):c.release_payload()
    c=M.CaptureReservation(command(),input_visible=True,VM_exclusive=True)
    with pytest.raises(ValueError):c.capture(0,398720+(1<<19),0,0,415)
    c.capture(0,398720,0,0,415)
    with pytest.raises(ValueError):c.capture(1,398721,0,0,415)


def test_physical_boundary_is_not_payload_or_local_field_bus():
    assert M.boundary()['verdict']=='UNBOUND'
    provider=dict(forward_bits=256,reverse_bits=12,clock_ratio=1,route_identity='candidate0to1',source_pin='fixture',SS_FF_qualified=False)
    assert M.boundary(offered=provider)['verdict']=='FAIL_WIDTH'
    provider['forward_bits']=330
    b=M.boundary(offered=provider)
    assert b['verdict']=='WIDTH_SCREEN_PASS_CONTEXT_UNBOUND' and not b['physical_qualified']
    provider['clock_ratio']=2
    assert M.boundary(offered=provider)['verdict']=='UNBOUND_CLOCK_BRIDGE'


def test_forecast_exact_source_stages_exposes_positive_delta():
    f=M.forecast()
    assert f['command']['TX_ACK_accept_edge']==18
    assert f['input'][-1]['TX_ACK_accept_edge']==1950
    assert f['conditional_owner_op_accept']==1950
    assert f['conditional_phase_accept']==1953
    assert f['conditional_source_idle']==2360
    assert f['result']['TX_ACK_accept_edge']==3084
    assert f['home_last_postNBA_visibility']==3083
    assert f['terminal_receipt_edge']==3088
    assert f['conditional_delta_vs_original_I66_idle_edges']==2666
    assert not f['route_or_actual_acceptance_qualified']


def producer_receipt():
    p=M.reuse_source_proof()
    return dict(producer=p['producer'],word_sha256=p['producer_template_word_sha256'],rank=0,generation=1,user=0,
                accepted_words=5120,visible_words=5120,last_visible_edge=10)


def call(node='L0.I66',eid=288):
    b=next(r['binding'] for r in M.S.load(M.OUT/'inputs/selected_six_calls.json')['calls'] if r['binding']['node']==node)
    return M.resolve_call(node,eid,0,1,0,dict(accepted=True,address=b['selector_VM_element_address'],read_edge=11,response_edge=12,value=eid))


def test_source_immutable_X_w1_w3_proof_and_phase_colocation():
    p=M.reuse_source_proof()
    assert p['producer']=='L0.I52' and p['first_source_SU_retirement_fence']=='L0.I53'
    assert len(p['six_W1_consumers'])==len(p['additional_six_W3_consumers'])==6
    for eid in range(384):
        a=call('L0.I66',eid);b=call('L0.I67',eid)
        assert a['owner_stage']==b['owner_stage']
        assert a['key_word']!=b['key_word']
        assert M.resolved_descriptor(b)['resolved_weight_base']==b['key_word']&((1<<30)-1)
    assert not p['runtime_no_mutation_proof']


def test_reuse_once_and_per_expert_positive_wire_and_ack_price():
    a=M.reuse_price([288,289,290,291,292,293])
    assert a['input_copies_per_expert']==6 and a['input_copies_reuse']==1
    assert a['per_expert_serial_transport_edges']==16080
    assert a['reuse_serial_transport_edges']==6390
    assert a['serial_transport_edges_saved']==9690
    assert a['candidate_forward_edges']==a['candidate_reverse_edges']==1
    assert a['registered_input_lease_check_edges_per_remote_command']==1
    assert a['AQ_local_per_phase_unchanged'] and not a['quantization_relocated']
    assert a['real_full_program_critical_delta_edges'] is None
    b=M.reuse_price([288,289,290,291,292,293],W1_only=False)
    assert b['input_copies_per_expert']==12 and b['input_copies_reuse']==1
    assert b['reuse_serial_transport_edges']==10842
    c=M.reuse_price([288,289,290,291,292,293],receiver_stall_edges_per_packet=7)
    assert c['reuse_serial_transport_edges']>a['reuse_serial_transport_edges']


def test_X_lease_stays_until_last_causal_consumer_retired():
    consumers=M.reuse_source_proof()['six_W1_consumers']
    l=M.InputLease(1,0,1,0,consumers,producer_receipt())
    with pytest.raises(ValueError):l.use(call())
    l.input_visible(5120,0)
    for node in consumers:
        c=call(node);l.use(c)
        with pytest.raises(ValueError):l.release()
        with pytest.raises(ValueError):l.retire(c,True,576,1)
        l.retire(c,True,576,0)
    l.release();assert l.released
    with pytest.raises(ValueError):l.use(call())


@pytest.mark.parametrize('field',['rank','generation','user','xversion','x_VM_elements'])
def test_X_lease_rejects_wrong_version_layout_rank(field):
    c=call();l=M.InputLease(1,0,1,0,[c['node']],producer_receipt());l.input_visible(5120,0)
    if field=='x_VM_elements':c[field]=[46465,51585]
    else:c[field]+=1
    with pytest.raises(ValueError):l.use(c)


def test_X_lease_source_order_producer_and_stale_retirement():
    with pytest.raises(ValueError):M.InputLease(1,0,1,0,['L0.I68','L0.I66'],producer_receipt())
    p=producer_receipt();p['visible_words']=5119
    with pytest.raises(ValueError):M.InputLease(1,0,1,0,['L0.I66'],p)
    c=call();l=M.InputLease(1,0,1,0,[c['node']],producer_receipt());l.input_visible(5120,0);l.use(c)
    stale=copy.deepcopy(c);stale['generation']=0
    with pytest.raises(ValueError):l.retire(stale,True,576,0)


def test_static_mutants_intervening_writer_and_dynamic_copy(tmp_path,monkeypatch):
    import gzip,json
    original=json.load(gzip.open(M.OUT/'inputs/demand-r5.json.gz','rt'))
    for mutation in ['writer','copy','consumer']:
        x=copy.deepcopy(original)
        n=next(n for n in x['nodes'] if n['id']==('L0.I66' if mutation=='consumer' else 'L0.I74'))
        if mutation=='writer':n['instruction']['o_base']=46464
        elif mutation=='copy':n['instruction']['mx_m']=2
        else:n['instruction']['qe_xbase']=46465
        path=tmp_path/'inputs';path.mkdir(exist_ok=True)
        with gzip.open(path/'demand-r5.json.gz','wt') as f:json.dump(x,f)
        (path/'selected_six_calls.json').write_bytes((M.OUT/'inputs/selected_six_calls.json').read_bytes())
        M.reuse_source_proof.cache_clear()
        with monkeypatch.context() as m:
            m.setattr(M,'OUT',tmp_path)
            with pytest.raises(ValueError):M.reuse_source_proof()
        M.reuse_source_proof.cache_clear()


def test_compact_kernel_exact_full_source_width_no_rounding_changes():
    k=M.compact_kernel(call())
    assert k['bits']==208
    assert dict(k['source_fields'])['QE_NB']==8
    assert not k['original_arithmetic_or_rounding_changed']
    h=M.encode_header(call(),'command',0,1)
    assert h.bit_length()<=256
    assert sum(w for _,w in M.HEADER)==236


def test_peer_conservative_envelope_requires_priced_source_timeout():
    s=M.peer_envelope_screen()
    assert s['default_verdict']['verdict']=='FAIL_SOURCE_DEFAULT_TIMEOUT'
    assert s['peer_forward_edges']==s['peer_reverse_edges']==1337
    assert s['opt_in_ACK_TIMEOUT']==4096 and s['extra_timer_storage_bits']==0
    p=s['six_W1']
    assert p['input_copies_reuse']==1 and p['input_copies_per_expert']==6
    assert p['per_expert_serial_transport_edges']==112272
    assert p['reuse_serial_transport_edges']==62502
    assert p['serial_transport_edges_saved']==49770
    assert not s['source_PHY_pin_OBS_PG_clock_available']
    assert s['full_duplex_tracks']==684
    with pytest.raises(ValueError,match='ACK_TIMEOUT'):
        M.reuse_price([288,289,290,291,292,293],1337,1337,ACK_TIMEOUT=4096,receiver_stall_edges_per_packet=2000)
