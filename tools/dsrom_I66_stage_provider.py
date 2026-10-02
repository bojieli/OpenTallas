#!/usr/bin/env python3
"""Opt-in software composition of current TX/RX source for remote S58 I66.
This is a candidate packet/capture ABI and source-calendar model, not an RTL
provider, PHY fit, measured remote execution, or full-token no-loss proof.
"""
import argparse
import collections
import copy
import hashlib
import gzip
import functools
import json
import re
from pathlib import Path
import dsrom_I66_stage_dispatch as D
P=D.P;J=D.J;S=D.S
OUT=S.ROOT/'results/uarch/dsrom_I66_stage_provider_20261002'
# Candidate SOFTWARE packet header. Widths beyond original source ports are
# explicit proposed ABI costs; they are not existing hardware declarations.
HEADER=[('magic',32),('kind',3),('stage',6),('rank',2),('eid',9),('phase',10),
        ('key',32),('generation',32),('user',32),('offset',19),('count',13),('pc',14),('xversion',32)]
MAGIC=0x49363601
KINDS={'command':0,'input':1,'result':2,'complete':3}


def source_contract():
    tx=(D.OUT/'inputs/stage_link_tx.sv.txt').read_text()
    rx=(OUT/'inputs/stage_link_rx.sv.txt').read_text()
    ep=(OUT/'inputs/stage_link_endpoint.sv.txt').read_text()
    core=(P.OUT/'inputs/core.sv.txt').read_text()
    tile=(P.OUT/'inputs/tile.sv.txt').read_text()
    assert 'if (out_fire && out_last)' in rx
    assert 'ack_valid <= 1\'b1;' in rx and 'expected_seq <= packet_seq + 1\'b1;' in rx
    assert 'assign out_valid = (state == ST_DELIVER);' in rx
    assert 'link_packet_seq != expected_seq - 1\'b1' in rx
    assert 'ST_WAIT_ACK' in tx and 'ACK_TIMEOUT = 1024' in tx
    assert '.abort(1\'b0)' in ep
    assert '.VAW(AW)' in core and 'AW   = FULL_SHAPE ? 30 : 24' in core
    assert 'if (xb_we4[b])' in tile and 'xb_wdata4[b*512 + 32*e +: 32]' in tile
    assert 'vm[{xb_raddr, 4\'(e)}]' in tile
    return dict(FLIT_W=256,MAX_FLITS=256,SEQ_W=8,ACK_TIMEOUT=1024,RETRY_MAX=2,
                tx_packet_credit=1,rx_packet_credit=1,ACK_after_last_service_delivery=True,
                abort_input_tied_low_in_existing_endpoint=True,physical_serialization_outside_wrapper=True,
                local_writer_bits=63,local_root_bits=69,VM_address_bits=19,
                existing_external_VM_write_bits=512,external_VM_read_bits=512,
                exclusive_VM_bridge_arbitration_present=False)


def encode_header(command,kind,offset,count):
    values=dict(magic=MAGIC,kind=KINDS[kind],stage=command['owner_stage'],rank=command['rank'],
                eid=command['expert'],phase=command['phase'],key=command['key_word'],
                generation=command['generation'],user=command['user'],offset=offset,count=count,
                pc=int(command['node'].split('I')[1]),xversion=command.get('xversion',0))
    word=0;shift=0
    for name,width in HEADER:
        v=values[name]
        if type(v)!=int or not 0<=v<1<<width:raise ValueError('candidate header overflow: '+name)
        word|=v<<shift;shift+=width
    assert shift<=256
    return word


def decode_header(word,command,kind,offset,count):
    if word!=encode_header(command,kind,offset,count):
        raise ValueError('stale/misrouted/header identity mismatch')
    return True


def resolved_descriptor(command):
    """Only two CONTROL fields change, originals are never overwritten.
    Source already supports nonindexed q_go: key=q_wbase; S_IDLE->S_LOOK.
    This removes the second remote EID read, not its original actual provenance.
    All rounding, operand, geometry, predicate and output fields stay byteexact.
    """
    calls=S.load(OUT/'inputs/selected_six_calls.json')['calls']
    record=next(r for r in calls if r['binding']['node']==command['node'])
    word=int(record['word']['word_hex'],16)
    pkg=(OUT/'inputs/isa_full.svh.txt').read_text()
    layout={name:(int(re.search(r'O_'+name+r' = (\d+);',pkg)[1]),
                  int(re.search(r'W_'+name+r' = (\d+);',pkg)[1])) for name in ['QE_IND','QE_WBASE','QE_MODE']}
    def get(w,name):
        off,width=layout[name];return (w>>off)&((1<<width)-1)
    if get(word,'QE_IND')!=1 or get(word,'QE_MODE')!=0:raise ValueError('wrong original instruction branch')
    original=word
    for name,value in [('QE_IND',0),('QE_WBASE',command['key_word']&((1<<30)-1))]:
        off,width=layout[name];mask=((1<<width)-1)<<off
        if not 0<=value<1<<width:raise ValueError('descriptor key truncation')
        word=(word&~mask)|(value<<off)
    allowed=sum(((1<<layout[n][1])-1)<<layout[n][0] for n in ['QE_IND','QE_WBASE'])
    if (original^word)&~allowed:raise ValueError('arithmetic/other control field changed')
    return dict(original_word_sha256=hashlib.sha256(original.to_bytes(256,'little')).hexdigest(),
                candidate_word_sha256=hashlib.sha256(word.to_bytes(256,'little')).hexdigest(),
                word_hex=f'{word:0512x}',changed_fields=['qe_ind','qe_wbase'],
                resolved_weight_base=get(word,'QE_WBASE'),arithmetic_fields_byteidentical=True,
                physical_command_injection_port_exists=False)


KERNEL_FIELDS=[('QE_WBASE',30),('QE_XBASE',30),('MX_XPS',30),('QE_OBASE',30),('MX_OPS',30),
               ('MX_M',3),('QE_UNROUNDED',1),('QE_IND',1),('QE_MODE',2),('QE_FP4',1),
               ('QE_NB',8),('QE_NOUT',21),('QE_TILES',21)]


def compact_kernel(command):
    descriptor=resolved_descriptor(command);word=int(descriptor['word_hex'],16)
    pkg=(OUT/'inputs/isa_full.svh.txt').read_text();payload=0;shift=0
    for name,width in KERNEL_FIELDS:
        off=int(re.search(r'O_'+name+r' = (\d+);',pkg)[1])
        actual=int(re.search(r'W_'+name+r' = (\d+);',pkg)[1])
        if width!=actual:raise ValueError('kernel source width mismatch '+name)
        payload|=((word>>off)&((1<<width)-1))<<shift;shift+=width
    assert shift==208
    return dict(word=payload,bits=shift,source_fields=KERNEL_FIELDS,
                omitted_instruction_fields='home scheduler dependencies already satisfied at actual indexed-response; direct source-adapter injection still unimplemented',
                original_arithmetic_or_rounding_changed=False)


def packet(start,n,collect_edges=None,forward_edges=0,reverse_edges=0,blocked_delivery=(),ACK_TIMEOUT=1024):
    """Healthy source TX+RX old-state edge calendar, synchronous clocks.
    No ready is forced: blocked sink edges postpone out_fire. Counter-triggered
    retries are reported unsupported, never silently modeled as healthy ACK.
    forward/reverse edges are explicit proposed pipe costs, not measured PHY.
    """
    if not 1<=n<=256 or start<0 or forward_edges<0 or reverse_edges<0 or ACK_TIMEOUT<1:
        raise ValueError('illegal packet/pipe geometry')
    collect=list(range(start,start+n)) if collect_edges is None else list(collect_edges)
    if len(collect)!=n or collect!=sorted(set(collect)) or collect[0]!=start:
        raise ValueError('invalid accepted TX collect edges')
    send=list(range(collect[-1]+1,collect[-1]+1+n))
    arrive=[t+forward_edges for t in send]
    deliver=[];edge=arrive[-1]+1;blocked=set(blocked_delivery)
    while len(deliver)<n:
        if edge not in blocked:deliver.append(edge)
        edge+=1
    ack_emit=deliver[-1];ack_observe=ack_emit+1+reverse_edges
    # ACK matching takes priority over timeout on the exact same edge.
    timeout_edge=send[-1]+ACK_TIMEOUT+1
    if ack_observe>timeout_edge:raise ValueError('actual source ACK_TIMEOUT triggers retry; clean calendar not applicable')
    return dict(flits=n,collect_edges=collect,send_edges=send,RX_capture_edges=arrive,
                service_accept_edges=deliver,RX_ACK_NBA_edge=ack_emit,TX_ACK_accept_edge=ack_observe,
                next_packet_accept_edge=ack_observe+1,exclusive_occupied_edges=ack_observe-start+1,
                successful_ACK_is_not_owner_completion=True,actual_runtime=False)


def input_packets(start,forward_edges=0,reverse_edges=0,ACK_TIMEOUT=1024):
    # Even payload flits preserve full512b VM words; no partial block overwrite.
    packets=[];offset=0
    for payload in [254,254,132]:
        p=packet(start,payload+1,forward_edges=forward_edges,reverse_edges=reverse_edges,ACK_TIMEOUT=ACK_TIMEOUT)
        p['VM_word_offset']=offset;p['VM_words']=payload//2
        p['postNBA_VM_commit_edges']=p['service_accept_edges'][2::2]
        assert len(p['postNBA_VM_commit_edges'])==payload//2
        packets.append(p);offset+=payload//2;start=p['next_packet_accept_edge']
    assert offset==320
    return packets


class CaptureReservation:
    """Software model of source no-ready obligation, all576 row slots before GO.
    The source64ports/shard must write independently; no shared ready/ACK pool.
    Hardware banking/placement and per-phase root-home map are still unbound.
    """
    def __init__(self,command,reserved_rows=576,input_visible=False,VM_exclusive=False):
        if reserved_rows!=576 or not input_visible or not VM_exclusive:
            raise ValueError('cannot GO: full capture/input/VM lease missing')
        if command['x_VM_elements']!=[46464,51584] or command['output_VM_elements'][1]-command['output_VM_elements'][0]!=576 or command['output_VM_elements'][0]%16:
            raise ValueError('wrong descriptor extent')
        if command['output_VM_elements'][1]>1<<19:raise ValueError('AW alias forbidden')
        self.command=copy.deepcopy(command);self.output_base=command['output_VM_elements'][0];self.rows={};self.fault=False;self.source_idle=False
        self.owner_complete=False;self.home_visible=set();self.debts=set();self.samples=collections.Counter()

    def capture(self,row,address,data,root,edge,poison=False):
        if not 0<=row<576 or row in self.rows or address!=self.output_base+row or not 0<=root<128 or not 0<=data<1<<32:
            raise ValueError('duplicate/misowned source capture')
        # No drain is needed for accepting another source writer row.
        self.rows[row]=(data,root,edge);self.samples[(edge,root)]+=1
        if self.samples[(edge,root)]!=1:raise ValueError('source root port overbooked')
        self.fault|=poison

    def source_terminal(self,idle,fault,edge=None):
        if edge is not None and self.rows and edge<=max(r[2] for r in self.rows.values()):
            raise ValueError('source idle is not after last accepted capture')
        self.source_idle=bool(idle);self.fault|=bool(fault)

    def release_payload(self):
        if len(self.rows)!=576 or not self.source_idle or self.fault:
            raise ValueError('unchecked/incomplete/quarantined source cannot publish')
        return [self.rows[i][0] for i in range(576)]

    def home_commit(self,row,generation,user):
        if generation!=self.command['generation'] or user!=self.command['user'] or row in self.home_visible:
            raise ValueError('stale/duplicate home commit')
        self.release_payload()
        if not 0<=row<576:raise ValueError('home row outside owned extent')
        self.home_visible.add(row)

    def complete(self):
        self.release_payload()
        if len(self.home_visible)!=576 or self.debts:raise ValueError('home visibility/accepted packet debt remains')
        self.owner_complete=True


def forecast(response_edge=12,forward_edges=0,reverse_edges=0,ACK_TIMEOUT=1024):
    """Representative EID0 same-native-service template only, not remote run.
    New control branch S_IDLE->S_LOOK removes two indexed read states.
    Field phase-to-idle407 is observed only for EID0/rank0, other mappings unbound.
    """
    command=packet(response_edge,2,forward_edges=forward_edges,reverse_edges=reverse_edges,ACK_TIMEOUT=ACK_TIMEOUT)
    inputs=input_packets(command['next_packet_accept_edge'],forward_edges,reverse_edges,ACK_TIMEOUT)
    # Last accepted512b VM write is postNBA visible at last RX delivery;
    # native GO can see it on the following edge, coincident with zero-wire ACK.
    op=inputs[-1]['service_accept_edges'][-1]+1
    phase=op+3;idle=phase+407
    start=idle+1
    # One source capture-bank scalar read/edge: eight rows make a256b flit.
    # Header then72 dataflits. No assumed eight-port capture RAM.
    collect=[start]+[start+8*(i+1) for i in range(72)]
    result=packet(start,73,collect_edges=collect,forward_edges=reverse_edges,reverse_edges=forward_edges,ACK_TIMEOUT=ACK_TIMEOUT)
    result['home_VM_commit_edges']=result['service_accept_edges'][2::2]
    assert len(result['home_VM_commit_edges'])==36
    completion=packet(result['next_packet_accept_edge'],1,forward_edges=reverse_edges,reverse_edges=forward_edges,ACK_TIMEOUT=ACK_TIMEOUT)
    terminal=completion['TX_ACK_accept_edge']
    old_idle=response_edge+410
    return dict(command=command,input=inputs,conditional_owner_op_accept=op,conditional_phase_accept=phase,
                conditional_source_idle=idle,result=result,completion_receipt=completion,
                home_last_postNBA_visibility=result['home_VM_commit_edges'][-1],
                terminal_receipt_edge=terminal,conditional_delta_vs_original_I66_idle_edges=terminal-old_idle,
                original_idle_edge=old_idle,packet_occupied_edges=sum(x['exclusive_occupied_edges'] for x in [command,*inputs,result,completion]),
                service_template_expert=0,service_template_rank=0,other_expert_service_edges=None,
                route_or_actual_acceptance_qualified=False)


def boundary(offered=None):
    """Endpoint logical wires must not be mislabeled PHY payload bandwidth."""
    expected=dict(forward_bits=330,reverse_bits=12,full_duplex_bits=684,
                  data_bits=256,CRC_bits=64,sequence_bits=8,last_bits=1,valid_bits=1,
                  return_ready_bits=1,return_ACK_bits=10,leased_remote_credit_bits=1)
    if offered is None:return dict(required=expected,physical_provider=None,verdict='UNBOUND')
    for field in ['forward_bits','reverse_bits','clock_ratio','route_identity','source_pin','SS_FF_qualified']:
        if field not in offered:raise ValueError('missing actual boundary binding '+field)
    if offered['forward_bits']<330 or offered['reverse_bits']<12:
        return dict(required=expected,offered=offered,verdict='FAIL_WIDTH',serialization_bridge_required=True)
    if offered['clock_ratio']!=1:
        return dict(required=expected,offered=offered,verdict='UNBOUND_CLOCK_BRIDGE')
    return dict(required=expected,offered=offered,verdict='WIDTH_SCREEN_PASS_CONTEXT_UNBOUND',physical_qualified=False)


def model():
    source=source_contract();f=forecast();node,table=D.owner_table()
    write_counts=S.load(J.OUT/'model.json')['per_shard_accepted_cadence']
    combined=collections.Counter()
    for shard in ['0','1']:
        combined.update({int(t):n for t,n in write_counts[shard+':VM_write_accept']['edge_counts'].items()})
    # Informational state count: storage is priced; no actual area credit.
    tx_state=65536+98
    rx_state=65536+(2+9+8+8+8+1+1+32+1+8+1+1+1)
    return dict(schema='opentallas.dsrom.I66.current-stage-link-software-composition.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',
                enabled_default=False,source_contract=source,compact_kernel_source_fields=KERNEL_FIELDS,compact_kernel_bits=sum(w for _,w in KERNEL_FIELDS),peer_requested_envelope_screen=peer_envelope_screen(),planned_software_ABI=dict(header_fields=HEADER,
                    header_bits=sum(w for _,w in HEADER),padded_header_flits=1,
                    generation_user_widths_are_new_candidate_contract=True,original_descriptor_audit_bits=2048,
                    compact_source_kernel_argument_bits=208,compact_kernel_flits=1,total_command_flits=2,
                    forward_input='320 aligned512b VM words via640 payload flits, chunked254/254/132',
                    return_output='36 aligned512b VM words via72 payload flits, golden BF16-in-FP32 data unchanged',
                    no_checkpoint_payload=True),
                routing=dict(source_stage=0,destination_from_exact_384_table=True,TP_rank_preserved=True,
                             one_remote_edge_candidate=[0,1],actual_physical_adjacency=None,
                             logical_shards_per_owner=2,local_cfg_bus_bits_per_shard=98304,local_activation_bus_bits=1632,
                             local_field_interfaces_are_not_remote_packet_provider=True,
                             local_field_context_delivery_still_unqualified=True),
                boundaries=boundary(),credit_ownership=dict(command_slots_per_owner=1,TX_packets_per_direction=1,
                    RX_packets_per_direction=1,packet_credit='leased RX slot; RX last-delivery ACK releases packet only',
                    source_go_credit='all576 capture rows + input/destination VM lease + actual input visibility',
                    command_completion='healthy source idle + all home postNBA visible rows + every accepted packet ACK',
                    sequence_wrap='8bit packet seq reuse only after packet/delivery/owner debts and causal visibility drained; header generation/user verified; reset is not assumed',
                    endpoint_credits_not_currently_generated=True),
                capture=dict(rows=576,writer_bits=63,retained_payload_bits=576*32,
                    occupancy_bits=576,sticky_fault_bits=1,information_state_bits=576*32+576+1,
                    actual_observed_total_peak_writes_per_edge=max(combined.values()),
                    actual_observed_per_shard_peak_writes_per_edge=64,
                    writer_edges=dict(sorted(combined.items())),no_source_ready=True,
                    source_capture_ports_required=128,ports_per_shard=64,
                    no_ready_writer_wire_bits_per_shard=64*63,
                    unbackpressured_root_wire_bits_per_shard=64*69,
                    scalar_drain_reads_per_edge=1,serializer_bits=256,
                    source_row_to_root_banking_other_experts=None,physical_padding_and_area=None,
                    no_publish_until_source_healthy_terminal=True,no_link_backpressure_into_field=True),
                storage=dict(existing_TX_state_bits_each=tx_state,existing_RX_sequential_state_bits_each=rx_state,
                    existing_bidirectional_endpoints_state_bits=2*(tx_state+rx_state),
                    candidate_capture_information_bits=19009,candidate_original_descriptor_audit_bits=2048,candidate_actual_kernel_hold_bits=208,
                    candidate_header_hold_bits=256,candidate_input_VM_bridge_hold_bits=512,
                    candidate_input_VM_hold_elements=5120,candidate_output_VM_hold_elements=576,
                    new_capture_banking_controls_and_packetization_area_mm2=None,area_credit_mm2=0),
                representative_calendar=f,input_reuse_source_proof=reuse_source_proof(),
                reuse_screens=dict(six_remote_W1=reuse_price([288,289,290,291,292,293]),
                    six_remote_W1_W3=reuse_price([288,289,290,291,292,293],W1_only=False),
                    mixed_W1=reuse_price([0,1,2,288,289,290]),
                    stalled_six_W1=reuse_price([288,289,290,291,292,293],receiver_stall_edges_per_packet=7)),
                conditional_target_time=dict(stream_period_ps=1000/1.2,
                    conditional_added_ns=f['conditional_delta_vs_original_I66_idle_edges']*(1000/1.2)/1000,
                    not_SS_frequency_qualification=True),
                selector_demand=dict(local_choices=288,remote_choices=96,legal_six_can_all_be_remote=True,
                    no_uniform_selection_or_whole_token_multiplier=True),
                source_pins={str(p.relative_to(S.ROOT)):S.sha(p) for p in [D.OUT/'inputs/stage_link_tx.sv.txt',
                    OUT/'inputs/stage_link_rx.sv.txt',OUT/'inputs/stage_link_endpoint.sv.txt',OUT/'inputs/isa_full.svh.txt',
                    P.OUT/'inputs/core.sv.txt',P.OUT/'inputs/tile.sv.txt',J.OUT/'model.json',
                    OUT/'inputs/demand-r5.json.gz',OUT/'inputs/selected_six_calls.json',OUT/'inputs/Maxwell_requested_envelope_WIP.json']},
                default_link_no_loss_verdict='FAIL_CONDITIONAL_SCREEN_EXPOSED_TRANSPORT',
                actual_single_user_delta=None,full_token_no_loss=False,RTL_admitted=False,
                remaining=['Maxwell actual physical adjacency/serialization/clock/SSFF boundary',
                           'command injection and exclusive external VM bridge arbitration',
                           'per-phase capture banking/padding for384owners, other-expert native service',
                           'actual PHW10 fullprogram accepted-origin observer',
                           'fault/CRC/timeout/cancel and header rejection connected recovery'])


@functools.lru_cache(maxsize=1)
def reuse_source_proof():
    demand=S.load_gz(OUT/'inputs/demand-r5.json.gz') if hasattr(S,'load_gz') else json.load(gzip.open(OUT/'inputs/demand-r5.json.gz','rt'))
    ns=[n for n in demand['nodes'] if n['scope']==0 and n['kind']=='instruction']
    records=S.load(OUT/'inputs/selected_six_calls.json')['calls']
    consumers=[r['binding']['node'] for r in records]
    producer=next(n for n in ns if n['id']=='L0.I52');g=producer['instruction']
    if not(g.get('unit')==2 and g.get('dst')==1 and g.get('o_base')==46464 and g.get('su_nout')==1 and g.get('su_nin')==5120 and g.get('o_si')==1 and not g.get('pred',0)):
        raise ValueError('wrong whole-X producer/version')
    writes=[]
    for n in ns:
        if not 52<n['instruction_index']<=93:continue
        z=n['instruction']
        if z.get('mx_m',0)>1 or any(z.get(k,0) for k in ['dslot','mx_ops','mx_xps']):
            raise ValueError('dynamic copy/version alias '+n['id'])
        spans=[];u=z.get('unit')
        if u==2:
            if z.get('dst')==1 and 'o_base' in z:
                if z.get('o_d',0):raise ValueError('dynamic output extent')
                spans.append((z['o_base'],z['o_base']+max(0,z.get('su_nout',1)-1)*z.get('o_so',0)+max(0,z.get('su_nin',1)-1)*z.get('o_si',0)+1))
            if z.get('red',0):
                if z.get('r_d',0):raise ValueError('dynamic reducer extent')
                spans.append((z['r_base'],z['r_base']+max(0,z.get('su_nout',1)-1)*z.get('r_so',0)+1))
        elif u==3:
            if z.get('qe_d_obase',0):raise ValueError('dynamic QE destination')
            spans.append((z['qe_obase'],z['qe_obase']+z.get('qe_nout',z.get('qe_nb',0)*32)))
        elif u==1 and z.get('me_oen',0):
            if z.get('me_d_obase',0):raise ValueError('dynamic ME destination')
            a=z['me_obase']*16;spans.append((a,a+z.get('me_nout',0)*max(1,z.get('me_ojs',1)*16)))
        elif u==4:
            if z.get('xu_d_n',0) or z.get('xu_d_k',0):raise ValueError('dynamic XU destination')
            spans.append((z['xu_dst'],z['xu_dst']+max(z.get('xu_n',0),z.get('xu_k',0),16)))
        elif u==5:spans.append((z['he_obase'],z['he_obase']+max(1,z.get('he_nout',0))*16))
        elif u==6:spans.append((z['coll_dst'],z['coll_dst']+z.get('coll_n',0)*4))
        elif z.get('_writes'):raise ValueError('unbound writer '+n['id'])
        for a,b in spans:
            if not 0<=a<=b<=1<<19:raise ValueError('VM aperture alias')
            if a<51584 and b>46464:raise ValueError('intervening immutable-X writer '+n['id'])
            writes.append(dict(node=n['id'],conservative_VM_extent=[a,b],predicate_not_waived=True))
    actions=[n for n in demand['nodes'] if n['scope']==0 and n['kind']=='runtime_action' and 52<n['action']['before_instruction']<=93]
    if actions:raise ValueError('runtime writer effect unbound')
    fence=next(n['id'] for n in ns if 52<n['instruction_index']<=66 and n['instruction'].get('wait',0)&2)
    for r in records:
        b=r['binding'];z=next(n['instruction'] for n in ns if n['id']==b['node'])
        if b['consumer_X_FP32_VM_elements']!=[46464,51584] or z.get('qe_xbase')!=46464 or z.get('qe_nb')!=160 or z.get('qe_nout')!=576 or z.get('qe_mode')!=0 or z.get('pred',0) or z.get('mx_m',0)>1 or any(z.get(k,0) for k in ['qe_d_xbase','dslot','mx_ops','mx_xps']):
            raise ValueError('consumer X layout/version mismatch')
    return dict(producer='L0.I52',producer_template_word_sha256=producer['template_word_sha256'],
                immutable_X_VM_elements=[46464,51584],FP32_words=5120,FP32_bits=163840,
                first_source_SU_retirement_fence=fence,consumers=consumers,
                six_W1_consumers=[b for b in consumers if b in ['L0.I66','L0.I68','L0.I72','L0.I82','L0.I87','L0.I92']],
                additional_six_W3_consumers=[b for b in consumers if b not in ['L0.I66','L0.I68','L0.I72','L0.I82','L0.I87','L0.I92']],
                writer_footprints=writes,source_write_acceptance_and_causal_visibility_unbound=True,
                runtime_no_mutation_proof=False,same_generation_rank_user_required=True,
                scope='L0 XN immutable window only; no across-token or W2-input reuse')


def resolve_call(node,eid,rank,generation,user,read):
    record=next(r for r in S.load(OUT/'inputs/selected_six_calls.json')['calls'] if r['binding']['node']==node)
    b=record['binding'];p=next((p for p in b['phase_choices'] if p['expert']==eid),None)
    if type(eid)!=int or not 0<=eid<384 or p is None or type(rank)!=int or not 0<=rank<4:
        raise ValueError('invalid selected consumer/EID/rank')
    if not read['accepted'] or read['address']!=b['selector_VM_element_address'] or read['response_edge']!=read['read_edge']+1 or read['value']!=eid:
        raise ValueError('actual per-slot selector provenance mismatch')
    return dict(node=node,expert=eid,rank=rank,generation=generation,user=user,
                owner_stage=p['stage'],phase=p['phase'],key_word=p['source_key_word'],
                read_edge=read['read_edge'],response_edge=read['response_edge'],selector_slot=b['selector_slot'],
                x_VM_elements=b['consumer_X_FP32_VM_elements'],output_VM_elements=[b['consumer_output_base_elements'],b['consumer_output_base_elements']+576],
                xversion=52,source_x_producer='L0.I52',source_program_provider_verified=False)


class InputLease:
    """One5120-word immutable VM extent per remote stage, held through suffix.
    Exact version provenance is explicit and same-generation; not a token cache.
    No timer can retire an accepted consumer or free this addressed VM lease.
    """
    def __init__(self,stage,rank,generation,user,ordered_consumers,producer_receipt):
        proof=reuse_source_proof()
        if not ordered_consumers or any(n not in proof['consumers'] for n in ordered_consumers) or ordered_consumers!=sorted(set(ordered_consumers),key=lambda n:int(n.split('I')[1])):
            raise ValueError('source phase order changed')
        if producer_receipt['producer']!='L0.I52' or producer_receipt['word_sha256']!=proof['producer_template_word_sha256'] or producer_receipt['accepted_words']!=5120 or producer_receipt['visible_words']!=5120:
            raise ValueError('source X-version/visible provenance missing')
        if (producer_receipt['rank'],producer_receipt['generation'],producer_receipt['user'])!=(rank,generation,user):
            raise ValueError('wrong X version rank/generation/user')
        self.identity=(stage,rank,generation,user,52);self.expected=list(ordered_consumers)
        self.active=None;self.cursor=0;self.released=False;self.remote_visible=False
        self.producer_receipt=copy.deepcopy(producer_receipt);self.input_debt=True

    def input_visible(self,words,packet_debts):
        if words!=5120 or packet_debts:raise ValueError('remote X preload not causal/drained')
        self.remote_visible=True;self.input_debt=False

    def use(self,c):
        if self.released or not self.remote_visible or self.input_debt or self.active is not None:
            raise ValueError('input/consumer credit unavailable')
        if (c['owner_stage'],c['rank'],c['generation'],c['user'],c.get('xversion'))!=self.identity or c['x_VM_elements']!=[46464,51584]:
            raise ValueError('input reuse identity/layout mismatch')
        if self.cursor>=len(self.expected) or c['node']!=self.expected[self.cursor]:raise ValueError('source consumer order changed')
        if c['response_edge']<self.producer_receipt['last_visible_edge']:
            raise ValueError('selected consumer precedes X visibility')
        self.active=copy.deepcopy(c)

    def retire(self,c,source_idle,home_visible_rows,packet_debts):
        if self.active!=c or not source_idle or home_visible_rows!=576 or packet_debts:
            raise ValueError('accepted consumer debt remains')
        self.cursor+=1;self.active=None

    def release(self):
        if self.active is not None or self.cursor!=len(self.expected) or self.input_debt:
            raise ValueError('X lease lifetime still active')
        self.released=True



def delayed_packet_cost(n,f,r,timeout,stall,collect_edges=None):
    base=packet(0,n,collect_edges=collect_edges,forward_edges=f,reverse_edges=r,ACK_TIMEOUT=timeout)
    first=base['service_accept_edges'][0]
    p=packet(0,n,collect_edges=collect_edges,forward_edges=f,reverse_edges=r,
             blocked_delivery=range(first,first+stall),ACK_TIMEOUT=timeout)
    return p['exclusive_occupied_edges']


def reuse_price(ids,forward_edges=1,reverse_edges=1,W1_only=True,receiver_stall_edges_per_packet=0,ACK_TIMEOUT=1024):
    """Serial blocking contribution in current PC order, no hidden overlap.
    Excludes unchanged local service/intervening jobs, whose full-program
    accepted calendar is not observed. All command/result/ACK costs remain.
    Positive wire defaults are a declared candidate sensitivity, not a PHY pin.
    """
    D.selected_six(ids);proof=reuse_source_proof()
    records=S.load(OUT/'inputs/selected_six_calls.json')['calls']
    if W1_only:records=[r for r in records if r['binding']['node'] in proof['six_W1_consumers']]
    commands=[]
    for r in records:
        b=r['binding'];eid=ids[b['selector_slot']]
        p=next(p for p in b['phase_choices'] if p['expert']==eid)
        commands.append(dict(node=b['node'],slot=b['selector_slot'],eid=eid,stage=p['stage'],phase=p['phase'],key=p['source_key_word']))
    remote=[c for c in commands if c['stage']!=0]
    seen=set();rows=[];once=0;each=0
    if receiver_stall_edges_per_packet<0:raise ValueError('negative receiver stall')
    input_cost=sum(delayed_packet_cost(n,forward_edges,reverse_edges,ACK_TIMEOUT,receiver_stall_edges_per_packet) for n in [255,255,133])
    for c in remote:
        hit=c['stage'] in seen
        # Registered lease check is explicitly priced one edge/command;
        # no assumption about zero header, wires, CDC, comparison or stalls.
        control=delayed_packet_cost(2,forward_edges,reverse_edges,ACK_TIMEOUT,receiver_stall_edges_per_packet)
        result=delayed_packet_cost(73,reverse_edges,forward_edges,ACK_TIMEOUT,receiver_stall_edges_per_packet,collect_edges=[0]+[8*(i+1) for i in range(72)])
        ack=delayed_packet_cost(1,reverse_edges,forward_edges,ACK_TIMEOUT,receiver_stall_edges_per_packet)
        fixed=control+result+ack+1
        per=fixed+input_cost;cached=fixed+(0 if hit else input_cost)
        rows.append(dict(**c,input_hit=hit,command_result_ACK_check_edges=fixed,
                         per_expert_input_edges=input_cost,once_input_edges=0 if hit else input_cost,
                         serial_per_expert_transport_edges=per,serial_reuse_transport_edges=cached))
        each+=per;once+=cached;seen.add(c['stage'])
    return dict(selected_ids=ids,W1_only=W1_only,source_PC_order=commands,remote_calls=rows,
                remote_consumer_count=len(remote),input_copies_per_expert=len(remote),input_copies_reuse=len(seen),
                per_expert_serial_transport_edges=each,reuse_serial_transport_edges=once,
                serial_transport_edges_saved=each-once,
                candidate_forward_edges=forward_edges,candidate_reverse_edges=reverse_edges,
                receiver_stall_edges_per_packet=receiver_stall_edges_per_packet,
                selected_ACK_TIMEOUT=ACK_TIMEOUT,
                registered_input_lease_check_edges_per_remote_command=1,
                additional_X_payload_memory_bits=0,existing_addressed_remote_VM_reservation_bits=163840,
                reservation_capacity_provider_verified=False,
                new_X_metadata_bits_lower_bound=6+2+32+32+32+19+13+4+1+1,
                AQ_local_per_phase_unchanged=True,quantization_relocated=False,
                real_full_program_critical_delta_edges=None,no_token_loss_proven=False)



def peer_envelope_screen():
    peer=S.load(OUT/'inputs/Maxwell_requested_envelope_WIP.json')
    f=peer['spatial']['forward_route_CDC_PHY_envelope_edges'];r=peer['spatial']['reverse_route_CDC_PHY_envelope_edges']
    timeout=peer['timeout']['proposed_ACK_TIMEOUT']
    try:
        input_packets(0,f,r)
        default=dict(verdict='PASS')
    except ValueError as e:
        default=dict(verdict='FAIL_SOURCE_DEFAULT_TIMEOUT',reason=str(e))
    return dict(peer_requested_envelope_not_physical_characterization=True,
                peer_forward_edges=f,peer_reverse_edges=r,default_ACK_TIMEOUT=1024,default_verdict=default,
                opt_in_ACK_TIMEOUT=timeout,original_RTL_changed=False,
                extra_timer_storage_bits=0,timeout_configuration_is_not_latency_or_ready_tuning=True,
                actual_stage_package_distance=peer['spatial']['source_stage_package_distance_um'],
                forward_bits=330,reverse_bits=12,full_duplex_tracks=684,
                requested_channel_width_um=peer['spatial']['channel_width_with_halfpool_reservation_um'],
                source_PHY_pin_OBS_PG_clock_available=False,
                six_W1=reuse_price([288,289,290,291,292,293],f,r,ACK_TIMEOUT=timeout),
                six_W1_W3=reuse_price([288,289,290,291,292,293],f,r,W1_only=False,ACK_TIMEOUT=timeout),
                single_template=forecast(forward_edges=f,reverse_edges=r,ACK_TIMEOUT=timeout))



def reanalyse_local_capture():
    c=D.resolve(0,0,0,0,dict(accepted=True,address=366688,read_edge=11,response_edge=12,value=0))
    reservation=CaptureReservation(c,input_visible=True,VM_exclusive=True)
    local_visible={};idle=None
    for e in S.events('r2_PASS'):
        if e['kind']=='VM_write_accept':
            reservation.capture(e['b']-398720,e['b'],e['c'],e['a'],e['edge'])
        elif e['kind']=='final_destination_visible':local_visible[e['a']-398720]=e
        elif e['kind']=='phase_retire':idle=e['edge']
    if idle!=422 or set(local_visible)!=set(range(576)):raise ValueError('qualified local runtime identity changed')
    reservation.source_terminal(True,False,edge=idle)
    data=reservation.release_payload()
    for row in range(576):
        if local_visible[row]['c']!=data[row]:raise ValueError('local source writer/capture visibility mismatch')
    peredge=collections.Counter(edge for data,root,edge in reservation.rows.values())
    return dict(verdict='PASS_REANALYSED_LOCAL_NO_READY_CAPTURE',rows=576,
                source_writer_edge_counts=dict(sorted(peredge.items())),peak=max(peredge.values()),
                original_source_idle=idle,local_staging_last_postNBA_visible=max(e['edge'] for e in local_visible.values()),
                raw_journal_sha256=S.sha_raw(S.A/'r2_PASS/actual.jsonl.gz'),
                remote_provider_runtime_measured=False,remote_home_visibility=None,new_runtime_invoked=False,
                scope='qualified EID0/rank0 LOCAL source only; no transfer to remote/direct-control branch or other expert service')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--reanalyse-local',action='store_true');a=p.parse_args()
    result=reanalyse_local_capture() if a.reanalyse_local else model()
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
