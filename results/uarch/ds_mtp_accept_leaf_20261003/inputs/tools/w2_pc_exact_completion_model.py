#!/usr/bin/env python3
"""Model-first exact PC completion successor; no RTL, launch, or SS claim.

Namespace nonreuse and fenced rearm are explicit ENVIRONMENT obligations, not
an unbounded hardware tombstone table. A registered write ACK uses its already
reserved transaction entry until the client accepts it. Physical write-visible
completion remains the provider's separate obligation.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/w2_pc_exact_completion_20261003'


def uint(value,width):
    if type(value)!=int or not 0<=value<1<<width:
        raise ValueError('identity width')
    return value


def owner46(physical_pc,client,original_tag,generation):
    """Canonical FULLWIDTH, never a compact parent/coalescer16 handle."""
    return ((uint(physical_pc,7)<<39)|(uint(client,3)<<36)|
            (uint(original_tag,32)<<4)|uint(generation,4))


def decode_owner46(value):
    uint(value,46)
    return dict(physical_pc=value>>39,client=(value>>36)&7,
                original_tag=(value>>4)&0xffffffff,generation=value&15)


class Service:
    """Reference edge model with three independent associative lookup ports.

    Namespace oracle `spent` is TEST/ENVIRONMENT state, not counted hardware.
    All callbacks belong to one service clock; actual CDC is not emulated.
    """
    def __init__(self,nc=5,limit=16,tagw=32,genw=4):
        if nc<2 or limit<1 or tagw<1 or genw<1:raise ValueError('geometry')
        self.nc,self.limit,self.tagw,self.genw=nc,limit,tagw,genw
        self.entries=[[None]*limit for _ in range(nc)]
        self.edge=0;self.rr=0;self.fault=False
        self.rq=None;self.rd=None;self.wq=None;self.sel=[None]*nc
        self.generation=None;self.spent=set();self.used_generations=set()

    def rearm(self,generation,provider_fenced=False,reset_fenced=False):
        # This models a coordinated reset/rearm REQUEST, not an uncontrolled
        # asynchronous power reset clearing accepted transactions for free.
        uint(generation,self.genw)
        if (any(e is not None for row in self.entries for e in row) or
                self.rq is not None or self.rd is not None or self.wq is not None or
                any(s is not None for s in self.sel)):
            self.fault=True;raise ValueError('accepted debt remains at rearm')
        if not provider_fenced or not reset_fenced:
            self.fault=True;raise ValueError('causal provider and reset fences required')
        self.generation=generation;self.spent=set();self.used_generations.add(generation)
        self.fault=False;self.rr=0

    def key(self,event):
        return (uint(event['client'],math.ceil(math.log2(self.nc))),
                uint(event['tag'],self.tagw),uint(event['generation'],self.genw),
                uint(event['write'],1))

    def lookup(self,entries,event,kind):
        key=self.key(event)
        if key[0]>=self.nc:return []
        return [(key[0],s) for s,e in enumerate(entries[key[0]]) if e is not None
                and e['key']==key and e['state']==kind]

    def tick(self,request=None,read=None,write=None,read_ready=None,write_ready=None):
        """One pre-edge -> post-edge transition; no same-edge free-credit reuse.

        Request is one already arbitrated client; full RR choice is separately
        source-priced. Read input may hold while read_accept=False. Write input
        uses the frozen NEW ready/valid port (legacy pulse needs an adapter).
        WQ can accept one each edge while healthy. Every accepted write already
        reserved its terminal seat. On fault, all normal grants/releases freeze.
        """
        self.edge+=1;t=self.edge
        before=copy.deepcopy(self.entries)
        rr=[True]*self.nc if read_ready is None else read_ready
        wr=[True]*self.nc if write_ready is None else write_ready
        if len(rr)!=self.nc or len(wr)!=self.nc:raise ValueError('ready shape')
        result=dict(edge=t,request_accept=False,read_accept=False,
                    write_accept=False,read_delivery=None,write_deliveries=[],fault=self.fault)
        # Joint old-state validation precedes ANY release. A wrong return must
        # not let another good terminal release a credit on the discovery edge.
        for q,direction in [(self.rq,0),(self.wq,1)]:
            if q is not None:
                hits=self.lookup(before,q,'ISSUED')
                if (len(hits)!=1 or q['write']!=direction or
                        before[hits[0][0]][hits[0][1]]['issue_edge']>=q['capture_edge']):
                    self.fault=True
        if request is not None:
            key=self.key(request)
            if (key[0]>=self.nc or any(e is not None and e['key']==key
                    for row in before for e in row)):
                self.fault=True
        if self.fault:
            result['fault']=True
            result['outstanding']=[sum(e is not None for e in es) for es in self.entries]
            return result
        # Held outputs and entry ownership are stable until client handshakes.
        if self.rd is not None:
            c,s=self.rd['slot']
            if rr[c]:
                result['read_delivery']=copy.deepcopy(self.rd)
                self.entries[c][s]=None;self.rd=None
        for c,s in enumerate(self.sel):
            if s is not None and wr[c]:
                e=before[c][s]
                if e is None or e['state']!='WR_HELD':raise ValueError('selector debt')
                result['write_deliveries'].append(dict(slot=(c,s),key=e['key']))
                self.entries[c][s]=None;self.sel[c]=None
        # Selector samples old HELD state only; a new ACK cannot bypass it.
        for c in range(self.nc):
            if self.sel[c] is None and not any(x['slot'][0]==c for x in result['write_deliveries']):
                candidates=[s for s,e in enumerate(before[c]) if e is not None and e['state']=='WR_HELD']
                if candidates:self.sel[c]=candidates[0]
        # Q -> match -> registered read holding output. RD cannot be replaced
        # on its consumer edge: that would be a different bypass architecture.
        old_rd_busy=bool(self.rd is not None or result['read_delivery'] is not None)
        rq_was_empty=self.rq is None
        if self.rq is not None and not old_rd_busy:
            hits=self.lookup(before,self.rq,'ISSUED')
            if len(hits)!=1 or self.rq['write']!=0:
                self.fault=True
            else:
                c,s=hits[0];e=before[c][s]
                if e['issue_edge']>=self.rq['capture_edge']:
                    self.fault=True
                else:
                    self.rd=dict(slot=(c,s),key=e['key'],data=self.rq['data'])
                    self.entries[c][s]['state']='RD_HELD'
            self.rq=None
        if read is not None and rq_was_empty:
            self.key(read);uint(read['data'],256)
            self.rq=dict(read,capture_edge=t);result['read_accept']=True
        # WQ processes one registered valid while accepting the next through
        # the NEW frozen write-ready port. Legacy pulse adaptation is separate.
        if self.wq is not None:
            hits=self.lookup(before,self.wq,'ISSUED')
            if len(hits)!=1 or self.wq['write']!=1:
                self.fault=True
            else:
                c,s=hits[0]
                if before[c][s]['issue_edge']>=self.wq['capture_edge']:
                    self.fault=True
                else:self.entries[c][s]['state']='WR_HELD'
            self.wq=None
        if write is not None:
            self.key(write);self.wq=dict(write,capture_edge=t);result['write_accept']=True
        if request is not None and not self.fault:
            key=self.key(request);c=key[0]
            live_duplicate=any(e is not None and e['key']==key for row in before for e in row)
            if c>=self.nc or live_duplicate:
                self.fault=True
            elif key in self.spent:
                raise ValueError('producer reused retired tuple: environment violation, not hardware-detectable ABA')
            else:
                free=[s for s,e in enumerate(before[c]) if e is None]
                if free:
                    s=free[0];self.entries[c][s]=dict(key=key,state='ISSUED',issue_edge=t)
                    self.spent.add(key);self.rr=(c+1)%self.nc;result['request_accept']=True
        result['fault']=self.fault
        result['outstanding']=[sum(e is not None for e in es) for es in self.entries]
        return result


def pins():
    p=json.loads((OUT/'source_pins.json').read_text())
    for path,h in p['inputs'].items():
        if hashlib.sha256((OUT/path).read_bytes()).hexdigest()!=h:raise ValueError('archive source changed')
    for path,h in p['originals'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('pinned original changed')
    return p


def tree_buffers(sinks,branch=8):
    total=0
    while sinks>1:
        sinks=math.ceil(sinks/branch);total+=sinks
    return total


def size(nc=5,limit=16,tagw=32,genw=4,npc=128,aw=34):
    if nc<2 or limit<1 or min(tagw,genw,npc)<1 or aw<32:raise ValueError('geometry')
    sid=math.ceil(math.log2(nc));sw=max(1,math.ceil(math.log2(limit)))
    cw=math.ceil(math.log2(limit+1));n=nc*limit;k=tagw+genw
    states={'table':n*(k+1+2),'read_query':sid+k+256+1,
            'read_delivery':sid+sw+k+256+1,'write_query':sid+k+1,
            'write_selection':nc*(sw+1),'retained_counters_RR_fault':nc*cw+sid+1,
            'registered_request_holder':aw+k+256+1+sid+sw+1}
    bits=sum(states.values());legacy=nc*cw+sid+1
    # Gross constructive cell screen: never a mapped-area/slot closure claim.
    prices=json.loads((OUT/'inputs/cell_prices.json').read_text())
    facts=prices['facts'];FF='DFFASRHQNx1_ASAP7_75t_R';N='NAND2x1_ASAP7_75t_R'
    I='INVx1_ASAP7_75t_R';B='BUFx4_ASAP7_75t_R'
    sections={}
    sections['storage_QN_restore']={FF:bits,I:bits}
    sections['registered_hold_mux']={N:3*bits,I:bits}
    sections['feedback_hold_twoBUF_floor']={B:2*bits}
    # Three independent lookups: request duplicate, read return, write ACK.
    sections['three_tag_generation_comparators']={N:3*n*(4*k+k-1),I:3*n*(k+k-1)}
    sections['direction_state_decode_and_multi_match_budget']={N:3*n*8+2*(n-1)*8,I:3*n*4+2*(n-1)*4}
    # Per-client registered selector reads retained tag/gen, not 256b payload.
    mux_bits=nc*k*(limit-1)
    sections['held_write_tag_generation_mux']={N:3*mux_bits,I:mux_bits}
    mux_req=(aw+tagw+genw+256+1)*((1<<sid)-1)
    sections['full_request_mux_including_existing']={N:3*mux_req,I:mux_req}
    sections['read_output_demux_and_ready']={N:nc*(k+256)*2,I:nc*(k+256)}
    sections['priority_slot_and_counter_logic_budget']={N:nc*limit*24,I:nc*limit*12}
    sections['clock_reset_trees_fanout8']={B:2*tree_buffers(bits)}
    areas={name:sum(q*facts[cell]['SS']['area_um2'] for cell,q in cells.items()) for name,cells in sections.items()}
    tie=bits*prices['TIEHI_body_um2'];body=sum(areas.values())+tie
    # Retain F0's mutable-state protection policy. This is the existing
    # protected64->72 and768two-input-equivalent/word planning convention,
    # not measured ECC logic or an installed protected completion service.
    def protected(b):return math.ceil(b/64)*72
    protected_sections={
        'table':n*protected(k+3),'read_query':protected(states['read_query']),
        'read_delivery':protected(states['read_delivery']),
        'write_query':protected(states['write_query']),
        'write_selection':nc*protected(sw+1),
        'retained_counters_RR_fault':nc*protected(cw)+protected(sid)+protected(1),
        'registered_request_holder':protected(states['registered_request_holder'])}
    protected_bits=sum(protected_sections.values());extra_bits=protected_bits-bits
    extra_storage_body=extra_bits*(facts[FF]['SS']['area_um2']+
        2*facts[I]['SS']['area_um2']+3*facts[N]['SS']['area_um2']+
        2*facts[B]['SS']['area_um2']+prices['TIEHI_body_um2'])
    extra_clock_reset=2*(tree_buffers(protected_bits)-tree_buffers(bits))*facts[B]['SS']['area_um2']
    ECC_words=protected_bits//72;ECC_gate_equivalents=ECC_words*768
    ECC_body=ECC_gate_equivalents*facts[N]['SS']['area_um2']
    protected_body=body+extra_storage_body+extra_clock_reset+ECC_body
    # Input compare broadcasts see one comparator per slot. Per-bank placement
    # limits fanout to16; upstream client demux and clock/reset are separate.
    return dict(geometry=dict(NC=nc,MAX_OUT=limit,CTAGW=tagw,GENW=genw,NPC=npc,AW=aw,
                    PTAGW=sid+tagw,backend_tag_plus_generation_bits=sid+k),
        state_bits_by_section=states,state_bits_per_PC=bits,
        incremental_state_bits_per_PC_over_counter_only=bits-legacy,
        state_bits_all_PCs=bits*npc,
        table_entries_per_PC=n,table_entry_bits=k+3,
        lookup_ports=dict(request_nonreuse=1,read_return=1,write_return=1),
        logical_table_updates_per_edge=dict(allocate=1,read_state_or_retire=1,write_match=1,write_retire_clients=nc),
        table_storage='FF entries with explicit update priority; no claimed multiported SRAM',
        request_data_bytes_per_accepted_edge=32,read_data_bytes_per_delivered_edge=32,
        port_signal_bits=dict(client_request_total=nc*(1+1+1+aw+tagw+genw+256),
            client_read_total=nc*(1+1+tagw+genw+256),
            client_write_completion_total=nc*(1+1+tagw+genw),
            backend_request=1+1+1+aw+sid+tagw+genw+256,
            backend_read_return=1+1+sid+tagw+genw+256,
            backend_write_completion=1+1+sid+tagw+genw),
        source_boundary_signal_track_floor=dict(backend_request=1+1+1+aw+sid+tagw+genw+256,
            backend_read_return=1+1+sid+tagw+genw+256,
            backend_write_completion=1+1+sid+tagw+genw,
            channel_capacity=None,shield_spacing_clock_PG_extra=True,
            distributed_PC_ports_not_one_free_shared_trunk=True),
        canonical_aggregated_boundary_signal_bits=dict(
            backend_request=1+1+1+aw+46+256,
            backend_read_return=1+1+46+256,
            backend_write_completion=1+1+46,
            added_PC_namespace_bits_per_transaction=7,
            actual_route_channels_and_new_shared_hold_registers_owned_by_Popper=True),
        request_frontend_proposal=dict(registered_holder_bits=states['registered_request_holder'],
            earliest_backend_admission_after_selection_edges=1,no_bypass_request_II_edges=2,
            requester_ready='Only actual backend acceptance acknowledges selected client. Hold the frozen tuple and free-slot reservation while stalled; no request accepted twice.',
            shadow_slot='One selected but not yet accepted free slot is pinned in holder, not an extra accepted credit.',
            full_arbitration_sequential_reference_tested=False),
        read_query_no_bypass_II_edges=2,read_first_delivery_after_backend_capture_edges=2,
        write_first_delivery_after_backend_pulse_edges=3,
        write_query_II_edges=1,client_write_outputs=nc,
        write_completion_hold_capacity='One reserved table entry per accepted write; count remains charged until client handshake.',
        credit_reusable='Following edge after client accepted read/write terminal. No same-edge full-table reuse.',
        comparator_bits_per_bank_query=k,comparator_broadcast_sinks_per_bit_per_client_bank=limit,
        reduction_depth_per_key=math.ceil(math.log2(k)),slot_mux_depth=math.ceil(math.log2(limit)),
        match_index_depth=math.ceil(math.log2(n)),
        compare_sink_SS_fF_per_bit_per_bank=limit*facts[N]['SS']['pins']['A']['cap_fF'],
        cell_counts_by_section=sections,cell_body_um2_by_section=areas,
        SETN_tie_body_um2=tie,gross_body_mm2_per_PC=body/1e6,
        gross_reservation50pct_mm2_all_PCs=body*2*npc/1e6,
        ASR_clock_pin_SS_fF_per_PC=bits*facts[FF]['SS']['pins']['CLK']['cap_fF'],
        ASR_reset_pin_SS_fF_per_PC=bits*facts[FF]['SS']['pins']['RESETN']['cap_fF'],
        protected_storage=dict(policy='F0 SECDED64-to72 for mutable state, ROM waiver not applied.',
            record_padding_and_check_bits_explicit=True,bits_by_section=protected_sections,
            bits_per_PC=protected_bits,bits_all_PCs=protected_bits*npc,
            ECC_logic_two_input_gate_equivalents_ASSUMED=ECC_gate_equivalents,
            ECC_gate_equivalents_per_codeword_ASSUMED=768,
            extra_storage_body_um2=extra_storage_body,extra_clock_reset_body_um2=extra_clock_reset,
            ECC_logic_body_um2_ASSUMED=ECC_body,
            gross_body_mm2_per_PC_ASSUMED=protected_body/1e6,
            gross_reservation50pct_mm2_all_PCs_ASSUMED=2*protected_body*npc/1e6,
            clock_pin_SS_fF_per_PC=protected_bits*facts[FF]['SS']['pins']['CLK']['cap_fF'],
            reset_pin_SS_fF_per_PC=protected_bits*facts[FF]['SS']['pins']['RESETN']['cap_fF'],
            exact_checker_encoder_cell_map_and_loaded_timing=False,
            correction_fault_holding_lifetime_and_controls_NOT_qualified=True),
        gross_screen_includes_existing_request_mux_and_counters=True,
        gross_screen_must_not_be_added_to_F0_without_once_only_replacement_ledger=True,
        comparator_loaded_SS_path_ps=None,feedback_loaded_FF_hold_ps=None,
        service_clock_period_ps=None,latency_ns=None,
        omitted_context_costs=['Exact F0 checker/encoder cell implementation and rare fault disposition',
            'Mapped FF control equivalence/update priority',
            'Named slot, loaded data/control routes, CDC/generation/reset producer, clock/PG'],
        SSFF_closed=False,hardware_admitted=False)


def model():
    p=pins();src=(OUT/'inputs/ot_hdc_qwen_pc_service.sv').read_text()
    for s in ['reg [CW-1:0] outstanding [0:NC-1];','if (grant) begin','if (p_wr_done_v && wr_id<NC) begin']:
        if s not in src:raise ValueError('original service changed')
    freeze=json.loads((OUT/'inputs/Russell_contract-r3.json').read_text())
    w2=json.loads((OUT/'inputs/Russell_W2-interface-contract-r1.json').read_text())
    canonical=json.loads((OUT/'inputs/Russell_canonical-fullwidth-C0-KV-read-r1.json').read_text())
    common=freeze['common_candidate']
    if (common['generation_bits']!=4 or common['aggregate_per_client_PC_limit']!=16 or
            common['tag_bits']!=16 or common['coalescer_tag']['bits']!=16):
        raise ValueError('Russell namespace freeze changed')
    if (w2['source_variants']['Nash_selected_model']['NC']!=5 or
            w2['W2_model_extension']['backend_echo']['p_req_generation']!=4 or
            w2['exact_table']['row_minimum_raw_bits']!=38 or
            w2['W2_model_extension']['physical_write_done_handshake']['p_wr_done_ready']!=1):
        raise ValueError('W2 interface freeze changed')
    if canonical['canonical_owner']['bits']!=46 or canonical['W4']['capture_bits_per_SM']!=55:
        raise ValueError('canonical fullwidth changed')
    pkg=(OUT/'inputs/ot_hbm_r14_pkg.sv').read_text()
    if 'pc_of=((s>>2)^(s>>7)^(s>>12))&31;' not in pkg:
        raise ValueError('actual R14 address hash changed')
    if 'ecc_gates=words*768' not in (OUT/'inputs/h4_hbm_baseline_bridge.py').read_text():
        raise ValueError('F0 protection price convention changed')
    return dict(scope='MODEL_AND_SOURCE_INTERFACE_ONLY',source_pins=p,
        current_source_top_geometry=dict(NC=6,CTAGW=32,MAX_OUT=16,NPC=128,AW=32),
        PC_module_defaults_are_not_top_binding=dict(NC=5,CTAGW=17),
        model_GENW=4,GENW_model_frozen=True,generation_wrap_source_qualified=False,
        Russell_tag_freeze_pending=False,
        canonical_fullwidth=dict(owner_bits=46,fields=dict(PC=7,client=3,originaltag=32,generation=4),
            W4_and_W6_identity_bits_with_RFslot9=55,
            scoped_PC_backend_identity_bits=39,
            implicit_static_table_owner_bits=10,
            explicit_at_aggregation_or_CDC=True,direction_is_separate=True,
            generator='Actual accepted requester/lane/client and source transaction allocator, not software-prelabelled receipt.'),
        distinct_namespaces=dict(optional_PC_handle='physicalPC7 plus client3/requesterSM5/slot4/gen4',
            coalescer_handle='separate client6/batchslot6/gen4; equal numeric16 does not imply equal owner',
            original_client_tag='Preserved32; original physical tag35 before compact adapter proof',
            source_exact_successor_boundary='Canonical fullwidth scoped physical tag35 plus explicit generation4; append explicit PC7 before aggregation. Compact is optional and not a build dependency.',
            optional_compact_missing_mapping='PC-handle↔coalescer-handle↔original-ring correspondence. No truncation or lane7→SM5 inference.'),
        actual_route_join=dict(chosen_leaf_on_Popper_route=False,connected_build_admitted=False,
            source_Qwen_route='p_req_addr[6:0] must equal generated service PC index.',
            R14_route='pc_of(sector)=((sector>>2)^(sector>>7)^(sector>>12))&31; separate STACK/DIE endpoint.',
            concrete_mismatch_witness=dict(sector=4,Qwen_low7_PC=4,R14_local_PC=1),
            R14_wire_tag_bits=16,R14_allocated_tag_bits=12,R14_private_identity_bits=192,
            R14_tag_owner_source_lookup_edges=12,
            source_leaf_terminal='Exactly one256-bit read or one write terminal per accepted PC32-byte sector.',
            R14_request_length_bits=6,R14_return_beat_bits=5,
            burst_mapping='Actual R14 LEN>1 needs source-owned split/assembly/beat terminal mapping and prices; cannot retire a W2 sector entry on the first arbitrary burst beat.',
            not_canonical_owner='R14 caller16 and tag16 do not contain owner46/gen4; preserve all existing192 identity fields.',
            required='Popper chooses actual accepted C0/KV caller→service→R14 ingress and returned owned interface. Reversible live mapping/fullwidth echo and address/beat/write-visible translation must be sized; no direct tag truncation or low7-guard transfer.',
            no_new_directory_client=True,no_adapter_slot_or_credit_assumed=True,
            source_matched_caller_and_backend_echo=None),
        prospective_latency_sensitivity=[dict(checked_lookup_stages=L,
            earliest_request_backend_admission_edges=L,
            earliest_read_client_accept_after_backend_capture_edges=L+1,
            earliest_write_client_accept_after_backend_capture_edges=L+2,
            no_bypass_request_II_edges=L+1,no_bypass_read_II_edges=L+1,
            provisional_1GHz_added_read_ns=L+1,provisional_1GHz_added_write_ns=L+2,
            qualified_clock=False,extra_registers_if_L_gt_1_NOT_priced=L>1)
            for L in [1,2,3]],
        lookup_stage_budget='Prospective one checked associative stage includes protection/check+match. Raw functional reference has no fault injection/protected-cell timing. Larger L requires its register/cell/port cost before selection.',
        native_R14_lookup_is_separate='Source12CORE-edge lookup cannot be hidden inside W2. Do not add edge counts across clocks until actual clock/CDC and replacement/once-only calendar are bound.',
        baseline_failures=['Return client count does not authenticate live tag or direction.',
            'Repeated/wrong tag can release another outstanding request.',
            'Write completion has no client ready/hold and retires immediately.',
            'Sticky fault does not suppress source request grants.',
            'Local reset erases counts without an explicit provider reset-stale fence.'],
        successor=size(),full_wrapper_variant=size(nc=6),
        minimum_row38=dict(fields=dict(valid=1,direction=1,generation=4,original_tag=32),
            NC5_rows=80,NC5_raw_bits=3040,NC6_rows=96,NC6_raw_bits=3648,
            not_complete_cost='Extra HELD state, query/output/select/request registers, three lookups, protection and physical control are separate.'),
        interface=dict(default_off='New copy/module namespace, OPT_EXACT_COMPLETION=0 until reviewed gate. Originals untouched.',
            request='Preserve full AW34 F0 address/data/clienttag32; add explicit generation4. Original AW32 default is not a legal unconditional34-bit truncation; parameter AW34 is legal but provider decoding remains separately bound.',
            request_stall='Freeze grant/free slot and entire tuple in registered request holder. Old combinational RR can change grant when an earlier client frees credits under backend stall. Holder is priced, full arbitration reference remains a next source gate.',
            namespace='Source-bound transaction-slot allocator owns generation; accepted requests can have different4-bit generations. Its all-copy wrap/reset producer is still unimplemented/unpriced, not a free global epoch wire.',
            backend='Echo full clienttag32+generation4; owner stays SIDW3. This is39 scoped source-side bits and46 with PC7. Compact16 is optional. Direction checked against separate read/write channel and entry.',
            client_read='Registered ready-held tag+generation+256b payload; table debt until handshake.',
            client_write='Add NC-bit c_wr_done_ready and generation. Select registered HELD entry and retain tag/gen/valid until handshake.',
            backend_write='Frozen new p_wr_done_ready plus valid/tag35/generation4. WQ accepts one/edge while healthy and holds/faults otherwise. Legacy unready pulse needs a separately priced source adapter, not assumed compatible.',
            fault='Reject malformed/duplicate/wrong-direction returns without a credit decrement. Stop new admission/issue and normal releases on sticky fault, including discovery-edge joint updates. Accepted debt remains for separate matched recovery/cancel; not discarded by reset.',
            reset='Coordinated provider/reset fence before rearm. Uncontrolled asynchronous reset is outside this safe contract.',
            ABA='Producer must prove no reused (client,tag,generation,direction) while any old copy can exist. Full live-table equality alone cannot detect ABA.',
            generation_wrap='Drain all service/client/backend/wire/held copies and causal provider visibility; fresh namespace fence before wrap/reuse. No reset-every-token assumption.'),
        producer_oracle_history_is_not_hardware=True,
        backend_write_echo_and_ready_installed=False,
        occupied_client5_KV_not_a_free_directory_lane=True,
        tag_mapping_F0_reference=dict(context_raw_bits=199,context_protected_bits=288,
            per_client_PC_slots=16,SM_does_not_multiply_credit_limit=True,
            original_tag32_gen4_write1_are_inside_F0_private_context=True,
            W2_table_reuse_credit=0,
            reuse_requirement='Prove shared accepted-entry mapping, three lookup ports and simultaneous state/terminal updates before replacing duplicate storage. Gross W2 cannot be blindly added to F0.',
            full_context_ownership_price_is_not_replaced_by_W2_lookup_table=True),
        provider_write_completion_is_not_physical_visibility_proof=True,
        KV_followon_contract=dict(original='ot_hdc_qwen_kv_pc_adapter.sv byte-identical',
            logical_outstanding=1,client5_full_wrapper_only=True,
            current_defects=['No generation match or completion-ready.',
                'Read response forwarded without accepted page/address/generation ownership.',
                'Write ACK matches low25tag but not captured full32tag/generation/page/address.',
                'Wrong completion can clear wr_pending before fault recovery.'],
            future_pending_identity_fields=dict(valid=1,direction=1,PC=7,originaltag=32,generation=4,physical_address=34),
            pending_raw_bits=79,old_write_pending_bits=33,
            incremental_pending_bits_before_ports_control_protection=46,
            read_release='Only exact frozen read identity and actual accepted return; RMW write still waits physical visibility-qualified completion.',
            write_release='bridge WRITE_REQ ready only on exact held write completion handshake, never on PC request acceptance.',
            page='Freeze accepted physical address and page provenance; cannot retarget an outstanding logical request when page changes.',
            untouched_arithmetic='Original half-sector FP8 bridge remains unchanged; no quantization/byte-order relocation.',
            full_price_and_build_admitted=False),
        build_sequence=['Popper actual accepted caller/R14 adapter/echo, all-copy wrap cost and fullwidth once-only ledger; field freeze already bound.',
            'Review default-off one-PC NC6/MAX16 source copy and exact sequential contract.',
            'Finite C0: full credits, simultaneous read/write, ready-held terminals, malformed/duplicate/resetstale negatives.',
            'Then actual KV read/client contract and provider write-visible bridge; Popper full bridge remains separate.'],
            resource_preparation=dict(build_now=False,scope='One PC NC5/80entries first; NC6/96entry variant joins whole bridge. No full bridge/engine/PHY.',
            source_and_generated_size_estimate=None,compile_time_estimate=None,
            prerequisites='New RTL dependency inventory/installed compiler and fresh measured host headroom before GO.',
            arbitrary_process_caps=False,PVE2_PVE3_new_jobs=False),
        jobs_launched=0,production_rate=None,physical_admission=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    text=json.dumps(model(),indent=2,sort_keys=True)+'\n'
    if a.output:a.output.write_text(text)
    else:print(text,end='')
