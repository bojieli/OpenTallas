#!/usr/bin/env python3
"""OFF analytical GPU landing-bank candidate; cycle oracle, no RTL or timing signoff."""
import argparse
from collections import deque, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TRANSPORT='results/uarch/w19_transport_contract_20261001/contract_r1.json'
COMPOSED='results/quality/w16_w19_composed_schedule_20261001/graph_summary.json'
KERNEL='results/quality/w16_w19_composed_schedule_20261001/kernel_binding.json'
MACRO='physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef'
HC_COMMIT='d801a2419'
HC_CONTRACT='results/uarch/w16_gpu_hc_simt_contract_20261001/contract_r1.json'
COMPOSED_COMMIT='6f286b368f121fc78966e6624c429fb423d7972a'


def digest(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def layout():
    old=json.loads((ROOT/TRANSPORT).read_text())
    if old['geometry']['read_line_slots']!=4096 or old['geometry']['read_context_bits']!=168:
        raise ValueError('transport geometry changed')
    # All sector banks use whole existing 1024x256 shapes. Half the depth is
    # deliberately unused, never credited as half a macro. Context is 164bits
    # (160 descriptor + generation3 + live1); mask4 moves to the scoreboard.
    sram=dict(landing_macros=8*4,context_macros=8,macro_depth=1024,
        macro_width=256,used_rows_per_macro=512,context_used_bits_per_row=164,
        landing_physical_bits=32*1024*256,context_physical_bits=8*1024*256)
    control=dict(PC_FIFO_payload_bits=32*8*(256+16+4),
        PC_FIFO_pointer_bits=32*(3+3+4),
        scoreboard_bits=4096*(3+1+4+1),
        completion_FIFO_bits=8*512*(9+3),
        completion_FIFO_pointer_bits=8*(9+9+10),
        output_skid_bits=8*2*(1024+164+12),
        output_skid_pointer_bits=8*4,
        SRAM_read_pipeline_bits=8*(1024+164+12+1),
        sector_arbiter_RR_bits=32*5)
    replaced=old['geometry']['storage_bits_per_controller']
    retained=sum(replaced.values())-replaced['read_landing_bits']-replaced['read_context_bits']
    total=sram['landing_physical_bits']+sram['context_physical_bits']+sum(control.values())+retained
    return dict(bank_count=8,sector_banks_per_line_bank=4,slots_per_bank=512,
        context_allocations_per_controller_cycle=1,context_allocation_cycles_per_line=1,
        bank='slot & 7',row='slot >> 3',sector_bank='beat & 3',
        PC_ingress_FIFO_depth=8,PC_count=32,SRAM=sram,control_storage_bits=control,
        retained_transport_storage_bits=retained,total_storage_bits_per_controller=total,
        bytes_per_controller=(total+7)//8,bytes_per_rank=4*((total+7)//8),
        bytes_all96=96*4*((total+7)//8),
        incremental_bytes_per_rank_vs_logical_contract=4*((total+7)//8)-old['geometry']['total_storage_bytes_per_rank'],
        SRAM_ports=dict(landing='32 separate 1R1W arrays; each writes <=1 sector and reads <=1 completed line sector/cycle',
            context='8 separate 1R1W arrays; <=1 allocation write and <=1 delivery read per bank/cycle; allocation supplies generation/live to register scoreboard on the same edge',
            scoreboard='8 register banks, each 512x9; up to4 response validations/merged updates plus1 allocation and1 retirement; these are explicit multiport register costs, not SRAM ports'),
        scoreboard_bits=dict(generation=3,live=1,received_sector_mask=4,completion_enqueued=1),
        replicas=dict(controllers_per_rank=4,ranks=96,whole_SRAM_macros_per_rank=160,whole_SRAM_macros_all96=15360),
        mux_and_merge=dict(sector_crossbar_32_to_32_mux_bit_equivalents=32*31*(256+16+4),
            rank_delivery_32_to_32_mux_bit_equivalents=32*31*(1024+164+12),
            same_line_pairwise_compares_per_bank=6,same_line_compare_bits=9+3,
            same_line_pairwise_compare_bit_equivalents_per_controller=8*6*12,
            scoreboard_4read_mux_bit_equivalents_per_controller=8*4*511*9,
            sector_RR_arbiters_per_controller=32,inputs_per_sector_arbiter=32,
            rank_delivery_candidates=32,SM_destinations=32,
            rank_candidate_SM_equal_compare_bit_equivalents=496*5,
            rank_candidate_priority_pairwise_comparisons=496,
            rank_age_counter_width=None,rank_age_storage_bits=None,
            rank_delivery_policy='Oldest eligible candidate; at most one grant per source bank and SM per cycle. Physical age implementation/width pending; oracle uses first-completion cycle.'),
        note='Storage excludes unbound physical rank-arbiter age logic and wires. No L2/RF/shared credit; SRAM read latency1 and update register logic at1.2GHz remain physical assumptions.')


def delivery_grants(candidates, ready):
    """Rank-wide matching: (age, controller, bank, SM). One source, one SM."""
    selected=[]; used_sources=set(); used_sm=set()
    for age,controller,bank,sm in sorted(candidates):
        if sm not in range(32) or controller not in range(4) or bank not in range(8):
            raise ValueError('rank endpoint outside GPU organization')
        source=(controller,bank)
        if sm in ready and source not in used_sources and sm not in used_sm:
            selected.append(source);used_sources.add(source);used_sm.add(sm)
    return selected


class Landing:
    """One controller, finite cycle oracle; bytes are copied unchanged."""
    def __init__(self,depth=8):
        if depth<=0: raise ValueError('finite queue required')
        self.depth=depth;self.cycle=0;self.pc=[deque() for _ in range(32)]
        self.rr=[0]*32;self.lines={};self.cq=[deque() for _ in range(8)]
        self.skid=[deque() for _ in range(8)];self.pipe=[None]*8
        self.writes=0;self.accepted=0;self.delivered=[];self.retired_generation={}
        self.same_line_merges=0;self.arb_collision_cycles=0;self.allocations=0

    def allocate(self,tag,owner):
        if not 0<=tag<32768 or owner not in range(32):
            raise ValueError('read tag/SM outside contract')
        slot=tag&4095
        if slot in self.lines: raise ValueError('live slot reuse')
        if (tag>>12)<=self.retired_generation.get(slot,-1):
            raise ValueError('retired tag generation reuse before drain/reset')
        self.lines[slot]=dict(tag=tag,owner=owner,mask=0,data={},enqueued=False)
        self.allocations+=1

    def candidates(self,controller=0):
        return [(q[0][0],controller,b,q[0][2]) for b,q in enumerate(self.skid) if q]

    def step(self, responses=None, ready=None, grants=None):
        responses={} if responses is None else responses
        if any(pc not in range(32) for pc in responses): raise ValueError('bad PC')
        # Ready is based on registered occupancy, not a long grant-to-ready path.
        accepted={pc for pc in responses if len(self.pc[pc])<self.depth}
        if grants is None:
            ready=set(range(32)) if ready is None else ready
            grants={b for c,b in delivery_grants(self.candidates(),ready)}
        delivered=[]
        for b in grants:
            if not self.skid[b]: raise ValueError('grant without assembled line')
            age,tag,owner,data=self.skid[b].popleft()
            del self.lines[tag&4095]
            self.retired_generation[tag&4095]=tag>>12
            event=dict(cycle=self.cycle,tag=tag,owner=owner,data=data)
            self.delivered.append(event);delivered.append(event)
        for b in range(8):
            if self.pipe[b] is not None:
                if len(self.skid[b])>=2: raise AssertionError('skid reservation lost')
                self.skid[b].append(self.pipe[b]);self.pipe[b]=None
            if self.cq[b] and len(self.skid[b])<2:
                age,tag=self.cq[b].popleft();line=self.lines[tag&4095]
                self.pipe[b]=(age,tag,line['owner'],b''.join(line['data'][i] for i in range(4)))
        heads=defaultdict(list)
        for pc,q in enumerate(self.pc):
            if q:
                tag,beat,data=q[0];slot=tag&4095
                line=self.lines.get(slot)
                if line is None or line['tag']!=tag or beat not in range(4) or line['mask']>>beat&1:
                    raise ValueError('unissued/stale/duplicate sector')
                heads[(slot&7)*4+beat].append(pc)
        updates=defaultdict(list)
        if any(len(pcs)>1 for pcs in heads.values()): self.arb_collision_cycles+=1
        for sb,pcs in heads.items():
            pc=min(pcs,key=lambda p:(p-self.rr[sb])%32)
            tag,beat,data=self.pc[pc].popleft();self.rr[sb]=(pc+1)%32
            updates[tag&4095].append((beat,data));self.writes+=1
        for slot,beats in updates.items():
            line=self.lines[slot];new_mask=line['mask']
            if len(beats)>1: self.same_line_merges+=1
            for beat,data in beats:
                new_mask|=1<<beat;line['data'][beat]=data
            line['mask']=new_mask
            if new_mask==15 and not line['enqueued']:
                if len(self.cq[slot&7])==512: raise AssertionError('completion reservation lost')
                self.cq[slot&7].append((self.cycle,line['tag']));line['enqueued']=True
        for pc in accepted:
            tag,beat,data=responses[pc]
            if not 0<=tag<32768 or beat not in range(4) or len(data)!=32:
                raise ValueError('sector payload/tag malformed')
            self.pc[pc].append((tag,beat,bytes(data)));self.accepted+=1
        self.cycle+=1
        return accepted,delivered

    def reset_drained(self):
        if self.lines or any(self.pc) or any(self.cq) or any(self.skid) or any(self.pipe):
            raise ValueError('cannot reset bank queues/scoreboard before complete drain')
        self.retired_generation.clear()


    def drain(self,limit=10000):
        for _ in range(limit):
            if not self.lines and not any(self.pc): return
            self.step()
        raise ValueError('finite schedule did not drain (missing sectors or destination progress)')


def campaigns():
    balanced=Landing()
    for slot in range(8): balanced.allocate(slot,slot)
    balanced.step({4*b+s:(b,s,bytes([4*b+s])*32) for b in range(8) for s in range(4)})
    balanced.drain()
    collide=Landing()
    for n in range(32): collide.allocate(8*n,n)
    for beat in range(4):
        collide.step({pc:(8*pc,beat,bytes([beat])*32) for pc in range(32)})
    collide.drain()
    sameSM=Landing()
    for slot in range(8): sameSM.allocate(slot,0)
    sameSM.step({4*b+s:(b,s,bytes([s])*32) for b in range(8) for s in range(4)})
    sameSM.drain()
    return {name:dict(preallocated_line_contexts=m.allocations,
        serial_context_allocation_cycles_before_return_trace=m.allocations,
        trace_scope='Response arrival through delivery only. Preallocation charged separately at1 line/controller/cycle; excludes HBM source wait and actual destination/CDC service.',
        accepted_sectors=m.accepted,written_sectors=m.writes,
        delivered_lines=len(m.delivered),last_delivery_cycle=max(e['cycle'] for e in m.delivered),
        first_delivery_cycle=min(e['cycle'] for e in m.delivered),
        same_line_merge_events=m.same_line_merges,sector_collision_cycles=m.arb_collision_cycles,
        exact_output_sha256=hashlib.sha256(b''.join(e['data'] for e in sorted(m.delivered,key=lambda e:e['tag']))).hexdigest())
        for name,m in [('balanced32PC',balanced),('same_sector_bank32PC',collide),('same_SM8banks',sameSM)]}


def hc_reconciliation():
    blob=subprocess.check_output(['git','show',HC_COMMIT+':'+HC_CONTRACT],cwd=ROOT)
    hc=json.loads(blob)
    if (hc['composition']['additional_transpose_cycles']!=35248 or
        hc['shared']['external_coefficient_transpose_bytes']!=2048 or
        hc['shared']['external_activation_transpose_bytes']!=1024 or
        hc['SM_count']!=32 or hc['RF']['live_projection_registers']!=32):
        raise ValueError('Turing HC resource shape changed')
    coeff=sum(w['coefficient']['raw_read_bytes'] for w in hc['transpose_waves'])*24
    activation=sum(w['activation']['raw_read_bytes'] for w in hc['transpose_waves'])*25
    if (coeff,activation)!=(1966080,1024000):
        raise ValueError('HC source raw/final byte accounting changed')
    return dict(input_acknowledged=True,commit=HC_COMMIT,path=HC_CONTRACT,
        sha256=hashlib.sha256(blob).hexdigest(),HC_clock_hz=hc['clock_hz'],
        transport_clock_hz=1200000000,CDC_completed_cycles=None,
        raw_destination_port_bytes_per_HC_cycle=128,
        raw_destination_port_ceiling_bytes_per_SM_second=128*hc['clock_hz'],
        CDC_capacity_bits=None,CDC_storage_bytes=None,
        source_transport_bytes_rank_before_bank_rounding=hc['communication']['transport_queue_storage_bytes_rank'],
        new_banked_transport_bytes_rank=layout()['bytes_per_rank'],
        conditional_transpose_increment_HC_cycles=35248,
        conditional_compute_staging_HC_cycles=hc['composition']['conditional_compute_staging_cycles_operator'],
        source_conflicts=dict(naive_coefficient=8,packed_activation=4,term_major=1),
        external_raw_buffers_bytes_per_SM=3072,external_raw_buffers_bytes_per_rank=3072*32,
        external_buffers_included_in_landing_storage=False,
        raw_write_endpoint_bytes_operator=dict(coefficient=coeff,activation=activation),
        scatter_write_bytes_operator=dict(coefficient=coeff,activation=activation),
        retained_r3_final_refill_write_bytes_operator=dict(coefficient=coeff,activation=activation),
        byte_accounting='Raw buffer writes, local INT/shared scatter and retained r3 final-refill writes are distinct serial services. Source transpose increment already includes raw bytes/128 and scatter; do not add these again as new kernel work. HBM/NoC landing, raw-buffer acceptance, CDC and endpoint finite waits must be bound separately before charging composed phases.',
        coefficient_HBM_source_bytes_operator=hc['communication']['coefficient_HBM_bytes_operator'],
        activation_source_reference_bytes=40960,activation_endpoint_copies=25,
        activation_ownership='Reference activation40960B delivered to24 projection SMs and norm SM24. Endpoint1,024,000B does not establish25 HBM reads or physical NoC wire bytes.',
        buffers='NonSM raw buffer is proposed valid/ready destination. Only consume skid on raw-buffer credit; keep queued/read/assembled landing live under stall. Existing bulk-copy response has no ready and still requires destination-ring reservation before request grant. No implicit reuse of external3072B, scratch12288B slack, RF32-register reserve or landing memory.',
        sequence=['prior phase controller/destination drain and all32SM global barrier',
            'tagged coefficient HBM arrivals and activation distribution; finite landing queues/assembly',
            'raw external-buffer writes accepted; 1.2-to0.9GHz CDC visibility fence',
            'ordinary serialized raw-read/address/scatter instructions; raw buffers recycled only after read retirement',
            'retained final shared refill writes complete; local wave barrier; operand visibility',
            'projection/norm ordered chunk and warp reductions; partials retained through final tree',
            'all25 producer results visible; all32SM global barrier before SM0 scalar phase',
            'scalar result staging/delivery visibility fence and all32SM drain before next operator'],
        global_barrier_cycles=None,controller_write_commit_cycles=None,
        raw_and_final_write_fence_cycles=None,no_overlap_credit=True,
        storage_bytes_rank_landing_and_external_buffers=layout()['bytes_per_rank']+3072*32,
        total_storage_scope='Known banked transport plus separately reserved raw buffers only; excludes unknown CDC, physical age arbitration and HC RF/shared budget. Not a complete fit.',
        unpriced_graph_nodes=[dict(compute_node=b['compute_node'],service_nodes_unpriced=b['service_nodes_unpriced']) for b in hc['composition']['bindings']],
        RF32_register_reserve_qualified=False,
        numerical_proof_scope=dict(boundaries=91,target_global_scratch_kernel_different=True,
            target_connected_GPU_hardware_proved=False),
        full_HC_service_cycles=None,complete_schedule_admitted=False)


def build():
    for path in ('tools/w19_composed_schedule.py',COMPOSED,KERNEL):
        historical=subprocess.check_output(['git','show',COMPOSED_COMMIT+':'+path],cwd=ROOT)
        if hashlib.sha256(historical).hexdigest()!=digest(path):
            raise ValueError('Turing composed source input drift: '+path)
    graph=json.loads((ROOT/COMPOSED).read_text())
    return dict(schema='opentallas.w19.banked_landing_model.v1',
        Turing_input_ack=dict(acknowledged=True,commit=COMPOSED_COMMIT,
            graph_sha256=graph['graph_sha256'],graph_source=COMPOSED,
            graph_service_provider_complete=False,HC_RF_shared_owner='Turing',transport_owner='W19'),
        pins={p:digest(p) for p in (TRANSPORT,COMPOSED,KERNEL,'tools/w19_composed_schedule.py',
            'tools/w19_transport_contract.py','tools/w19_landing_banks.py',MACRO)},
        layout=layout(),HC_reconciliation=hc_reconciliation(),clock_hz=1200000000,period_ps_exact=str(Fraction(10**12,1200000000)),
        pipeline=dict(ingress_accept_edge=0,sector_arbitrate_write_merge_edge=1,
            completed_line_read_request_edge=2,SRAM_read_skid_edge=3,destination_delivery_edge=4,
            no_stall_ingress_to_delivery_cycles=4,
            no_stall_ingress_to_delivery_ps_exact=str(Fraction(4*10**12,1200000000)),
            cycle_assumption='One-cycle registered arbitration/write/merge and one-cycle SRAM read are analytical assumptions, not 1.2GHz closure evidence.',
            after_final_sector_write_to_delivery_cycles=3,
            collision='At most1 sector/bank/cycle. RR32 PC heads, perPC in-order; head-of-line blocking retained. Full FIFO deasserts ready; source must hold unaccepted response.',
            bitmap_merge='Per bank group four granted sector writes compare row9+generation3; matching rows OR four beat bits once against prior mask. Enqueue completion exactly once, only at1111.',
            read_pipeline='1R1W landing/context read assumed1 cycle. Two skid entries/bank reserved before read. Same-slot read/write forbidden by completed bitmap and live-tag checks.',
            assembly_lanes_per_controller=8,delivery_bytes_per_controller_cycle_peak=1024,
            peak_delivery_bytes_per_controller_second=1024*1200000000,
            old_one_lane_ceiling_bytes_per_controller_second=128*1200000000,
            upstream_one_4sector_request_per_cycle_ceiling_bytes_second=128*1200000000,
            upstream_bound='Source read length supports16 sectors, but prior line-slot/tag contract grants4. Burst4-line tag/beat allocation is NOT supplied here; no full-stack sustainable bandwidth credit.',
            destination_wait_cycles=None,HBM_loaded_wait_cycles=None,controller_commit_fence_cycles=None,
            full_token_cycles=None),
        cycle_oracle_traces=campaigns(),
        boundary_bits_per_cycle=dict(controller_response_existing=32*(256+16+4+2),
            ingress_to_sector_crossbar=32*(256+16+4),
            bank_to_rank_delivery=8*(1024+164+12+1+1),
            rank_delivery_candidate_count=32,rank_SM_delivery_output_count=32),
        physical=dict(clock_closure=False,SS_setup=False,FF_hold=False,uncertainty_setup_ps=60,
            uncertainty_hold_ps=25,area_mm2=None,route_tracks=None,channel_capacity_tracks=None,slot_fit=None,
            footprint_note='Macro shape only; 1R1W1024x256 replicated40/controller. Logical unused rows/bits count physically. Arbitration, scoreboard multiport logic and rank network have no qualified area/route yet.'),
        composed_service_provider=False,unified_model_changed=False,new_RTL=False,new_PnR=False,
        enabled_default=False,ready_to_build=False,full_resident_admitted=False,hardware_adopted=False,
        arithmetic='Byte identity only; no FP conversion/Engram scale collapse; accepted256 baseline unmodified',
        prerequisite='Turing must compose this bank service with qualified GPU RF/shared schedule, real burst tagging, source waits/destination ownership, commit/fence and physical area/routes before RTL.')


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--out',type=Path);g.add_argument('--check',type=Path);a=p.parse_args();r=build()
    if a.check:
        if json.loads(a.check.read_text())!=r: raise ValueError('bank model/source drift')
    else:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x') as f: json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print('PASS banked cycle model; RTL/PnR/composed service/adoption remain OFF')

if __name__=='__main__': main()
