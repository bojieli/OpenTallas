#!/usr/bin/env python3
"""Literal Popper callee RF port trace. Does not manufacture runtime receipts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h3_complete_native_calendar_20261002/pc40_source_ports_r10'
# Reachable normal-path states, taken from frozen case(phase), not R9 demand.
TRACE=('HOME_RD','HOME_RSP','A_WR','A_ACK','B_WR','B_ACK','WORK_RD','WORK_RSP',
       'ALU','OUT_WR','OUT_ACK','CONST_WR','CONST_ACK','FMAX_RD','FMAX_RSP',
       'FMAX_CAPTURE','FMAX_WRITE','FMAX_ACK','FENCE')
READS={'HOME_RD':(38,38),'WORK_RD':(17,18),'FMAX_RD':(17,18)}
WRITES={'A_WR':17,'B_WR':18,'OUT_WR':17,'CONST_WR':18,'FMAX_WRITE':19}


def need(ok,message):
    if not ok:raise ValueError(message)


def inputs():
    result={}
    for name,row in json.loads((BASE/'input_manifest.json').read_text()).items():
        raw=(BASE/'inputs'/name).read_bytes()
        need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'source pin '+name)
        result[name]=raw.decode()
    return result


def compile_ports(*, service_wait_bound=None, entering_live_leases=None):
    source=inputs();bridge=source['bridge.sv'];rf=source['RF.sv'];model=json.loads(source['model.json'])['model']
    # Refuse drift in the source transactions or the sole held-port credit.
    for token in ['!read_pending && !rsp_valid && !ack_valid','if(read_pending) begin rsp_a<=words_a[page_a];rsp_b<=words_b[page_b];rsp_valid<=1;',
                  'if(write_go) begin ack_valid<=1;', 'else if(ack_valid && ack_ready) ack_valid<=0;']:
        need(token in rf,'actual source RF held transaction contract')
    for token in ["phase==HOME_RD?9'd38:phase==WORK_RD?9'd17:9'd17", "phase==HOME_RD?9'd38:phase==WORK_RD?9'd18:9'd18",
                  "phase==A_WR?9'd17:phase==B_WR?9'd18:phase==OUT_WR?9'd17:phase==CONST_WR?9'd18:9'd19"]:
        need(token in bridge,'source actual RF address expression')
    for a,b in zip(TRACE,TRACE[1:]):
        line=next((s for s in bridge.splitlines() if s.strip().startswith(a+':')),None)
        need(line is not None and ('='+b+';' in line or a=='FENCE'),'source ordered reachable transition '+a)
    need(model['calendar']['event_edges']['RF_read']==9 and model['calendar']['event_edges']['RF_write']==10,'source3paired-read/5mirrored-write service inventory')
    if service_wait_bound is not None:
        need(type(service_wait_bound)is int and service_wait_bound>0,'positive prospective wait bound')
    if entering_live_leases is not None:
        need(all(set(x)>={'slot','lease'} for x in entering_live_leases),'typed entering live lease inventory')
        need(not any(x['slot'] in (17,18,19) for x in entering_live_leases),'actual entering workspace alias')
    events=[];edge=0;prior=None;RFheld=None;allocation={};read_pairs=0;writes=0;phases=[]
    def append(phase,cost,**extra):
        nonlocal edge,prior
        key='PC40/callee/'+str(len(events));events.append(dict(eventID=key,phase=phase,dependency=[] if prior is None else [prior],
            start_min_edge=edge,end_min_edge=edge+cost,source_clock='streaming_target_1.2GHz_UNQUALIFIED',
            accepted_receipt=False,**extra));prior=key;edge+=cost
    append('DISPATCH_W6_REQUEST',1,source='actual accept=req_valid&&req_ready and W6 req_valid=accept',
           source_owner='external issuer supplied; not synthesized by calendar')
    for phase in TRACE:
        phases.append(phase)
        if phase in READS:
            need(RFheld is None,'RF read while held ACK/response')
            RFheld=('read',phase);read_pairs+=1
            append(phase,1,read_a=READS[phase][0],read_b=READS[phase][1],physical_read_copies=2,
                   read_bits=8192,logical_unique_vectors=len(set(READS[phase])))
        elif phase.endswith('_RSP'):
            need(RFheld and RFheld[0]=='read','unowned RF response')
            append(phase,2,response_capture_bits=8192,held_until_actual_rsp_ready=True);RFheld=None
        elif phase in WRITES:
            need(RFheld is None,'RF write while read/ACK held')
            slot=WRITES[phase];RFheld=('write',slot);writes+=1
            if slot in allocation:
                need((phase=='OUT_WR' and 'WORK_RSP' in phases) or (phase=='CONST_WR' and 'ALU' in phases),'overwrite before actual source read/capture')
            allocation[slot]=phase
            append(phase,1,write_slot=slot,physical_mirror_copies=2,write_bits_per_copy=4096)
        elif phase.endswith('_ACK'):
            need(RFheld and RFheld[0]=='write','unowned common RF ACK')
            append(phase,1,ack_slot=RFheld[1],bare_ACK=True,physical_ACK_identity_fields=0,
                   retained_callee_identity=True,all_stale_copies_drained_proof='UNKNOWN');RFheld=None
        elif phase=='ALU':append(phase,3,native_steps=['BITCAST_U','XOR','BITCAST_F'],lane_local=True,RF_roundtrip=False)
        elif phase=='FMAX_CAPTURE':append(phase,1,leaf_pipeline_clock_edges=1,source_arithmetic='actual selected FMAX leaf; nonfinite fault retained')
        # W6 request and final RF/common host-ACK were already paid. Of its
        # nineteen positive protocol edges, reserve the remaining seventeen.
        elif phase=='FENCE':append(phase,17,W6_protocol_total_edges=19,W6_request_paid_once=1,W6_shared_host_ACK_paid_once=1,
                                 owner_supplied_by='issuer_binding_valid external producer UNKNOWN',
                                 W6_release='actual consumer/reverse/CDC/current allcopy handshake required',actual_receipt=None)
    need(RFheld is None and read_pairs==3 and writes==5,'complete finite RF source service')
    return dict(schema='PC40_SOURCE_PORT_CALENDAR_R10',source_commit='bfbcf472b',events=events,
                RF_read_pairs=read_pairs,RF_read_bits=read_pairs*8192,RF_writes=writes,RF_physical_mirror_write_bits=writes*8192,
                physical_RF_transaction_credits=1,read_write_simultaneous=False,read_ports=2,write_ports=1,mirrors=2,
                source_min_edge_obligations=edge,minimum_is_serial_reservation=True,W6_ACK_and_request_deduplicated=True,
                external_service_wait_bound_assumed=service_wait_bound,
                conditional_handshake_wait_terms=dict(dispatch=1,RF_request_ready=8,RF_response_or_ACK=8,W6_visibility_consumer_reverse_drain_retire=8),
                conditional_extra_wait_edges=None if service_wait_bound is None else 25*(service_wait_bound-1),
                conditional_source_reservation_edges=None if service_wait_bound is None else edge+25*(service_wait_bound-1),
                conditional_bound_scope='all25 handshake eligibilities independently withinB including issuer, exclusive RF and W6; prospective assumption, not installed proof',
                external_service_wait_bound_installed=False,finite_production_upper=None,
                live_workspace_scope='REFUSED_MISSING_ENTERING_LEASES' if entering_live_leases is None else 'PROSPECTIVE_DISJOINT_ALLOCATION',
                source_callee_workspace=[17,18,19],entering_live_leases=entering_live_leases,
                final_FMIN_source_consumer_payload_proof='UNKNOWN; live r2 work not source-frozen/adopted',
                W2_HBM_commands=0,parent55_fabricated=False,whole_token_ns=None,
                source_clock_cost_scope='positive prospective source edge reservations; not elapsed CPU time or measured clock',
                actual_RF_ACK_RESET_rearm_scope='bare common ACK retained sole context, issuer/allcopy/reset integration UNKNOWN')


def compose_caller(callee,caller):
    """Reconcile the actual retained gate/up source tuple, without allocating it.

    The callee's HOME read already pays the local gate read. The remote up
    source is an additional RF endpoint and NoC/CDC obligation, not HBM traffic.
    A shared event may be removed only after version/lease/slot identity match.
    """
    gate=caller['source_gate_home'];up=caller['source_up_home']
    need(caller['source_RF_read_services']==2 and caller['NoC_up_pages']==1 and caller['NoC_up_payload_bits']==4096,'actual caller source transport counts')
    need((gate['storage_rank'],gate['storage_SM'],gate['RFslot9'],gate['word_start'])==(0,0,38,0),'source gate read matches callee HOME tuple')
    need((up['storage_rank'],up['storage_SM'],up['RFslot9'],up['word_start'])==(0,24,32,6144),'actual remote up read, no synthetic local source')
    need(gate['version']==up['version']=='Qwen.39.L0.d0.gu_post.49' and gate['lease']==up['lease']=='value:Qwen.39.L0.d0.gu_post.49','actual released source caller lease')
    need(all(v['storage_class']=='RF' and v['HBM_byte_address'] is None and v['parent55'] is None for v in [gate,up]),'actual directRF caller, never HBM owner')
    home=next(e for e in callee['events'] if e['phase']=='HOME_RD')
    need((home['read_a'],home['read_b'])==(38,38),'matched callee RF event')
    return dict(schema='PC40_CALLER_CALLEE_PORT_JOIN_R10',callee=callee,
                gate_read_replacement=dict(removed='caller local gate RF read',retained_eventID=home['eventID'],
                    version=gate['version'],lease=gate['lease'],rank=0,SM=0,RFslot9=38,logical_words128=1,
                    both_physical_copies_still_paid=True),
                callee_RF_read_pairs=callee['RF_read_pairs'],additional_caller_up_RF_read_pairs=1,
                total_caller_callee_RF_read_pairs=callee['RF_read_pairs']+1,
                source_up_RF=dict(rank=0,SM=24,slot=32,word_start=6144,RF_read_payload_bits=8192,
                                  transport_payload_bits=4096,publication=up['publication_event'],lease=up['lease']),
                additional_caller_RF_source_min_edges=3,
                NoC_and_CDC_min_edge_inputs=None,NoC_and_CDC_max_edge_inputs=None,
                NoC_scope='one actual512B remote up page; no ideal overlap or zero transport price',
                caller_retained_slot_binding=caller['caller_retained_slot_binding'],
                caller_retained_slot_admission='REFUSED_UNBOUND' if caller['caller_retained_slot_binding'] is None else 'SOURCE_BINDING_REQUIRES_LIVE_LEASE_PROOF',
                gate_and_up_release='whole PC40 reciprocal and final ordered products; never leaf FMAX/FMIN release',
                next_consumer_RF19_read_extra=None,next_consumer_scope='await frozen Popper r2 consumer; not charged from mutable WIP',
                production_admitted=False,whole_token_ns=None)


def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
    callee=compile_ports();caller=json.loads(inputs()['caller.json'])
    raw=(json.dumps(compose_caller(callee,caller),sort_keys=True,indent=2)+'\n').encode();path=BASE/'calendar_caller_join_r3.json'
    if a.verify:need(path.read_bytes()==raw,'exact source port calendar replay')
    else:need(not path.exists() or path.read_bytes()==raw,'immutable evidence overwrite refused');path.write_bytes(raw)
    print('PASS source3pairedreads/5mirroredwrites; actual lease/ACK/reset integration UNKNOWN')


if __name__=='__main__':main()
