import copy, json, sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_selected_stage_provider as M

@pytest.fixture(scope='module')
def model():return M.build()

def test_frozen_model_inputs_and_source_contract(model):
    assert len(model['source_pins'])==7
    assert model['provider_id']=='S58-NN-STAGE-LINK-PRELOAD-CAPTURE-v1'
    assert model['topology']['I66_owner_counts']=={'0':288,'1':96}
    assert model['topology']['logical_links']==228
    assert model['ports']['command_bits']==221
    assert model['ports']['forward_total_bits']==330
    assert model['ports']['reverse_ACK_ready_credit_bits']==12

@pytest.mark.parametrize('n',[1,2,131,143,256])
def test_independent_NBA_packet_state_recurrence(n):
    # Independent explicit state traversal with two edge wire/ACK delays.
    t=17;collect=[];send=[];receive=[];deliver=[]
    state='COLLECT';k=0
    while state!='DONE':
        if state=='COLLECT':
            collect.append(t);k+=1
            if k==n:state='SEND';k=0
        elif state=='SEND':
            send.append(t);receive.append(t+2);k+=1
            if k==n:state='DELIVER';k=0;t=receive[-1]
        elif state=='DELIVER':
            deliver.append(t);k+=1
            if k==n:state='ACK';t+=2
        elif state=='ACK':ack=t;state='DONE'
        t+=1
    p=M.packet(17,n,2,2)
    assert p['last_collect']==collect[-1]
    assert p['last_send']==send[-1]
    assert p['last_receive']==receive[-1]
    assert p['last_deliver']==deliver[-1]
    assert p['matching_positive_ACK_seen']==ack
    assert p['next_packet_credit']==ack+1

@pytest.mark.parametrize('args',[(0,0,1,1),(0,257,1,1),(0,1,0,1),(0,1,1,0)])
def test_nonpositive_or_oversize_service_refused(args):
    with pytest.raises(ValueError):M.packet(*args)

def test_default_timeout_cannot_adopt_requested_spatial_envelope(model):
    f=model['spatial']['forward_route_CDC_PHY_envelope_edges']
    with pytest.raises(ValueError,match='timeout'):M.packet(0,256,f,f,timeout=1024)
    p=M.packet(0,256,f,f,timeout=model['timeout']['proposed_ACK_TIMEOUT'])
    assert p['TX_WAIT_ACK_edges']==model['timeout']['required_successful_max_edges']
    assert model['timeout']['default_screen_PASS'] is False

def test_transport_packetization_conserves_full_input_result(model):
    assert M.chunks(5120*32)==[256,256,131]
    assert M.chunks(576*63)==[143]
    assert (sum(M.chunks(5120*32))-3)*256==5120*32
    assert (143-1)*256>=576*63
    assert sum(model['ports']['packet_header_fields'].values())==128

@pytest.mark.parametrize('capacity',[64,128,256,575])
def test_no_ready_root_reservation_is_before_GO(capacity):
    with pytest.raises(ValueError):M.CaptureLease(capacity,('phase10','EID0','generation1'))

def test_root_visibility_ACK_and_owner_idle_all_required():
    id=('phase10','EID0','generation1');x=M.CaptureLease(576,id)
    for row in range(576):x.capture(row,id,414+row//128)
    with pytest.raises(ValueError):x.retire(id,True)
    with pytest.raises(ValueError):x.capture(0,id,419)
    with pytest.raises(ValueError):x.destination(0,id,414)
    with pytest.raises(ValueError):x.destination(0,('wrongphase',),450)
    for row in range(576):x.destination(row,id,1000+row//4)
    with pytest.raises(ValueError):x.retire(id,True)
    x.owner_idle=True
    with pytest.raises(ValueError):x.retire(id,False)
    assert x.retire(id,True)

def test_input_fence_precedes_dispatch_and_native_service(model):
    c=model['calendar'];p=c['packets']
    assert c['input_last_visible']<p[3]['first_collect']<c['owner_native_origin']
    assert c['shifted_EID0_template_owner_idle']-c['owner_native_origin']==412
    assert p[4]['first_collect']>c['shifted_EID0_template_last_root']
    assert c['all_delivery_owner_debt_retired']>c['final_destination_visible']
    assert c['strictly_positive_intrinsic_source_store_forward_delta_edges']==2377
    assert c['extra_critical_path_edges']==17073
    assert c['extra_destination_visibility_edges']==13060
    assert c['prefetch_lead_needed_to_keep_original_owner_origin_edges']==11294
    assert c['result_last_visibility_delta_even_if_entire_input_prefetched_edges']==1766
    assert c['extra_critical_path_us_conditional']==14.2275

def test_link_buffer_credit_never_reuses_on_send_or_timeout(model):
    for p in model['calendar']['packets']:
        assert p['next_packet_credit']>p['matching_positive_ACK_seen']>p['last_deliver']>p['last_send']
    d,_=M.inputs()
    # Source duplicate multi-flit first-flit ACK is a separate explicit gate.
    assert "link_packet_seq == expected_seq - 1'b1" in d['rx.sv']
    assert model['timeout']['source_multi_flit_duplicate_ACK_first_flit_behavior_requires_gate']

def test_current_cfg72_receipt_not_weight274_clock_transfer(model):
    c=model['configuration']
    assert c['actual_macro_SS_clkq_ps']==pytest.approx(667.0755828482402)
    assert c['single_edge_remaining_before_setup_wire_skew_ps']==pytest.approx(106.2577504850932)
    assert c['actual_setup_mux_wire_clock_ps'] is None

def test_area_scope_and_missing_costs_do_not_become_fit_or_rate(model):
    a=model['area'];s=model['spatial']
    assert a['source_endpoint_state_bits']==65536*2+98+89
    assert a['root_capture_added_bits']==576*69+128
    assert s['full_duplex_directional_tracks']==684
    assert s['source_horizontal_layer']=='M4'
    assert s['proposed_neighbor_strips_mm']['west'][2]<s['proposed_neighbor_strips_mm']['east'][0]
    assert s['channel_width_with_halfpool_reservation_um']==65.664
    assert a['updated_screen_mm2']==pytest.approx(755.0646357267658+2*(.75+65.664*21459.76/1e6))
    assert a['packing_proven'] is False
    assert a['CRC_decoder_mux_clock_reset_PG_hold_extra_unpriced']
    assert model['calendar']['whole_token_delta'] is None
    assert not model['calendar']['no_token_loss_proven']
    assert not model['physical_build_admitted']
    assert not model['full_token_rate_qualified']
    assert model['spatial']['source_stage_package_distance_um'] is None


def test_capacity_is_not_raw_link_width_or_infinite_issue(model):
    p=model['parallel_capacity_requirements']
    assert p['minimum_data_link_lanes_for_one_VM_beat_per_edge']==9
    assert p['one_VM_beat_credit_interval_even_with_minimal_positive_wire_edges']==30
    assert p['required_one_packet_endpoint_contexts_if_no_prefetch_and_one_VM_beat_per_edge']==30
    assert p['root_writer_payload_minimum_link_flits_per_edge']==32
    assert p['prefetch_available_window_from_actual_issue_graph'] is None
    assert model['compute_and_communication']['provider_MACs_per_cycle']==0
    assert model['compute_and_communication']['source_paired_CE_total']==23040
