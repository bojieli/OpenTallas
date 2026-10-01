#!/usr/bin/env python3
"""Source-bound, OFF multi-line HBM burst analytical model; no RTL/build."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import w19_landing_banks as B

ROOT=Path(__file__).resolve().parents[1]
CTRL='rtl/hdc/kv/ot_hdc_hbm_model.sv'


def source_contract():
    source=(ROOT/CTRL).read_text()
    params={k:int(re.search(r'parameter integer\s+'+k+r'\s*=\s*(\d+)',source).group(1)) for k in ('LENW','BEATW','TAGW','QD','RQD')}
    required=('LENMAX = 1 << (LENW - 1)', 'q_beat[p][slot] = i[BEATW-1:0]',
        'q_tag[p][slot] = req_tag',
        '(((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC))) & (NPC - 1)',
        'if (tb_i < req_len)', 'for (i = 0; i < req_len; i = i + 1)')
    if not all(text in source for text in required): raise ValueError('controller length/tag/map source changed')
    if (params['LENW'],params['BEATW'],params['TAGW'])!=(5,4,16): raise ValueError('wire widths changed')
    params.update(runtime_NPC=32,runtime_sector_AW=27,sector_bytes=32,
        safe_max_read_sectors=min(1<<(params['LENW']-1),1<<params['BEATW']),
        existing_request_ports=1,
        oversized_len='Reject0 and17..31. Existing admission only scans16 needs while enqueue scans req_len, and4bit beat would alias. Width5 does not imply a safe31sector burst.',
        write_rule='req_we stays0 on this candidate; writes remain one32B sector with separate commit/fence contract')
    return params


def pc_of(sector): return ((sector>>2)^(sector>>7)^(sector>>12))&31


def need(sector,length):
    if sector%4 or length not in (4,8,12,16) or not 0<=sector<1<<27 or sector+length>1<<27:
        raise ValueError('aligned128B line burst4..16sectors must fit full27bit aperture')
    c=Counter(pc_of(sector+i) for i in range(length))
    return [c[p] for p in range(32)]


def joint_ready(requests,rooms):
    if len(rooms)!=32 or any(not 0<=r<=64 for r in rooms): raise ValueError('finite PC rooms required')
    combined=[0]*32
    for addr,length in requests:
        for p,n in enumerate(need(addr,length)):combined[p]+=n
    return all(n<=rooms[p] for p,n in enumerate(combined))


class Burst:
    """Finite groups tied to the banked cycle oracle; atomic reservation model."""
    def __init__(self,groups=1024,credits=None):
        if not 0<groups<=1024:raise ValueError('finite groups required')
        self.generations=[0]*groups;self.pending={};self.landing=B.Landing()
        self.credits=Counter() if credits is None else credits
        self.ring_lines={};self.epoch=0

    def prepare(self,addr,owners,region_end,mode='SM'):
        n=len(owners);length=4*n
        need(addr,length)
        if n not in range(1,5) or any(o not in range(32) for o in owners) or addr+length>region_end or mode not in ('SM','raw'):
            raise ValueError('burst crosses legal region/endpoint contract')
        demand=Counter(owners)
        if mode=='SM' and any(self.credits.get(o,0)<count for o,count in demand.items()):return None
        used={p['group'] for p in self.pending.values()}
        group=next((i for i,g in enumerate(self.generations) if i not in used and g<8),None)
        if group is None:return None
        tag=(self.generations[group]<<12)|(group<<2)
        # Four group slots stay reserved, including unused short-burst suffix.
        for i,o in enumerate(owners):self.landing.allocate(tag+i,o)
        if mode=='SM':
            for o,count in demand.items():self.credits[o]-=count
        self.pending[tag]=dict(group=group,addr=addr,length=length,owners=list(owners),
            epoch=self.epoch,issued=False,seen=0,delivered=0,mode=mode)
        return tag

    def grant(self,tag,rooms,controller_ready=True):
        p=self.pending[tag]
        if p['issued']:raise ValueError('duplicate request grant')
        if not controller_ready or not joint_ready([(p['addr'],p['length'])],rooms):return False
        p['issued']=True
        return True

    def request(self,tag):
        p=self.pending[tag]
        return dict(req_we=0,req_addr=p['addr'],req_len=p['length'],req_tag=tag)

    def step(self,responses=None,ready=None):
        responses={} if responses is None else responses
        mapped={}
        for pc,(tag,beat,data,epoch) in responses.items():
            p=self.pending.get(tag)
            if p is None or not p['issued'] or epoch!=p['epoch'] or not 0<=beat<p['length'] or p['seen']>>beat&1 or pc!=pc_of(p['addr']+beat):
                raise ValueError('unissued/stale/duplicate/PC/beat burst response')
            mapped[pc]=(tag+(beat>>2),beat&3,data)
        accepted,events=self.landing.step(mapped,ready=ready)
        for pc in accepted:
            tag,beat,_,_=responses[pc];self.pending[tag]['seen']|=1<<beat
        for event in events:
            tag=event['tag']&~3;p=self.pending[tag];i=event['tag']&3
            p['delivered']|=1<<i
            if p['mode']=='SM':self.ring_lines[event['tag']]=(event['owner'],False)
            if p['delivered']==(1<<len(p['owners']))-1:
                if p['seen']!=(1<<p['length'])-1:raise AssertionError('delivered before all sectors accepted')
                self.generations[p['group']]+=1;del self.pending[tag]
        return accepted,events

    def consume_SM_line(self,line_tag):
        owner,_=self.ring_lines.pop(line_tag)
        self.credits[owner]=self.credits.get(owner,0)+1

    def reset_drained(self):
        if self.pending or self.ring_lines:raise ValueError('burst/ring consumers not drained')
        self.landing.reset_drained();self.generations=[0]*len(self.generations)
        self.epoch=(self.epoch+1)&65535


def trace():
    m=Burst(credits=Counter({s:1 for s in range(4)}))
    tag=m.prepare(0,list(range(4)),16);assert m.grant(tag,[64]*32)
    # Actual NPC is one sector/PC/cycle. Every line returns in reverse order.
    for beat_in_line in (3,1,2,0):
        m.step({pc_of(4*line+beat_in_line):(tag,4*line+beat_in_line,bytes([4*line+beat_in_line])*32,0) for line in range(4)})
    for _ in range(12):m.step()
    assert not m.pending and len(m.ring_lines)==4
    events=m.landing.delivered
    expected=b''.join(bytes([i])*32 for i in range(16))
    actual=b''.join(e['data'] for e in sorted(events,key=lambda e:e['tag']))
    assert actual==expected
    return dict(request=m.request(tag) if tag in m.pending else dict(req_we=0,req_addr=0,req_len=16,req_tag=tag),
        physical_PC_counts=need(0,16),accepted_sectors=m.landing.accepted,
        delivered_lines=len(events),first_delivery_cycle=min(e['cycle'] for e in events),
        last_delivery_cycle=max(e['cycle'] for e in events),exact_bytes_sha256=hashlib.sha256(actual).hexdigest(),
        SM_credits_after_delivery=dict(m.credits),SM_ring_lines_awaiting_consumers=len(m.ring_lines),
        scope='Finite cycle oracle only; source wait/preparation/CDC/physical clocks excluded')


def trace32PC():
    m=Burst(groups=8,credits=Counter({sm:1 for sm in range(32)}))
    tags=[]
    for g in range(8):
        tag=m.prepare(16*g,list(range(4*g,4*g+4)),128)
        assert m.grant(tag,[64]*32);tags.append(tag)
    for beat_in_line in (3,1,2,0):
        responses={}
        for g,tag in enumerate(tags):
            for line in range(4):
                beat=4*line+beat_in_line;pc=pc_of(16*g+beat)
                assert pc not in responses
                responses[pc]=(tag,beat,bytes([g*16+beat])*32,0)
        accepted,_=m.step(responses);assert len(accepted)==32
    for _ in range(100):m.step()
    assert not m.pending and len(m.ring_lines)==32
    events=sorted(m.landing.delivered,key=lambda e:e['tag'])
    actual=b''.join(e['data'] for e in events)
    assert actual==b''.join(bytes([i])*32 for i in range(128))
    return dict(preissued_bursts=8,serial_prepare_cycles=8,serial_request_grant_cycles=8,
        accepted_sectors=m.landing.accepted,written_sectors=m.landing.writes,
        delivered_lines=len(events),sector_bank_collision_cycles=m.landing.arb_collision_cycles,
        first_delivery_cycle=min(e['cycle'] for e in events),last_delivery_cycle=max(e['cycle'] for e in events),
        exact_bytes_sha256=hashlib.sha256(actual).hexdigest(),
        scope='Response-only trace with actual32PC map; preissued bursts and required setup/grant cycles explicit, HBM timing/CDC waits unpriced. Synchronized beat phases expose landing collisions; not a sustained service rate.')


def build():
    wire=source_contract();old=B.layout();clock=1200000000;burst_bytes=wire['safe_max_read_sectors']*32
    one=burst_bytes*clock;minimum=math.ceil(1e12/one)
    # Group static80bits => one whole1024x256 macro. Mutable32bits/group
    # are multiport registers for32PC merges and8 delivery retirements.
    static_fields=dict(physical_sector=27,epoch=16,sequence=32,line_count=3,service_class=2)
    hot_fields=dict(generation=3,live=1,valid_lines=4,received_sectors=16,delivered_lines=4,issued_lines=4)
    assert sum(static_fields.values())==80 and sum(hot_fields.values())==32
    extra_bits=1024*256+1024*32+10+50
    one_bytes=old['bytes_per_rank']+4*((extra_bits+7)//8)
    # Two allocators need two context banks: each512used rows occupies a full
    #1024x256 macro. Complementary group parity maps four line writes to
    #different halves of the eight line banks; same parity must stall.
    extra_two_bits=2*1024*256+1024*32+2*(10+50)
    two_bytes=old['bytes_per_rank']+4*((extra_two_bits+7)//8)
    return dict(schema='opentallas.w19.burst_ingress_model.v1',source_wire_contract=wire,
        pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (CTRL,
            'tools/w19_landing_banks.py','tools/w19_transport_contract.py','tools/w19_burst_ingress.py',B.TRANSPORT,B.MACRO)},
        addressing=dict(physical_consecutive=True,alignment_sector_multiple=4,sector_AW=27,
            region_end_checked=True,virtual_stripe='Four physical lines/controller correspond to virtual strides512B. Coalesce only inside actual compatible descriptor extent; no host repack, modulo, reload or borrowed service.'),
        tags=dict(bits=16,write_namespace_bit=15,read_generation_bits='14:12',
            group_bits='11:2',reserved_zero_bits='1:0',groups=1024,slots_per_group=4,
            response_wire_epoch_bits=0,
            epoch_oracle_scope='The oracle epoch operand is fault-control metadata, not a controller response wire. Actual epoch/tag-generation reuse requires complete source/controller/landing/destination drain; no implicit epoch field or hardware epoch-fault qualification claimed.',
            line_slot='(req_tag&4095)+(rsp_beat>>2)',sector_in_line='rsp_beat&3',
            generation='All requested members share generation. Hold complete four-slot group until every requested line is delivered. Increment only then; no wrap before drained epoch transition.',
            short_burst='1..4 lines use a group prefix; unused suffix remains reserved. No independent reuse inside a live group.',
            reset='Drain prepared/issued groups, ingress FIFOs, assembled outputs and SM ring consumers before epoch/reset; request acceptance never implies write commit.',
            atomic='Reserve group, all per-line immutable contexts and required SM destination ring credits together before req_valid. Stall retains req_addr/req_len/tag and reservations. Raw HC destinations use valid/ready and hold landing on stall.'),
        PC_map_samples={str(s):need(s,16) for s in (0,124,4092,4096,(1<<26),(1<<27)-16)},
        credit=dict(controller_QD_per_PC=64,controller_RQD_per_PC=32,
            actual_default_PC_RDY=0,targeted_PC_RDY=1,
            rule='Default readiness requires16 free on everyPC; targeted mode uses exact16sector need. Two proposed ports require joint need=sum(port demands) before either grant; independently ready requests can overfill a PC.',
            SM_ring_credit_counter_bits_per_rank=32*11,SM_ring_credit_counter_storage_included=False,SM_credit_authority='Single authoritative rank/SM ring ledger; no independent shadow pools across controllers. Reservation grants and multiport counter updates unqualified.',
            SM_credit_release='Destination landing does not free SM ring capacity; only downstream SM consumer releases it.',
            nonSM_HC='External3072B/SM buffers are separate from landing; CDC/visibility/global barrier waits remain unknown. No free overlap or RF32temporary reserve credit.'),
        throughput=dict(clock_hz=clock,max_wire_burst_sectors=16,max_wire_burst_bytes=burst_bytes,
            single_request_port_ceiling_bytes_s=one,minimum_request_ports_for_nominal_1TB_s=minimum,
            proposed_two_port_ceiling_bytes_s=2*one,response32PC_ceiling_bytes_s=32*32*clock,
            eight_landing_lane_ceiling_bytes_s=8*128*clock,
            sustained_completed_service_bytes_s=None,one_TB_credited=False,
            note='Two-port nominal1.2288TB/s is conditional on queue admission, complementary metadata allocation and delivery. Existing controller has one port. HBM burst timing/refresh/source/destination stalls reduce actual completed service.'),
        storage=dict(group_static_fields=static_fields,group_hot_fields=hot_fields,
            group_hot_multiport_update='Up to32 response mask writes merge per burst group; up to8 delivered-line updates merge with them. Single live/gen/valid state; duplicate/stale beat checks before credit retirement.',
            baseline_banked_bytes_per_rank=old['bytes_per_rank'],
            one_port_extra_bits_per_controller=extra_bits,
            one_port_total_bytes_all96=one_bytes*96,
            one_port_total_bytes_per_rank=one_bytes,one_port_macros_per_controller=41,
            two_port_extra_bits_per_controller=extra_two_bits,
            two_port_total_bytes_per_rank=two_bytes,two_port_macros_per_controller=42,
            two_port_total_bytes_all96=two_bytes*96,
            excluded_unknown_storage='SM authoritative credit allocator logic, CDC and physical rank-age arbitration remain separately unqualified'),
        ports_and_schedule=dict(one_port_prepare_contexts_per_cycle=4,
            one_port_group_metadata_write_ports=1,per_line_context_banks_written=4,
            one_port_prepare_cycles=1,earliest_request_grant_edge_after_prepare=1,
            response_group_hot_updates_per_cycle=32,delivery_group_hot_updates_per_cycle=8,
            joint_queue_credit_PC_count=32,joint_need_adders_for_two_ports=32,
            same_group_pairwise_comparisons_for32returns_and8retirements=40*39//2,
            group_compare_bits=10+3,actual_request_boundary_bits=307,
            proposed_two_port_request_boundary_bits=614,
            two_port_allocation='Two group context banks by group parity; choose one even and one odd to write8 distinct line banks in one cycle. Stalls if complementary free groups/credits unavailable; no peak-rate guarantee.',
            two_port_request_enqueue='Up to32 sectors accepted/controller/cycle; multiple writes to each64-entry PC queue need explicitly coalesced enqueue indices. Current one-port behavioral loop is not a priced dual-port hardware implementation.',
            arbitration_pipeline_cycles=None,actual_grant_latency_cycles=None),
        cycle_oracle=trace(),cycle_oracle_actual32PC=trace32PC(),area_mm2=None,route_tracks=None,slot_fit=None,
        clock_closure=False,HC_CDC_and_fence_cycles=None,full_token_cycles=None,
        enabled_default=False,ready_to_build=False,new_RTL=False,new_PnR=False,
        unified_generator_modified=False,accepted256_baseline_modified=False,hardware_adopted=False,
        owner_handshake=dict(transport_owner='W19',composed_graph_and_HC_owner='Turing',
            source_graph_pin_changed=False,pending22phase_companion_qualified=False,
            next='Bind burst reservation/preparation and increased41/42macro storage to actual descriptor extents, HC/raw writes, barriers and complete source/destination service. Area/route/SSFF remain prerequisite.'))


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--out',type=Path);g.add_argument('--check',type=Path);a=p.parse_args();r=build()
    if a.check:
        if json.loads(a.check.read_text())!=r:raise ValueError('burst model/source drift')
    else:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print('PASS finite burst analytical model; single-port614.4GB/s ceiling, no1TB credit or build/adoption')

if __name__=='__main__':main()
