#!/usr/bin/env python3
"""ONE visibility-anchored source owner; no unreserved downstream transfer.
169-bit context retained. Widen proposed user16 wire fields to32; no truncation
or unproved runtime-user domain. Original provider/FAIL records unchanged.
"""
import argparse,hashlib,json,heapq
from fractions import Fraction
from pathlib import Path
import dsrom_I66_capture_owner as O
OUT=O.ROOT/'results/uarch/dsrom_I66_capture_visibility_successor_20261002'
class Owner(O.Owner):
    def __init__(self,*a):
        super().__init__(*a);self.credit_retired=set();self.visibility_edges={};self.delivery_edges={};self.credit_capture_edges={}
    def issue(self,row,ctx,edge,physical_shard):
        just_returned=sum(t==edge for t in self.credit_capture_edges.values())
        if len(self.issued)+just_returned>=self.capacity:return False
        return super().issue(row,ctx,edge,physical_shard)
    def consume(self,ready,edge):
        r=self.next_delivery
        if not ready or r not in self.returned:return None
        if edge<=self.arrival_edges[r] or (self.last_consume is not None and edge<=self.last_consume):
            raise ValueError('registered consumer acceptance')
        # Keep issued source debt and original captured row. No new VM seat.
        value=self.returned.pop(r);self.next_delivery+=1;self.last_consume=edge;self.delivery_edges[r]=edge
        return r,value
    def mark_visible(self,row,ctx,edge):
        if row not in self.delivery_edges or edge<=self.delivery_edges[row]:raise ValueError('actual causal visibility after writer')
        super().mark_visible(row,ctx);self.visibility_edges[row]=edge
    def captured_credit(self,row,ctx,edge,delay):
        if O.identity(ctx)!=self.ctx or row not in self.issued or row not in self.visibility_edges or row in self.credit_retired:
            raise ValueError('unowned/duplicate/before-visible credit')
        if delay<=0 or edge<self.visibility_edges[row]+delay:raise ValueError('positive visibility-to-captured-return')
        self.issued.pop(row);self.credit_retired.add(row);self.credit_capture_edges[row]=edge
    def release(self,*a):
        if len(self.credit_retired)!=576:raise ValueError('source row credit debt')
        super().release(*a)

def identity_wire(ctx):
    O.identity(ctx)
    # The minimal selected repair is widening, never domain inference/narrowing.
    return dict(ctx)

def widths():
    p=json.loads((OUT/'inputs/selected_provider.json').read_text())['ports']
    if p['packet_header_fields']['user']!=16 or p['command_fields']['user']!=16:raise ValueError('pinned source user16 proposal changed')
    hf=dict(p['packet_header_fields']);cf=dict(p['command_fields']);hf['user']=32;cf['user']=32
    if sum(hf.values())!=144 or sum(cf.values())!=237:raise ValueError('complete header/command width')
    return dict(context_bits=169,compound_context_bits=170,request_bits=187,reply_bits=240,
        original_proposal_user_bits=16,selected_wire_user_bits=32,header_fields=hf,command_fields=cf,
        header_bits=144,command_bits=237,flit_bits=256,header_flits=1,command_flits=1,
        extra_packet_memory_or_CRC_data_bits=0,CRC_covers_entire_existing256bit_flit=True,
        padding_bits_consumed_header=16,padding_bits_consumed_command=16,
        source_TX_RX_256bit_memories_unchanged=True,header_and_command_codec_new_implementation_required=True,
        per_dedicated_header_or_command_register_extra_bits=16,
        codec_compare_control_area_and_fanout_not_free=True,physical_boundary_width_changes=0,
        full_phase_cycles_unchanged_claim=False,runtime_user_domain_assumption=False)

def encode(fields,values):
    if set(fields)!=set(values):raise ValueError('complete wire identity fields')
    word=0;offset=0
    for name,width in fields.items():
        v=values[name]
        if type(v)!=int or not 0<=v<1<<width:raise ValueError('wire field width, no truncation')
        word|=v<<offset;offset+=width
    if offset>256:raise ValueError('packet capacity')
    return word

def decode(fields,word):
    if type(word)!=int or not 0<=word<1<<256:raise ValueError('flit width')
    values={};offset=0
    for name,width in fields.items():values[name]=(word>>offset)&((1<<width)-1);offset+=width
    if word>>offset:raise ValueError('noncanonical padding')
    return values

def replay(ctx,capacity,issue_edges,return_delays,consumer_edges,visible_edges,ack_edge,credit_return_delay):
    rows={r:(r%256)//2 for r in range(576)};o=Owner(ctx,rows,capacity)
    for r in range(576):o.capture(r,rows[r],r) # opaque software controltest values
    o.source_terminal(True)
    def ordered(xs):
        xs=list(map(Fraction,xs))
        if any(b<=a for a,b in zip(xs,xs[1:])):raise ValueError('ordered edge identity')
        return set(xs)
    issues=ordered(issue_edges);consumers=ordered(consumer_edges)
    delay=Fraction(credit_return_delay)
    if delay<=0 or set(return_delays)!={0,1} or min(map(Fraction,return_delays.values()))<=0:raise ValueError('positive reply and capturedcredit providers')
    if set(visible_edges)!=set(rows):raise ValueError('all actual VM visibility obligations required')
    visible={r:Fraction(t) for r,t in visible_edges.items()}
    ack=Fraction(ack_edge);queued=issues|consumers|set(visible.values())|{ack};heap=list(queued);heapq.heapify(heap)
    pending={};credits={};journal=[];peak=0
    def schedule(t):
        if t not in queued:queued.add(t);heapq.heappush(heap,t)
    while heap:
        e=heapq.heappop(heap)
        for r in pending.pop(e,[]):
            o.arrive(r,ctx,r,e,rows[r]//64);journal.append(dict(kind='registered_return',row=r,time=str(e)))
        r=o.next_delivery
        if e in consumers and r in o.returned and o.arrival_edges[r]<e:
            o.consume(True,e);journal.append(dict(kind='consumer_accept',row=r,time=str(e)))
        for r,t in visible.items():
            if t==e:
                o.mark_visible(r,ctx,e);journal.append(dict(kind='home_visible',row=r,time=str(e)))
                t=e+delay;credits.setdefault(t,[]).append(r);schedule(t)
        # Credit captured post-edge cannot finance this edge's source acceptance.
        if e in issues and o.next_issue<576:
            r=o.next_issue
            if o.issue(r,ctx,e,rows[r]//64):
                t=e+Fraction(return_delays[rows[r]//64]);pending.setdefault(t,[]).append(r);schedule(t)
                journal.append(dict(kind='read_accept_reserved',row=r,time=str(e),shard=rows[r]//64))
        peak=max(peak,len(o.issued))
        for r in credits.pop(e,[]):
            o.captured_credit(r,ctx,e,delay);journal.append(dict(kind='credit_return_capture',row=r,time=str(e)))
        if e==ack:o.packet_ack(ctx,e,True,True)
    o.release(True,True,True)
    return dict(rows=576,capacity=capacity,peak_source_credit_debt=peak,journal=journal,
        separate_downstream_seat_assumed=False,actual_provider_qualified=False,actual_consumer_deadline=None)

WRITER_FAMILIES={'ww_h','rom','vw_me','vw_su','vw_rd','xs_vm','xs_res','vw_xe','ww_q','ww_x','xa','xb'}
def publication_contract(record,descriptor,vm_after_NBA,writers,observed_families):
    # All native writers must be observed; absence of an event is not coverage.
    if set(observed_families)!=WRITER_FAMILIES:raise ValueError('complete actual writer coverage')
    address,value=O.source_formatter(record,descriptor)
    own=[w for w in writers if w['family']=='rom' and w['slot']==0 and w['address']==address and w['data']==value]
    if len(own)!=1:raise ValueError('named scalar ROM ingress not accepted')
    for w in writers:
        if w['family'] not in WRITER_FAMILIES:raise ValueError('unknown writer owner')
        if not 0<=w['address']<1<<19:raise ValueError('writer VM alias')
        if w['address']==address and w is not own[0]:raise ValueError('competing writer publication ownership')
    if vm_after_NBA!=value:raise ValueError('writer acceptance is not VM visibility')
    return dict(address=address,data=value,port='dut.u_tile.rom_we[0]/rom_waddr[0+:AW]/rom_wdata[0+:32]',
                publication_witness_only=True,actual_runtime_enrolled=False)

def native_source_contract():
    s=(OUT/'inputs/native_tile.sv').read_text()
    needed=['parameter integer AW = FULL_SHAPE ? 30 : 24',
        'parameter integer VM_AW   = FULL_SHAPE ? 19 : 16',
        'if (rom_we[q]) vm[rom_waddr[q*AW +: VM_AW]] <= rom_wdata[32*q +: 32]',
        "2'd0: xs_rd_q[32*q +: 32] <= vm[xa[VM_AW-1:0]]",'if (xa_we) vm[{xa_waddr,', 'if (xb_we4[b])']
    if any(n not in s for n in needed):raise ValueError('native publication/read source changed')
    return dict(publication_candidate='scalar slot0 of existing ROM writer vector, source-identical formatter; DEFAULT-OFF ingress substitution/intercept must be implemented and priced',
        origin='actual tile posedge NBA ROM writes',AW=30,VM_AW=19,scalar_data_bits=32,scalar_intent_bits=63,
        named_write='dut.u_tile.rom_we[0], rom_waddr[0+:AW], rom_wdata[0+:32]',
        visibility='same identity/address/data postNBA plus complete competing-writer coverage; acceptance alone is insufficient',
        competing_writer_families=sorted(WRITER_FAMILIES),sameaddress_equaldata_is_not_ownership=True,
        named_consumer='dut.u_tile.xs_rd_re[q] && xs_rd_src[2*q+:2]==0; xs_rd_addr resolves VM19; read-aligned vx/cwx tag',
        writer_visible_strictly_before_consumer_read=True,existing_VM512_xa_xb_used=False,
        existing_ROM_port_not_assumed_free=True,ingress_substitution_mux_and_owner_tags_bits_area_pending=True,
        current_source_no_write_arbitration_guarantee=True,physical_VM_provider_ports_and_visiblelatency_bound=False)

def model():
    origins=json.loads((OUT/'inputs/origins.json').read_text())
    for n,p in origins.items():
        if hashlib.sha256((OUT/'inputs'/n).read_bytes()).hexdigest()!=p['sha256']:raise ValueError('source input changed')
    return dict(verdict='VISIBILITY_ANCHORED_SOURCE_DEBT_CONTRACT_PHYSICAL_CALENDAR_PENDING',one_candidate=True,
        widths=widths(),native_publication_path=native_source_contract(),source_row_retirement='actual sameidentity VM publication visible -> positive returnedcredit captured -> source seat reusable at subsequent qualified edge',
        release_on_consumer_acceptance=False,separate_downstream_lease_assumed=False,
        source_raw_record_retained_until_credit=True,packet_ACK_is_not_VM_visible=True,
        prior_unreserved_delivery_credit_rejected=True,prior_commit_preserved='7eed5623b684ec13592bccf8ed7416d348690032',
        common_owner=dict(proposed_shard=0,gather='HUB_GATHER',actual_ports_routes_and_exclusive_VM_publication=None),
        source_storage=dict(raw_bits=39744,controller_bits=1483,required_extra_key_PC_bits=46,remote_endpoint_lease_bits=None,
            gather_seats_C=None,CDC_token_bits=None,codec_and_clock_reset_PG_area=None),
        native_VM_path_not_free=True,VM512_lease_assumed=False,publication_candidate_selected='native ROM scalar slot0 substitution, defaultoff; not implemented',native_raw_roots_generation_bits=0,C=None,register_stations=None,
        accepted_consumer_first_edge=None,accepted_consumer_last_edge=None,source_period_and_CDC_phase_unbound=True,
        old_e899_FAIL_preserved=True,default1024_FAIL_preserved=True,model_complete=False,RTL_or_build_admitted=False,
        next='bind named publication writer/address/mask-arbitration/visibility callback, local+gather grants and positive CDC creditreturn, then derive ONE C/stations and accepted-consumer deadline')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True,type=Path);a.add_argument('--verify',action='store_true');args=a.parse_args()
    m=model();m['source_pins']={**O.pins(),str(Path(__file__).relative_to(O.ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        **{str(p.relative_to(O.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'inputs'/n for n in ['origins.json']+sorted(json.loads((OUT/'inputs/origins.json').read_text()))]}}
    raw=(json.dumps(m,indent=2,sort_keys=True)+'\n').encode()
    if args.verify:
        if args.out.read_bytes()!=raw:raise SystemExit('FAIL successor replay')
        print('PASS byteexact successor contract; physical/deadline admission false')
    else:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(raw)
