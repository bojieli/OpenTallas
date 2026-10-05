#!/usr/bin/env python3
"""Complete source-owned QROM parent interface and finite startup mailbox model.

Additive R0/Q2 contract, not RTL or actual provider qualification. Price a
single explicit interface, including replicated sinks and deterministic wire
allocation. Source snapshots, physical clock/CDC and KV policy remain gates.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from qwen_rom_kv_launch_readiness import FIELDS, fifo_released_empty, zero
from uarch_model_qwen_kv_rate_risk import build as rate_risk

ROOT=Path(__file__).resolve().parents[1]
OWNER_FIELDS=(('user',16),('rank',2),('layer',6),('epoch',32),('producer_pc',12),('sequence',32))
STATUS_FIELDS=('released','drained','state_bound','healthy')
OWNER_BITS=sum(w for _,w in OWNER_FIELDS)
FRAME_BITS=OWNER_BITS+len(STATUS_FIELDS)
EXPORTS=('service0','service1','service2','service3','serial','stream')


def owner_word(owner):
    if set(owner)!=dict(OWNER_FIELDS).keys():raise ValueError('complete owner/PC/sequence required')
    word=0
    for name,width in OWNER_FIELDS:
        v=owner[name]
        if type(v) is not int or not 0<=v<1<<width:raise ValueError('owner aperture')
        word=(word<<width)|v
    if owner['layer']>=36:raise ValueError('actual36layer owner aperture')
    return word


def service_status(s):
    """Actual local registers plus quarantine debt: no constant-ready export."""
    if len(s['qcount'])!=32 or len(s['rcount'])!=32:raise ValueError('all32PCs required')
    for k in ('local_release','state_bound','enabled','fault'):
        if type(s[k]) is not int or s[k] not in (0,1):raise ValueError('binary source status required')
    if len(s['owners'])!=1:raise ValueError('the single actual owner instance required')
    owner_debt=[v for o in s['owners'] for v in (o['live_tags'],o['state'],o['held'])]
    quiet=zero(s['qcount']+s['rcount']+owner_debt+[s[k] for k in
        ('ingress','wr_live','wr_backed','wr_mapped','grant_valid','live_tags',
         'owner_state','owner_held','route_live','quarantine_debt','flight_debt','bank_lease_debt','inflight_beat_debt')])
    bridges=s['bridges']
    if not bridges:raise ValueError('actual CDC instance inventory required')
    return dict(released=int(s['local_release'] and all(fifo_released_empty(f) for f in bridges)),
        drained=int(quiet),state_bound=int(s['state_bound']),healthy=int(s['enabled']==1 and s['fault']==0))


def local_status(kind,s):
    for k in ('local_release','state_bound','fault'):
        if type(s[k]) is not int or s[k] not in (0,1):raise ValueError('binary source status required')
    if kind=='serial':
        quiet=zero([s[k] for k in ('active','inflight','pending_kv_writes')])
    elif kind=='kv':
        quiet=zero([s[k] for k in ('used','fl_v','boot_busy','boot_any_v','desc_pending','kvd_v',
                                   'live_assembly','live_readers','reverse_credit_debt')]) and s['adapter_idle']==1
    elif kind=='array':
        # Complete instantiated replicas; no spine-ready substitute.
        if len(s['tiles'])!=1536:raise ValueError('all1536 current tiles required')
        quiet=all(zero([t[k] for k in ('active','pend','go_q','kv_rd_q','rom_inflight')]) for t in s['tiles'])
        quiet=quiet and zero([s[k] for k in ('broadcast_go_debt','x_valid_debt','tree_valid_debt')])
    else:raise ValueError('export kind')
    return dict(released=int(s['local_release']),drained=int(quiet),
                state_bound=int(s['state_bound']),healthy=int(s['fault']==0))


def stream_status(kv,array):
    """Fold both local predicates into the existing six-export peer contract."""
    a=local_status('kv',kv);b=local_status('array',array)
    return {k:int(a[k] and b[k]) for k in STATUS_FIELDS}


class OwnedMailbox:
    """One leased four-phase request, source2FF and stream2FF ack sync.

    Multibit104 data is held until consume; never bitwise synchronized. Each
    source snapshot callback must read actual owned state. Tests are fixtures.
    Timing/aperture of the held data bus requires the physical contract.
    """
    def __init__(self):
        self.req=0;self.ack=0;self.rs=[0,0];self.as_=[0,0]
        self.owner=None;self.frame=None;self.captured=None;self.leased=False
        self.phase='idle'

    def offer(self,owner):
        if self.phase!='idle':raise ValueError('single mailbox owner until source release acknowledged')
        self.owner=dict(owner);owner_word(owner);self.req=1;self.phase='request'

    def source_edge(self,provider):
        old=self.rs[:];self.rs=[self.req,old[0]]
        if old[1]==0 and self.ack==1:
            self.frame=None;self.leased=False;self.ack=0
        elif old[1]==1 and self.ack==0:
            actual_owner,status=provider()
            if actual_owner!=self.owner:raise ValueError('source owns a different epoch/PC/sequence')
            if set(status)!=set(STATUS_FIELDS) or any(type(status[k]) is not int or status[k] not in (0,1) for k in status):
                raise ValueError('source binary status required')
            if all(status.values()):
                self.frame=(owner_word(actual_owner),dict(status));self.ack=old[1];self.leased=True
        elif old[1]==1 and self.ack==1:
            actual_owner,status=provider()
            if actual_owner!=self.owner or status!=self.frame[1]:
                raise ValueError('source lease changed; quarantine required before launch')
        return self.leased

    def stream_edge(self):
        old=self.as_[:];self.as_=[self.ack,old[0]]
        if self.phase in ('request','held') and old[1]==1:
            if not self.leased or self.frame is None or self.frame[0]!=owner_word(self.owner):
                raise ValueError('ack without matching stable source-owned frame')
            self.captured=self.frame
            self.phase='held'
        elif self.phase=='return' and old[1]==0 and self.ack==0:
            self.owner=None;self.captured=None;self.phase='idle'
        return self.captured is not None

    def consume(self):
        if self.phase!='held':raise ValueError('consume before acknowledged capture')
        # Return-to-zero also crosses2sourceFFs; no direct cross-domain clear.
        result=self.captured;self.req=0;self.phase='return'
        return result


class ParentJoin:
    """All six held exports match one owner before registered launch.

    Startup only; per-op admission still uses real KV descriptor/readiness.
    No request/lease may be reused while a registered launch is pending.
    """
    def __init__(self):
        self.owner=None;self.receipts={};self.ready=False;self.launch=False
        self.consumed=False

    def offer(self,owner):
        if self.owner is not None:raise ValueError('live parent owner')
        owner_word(owner);self.owner=dict(owner)

    def receipt(self,name,frame):
        if name not in EXPORTS or name in self.receipts or self.owner is None:
            raise ValueError('unowned/duplicate export')
        if (frame[0]!=owner_word(self.owner) or set(frame[1])!=set(STATUS_FIELDS)
            or not all(type(frame[1][k]) is int and frame[1][k]==1 for k in STATUS_FIELDS)):
            raise ValueError('mismatched/unfinished source export')
        self.receipts[name]=frame

    def edge(self,request_go,reset_released):
        if type(request_go) is not bool or type(reset_released) is not bool:raise ValueError('binary control')
        if not reset_released and (self.receipts or self.launch):
            raise ValueError('abort/reset requires explicit lease quarantine, never erase ownership')
        old_ready=self.ready
        accepted=self.launch
        if accepted and request_go:raise ValueError('duplicate launch from held request')
        if request_go and self.consumed:raise ValueError('owner already consumed; await lease release')
        self.ready=reset_released and len(self.receipts)==len(EXPORTS) and not (accepted or self.consumed)
        self.launch=bool(request_go and old_ready and reset_released and self.owner is not None and not self.consumed)
        self.consumed=self.consumed or accepted
        return dict(ready_registered=self.ready,launch_registered=self.launch,
                    launch_consumed=accepted)

    def retire(self,released_exports):
        if not self.consumed or set(released_exports)!=set(EXPORTS):
            raise ValueError('registered launch and every source lease-release ACK required')
        self.owner=None;self.receipts={};self.ready=False;self.launch=False;self.consumed=False


def tree_count(n,fanout):
    levels=[]
    while n>1:n=math.ceil(n/fanout);levels.append(n)
    return dict(levels=levels,nodes=sum(levels),depth=len(levels))


def partition_read(base,sectors):
    if type(base) is not int or type(sectors) is not int or sectors<=0 or base<0 or base+sectors>703125000:
        raise ValueError('actual provider aperture')
    parts=[]
    while sectors:
        n=min(sectors,16-(base%16))
        parts.append(dict(base_sector=base,sectors=n));base+=n;sectors-=n
    return parts


class ElasticRoute:
    """Proposed39registered2entry stages. II1 is NEW, not current route behavior.

    Each stage reads preedge occupancy; registered readiness, no38-gate ready
    chain.39stages keep actual held-route first-consume latency39edges.
    Finite lossless software gate only; no hardware timing/adoption claim.
    """
    def __init__(self):self.q=[[] for _ in range(39)]
    def edge(self,packet=None,take=False):
        old=[q[:] for q in self.q]
        moves=[bool(old[i]) and (take if i==38 else len(old[i+1])<2) for i in range(39)]
        accepted=packet is not None and len(old[0])<2
        out=old[-1][0] if moves[-1] else None
        for i in range(39):
            new=old[i][1:] if moves[i] else old[i][:]
            if i and moves[i-1]:new.append(old[i-1][0])
            if not i and accepted:new.append(packet)
            if len(new)>2:raise AssertionError('finite stage overflow')
            self.q[i]=new
        return accepted,out


class TaggedOwnerPipeline:
    """Finite proposal against32 actual banks, retaining12-edge read lease.

    Fixture gate only. Each admitted return reserves a final output slot before
    its bank read. No context bank can be re-addressed before capture. Duplicate
    beats are rejected across flight and committed masks. One consumed output
    updates remaining_PC; allocation and final retirement change live_tags
    jointly. Reverse grant quarantine remains the external CausalJoin gate.
    """
    def __init__(self):
        self.cycle=0;self.contexts={};self.remaining={};self.flight=[];self.output=[]
        self.banks={};self.inflight=set();self.seen=set();self.live_tags=0;self.quarantine=set()

    def allocate(self,tag,pc_beats):
        if tag in self.remaining or tag in self.quarantine or not 0<=tag<4096 or not pc_beats:raise ValueError('live allocation/tag')
        for pc,beats in pc_beats.items():
            if sum(k[1]==pc for k in self.contexts)>=128:raise ValueError('finite128context bank')
            if not 0<=pc<32 or not beats or any(not 0<=b<32 for b in beats):raise ValueError('context beat aperture')
        self.remaining[tag]=len(pc_beats)
        for pc,beats in pc_beats.items():self.contexts[tag,pc]=set(beats)
        self.live_tags+=1

    def release(self,tag,reverse_grant_consumed,readers_drained):
        if tag not in self.quarantine or reverse_grant_consumed is not True or readers_drained is not True:
            raise ValueError("actual reverse grant and reader drain required")
        self.quarantine.remove(tag);self.seen={k for k in self.seen if k[0]!=tag}

    def edge(self,record=None,take=False,allocation=None):
        out=self.output.pop(0) if take and self.output else None
        if out is not None:
            key=(out['tag'],out['pc'],out['beat']);self.inflight.remove(key);self.seen.add(key)
            context=self.contexts[out['tag'],out['pc']]
            if all((out['tag'],out['pc'],b) in self.seen for b in context):
                del self.contexts[out['tag'],out['pc']];self.remaining[out['tag']]-=1
                if self.remaining[out['tag']]==0:
                    del self.remaining[out['tag']];self.live_tags-=1;self.quarantine.add(out['tag'])
        # Completed contexts cannot be reassigned to the same physical tag
        #until the separately owned reverse/grant quarantine receipt exists.
        if allocation is not None:self.allocate(*allocation)
        for flight in self.flight[:]:
            if self.cycle-flight['accepted_edge']>=12:
                captured=flight['read_context']()
                if not isinstance(captured,bytes) or len(captured)!=32:raise ValueError('actual256bit RAM capture required')
                self.output.append(dict(tag=flight['tag'],pc=flight['pc'],beat=flight['beat'],
                    data=flight['data'],context=captured,accepted_edge=flight['accepted_edge']))
                del self.banks[flight['pc']];self.flight.remove(flight)
        accepted=False
        if record is not None:
            key=(record['tag'],record['pc'],record['beat'])
            if key in self.inflight or key in self.seen:raise ValueError('duplicate in-flight/committed beat')
            if (key[0],key[1]) not in self.contexts or key[2] not in self.contexts[key[0],key[1]]:
                raise ValueError('unallocated/retired context beat')
            if not isinstance(record['data'],bytes) or len(record['data'])!=32 or not callable(record['read_context']):
                raise ValueError('actual return payload and bank provider required')
            if key[1] not in self.banks and len(self.flight)+len(self.output)<32:
                f=dict(record,accepted_edge=self.cycle);self.flight.append(f)
                self.banks[key[1]]=key;self.inflight.add(key);accepted=True
        assert len(self.flight)+len(self.output)<=32
        self.cycle+=1
        return accepted,out


def service_candidate(p,ff,inv,buf,and3):
    old=rate_risk(p.parent)
    for pins in (old['source_sha256'],old['parent_physical_context_sha256'],old['extension_source_sha256']):
        for path,digest in pins.items():
            if hashlib.sha256(p.raw(path)).hexdigest()!=digest:raise ValueError('rate predecessor pin changed: '+path)
    p.obj('results/uarch/qwen_rom_kv_rate_risk_20261002/model_r3.json')
    source=p.text('rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv')
    for declaration in ('reg [4095:0] live;','reg [5:0] remaining_PC[0:4095];',
                        'reg [12:0] cam[0:31][0:127];reg [31:0] seen[0:31][0:127];'):
        if declaration not in source:raise ValueError('owner inventory changed')
    bridge=p.text('rtl/test/model_ready_hbm_r14/tb_hbm_finite_stage.sv')
    for w in (455,467,404):
        if '.WIDTH('+str(w)+')' not in bridge:raise ValueError('native clock bridge width changed')
    macros=p.obj('physical/asap7_memory_macros/index.json')
    # Index schema is a list of macro records inside macros.
    records=macros['macros']
    if isinstance(records,dict):record=records['ot_sram_1r1w_128x256_m1_r2c2']
    else:record=next(x for x in records if x['name']=='ot_sram_1r1w_128x256_m1_r2c2')
    macro_area=record['area_um2']
    screen=p.obj('results/uarch/qwen_rom_parallel_owner_screen_20261002/model-r1.json')
    if screen['owners_per_stack']!=14:raise ValueError('pin existing14owner comparison, no replica sweep')
    owners=1
    extra_owners=4*(owners-1)
    owner_ff=4096+4096*6+32*128*(13+32)+781
    extra_macros=extra_owners*32
    equality_per_owner=32*128*12*(3*and3+5*inv)
    mux_bits_per_owner=(32-1)*256+(128-1)*32+(4096-1)*6
    mux_per_owner=mux_bits_per_owner*(3*and3+2*inv)
    extra_owner_area=extra_owners*(owner_ff*(ff+inv)+equality_per_owner+mux_per_owner)+extra_macros*macro_area
    pipeline_metadata_bits=5+12+5+7+256+256+1
    pipeline_FF_per_stack=32*pipeline_metadata_bits+32*467+32*128*32+32*2+32*7+4096+16
    pipeline_mux_bits_per_stack=31*(pipeline_metadata_bits+467)+32*128*32
    pipeline_area=4*(pipeline_FF_per_stack*(ff+inv)+pipeline_mux_bits_per_stack*(3*and3+2*inv))
    widths=(455,467,404)
    pipe_ff_each_stack=sum(39*(2*w+4) for w in widths)
    old_route_ff_each_stack=sum(w+7 for w in widths)
    extra_pipe_ff=4*(pipe_ff_each_stack-old_route_ff_each_stack)
    pipe_mux_bits=4*39*sum(widths)
    pipe_area=extra_pipe_ff*(ff+inv)+pipe_mux_bits*(3*and3+2*inv)
    # Explicit two-input owned/grant mux (one owner plus consumed grant).
    arb_mux_bits=4*owners*467
    arb_area=arb_mux_bits*(3*and3+2*inv)
    provider=p.text('rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv')
    if 'if(return_arb==6)' not in provider:raise ValueError('shared return arbiter changed')
    # Current7-edge shared scan is upstream of all owners. A fixed one-edge
    #registered36-way arbiter (32read PCs+4visible write residences) is required
    #to feed the selected finite tagged pipeline; independently multiplying owners
    #through the unchanged global scan is invalid. Retain complete native tag.
    return_mux_bits=4*35*(5+16+5+256+1)
    return_arb_FF=4*(2*(5+16+5+256+1)+6+36)
    return_arb_area=return_mux_bits*(3*and3+2*inv)+return_arb_FF*(ff+inv)
    # Source vector producer cannot backpressure already-issued writes. Retain
    #the full128beat source FIFO; add coherent owner/PC to its async delivery.
    producer_bits=64*(1+24+32)+OWNER_BITS
    producer_fifo_FF=128*64*(1+24+32)+OWNER_BITS
    producer_CDC_FF=39*(2*producer_bits+4)+4*producer_bits+52
    # Existing128beat data FIFO is retained and charged once. Only new held
    #owner metadata and transport registers enter the incremental debit.
    producer_new_FF=OWNER_BITS+producer_CDC_FF
    producer_area=producer_new_FF*(ff+inv)+39*producer_bits*(3*and3+2*inv)
    # Explicit independent quarantine validity mask plus16fullburst receipts,
    #not software debt substituted for missing mutable hardware.
    quarantine_FF=4*owners*4096+4*16*(192+16+6+5*32)
    quarantine_area=quarantine_FF*(ff+inv)
    # Two current54row windows fit128rows, but the current source has no
    #window address selector or two independent ownership leases. Reserve
    #actual bits/logic for that mandatory successor; no SRAM depth change.
    # Conservative one full operand stage per tile: all379 fields, x128,
    #ROM512, KV512 and three valid/control bits. Price both paths together,
    #rather than reserving an address edge while misaligning golden operands.
    window_operand_FF_per_tile=379+128+512+512+3
    window_FF=1536*(3+window_operand_FF_per_tile)+2*(OWNER_BITS+54+16)
    window_area=window_FF*(ff+inv)+1536*7*(9*and3+7*inv)
    new_clocks=extra_owners*owner_ff+4*pipeline_FF_per_stack+extra_pipe_ff+producer_new_FF+quarantine_FF+window_FF+return_arb_FF
    collector_allocation=[dict(name='extra_owner',domain='service',replicas=extra_owners,
                               clock_sinks=owner_ff+32,reset_sink_upper=owner_ff)]
    for w in widths:
        n=39*(2*w+4)-(w+7)
        collector_allocation.append(dict(name=f'route{w}_delta',domain='FAST_stream',replicas=4,
            clock_sinks=n,reset_sink_upper=n))
    collector_allocation.extend([
        dict(name='tagged_owner_flights',domain='service',replicas=4,
             clock_sinks=pipeline_FF_per_stack,reset_sink_upper=pipeline_FF_per_stack),
        dict(name='producer_route',domain='FAST_stream',replicas=1,
             clock_sinks=39*(2*producer_bits+4),reset_sink_upper=39*(2*producer_bits+4)),
        dict(name='producer_source_FIFO_metadata',domain='serial',replicas=1,
             clock_sinks=2*producer_bits+26+OWNER_BITS,reset_sink_upper=2*producer_bits+26+OWNER_BITS),
        dict(name='producer_destination_FIFO',domain='stream',replicas=1,
             clock_sinks=2*producer_bits+26,reset_sink_upper=2*producer_bits+26),
        dict(name='quarantine_per_stack',domain='service',replicas=4,
             clock_sinks=quarantine_FF//4,reset_sink_upper=quarantine_FF//4),
        dict(name='window_operand_stage_per_tile',domain='stream',replicas=1536,
             clock_sinks=3+window_operand_FF_per_tile,reset_sink_upper=3+window_operand_FF_per_tile),
        dict(name='window_leases',domain='stream',replicas=1,
             clock_sinks=2*(OWNER_BITS+54+16),reset_sink_upper=2*(OWNER_BITS+54+16)),
        dict(name='return_arbiter',domain='service',replicas=4,
             clock_sinks=return_arb_FF//4,reset_sink_upper=return_arb_FF//4)])
    assert sum(a['replicas']*a['clock_sinks'] for a in collector_allocation)==new_clocks+extra_macros
    collectors=sum(a['replicas']*(tree_count(a['clock_sinks'],8)['nodes']+
                   tree_count(a['reset_sink_upper'],8)['nodes']) for a in collector_allocation)
    collector_area=collectors*buf
    known_area=extra_owner_area+pipeline_area+pipe_area+arb_area+return_arb_area+producer_area+quarantine_area+window_area+collector_area
    closing=old['logical_bytes']['conditional_offchip_read_stacks']
    writes=old['logical_bytes']['conditional_selected_closing_K_V_write_stacks']
    sectors=[(r+w)//32 for r,w in zip(closing,writes)]
    # One owned/grant bus/stack carries two receipts per32B sector.
    owned_bus_s=max(sectors)*2/1e9
    owner_s=max(sectors)/1e9
    ingress_s=max(math.ceil(r/(16*32))*17+(w//32)*2 for r,w in zip(closing,writes))/1e9
    command_s=max(sectors)/1e9
    fill_s=old['token_lower_bounds']['tail_bypass_masked_fill_s']
    compute_s=old['token_lower_bounds']['conditional_compute_s']
    return dict(status='ONE_FINITE_TAGGED_OWNER_PIPELINE_STAGE_WINDOW_CANDIDATE_NOT_ADOPTED',
      selection_reason='One owner/stack against its32actual1R1W banks, retaining12-edge read latency. Existing14owner screen is a comparison only. No CAM/contextRAM replication or replica sweep.',
      policy='Die-local HBM homes, two54row stage-window leases within128current rows, actual current Ktail+Vforward only if state join passes. Full36residency not assumed.',
      owners_per_stack=owners,PCs_per_owner=32,owner_source_II_edges=14,owner_source_first_lookup_edges=12,
      tagged_pipeline=dict(first_lookup_edges=12,first_output_consume_edge=13,
        proposed_global_II_edges=1,bank_read_lease_min_edges=12,bank_count=32,
        flight_entries=32,output_entries=32,total_reserved_return_credits=32,
        metadata_bits=pipeline_metadata_bits,new_FF_per_stack=pipeline_FF_per_stack,
        new_mux_bits_per_stack=pipeline_mux_bits_per_stack,cell_reservation_um2=pipeline_area,
        duplicate_mask_bits_per_stack=32*128*32,
        invariants=['One immutable tagged bank read lease until captured at12edges; stall repeatedPC bank while leased.',
          'Reserve final output credit at return admission, preserve context/data under output backpressure.',
          'Set in-flight beat before ir acceptance; reject duplicate beats against in-flight and committed seen masks.',
          'One consumed output updates seen/remaining_PC; simultaneous allocation and final-retire use joint live_tags += alloc - retire.',
          'No context/CAM/live physical-tag reuse until consumed output, reverse grant and reader quarantine release.'],
        same_tag_hazards='One commit/edge; per-tag remaining_PC RMW serialized/forwarded. Allocation cannot share a live or quarantined tag; source ar and ir need explicit joint-update successor.',
        allocation_write_read_hazard='All32bank 1R1W writes retain actual wanted PC mask; free-context selection excludes any read lease/valid CAM, same-address read/write forbidden.',
        source_instantiated=False,physical_II_proven=False,
        comparisons=dict(existing14owner_known_macro_state_collector_mm2=screen['incremental_known_reservation_mm2'],
          pipeline_cells_before_collectors_mm2=pipeline_area/1e6,new_context_macros=0,
          pipeline_cells_plus_local_collectors_mm2=(pipeline_area+8*tree_count(pipeline_FF_per_stack,8)['nodes']*buf)/1e6,
          bandwidth='InterleavedPC stream can accept1/edge at12latency. SamePC stream cannot exceed1/12 while bank leased; actual program PC/calendar required. Matches14owner global command ceiling only conditionally.')),
      source_II1_claim=False,read_burst_MAX_LEN=16,read_burst_rule='Split at16sector boundary to fit declared PHY LEN5/BEAT4 aperture. Route complete burst to IRSslot-selected full32PC owner; all native returnPCs restore the same allocated burst, never scatter its remaining_PC counter.',
      tag_namespace='Single owner perstack uses physical12/native16 upper4zero exactly as source. All16IRSslots share owner credits. Retain192identity/404reverse; quarantine includes stack/tag/generation.',
      finite=dict(burst_slots_per_stack=16,slots_per_lane='all16 at single owner',read_sectors_max_per_stack=256,
        held_response_bytes_per_stack=16384,assembly_slots_per_stack=1024,write_residences_per_stack=4,
        request_entries_per_PC=64,return_entries_per_PC=32,owner_outstanding_limit=16,
        reverse_grant_and_reader_drain_required_before_reuse=True,tail_write_LEN=1),
      command=dict(ports_per_stack=1,payload_B_per_command=32,stacks=4,source_column_ceiling_Bps_per_rank=128e9,
        current_command_bits=339,proposed_command_bits=339,PHY_abstract_command_bits=344,
        source_tag_width_change='None for one-owner pipeline; validate native16 upper4zero and full stack/generation identity. Historical14owner aliases not adopted.',
        native_LEN6_to_PHY_LEN5='LEN1..16 retain positive counts, BEAT0..15 zeroextends into native5; licensed PHY semantics and shim gate still required.',
        actual_sustained_PHY_HBM_Bps=None,extra_PHY_ports_claimed=False,three_k_requirement_ref='results/uarch/qwen_rom_kv_rate_risk_20261002/model_r3.json#/three_k_requirement'),
      return_and_grant=dict(owned467_buses_per_stack=1,receipts_per_data_or_write_sector=2,
        source_bus_core_ceiling_data_Bps_per_rank=64e9,
        target_endpoint='Four independent STREAM stack assembly/grant endpoints; one global64Bfill. Serial producer remains separate. Native fixture globalSERresult arbiter is not sustainable production topology.',
        inherited_fixture_global_SER_arbiter_ceiling_data_Bps=14.4e9,
        combined_ingress_mux_inputs_per_stack=2,new_mux_bits=arb_mux_bits,new_mux_reservation_um2=arb_area,
        current_shared_return_arbiter_II_edges=7,current_arbiter_lower_bound_s=max(sectors)*7/1e9,
        necessary_successor='Registered fair36-way read/visible-write arbiter, source-tag identity validation, per-owner ready; emit at most one lookup/edge. No allocation or write completion bypass.',
        proposed_shared_return_arbiter_II_edges=1,proposed_arbiter_FF=return_arb_FF,
        proposed_arbiter_mux_bits=return_mux_bits,proposed_arbiter_cell_reservation_um2=return_arb_area,
        source_successor_instantiated=False),
      CDC=dict(source_route='Current held38FASTedges route consumes firstat39,nextat40;sourceII40, notII1.',
        selected_candidate='39twoentryregisteredstages per455request/467response/404reverse link; retains39firstconsume edges, newII1under no stalls must pass literal functional gate and SS/FF.',
        current_route_II_edges=40,proposed_route_II_edges=1,proposed_route_slots_per_link=78,
        bridges=12,extra_route_FF=extra_pipe_ff,extra_mux_bits=pipe_mux_bits,
        area_reservation_um2=pipe_area,source_existing_FIFOs_recharged=False,
        same_context_widths_and_payload_order=True,physical_build_admitted=False),
      producer_CDC=dict(source='ot_hdc_qwen_kv_vector_bridge source128beat FIFO,SW64,AW24,F32alreadyFP8rounded',
        serial_to_stream_packet_bits=producer_bits,full_source_FIFO_FF=producer_fifo_FF,
        retained_source_FIFO_recharged=False,new_metadata_FF=OWNER_BITS,
        async_route_and_FIFO_FF=producer_CDC_FF,cell_reservation_um2=producer_area,
        max_actual_KV_instruction_elems=256,maximum_source_fifo_elems=8192,
        holds_full_maximum_issued_op=True,drained_ack='Actual source-FIFO empty + all stream/tail/HBM visible/backed/reverse grant debts drained; return acknowledgment crosses to serial before next SU KV op.',
        rounding='Canonical bytes only from actual already-rounded source. No new rounding or synthetic payload.',
        actual_source_serial_split=False,actual_producer_trace=None),
      stage_windows=dict(rows_per_window=54,windows=2,required_rows=108,current_rows=128,
        spare_rows_not_capacity_for_full36_layers=20,selector_and_lease_FF=window_FF,
        full_operand_alignment_FF_per_tile=window_operand_FF_per_tile,
        selector_and_lease_cell_reservation_um2=window_area,
        address='physical_row=window*54+local_row, local_row0..53; reserved108..127 inaccessible',
        lease='Full owner/state and54-row validity; reader count16bits per window; no refill/reassign until last reader and reverse grant drain.',
        source_selector_instantiated=False,source_accepted_demand_calendar=None,
        added_full_operand_alignment_latency_reserve_stream_edges_per_ME=1,
        per_token_latency_formula='actual_ME_instruction_count /1.2GHz; additional to registered parent launch. Conservatively align ROM/KV/x/tags together; current source MEM_EXTRA1 capture remains once, proposed extra full stage unimplemented. No current SS closure or instruction-count claim'),
      ports=dict(global_fill_lanes=1,global_fill_payload_B_per_stream_edge=64,fill_bits=1048,
        native_request455_per_stack=4,native_return467_per_stack=4,native_reverse404_per_stack=4,
        native_total_signal_bits=4*sum(widths)+producer_bits,extra_command_tag_tracks=0,
        these_routes_are_separate_from_tile_fill_cut=True,
        physical_tile_ports_not_global_lanes=True),
      area=dict(extra_context_macros=extra_macros,extra_owner_FF=extra_owners*owner_ff,
        extra_owner_macro_logic_reservation_um2=extra_owner_area,extra_route_mux_arb_reservation_um2=pipe_area+arb_area,
        tagged_owner_pipeline_cell_reservation_um2=pipeline_area,
        producer_CDC_and_source_fifo_reservation_um2=producer_area,
        quarantine_FF=quarantine_FF,quarantine_cell_reservation_um2=quarantine_area,
        shared_return_arbiter_cell_reservation_um2=return_arb_area,
        stage_window_cell_reservation_um2=window_area,
        new_clock_sinks=new_clocks+extra_macros,new_reset_sink_upper=new_clocks,
        clock_reset_collector_buffers=collectors,collector_cell_reservation_um2=collector_area,
        per_domain_replica_collector_allocation=collector_allocation,
        collector_wire_total_um=collectors*32,leaf_wire_segment_bound_um=32,
        known_incremental_mm2=known_area/1e6,
        inherited_owner_replacement_credit=0,full_actual_context_macros_retained_per_owner=32,
        control_protection_CTS_reset_decoder_PG_OBS_route_cost='Named endpoint placements, dynamic fanout, protection and extracted collector timing required. Finite collector32umsegment/count priced, no complete fit credit.',
        useful_full_residency_min_increment_mm2=old['area']['useful_capacity_only_macro_increment_mm2'],
        literal_full_residency_increment_mm2=old['area']['resident_literal_macro_increment_mm2']),
      lower_bounds=dict(scope='Conditional optimistic source-port capacities. Neither actualHBMBW nor sustainable workload prediction.',
        owner_s=owner_s,shared_ingress_s=ingress_s,shared_column_s=command_s,
        owned_data_plus_grant_s=owned_bus_s,single_fill_s=fill_s,
        perfect_compute_overlap_transport_s=max(owner_s,ingress_s,command_s,owned_bus_s,fill_s),
        no_compute_overlap_reference_s=max(owner_s,ingress_s,command_s,owned_bus_s,fill_s)+compute_s,
        compute_reference_s=compute_s,
        compound_source_12_and_14_not_II1=True,three_k_admitted=False),
      target_feasibility=dict(target_token_period_s=1/3000,
        necessary_transport_period_s=max(owner_s,ingress_s,command_s,owned_bus_s,fill_s),
        explicit_deficit_factor=max(owner_s,ingress_s,command_s,owned_bus_s,fill_s)*3000,
        necessary_transport_time_over_budget_s=max(owner_s,ingress_s,command_s,owned_bus_s,fill_s)-1/3000,
        verdict='FAIL_3K_EVEN_AT_PERFECT_COMPUTE_OVERLAP_AND_OPTIMISTIC_PORT_CEILINGS',
        required_minima_predecessor='results/uarch/qwen_rom_kv_rate_risk_20261002/model_r3.json#/three_k_requirement',
        independent_ports_or_PHYs_selected=False,
        actual_PHY_service_calendar=None,
        actual_parallel_PHY_BW=None,
        qualification='Finite protocol fixtures and priced slot demands do not supply the missing actual producer/PHY/window service journal; explicit deficit does not depend on proving perfect overlap.'),
      production_calendar_required='Actual producer/persistent state/descriptor demand, paired K/V macro writes, allocation/full native tag/owner, all four independent stream grants, row/bank/refresh/turnaround command service and current arithmetic/CDC journal. Cold36/144 calendar remains correctness reference.',
      baseline_accounting='Replace existing KV read once. All current32PC request/return SRAM and fourPHYs charged once by named baseline join. One finite tagged-flight pipeline and replacement route delta only; no blanket inherited16.6015872mm2slot refund.',
      feasibility='Known source-sized capacity/area screen only. Sustainable service, complete floorplan and actual production policy not admitted; no final target prediction.',
      build_admitted=False)


class Pins:
    def __init__(self,parent):
        self.parent=subprocess.check_output(['git','rev-parse',parent],cwd=ROOT,text=True).strip();self.hashes={}
    def raw(self,path):
        b=subprocess.check_output(['git','show',self.parent+':'+path],cwd=ROOT)
        self.hashes[path]=hashlib.sha256(b).hexdigest();return b
    def text(self,path):return self.raw(path).decode()
    def obj(self,path):return json.loads(self.raw(path))


def build(parent):
    p=Pins(parent)
    sources={name:p.text('rtl/'+name) for name in (
       'hdc/ot_qwen_me_array_w12.sv','hdc/ot_qwen_rom_tile_context_candidate_r3_retained.sv',
       'hdc/ot_qwen_w12_matvec.sv','hdc/ot_hdc_core_vector_weight.sv','hdc/ot_hdc_vstream.sv',
       'hdc/kv/ot_hdc_qwen_kv_system.sv','hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv',
       'model_ready_hbm_r14/ot_hbm_causal_command_provider.sv','model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
       'model_ready_hbm_r14/ot_hbm_r14_fifo2.sv','model_ready_hbm_r14/ot_hbm_r14_route.sv',
       'physical/ot_qwen_rom_reset_parent_provider.sv')}
    anchors={
      'hdc/ot_qwen_me_array_w12.sv':['.d(go && ready)', '.D(BD - IREG)', '.D(BD - XVM - IREG)', '(t % NXL)*TG*32'],
      'hdc/ot_qwen_rom_tile_context_candidate_r3_retained.sv':['else go_q <= ib_go;', 'ib_q <= ib; xl_q <= xl;'],
      'hdc/ot_qwen_w12_matvec.sv':['assign ready = !active && !pend;'],
      'hdc/ot_hdc_core_vector_weight.sv':['(kv_ok && !kvd_v)','assign su_inflight = u_su.inflight;'],
      'hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv':['assign drained = used == 0 && adapter_idle && !fl_v;']}
    for name,aa in anchors.items():
        for a in aa:
            if a not in sources[name]:raise ValueError('source changed: '+a)
    physical=p.obj('results/uarch/qwen_rom_current_reset_construction_20261002/inputs/model.json')
    retained=p.obj('results/uarch/qwen_rom_retention_parent_launch_20261002/model-r1.json')
    rc=p.text('results/uarch/qwen_rom_current_reset_construction_20261002/inputs/setRC.tcl')
    cap=float(re.search(r'set_wire_rc -signal.*?-capacitance ([\d.Ee+-]+)',rc)[1])
    res=float(re.search(r'set_wire_rc -signal -resistance ([\d.Ee+-]+)',rc)[1])
    lib=gzip.decompress(p.raw('results/uarch/qwen_rom_reset_producer_g0_20261002/inputs/seq_ss.lib.gz')).decode()
    invlib=gzip.decompress(p.raw('results/uarch/qwen_rom_reset_producer_g0_20261002/inputs/invbuf_ss.lib.gz')).decode()
    def area(name,text):
        m=re.search(r'cell\s*\('+re.escape(name)+r'\)\s*\{\s*area\s*:\s*([\d.]+)',text)
        if not m:raise ValueError('missing pinned cell area '+name)
        return float(m[1])
    ff=area('DFFASRHQNx1_ASAP7_75t_R',lib);inv=area('INVx1_ASAP7_75t_R',invlib);buf=area('BUFx4_ASAP7_75t_R',invlib)
    joins=p.obj('results/uarch/qwen_rom_current_reset_construction_20261002/inputs/launch_join_cells_r1.json')
    and3=joins['ss']['area_um2']
    terminal=p.obj('results/rtl/qwen_rom_TP4_terminal_20261002/original_terminal.json')
    numerical=dict(design_point=terminal['design_point'],wire_stages=terminal['wire_stages'])
    # These are retained wire stages, not a new all-1.2GHz numerical position.
    bd=numerical['wire_stages']['broadcast_and_x_network_bd']
    xvm=numerical['wire_stages']['vm_conflict_register_xvm']
    nt=1536;tg=4;smax=numerical['design_point']['smax'];nxl=(1<<smax)//tg
    if nt%nxl:raise ValueError('source x line replica partition')
    inst_tree=tree_count(nt,8);array_tree=tree_count(nt,8)
    # Minimum explicit global buffer topology, not extracted electrical closure.
    inst_buffers=380*inst_tree['nodes'];x_buffers=nxl*128*tree_count(nt//nxl,8)['nodes']
    peer_ready=p.obj('results/uarch/qwen_rom_owned_ready_context_20261002/model-r1.json')
    peer_parent=p.obj('results/uarch/qwen_rom_local_parent_composition_20261002/model-r1.json')
    remote=5;local=1
    remote_ff=1+2+FRAME_BITS+1+2+FRAME_BITS+1+2
    new_ff=remote*remote_ff+local*FRAME_BITS+1+379+OWNER_BITS+192+1+nt+array_tree['nodes']
    # Existing452 inputs plus13 additional owner predicates, per peer screen;
    #quarantine4096*14 validity bits must also be reduced, never hidden debt.
    service_inputs=452+4096+32*128*32+32+16
    source_status_bits=dict(service_per_stack=service_inputs,serial=11,kv=64,array_per_tile=7)
    reductions=sum(tree_count(n,3)['nodes'] for n in (service_inputs,)*4+(11,64,7))
    # Register tile ready reduction; inactive source-state bits are local.
    raw_status_inv=4*service_inputs+11+64+nt*7
    local_reduction_cells=reductions+nt*tree_count(7,3)['nodes']
    equality_bits=len(EXPORTS)*OWNER_BITS
    # Explicit area reservation for bit equality:3AND3+5INV/bit then AND3 tree.
    equality_area=equality_bits*(3*and3+5*inv)+len(EXPORTS)*tree_count(OWNER_BITS,3)['nodes']*and3
    parent_collectors=2*tree_count(new_ff,8)['nodes']
    new_area=new_ff*(ff+inv)+(inst_buffers+x_buffers+parent_collectors)*buf+raw_status_inv*inv+local_reduction_cells*and3+equality_area
    service=service_candidate(p,ff,inv,buf,and3)
    # Current tile geometry, one deterministic64x24 model allocation in envelope.
    slot=physical['slot'];w=slot['w_um'];h=slot['h_um'];cols=64;rows=24
    common_wire=(rows-1)*h+rows*(cols-1)*w
    ib_wire=380*common_wire
    # One3sink x tree/line, explicit two neighbor links per payload bit.
    x_wire=nxl*128*2*w
    # Six ready exports to parent and tile readiness aggregation use same grid.
    ready_wire=common_wire
    # CDC mailbox/control/capture-to-sink segments retain explicit32um each;
    # endpoint-to-parent lengths are separate measured dependencies, not zero.
    local_cdc_wire=remote*(OWNER_BITS+1+FRAME_BITS+1)*32+parent_collectors*32
    wire=ib_wire+x_wire+ready_wire+local_cdc_wire
    signals=1048+64+64+379+1+128+1
    capacity=sum(physical['corridor']['capacity_by_layer'].values())
    tree_pipe_ff=nt+array_tree['nodes']
    exports={
      'service0..3':dict(domain='service candidate1GHz',instances=4,owner='Kepler/Russell',
        source='ot_hbm_causal_command_provider.on qcount[32],rcount[32],ingress,wr_live/backed/mapped,grant_valid; owner state/held/live_tags; all connected bridge pointers/on and route.live',
        local_export='Registered local_release && enabled && !fault && all source queues/held route empty && quarantined allocations/reverseACK/grant/readers drained',
        added_ownership='Current early tag-free source requires retained quarantine debt until consumed reverse grant; snapshot may not repair missing ACKs.'),
      'serial':dict(domain='serial target0.9GHz',instances=1,owner='Ampere/Euclid',
        source='ot_hdc_core_vector_weight.g_vsu.u_su.active/inflight/idle and KV producer strobes; real SU FIFO/held write debts',
        local_export='Registered released && !active && inflight==0 && no accepted producer/write debt && healthy',
        current_source='SU currently uses clk, not a separate physical serial clock/reset port. Contract prices target CDC; it does not assert source split exists.'),
      'kv':dict(domain='stream target1.2GHz',instances=1,owner='Russell',
        source='ot_hdc_qwen_kv_system desc_pending/boot; vector_bridge used/adapter_idle/fl_v; actual tail/window ownership and assembly/readers/reverse credits',
        local_export='Registered mutable state owner bound to same user/rank/epoch, writes visible and prior readers drained. Never reset persistent payload on layer hop.'),
      'array':dict(domain='stream target1.2GHz',instances=1,owner='Euclid/Ampere',
        source='All1536tile issuer active/pend/go_q and ROM/KV capture validity, array broadcast/x/tree validity debt',
        local_export='1536 local ready FFs and220 eight-way registered aggregation FFs;4startup edges. Safe per-op broadcast remains a source timing induction using actual go&&ready.',
        incremental_FF=tree_pipe_ff)}
    return dict(schema='opentallas.qrom-parent-context-g0-interface.v1',
      status='COMPLETE_INTERFACE_PRICE_CONTRACT_PHYSICAL_AND_ACTUAL_SERVICE_GATES_FAIL',parent=p.parent,
      selected_interface='Existing six-export topology; five remote leased104bit four-phase mailboxes, one local stream export folding KV and all tile readiness; registered join/launch and actual source379bit+128x capture retained.',
      peer_join=dict(owned_ready_status=peer_ready['status'],local_parent_status=peer_parent['status'],
        topology_replaced_not_added=True,export_count=6,
        stream_fold='kv AND all1536 array predicates are one stream export, not a seventh channel',
        metadata_delta='33bit sequence+ready upgraded to100bit owner/PC/sequence+4 predicates. Full192bit native transaction identity remains in service receipt path.',
        area_credit=0,reason='No named baseline realization; total required cells reported rather than adding both readiness candidates.'),
      owner_fields=OWNER_FIELDS,status_fields=STATUS_FIELDS,exports=exports,
      protocol=dict(startup='QUIESCE -> same-owner request -> local release/drain/state binding -> held source frame/ack -> stream2FF ack/capture -> all6sameowner -> registered ready -> registered launch -> explicit matching consume; reset/abort requires quarantine receipt.',
        CDC='Request2FF in source; source frame registered and stable before ack. Ack2FF in stream, destination capture next edge. Consumer drops request only after registered launch; source releases lease after2FF request/oneedge and stream waits2FF ack/oneedge before reuse.100/104bit buses held, never independently bit-synchronized. Ampere must time aperture and ack/data skew.',
        no_deadline='Source waits for actual drain/state; finite residence is not a finite elapsed-time guarantee under stalled consumer.',
        per_instruction='Startup once per reset/epoch; retain actual core issue/kv_ok&&!kvd_v, write-visible/dependent order. Hold complete379 fields/ownerPC at accepted root issue; registeredlaunch1edge then same BD pipeline. X remains its source-addressed stream, never an instruction-lifetime constant.'),
      parent_connections=dict(request='Actual core.issue/me_go, decoded DYN-adjusted ME fields, core.pc and Owner/sequence ->379bit held root record; source must stall load/reuse while occupied.',
        registered_launch='Stream parent launch FF drives spine.go with held fields; top go&&ready drives existing BD-IREG go pipeline; tile go_q/ib_q sample existing IREG.',
        x='Existing x_q -> x_split delayed2+XVM -> source r&(quads-1) line selection -> BD-XVM-IREG -> tile xl_q128 -> MEM_EXTRA1. Preserve every streaming value/tag in golden order.',
        receipt='All owner exports and root/tile acceptance journal must match actual source edges. Per-tile128x differs by line; no global128bit broadcast fiction.'),
      clocks=dict(stream_Hz=1200000000,serial_target_Hz=900000000,service_candidate_Hz=1000000000,
        SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,source_closed=False,
        new_clock_sinks_per_rank=new_ff,new_reset_sinks_upper_per_rank=new_ff,
        existing_tile_clock_sinks_per_rank=102352*nt,existing_tile_reset_sinks_per_rank=56683*nt,
        service_macro_clocks=384,tail_macro_clocks=128,these_MACRO_clocks_recharged=False,
        additional_CTS_reset_PG_cost='Ampere source-local allocation required; included new sink demand, no zero wire/CTS cost or imported balanced tree claim.'),
      ports=dict(MACs_per_cycle=0,memory_bytes_per_cycle_added=0,
        tile_instruction_bits=379,tile_x_bits=128,tile_go_bits=1,replicas=nt,
        existing_capture_bits=nt*508,existing_capture_area_reservation_um2=nt*508*ff,existing_capture_recharged=False,
        unique_x_lines=nxl,x_line_fanout=nt//nxl,x_payload_bytes_per_stream_edge=nxl*16,
        actual_local_x_pin_bytes_per_stream_edge=nt*16,these_are_not_KV_HBM_bandwidth=True,
        remote_mailbox_count=remote,forward_bits_per_mailbox=OWNER_BITS+1,reverse_bits_per_mailbox=FRAME_BITS+1,
        raw_PC_counts_crossed=False,source_owned_local_reductions=True,
        instruction_fanout=nt,instruction_distribution_buffers=inst_buffers,x_distribution_buffers=x_buffers,
        actual_mux_rule='src=r&((1<<x_split)/TG-1), all source x_q32bits. Current mux area stays in baseline; current instruction data delay registers stay in baseline.'),
      cells=dict(ASR_area_um2=ff,INV_area_um2=inv,BUF_area_um2=buf,AND3_area_um2=and3,
        remote_mailbox_FF_each=remote_ff,total_new_FF=new_ff,
        new_FF_area_um2=new_ff*(ff+inv),clock_reset_collector_buffers=parent_collectors,
        distribution_buffer_area_um2=(inst_buffers+x_buffers)*buf,source_status_input_bits=source_status_bits,
        local_status_INV=raw_status_inv,local_reduction_AND3=local_reduction_cells,
        equality_area_reservation_um2=equality_area,known_incremental_area_um2=new_area,
        known_incremental_area_mm2_per_rank=new_area/1e6,
        scope='Explicit conservative cell reservation, not mapped cell count or electrical fit. Existing global distribution replacement credit0 until Maxwell names baseline components; never recharge existing508tile capture FFs.'),
      wire=dict(grid_columns=cols,grid_rows=rows,grid_w_um=cols*w,grid_h_um=rows*h,
        instruction_um=ib_wire,x_um=x_wire,ready_um=ready_wire,local_mailbox_segments_um=local_cdc_wire,
        total_allocated_um=wire,nominal_cap_fF=wire*cap,nominal_resistance_ohm_per_um=res,
        root_to_remote_service_mailbox_global_segments='Ampere must allocate real endpoint coordinates; not hidden in32umlocal tails.',
        allocation_scope='Deterministic current-slot row-spine wiring price, not a routed die or an optional design sweep.',
        nominal_RC_extracted=False,
        shared_tile_cut_tracks_required=signals,shared_tile_cut_nominal_capacity=capacity,deficit=signals-capacity,
        separate_channel_allocation_required=True,shared_corridor_admitted=False),
      slot=dict(baseline_array_mm2=slot['array_area_mm2_per_1536tile_die'],remaining_other_services_mm2=slot['die_other_services_remaining_mm2'],
        KV_service_plus_tail_macro_mm2=4.569720064,KV_assembly_logic_lower_mm2=.9399877632,
        additional_parent_interface_cell_reservation_mm2=new_area/1e6,
        inherited_service_or_global_distribution_replacement_credit=0,
        complete_slot_fit=False,complete_cell_fit_in_tile=False,
        retained_physical_status=retained['status'],CTS_reset_PG_wires_and_controller_cost_not_zero=True),
      joint_service_architecture=service,
      baseline_debit_join=dict(existing_tile_capture='All508bits/tile and source BD/XVM/MEM_EXTRA remain in current tile/parent source budget. Increment0;379root hold is a new proposed FF bank.',
        existing_KV='Replace useful KV read byte charge once. Same mutable HBM homes and current windows; no full-refill surcharge.',
        existing_owner='Current4owners/32PC request+return arrays perstack included once. One proposed32flight owner pipeline perstack, no extra contextRAM/CAM copies; full original384service macros remain once.',
        PHY='Four source PHY footprint40.00784006016mm2 is charged only if absent from named baseline; no new PHY bandwidth or replicas claimed.',
        global_distribution='Total required83600instruction and65536x buffers priced; root/array placement and named baseline credits pending. These cell counts do not automatically enlarge747.652allocated array footprint.',
        known_new_service_cell_mm2=service['area']['known_incremental_mm2'],
        parent_interface_cell_reservation_mm2=new_area/1e6,
        remaining_if_all_new_debits_and_PHY_outside_baseline_mm2=slot['die_other_services_remaining_mm2']-4.569720064-.9399877632-service['area']['known_incremental_mm2']-new_area/1e6-40.00784006016,
        complete_named_Maxwell_receipt=False,complete_slot_fit=False,
        no_baseline_refund_or_doublecharge_claim=True),
      latency=dict(startup_only=True,remote_service_ack_bound_if_ready_ns=3/1e9*1e9+3/1.2e9*1e9,
        remote_serial_ack_bound_if_ready_ns=3/.9e9*1e9+3/1.2e9*1e9,
        array_aggregation_stream_edges=array_tree['depth'],registered_ready_edges=1,registered_launch_edges=1,
        startup_composition='max(actual domain release/drain+source mailbox acknowledgment, array4edges)+ready1edge+launch1edge; boot/state/consumer stalls additional.',
        incremental_per_ME_launch_stream_edges=1,incremental_per_ME_launch_ns=1/1.2e9*1e9,
        per_token_increment_formula='accepted_ME_instruction_count *0.833333ns, once; emitted/actual accepted journal required for total. Existing BD/XVM/MEM_EXTRA/ORD price replaced/joined once, never doublecharged.',
        existing_BD=bd,existing_XVM=xvm,retained_numerical_reference=numerical,
        current_SMIN6_wire_calendar_join_required=True,old_SMIN7_wire_calendar_transferred=False,
        current_transport_read_write_lower_bound_ms=16.498944,no_3k_rate=True,adopted_latency=False),
      obligations=['Source-state exporter callbacks and leases backed by actual mutable state/provider and literal allocation/ACK/grant/drain journal',
        'Euclid source split/order/379+128 capture graph and safe all1536 acceptance',
        'Ampere full remote endpoint placements, local-domain reset/CTS and mailbox held-data aperture/setup/hold routes',
        f'Maxwell named baseline components and separate signal cuts; known corridor{signals-capacity}track deficit and retained clock failures block RTL',
        'Russell selected persistent production calendar and safe quarantine successor full model; cold calendar never production'],
      source_sha256=p.hashes,hardware_admitted=False,new_RTL=False,new_decode=False,new_PnR=False)


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--parent-ref',required=True);a.add_argument('--result',type=Path,required=True)
    args=a.parse_args();record=build(args.parent_ref)
    with args.result.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
