#!/usr/bin/env python3
"""Software-only exact S58 indexed owner dispatcher and finite transport screen.
No hardware selection, local-owner fallback, synthesized acceptance, or ECC pool.
"""
import argparse
import collections
import copy
import json
import functools
import gzip
from pathlib import Path
import dsrom_I66_provider_clock_contract as P
J=P.J
S=J.S
OUT=S.ROOT/'results/uarch/dsrom_I66_stage_dispatch_20261002'


@functools.lru_cache(maxsize=1)
def _source_table():
    node=S.load(J.OUT/'inputs/I66_node_binding.json')
    entries={p['expert']:copy.deepcopy(p) for p in node['phase_choices']}
    if set(entries)!=set(range(384)) or len(node['phase_choices'])!=384:
        raise ValueError('incomplete or duplicate expert ownership')
    if len({(p['stage'],p['phase']) for p in entries.values()})!=384:
        raise ValueError('phase alias within stage')
    for p in entries.values():
        if not 0<=p['stage']<58 or not 0<=p['phase']<1024:
            raise ValueError('stage/PHW10 bounds')
        if p['config_logical_word_range']!=[25*p['phase'],25*(p['phase']+1)]:
            raise ValueError('configuration address inconsistent with phase')
    with gzip.open(OUT/'inputs/cfg_phase_directory.jsonl.gz','rt') as f:
        phases={(p['stage'],p['phase']):p for p in map(json.loads,f)}
    with gzip.open(OUT/'inputs/cfg_key_tables.jsonl.gz','rt') as f:
        keys={p['stage']:p for p in map(json.loads,f)}
    for p in entries.values():
        phase=phases[(p['stage'],p['phase'])]
        for k in ['stage','phase','source_key_word','matrix_journal_ordinal','alias','config_logical_word_range']:
            if phase[k]!=p[k]:raise ValueError('current622 phase mismatch: '+k)
        if keys[p['stage']]['PHW']!=10 or keys[p['stage']]['words'][p['phase']]!=p['source_key_word']:
            raise ValueError('compiled key/PHW mismatch')
        if phase['K_per_rank']!=5120 or phase['rows_per_rank']!=576 or phase['format']!='fp4' or phase['layer']!=0:
            raise ValueError('expert format/shape source mismatch')
        if len(phase['rank_slices'])!=4:
            raise ValueError('TP4 source slices missing')
        p['source_tensor']=phase['source_tensor']
        p['rank_slices']=phase['rank_slices']
        p['payload_plan_sha256']=phase['payload_plan_sha256']
        p['active_pair_count']=phase['active_pair_count']
    return node,entries


def owner_table():
    return copy.deepcopy(_source_table())


def selected_six(ids):
    if len(ids)!=6 or any(type(i)!=int or not 0<=i<384 for i in ids) or ids!=sorted(set(ids)):
        raise ValueError('actual selector contract requires six distinct ascending IDs0..383')
    return list(ids)


def resolve(eid,rank,generation,user,accepted_read):
    """Bind an actual accepted selector read and its registered response.
    accepted_read fields are observations, not issued or force-ready stimuli.
    API returns a command for the real owner, never a local phase on lookup miss.
    """
    node,table=owner_table()
    if type(eid)!=int or eid not in table:raise ValueError('invalid EID; no mask/modulo alias')
    if type(rank)!=int or not 0<=rank<4:raise ValueError('TP4 rank bounds')
    if type(generation)!=int or generation<0 or type(user)!=int or user<0:
        raise ValueError('invalid lifecycle identity')
    if not accepted_read['accepted'] or accepted_read['address']!=node['selector_VM_element_address']:
        raise ValueError('unaccepted/wrong selector read')
    if accepted_read['response_edge']!=accepted_read['read_edge']+1 or accepted_read['value']!=eid:
        raise ValueError('registered EID identity mismatch')
    p=table[eid]
    return dict(node=node['node'],expert=eid,rank=rank,generation=generation,user=user,
                read_edge=accepted_read['read_edge'],response_edge=accepted_read['response_edge'],
                owner_stage=p['stage'],phase=p['phase'],key_word=p['source_key_word'],
                matrix_journal_ordinal=p['matrix_journal_ordinal'],alias=p['alias'],
                config_logical_word_range=p['config_logical_word_range'],
                x_VM_elements=node['consumer_X_FP32_VM_elements'],
                output_VM_elements=[node['consumer_output_base_elements'],node['consumer_output_base_elements']+576],
                shards=[dict(shard=s,global_site_range=[2048*s,2048*(s+1)],root_range=[64*s,64*(s+1)]) for s in range(2)],
                source_tensor=p['source_tensor'],rank_slice=p['rank_slices'][rank],
                payload_plan_sha256=p['payload_plan_sha256'],active_pair_count=p['active_pair_count'],
                ordered_K_grain=[0,5120],TP=4,hardware_dispatch_selected=False)


class DispatchLedger:
    """One software command in flight; not an allocated hardware queue.
    Accepted remote WC/root writes remain owed until per-row visibility receipts.
    Packet ACK and source idle individually cannot retire the operation.
    """
    def __init__(self):
        self.command=None;self.rows=set();self.retired=False;self.transport_debts=set();self.source_idle=False
        self.seen=set();self.packet_seen=set()

    def accept(self,command,owner_stage,edge):
        if self.command is not None:raise ValueError('command credit occupied')
        if command['owner_stage']!=owner_stage:raise ValueError('wrong owner; local-stage fallback forbidden')
        identity=tuple(command[k] for k in ['node','expert','rank','generation','user'])
        if identity in self.seen:raise ValueError('replayed command identity')
        if edge<command['response_edge']:raise ValueError('owner accepted before EID response')
        self.command=copy.deepcopy(command);self.accept_edge=edge;self.seen.add(identity)
        self.rows=set();self.source_idle=False;self.retired=False;self.packet_seen=set()

    def _identity(self,c):
        if self.command is None or any(c[k]!=self.command[k] for k in ['node','expert','rank','generation','user','owner_stage','phase','key_word']):
            raise ValueError('stale/wrong transaction owner')

    def transport_accept(self,c,packet):
        self._identity(c)
        if packet in self.packet_seen:raise ValueError('duplicate transport debt')
        self.transport_debts.add(packet);self.packet_seen.add(packet)

    def transport_ack(self,c,packet):
        self._identity(c)
        if packet not in self.transport_debts:raise ValueError('unknown/duplicate transport ACK')
        self.transport_debts.remove(packet)

    def visible(self,c,row,address,write_edge,visible_edge):
        self._identity(c)
        if type(row)!=int or not 0<=row<576 or row in self.rows:raise ValueError('missing/duplicate row identity')
        if address!=c['output_VM_elements'][0]+row:raise ValueError('destination alias')
        if write_edge<self.accept_edge or visible_edge<write_edge:raise ValueError('visibility before accepted writer')
        self.rows.add(row)

    def idle(self,c,edge):
        self._identity(c)
        if edge<self.accept_edge:raise ValueError('idle before operation')
        self.source_idle=True

    def retire(self,c):
        self._identity(c)
        if not self.source_idle or len(self.rows)!=576 or self.transport_debts:
            raise ValueError('source/visibility/transport debt remains')
        self.retired=True;self.command=None


def packet_screen(bits):
    """Existing stage-link defaults only, NOT selected PAR2 hardware provider.
    Source ST_COLLECT stores entire packet before ST_SEND, then ST_WAIT_ACK.
    Lower bound assumes uninterrupted input/link acceptance, minimum next-edge
    ACK, no header, no wire/CDC, no retry, available remote credit each packet.
    Real stalls and ACK latency add directly; timer is not completion evidence.
    """
    source=(OUT/'inputs/stage_link_tx.sv.txt').read_text()
    for s in ['FLIT_W = 256','MAX_FLITS = 256','SEQ_W = 8','ST_WAIT_ACK','if (in_last)','state <= ST_SEND;']:
        if s not in source:raise ValueError('transport screen source changed')
    flits=(bits+255)//256;chunks=[]
    left=flits
    while left:
        n=min(left,256);chunks.append(n);left-=n
    # n collects, n sends, then one successful ACK edge. Next IDLE accept
    # occurs on the next edge; thus elapsed exclusive slot count 2*n+1.
    return dict(bits=bits,flits=flits,packet_flits=chunks,packet_count=len(chunks),
                minimum_occupied_edges=sum(2*n+1 for n in chunks),
                reverse_packet_ACK_control_bits=10,minimum_reverse_ACK_edges_per_packet=1,
                reverse_ACK_wire_CDC_latency_edges=None,
                matching_ACK_sequence_bits=8,ACK_does_not_prove_destination_visibility=True,
                source_payload_buffer_bits=256*256,source_control_state_bits=98,
                source_total_state_bits=65536+98,source_packet_credit=1,
                header_bits=None,actual_link_ready_edges=None,actual_ACK_edges=None,
                actual_provider_selected=False,qualification='lower bound screen only')


def compose(command,owner_accept_edge,receipts):
    """Insert observed accepted service and transport receipts in native calendar.
    Native template is measured expert0 only. Others require their own actual
    accepted per-phase service journals; equal shape is not runtime transfer.
    """
    if receipts['identity']!={k:command[k] for k in ['node','expert','rank','generation','user','owner_stage','phase','key_word']}:
        raise ValueError('service receipt owner mismatch')
    if not receipts['actual_accepted'] or owner_accept_edge<command['response_edge']:
        raise ValueError('offered origin cannot bind accepted service')
    if receipts['source_idle_edge']<owner_accept_edge or receipts['first_VM_read_edge']<owner_accept_edge:
        raise ValueError('service boundary precedes owner acceptance')
    if receipts['input_last_visible_edge']>receipts['first_VM_read_edge']:
        raise ValueError('input not visible before consumer read')
    rows=receipts['visible_rows']
    if len(rows)!=576 or {r['row'] for r in rows}!=set(range(576)):
        raise ValueError('incomplete/duplicate destination visibility')
    if any(r['address']!=command['output_VM_elements'][0]+r['row'] or r['visible_edge']<r['write_edge'] or r['write_edge']<owner_accept_edge for r in rows):
        raise ValueError('writer visibility identity mismatch')
    if receipts['forward_debt'] or receipts['result_debt']:
        raise ValueError('accepted transport debt not drained')
    end=max(receipts['source_idle_edge'],max(r['visible_edge'] for r in rows),receipts['last_transport_ACK_edge'])
    return dict(accepted_owner_edge=owner_accept_edge,completed_edge=end,
                forwarding_edges=owner_accept_edge-command['response_edge'],
                service_edges=receipts['source_idle_edge']-owner_accept_edge,
                completion_after_source_edges=end-receipts['source_idle_edge'],
                accepted_receipt_contract_checked=True,source_runtime_verified=False,physical_admission=False,no_token_loss_proven=False)


def model():
    node,table=owner_table();native=S.load(J.OUT/'model.json')
    return dict(schema='opentallas.dsrom.I66.S58-software-dispatch.v1',candidate=native['candidate'],
                expert_coverage=384,TP=4,rank_bindings=1536,
                stages=dict(sorted(collections.Counter(str(c['stage']) for c in table.values()).items())),
                owner_table=[table[k] for k in sorted(table)],
                source_pins={str(p.relative_to(S.ROOT)):S.sha(p) for p in [J.OUT/'inputs/I66_node_binding.json',J.OUT/'model.json',P.OUT/'inputs/runtime_spine.sv.txt',OUT/'inputs/stage_link_tx.sv.txt',OUT/'inputs/cfg_phase_directory.jsonl.gz',OUT/'inputs/cfg_key_tables.jsonl.gz']},
                source_demands=dict(input_FP32_bits=5120*32,VM_read_beats=80,VM_read_bits_per_beat=2048,
                                    alternative_native_FP4_stream_bits=80*549,alternative_requires_actual_AQ_dispatch_binding=True,
                                    result_data_bits=576*32,result_writer_identity_bits=576*63,
                                    local_configuration_bits_both_shards=4096*25*48,
                                    local_configuration_edges=25,configuration_not_link_traffic=True),
                current_provider=dict(cross_stage_dispatch_present=False,forwarding_width=None,forwarding_credit=None,
                                      input_accepted_edges=None,result_delivery_edges=None,completion_receipt_edges=None),
                existing_stage_link_default_screen=dict(input=packet_screen(5120*32),result=packet_screen(576*63),
                    command_source_fields_bits=1+10+3+4*19+2,
                    command_route_key_expert_rank_minimum_extra_bits=6+32+9+2,
                    command_unknown_lifecycle_header_bits=None,
                    reverse_ACK_control_width_bits=10,
                    ACK_wire_provider_or_serialization=None,
                    two_direction_existing_TX_state_bits=2*(65536+98),
                    actual_provider_replica_count=None,physical_link_clock_ratio=None,
                    forward_reverse_completion_minimum_total_occupied_edges=1283+285,
                    total_excludes_command_headers_route_and_owner_service=True,
                    area_credit_mm2=0,additional_hardware_admitted=False),
                native_reference=dict(expert=0,rank=0,origin=10,phase=15,first_VM_read=45,last_VM_read=124,
                                      last_root=419,last_visible=420,spine_idle=421,adapter_idle=422,
                                      other_expert_latency_transferred=False),
                software_control=dict(command_slots=1,new_hardware_storage_bits=0,new_ACK_protocol=False,
                                      completion='actual owner source idle + all576 causal destination visibility + all accepted transport debt retired',
                                      sequence_reuse='requires owner/source/delivery/causalvisibility/provenance drained; never elapsed timer'),
                no_localstage_fallback=True,no_crossshard_K_reassociation=True,ECC_pool_bits=0,
                no_token_loss_proven=False,RTL_admitted=False,
                next_gate='Bind actual forwarding/input/result provider and actual per-phase accepted receipts with Maxwell/Hubble; run software compose before RTL.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--resolve',type=Path);a=p.parse_args()
    if a.resolve:
        c=S.load(a.resolve);result=resolve(c['eid'],c['rank'],c['generation'],c['user'],c['accepted_read'])
    else:result=model()
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
