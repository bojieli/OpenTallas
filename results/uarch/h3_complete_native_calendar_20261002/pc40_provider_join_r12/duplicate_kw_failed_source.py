#!/usr/bin/env python3
"""Join released PC40 payload, concrete source homes and finite RF/NoC obligations.

No numerical execution, RTL launch, fabricated ready/ACK, or token-rate adoption.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results/uarch/h3_complete_native_calendar_20261002/pc40_provider_join_r12'


def need(value, message):
    if not value:
        raise ValueError(message)


def load(directory=BASE):
    result = {}
    for name, pin in json.loads((directory/'input_manifest.json').read_text()).items():
        raw = (directory/'inputs'/name).read_bytes()
        need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'], 'source pin '+name)
        result[name] = raw
    return result


def payload_binding(inputs):
    c, t = (json.loads(inputs[k]) for k in ('capture.json','terminal.json'))
    need(c['native_PC']==40 and c['template']=='exp' and c['step']==0 and c['opcode']=='FMAX', 'literal native PC40 exp step0')
    need(c['source_call_complete'] and t['verdict']=='PASS' and t['oracle_only_after_capture'] and not t['oracle_input_injection'], 'actual producer before oracle')
    owner = c['actual_gate_owner']
    need(owner['source_key']==['RF',0,0,38] and owner['published'] and not c['source_gate_lease_released'], 'actual entering gate home/lease')
    for name, spec in c['frames'].items():
        raw = inputs[spec['file']]
        need(len(raw)==spec['bytes']==512 and hashlib.sha256(raw).hexdigest()==spec['sha256'], 'actual captured frame '+name)
        compare = t['comparisons'][name]
        need(compare['words']==128 and compare['bit_mismatches']==0 and compare['actual_nonfinite']==0 and compare['expected_sha256']==spec['sha256'], 'checkpoint comparison '+name)
    need(owner['mirror_word_sha256']==c['frames']['gate']['sha256'], 'actual RF mirror word bytes')
    return dict(gate_owner=owner,frame_pins=c['frames'],checkpoint_revision=c['checkpoint_revision'],
                checkpoint_payload_pass=True,hardware_handshake_observed=c['real_RF_or_HBM_handshake'],
                up_payload_captured=False,source_gate_released=False,numerical_execution_in_calendar=False)


def source_contract(inputs):
    bridge, consumer = (inputs[k].decode() for k in ('bridge.sv','consumer.sv'))
    for token in ["phase==HOME_RD?9'd38", "phase==A_WR?9'd17", "phase==B_WR?9'd18", "phase==CONST_WR?{128{32'hc2ae0000}}", 'remote_wr_valid=0', 'host_ack_valid(live && phase==FMAX_ACK && local_ack_valid)', '!local_ack_valid && !remote_ack_valid && !local_rsp_valid']:
        need(token in bridge, 'source callee control/ACK '+token)
    for token in ["rd_a=9'd19;assign rd_b=9'd19", "b=32'h42b00000", 'OUTPUT_VALUE:if(result_ready)', 'ACK:if(consumer_ready)', 'visible_identity']:
        need(token in consumer, 'literal actual FMIN/owner '+token)
    for token in ['phase==VISIBLE && age_ok', 'phase==CONSUMER && age_ok', 'phase==CDC && cdc_age_ok', '(&alldrain_live)', 'raw[70:69]>=1', 'raw[70:69]>=2']:
        need(token in inputs['W6.sv'].decode(), 'W6 actual boundary age/debt '+token)
    need('[31:0][4095:0] host_rsp_a,host_rsp_b' in inputs['RF_context.sv'].decode(), 'physical32SM pairedRF context')
    model = json.loads(inputs['connected_model.json'])['model']
    need(model['ports']['RF_read_commands']==4 and model['ports']['RF_write_commands']==5 and model['ports']['HBM_commands']==0, 'source physical RF inventory')
    return model


def schedule(events, known_external, service_bounds=None):
    """Serialize actual endpoint resources; unknown cost remains unknown.

    Numeric times are local source-clock reservations after supplied external
    publications. Missing transport/lease cost propagates only to consumers of
    that path; independent gate work remains schedulable. No ideal overlap is
    assumed for shared resources. An upper bound requires every service term.
    """
    bounds = service_bounds or {}
    finish = dict(known_external)
    port_end = {}
    result = []
    for event in events:
        need(event['eventID'] not in finish, 'duplicate event or double charge')
        need(all(d in finish for d in event['deps']), 'missing causal producer')
        cost = event['min_edges']
        if cost is None and event['eventID'] in bounds:
            supplied = bounds[event['eventID']]
            need(type(supplied['min_edges']) is int and supplied['min_edges']>0 and supplied.get('source_pin'), 'positive source-pinned service required')
            cost = supplied['min_edges']
        need(cost is None or type(cost) is int and cost>0, 'unknown is not zero')
        resource = event['resource']
        predecessors = [finish[d] for d in event['deps']]+[port_end.get(resource,0)]
        start = None if any(v is None for v in predecessors) else max(predecessors, default=0)
        end = None if start is None or cost is None else start+cost
        finish[event['eventID']] = end
        port_end[resource] = end
        result.append(dict(event,start_min_edges=start,end_min_edges=end,resolved_min_edges=cost))
    return result


def compile_join(inputs, *, entering_leases=None, transport=None):
    payload = payload_binding(inputs)
    model = source_contract(inputs)
    caller = json.loads(inputs['caller.json'])
    gate, up = caller['source_gate_home'], caller['source_up_home']
    need((gate['storage_rank'],gate['storage_SM'],gate['RFslot9'],gate['word_start'])==(0,0,38,0), 'actual RF38 source tuple')
    need((up['storage_rank'],up['storage_SM'],up['RFslot9'],up['word_start'])==(0,24,32,6144), 'actual remote RF32 source tuple')
    need(gate['version']==up['version']==payload['gate_owner']['version'] and gate['lease']==up['lease']==payload['gate_owner']['lease'], 'same actual producer version/lease')
    need(all(h['storage_class']=='RF' and h['parent55'] is None and h['HBM_byte_address'] is None for h in (gate,up)), 'no invented HBM parent')
    if entering_leases is not None:
        need(all(set(x)>={'rank','SM','slot','lease'} and x['lease'] for x in entering_leases), 'typed entering lives')
        need(not any(x['rank']==0 and x['SM']==0 and x['slot'] in (17,18,19) for x in entering_leases), 'actual workspace lease alias')
    events = []
    def add(key, deps, resource, edges, **extra):
        events.append(dict(eventID=key,deps=deps,resource=resource,min_edges=edges,
                           clock='component_streaming_target_1.2GHz_UNQUALIFIED',accepted_receipt=False,**extra))
    gate_pub, up_pub = gate['publication_event'], up['publication_event']
    # External publication times are not charged again. Zero is the relative
    # origin AFTER supplied publication, not a zero-cost producer execution.
    add('up.RF32_read_pair',[up_pub],'rank0/SM24/RF_sole_credit',3,read_slots=[32,32],physical_read_bytes=1024,lease=up['lease'])
    add('up.NoC_SM24_SM0',['up.RF32_read_pair'],'rank0/NoC_SM24_SM0',None,payload_bytes=512,
        source_home=[0,24,32,6144],destination_home=None,destination_lease=None,
        source_lease_held_until='actual full PC40 products and validated reverse')
    add('up.publication_at_SM0',['up.NoC_SM24_SM0'],'rank0/SM0/up_capture_owner',None,
        payload_bytes=512,caller_retained_slot_binding=caller['caller_retained_slot_binding'])
    prior = gate_pub
    def local(key, edges, **extra):
        nonlocal prior
        add(key,[prior],'rank0/SM0/RF_and_exclusive_PC40_caller',edges,**extra)
        prior = key
    local('callee.accept_owner55_workspace',2,owner55='accepted opaque owner46 + RFslot19',native_identity_bits=128,physical_ACK_identity_bits=0,slots=[17,18,19])
    local('gate.HOME_RF38_read_pair',3,read_slots=[38,38],physical_read_bytes=1024,frame_sha256=payload['frame_pins']['gate']['sha256'])
    for name,slot in [('gate.A_write_ACK',17),('NEG.mask_write_ACK',18)]:
        local(name,2,write_slot=slot,physical_mirror_write_bytes=1024,ACK='bare common ACK in sole held context; reset drain proof required')
    local('NEG.WORK_read_pair',3,read_slots=[17,18],physical_read_bytes=1024)
    local('NEG.bitcast_XOR_bitcast',3,arithmetic=['BITCAST_U','XOR','BITCAST_F'],mask=0x80000000)
    local('NEG.write17_ACK',2,write_slot=17,physical_mirror_write_bytes=1024,frame_sha256=payload['frame_pins']['negative']['sha256'])
    local('FMAX.constant18_write_ACK',2,write_slot=18,physical_mirror_write_bytes=1024,literal_bits=0xc2ae0000)
    local('FMAX.read_pair',3,read_slots=[17,18],physical_read_bytes=1024)
    local('FMAX.compute',3,source_ref='Qwen PC40/exp/step0',clock_cost='selected connected model; positive prospective source edges')
    local('FMAX.write19_ACK',2,write_slot=19,physical_mirror_write_bytes=1024,frame_sha256=payload['frame_pins']['FMAX']['sha256'])
    # W6 age boundaries are post-ACK; no debit for unrelated request/ACK.
    add('W6.ACK_to_visible',['FMAX.write19_ACK'],'rank0/SM0/W6',2,
        visible_owner55='same accepted issuer owner46+19')
    add('W6.visible_to_consumer_ready',['W6.ACK_to_visible'],'rank0/SM0/W6',2)
    add('FMIN.RF19_read_pair',['W6.ACK_to_visible'],'rank0/SM0/RF_and_exclusive_PC40_caller',3,
        read_slots=[19,19],physical_read_bytes=1024)
    add('FMIN.compute',['FMIN.RF19_read_pair'],'rank0/SM0/RF_and_exclusive_PC40_caller',2,
        source_ref='Qwen PC40/exp/step1',literal_bits=0x42b00000)
    add('FMIN.held_value_accept',['FMIN.compute'],'rank0/SM0/consumer_result',None,payload_bytes=512)
    # Structural consumer handshake is shared with FMIN, so use its existing
    # completion dependency instead of charging a second acceptance operation.
    reverse_deps = ['FMIN.held_value_accept','W6.visible_to_consumer_ready']
    for key,edges in [('consumer_to_child_reverse',2),('child_to_parent_reverse',2),
                      ('parent_to_reverse_CDC',3),('reverse_CDC_to_drain_request',2),
                      ('drain_request_to_allcopies',2),('allcopies_to_retire',2),
                      ('retire_to_new_accept',2)]:
        add('W6.'+key,reverse_deps,'rank0/SM0/W6',edges,
            matched_owner55_required=True,accepted_receipt=False,
            external_ready_or_current_drain_bound=None)
        reverse_deps = ['W6.'+key]
    add('PC40.final_product_source_join',['up.publication_at_SM0','FMIN.held_value_accept'],'rank0/SM0/full_PC40_products',None,
        source_scope='remaining exp/reciprocal/ordered SILU products not implemented by this component',releases_gate_or_up=False)
    rows = schedule(events,{gate_pub:0,up_pub:0},transport)
    return dict(schema='ACTUAL_PC40_PROVIDER_CALENDAR_R12',payload=payload,events=rows,
        source_callee='8c3dfbf79',requested_owner55_successor_bb3='NOT_LOCALLY_RESOLVED; no silent substitution',
        physical_RF_reads=5,RF_response_bus_bytes=5120,physical_mirror_writes=5,RF_write_bytes=5120,
        NoC_payload_bytes=512,source_gate=gate,source_up=up,
        workspace_entering=entering_leases,workspace_admission='REFUSED_MISSING_ENTERING_LEASES' if entering_leases is None else 'SOURCE_DISJOINT_ONLY',
        W6_boundary_edges=19,W6_through_retire_edges=17,W6_next_accept_edges=2,
        W6_request_and_RF_ACK_subtracted=False,calibration=model['cost_events'],
        fullshape_transport_min=None,finite_production_upper=None,
        source_owner55_producer='accepted external issuer binding required; no owner allocated by this calendar',
        physical_common_ACK_tag_bits=0,reset_allcopy_issuer_bound=False,
        lease_release='full PC40 completion + validated reverse, not FMIN',
        W2_HBM_commands=0,I64_or_RMW_recharged=False,
        paid_replacement='exact matched PC40 R9/R10 subtree; never add over original costs',
        headline_adoption=False,physical_qualified=False,whole_token_ns=None,
        observed_protocol_waits=False,minimum_edges_are_not_finite_upper_bounds=True,
        legacy_R10_W6_subtraction='UNADOPTED: 19 is post-ACK; retain old record, replace selected cost once',
        unknowns=['up payload not captured by 93b leaf proof','NoC port width/service and actual retained destination home',
                  'actual entering workspace17/18/19 lives','issuer owner55/reset/allcopies producer',
                  'actual visibility/consumer/reverse/drain acceptance trace','full PC40 downstream native arithmetic and waits'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');a=p.parse_args()
    raw=(json.dumps(compile_join(load()),indent=2,sort_keys=True)+'\n').encode()
    target=BASE/'calendar.json'
    if a.verify:need(target.read_bytes()==raw,'cold calendar byte replay')
    else:need(not target.exists(),'immutable artifact overwrite');target.write_bytes(raw)
    print(json.dumps(dict(sha256=hashlib.sha256(raw).hexdigest(),events=len(json.loads(raw)['events']),
                         read_pairs=5,mirror_write_bytes=5120,NoC_payload_bytes=512,production_upper=None)))

if __name__=='__main__':main()
