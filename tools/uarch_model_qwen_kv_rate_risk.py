#!/usr/bin/env python3
"""Current R0/Q2 feasibility extension: source capacity, traffic and rate risk.

No baseline edits, new design sweep, numerical run or hardware admission.
Bandwidths below are port/FSM ceilings at candidate clocks, NOT sustained HBM
bandwidth. Finite resource replay supplements, never substitutes for, actual
payload/causal and DRAM-command checks in qwen_rom_kv_causal_join.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
from qwen_rom_persistent_kv_g0 import ROOT, Owner
from qwen_rom_kv_production_join import contract, tail_sizing


def owner_interval():
    """Literal earliest r14 state/held transition witness, no stalls/allocations.

    Lookup accepted at0; delay==11 branch at12; held consumed at13; next
    lookup accepted at14. An allocation, backpressure or grant only delays it.
    """
    state, delay, held = 0, 0, False
    accepted, consumed = [], []
    for edge in range(100):
        if state == 0 and not held:
            accepted.append(edge); state, delay = 1, 0
        elif state == 1:
            if delay == 11:
                held, state = True, 2
            else:
                delay += 1
        elif held:
            consumed.append(edge); held, state = False, 0
    return dict(lookup_edges=12, min_accept_interval_edges=accepted[1]-accepted[0],
                accepted=accepted[:5], consumed=consumed[:5],
                assumptions='No allocation conflicts, grant blocking, stalls, refresh or missing PHY data.')


class FinitePrefetchReplay:
    """Actual-calendar resource checker; no implicit prefetch or overlap.

    Event tick is 1/3ps: service edge3000, stream edge2500. This matches
    candidate1GHz/stream1.2GHz and requires an explicitly pinned phase receipt.
    One return owner/stack,16 burst slots,4 writers,64request/32return perPC,
    16KiB held payload/stack,1024 assembly slots/stack,one64B fill/stream edge.
    Drain transfers ownership from provider response to a visible SRAM row;
    actual payload identity and command timing require their separate joins.
    """
    def __init__(self):
        self.tags, self.requests, self.returns, self.buffered = {}, {}, {}, {}
        self.owner_busy, self.owner_next = {}, {}
        self.command_at, self.ingress_until, self.fill_at = {}, {}, -2500
        self.assembly, self.windows = {}, {}
        self.tick = -1
        self.read_bytes = self.fill_bytes = self.max_outstanding = 0

    @staticmethod
    def pc(sector):
        return ((sector>>2)^(sector>>7)^(sector>>12))&31

    def apply(self, e):
        now = e['tick_1over3ps']
        if not isinstance(now,int) or now < self.tick:
            raise ValueError('calendar clock order')
        owner=Owner(**e['owner']); stack=(owner.rank,e['stack'])
        if not 0 <= e['stack'] < 4: raise ValueError('stack')
        event=e['event']; tag=(stack,e.get('tag'))
        if event=='allocate':
            n=e['sectors']; active=[x for k,x in self.tags.items() if k[0]==stack]
            if (tag in self.tags or not 0 <= e['tag'] < 4096 or not 1 <= n <= 32 or
                    len(active)>=16 or now<self.ingress_until.get(stack,0) or
                    stack in self.owner_busy or now<self.owner_next.get(stack,0)):
                raise ValueError('finite allocation/ingress capacity')
            if e['write'] and (n!=1 or sum(x['write'] for x in active)>=4):
                raise ValueError('current LEN1/four writer residence bound')
            counts={}
            for b in range(n):
                s=e['base_sector']+b
                if not 0<=s<703125000: raise ValueError('sector bounds')
                k=(stack,self.pc(s)); counts[k]=counts.get(k,0)+1
            if any(self.requests.get(k,0)+v>64 for k,v in counts.items()):
                raise ValueError('request SRAM/PC overflow')
            for k,v in counts.items(): self.requests[k]=self.requests.get(k,0)+v
            self.tags[tag]=dict(owner=owner,base=e['base_sector'],n=n,write=e['write'],
                command=set(),command_tick={},raw=set(),looked_up=set(),consumed=set(),filled={},visible=set(),credit=set(),grant=set())
            self.ingress_until[stack]=now+(n+1)*3000
            self.owner_next[stack]=now+3000 # av blocks ir on allocation edge
            self.max_outstanding=max(self.max_outstanding,len(active)+1)
        elif event=='window':
            slot=e['slot']
            if slot not in (0,1) or (owner.rank,slot) in self.windows:
                raise ValueError('54rows/window,128 current rows: two finite leases maximum')
            self.windows[owner.rank,slot]=owner
        elif event=='window_drain':
            if (self.windows.get((owner.rank,e['slot']))!=owner or
                    any(x['owner']==owner for x in self.tags.values())):
                raise ValueError('window lacks consumer drain identity')
            del self.windows[owner.rank,e['slot']]
        else:
            if tag not in self.tags or self.tags[tag]['owner']!=owner:
                raise ValueError('missing allocation/owner')
            x=self.tags[tag]; beat=e.get('beat')
            if event!='retire' and (not isinstance(beat,int) or not 0<=beat<x['n']):
                raise ValueError('beat')
            pc=(stack,self.pc(x['base']+(beat or 0)))
            if event=='command':
                if now<self.command_at.get(stack,-3000)+3000 or beat in x['command']:
                    raise ValueError('single stack command port/duplicate command')
                x['command'].add(beat);x['command_tick'][beat]=now
                self.command_at[stack]=now;self.requests[pc]-=1
            elif event=='write_backing':
                if (not x['write'] or beat not in x['command'] or beat in x['raw'] or
                        now<x['command_tick'][beat]+8*3000):
                    raise ValueError('write command/backing eight-cycle visibility')
                x['raw'].add(beat)
            elif event=='raw_return':
                if x['write'] or beat not in x['command'] or beat in x['raw'] or self.returns.get(pc,0)>=32:
                    raise ValueError('unissued/duplicate return or32 return SRAM slots exhausted')
                x['raw'].add(beat); self.returns[pc]=self.returns.get(pc,0)+1
            elif event=='lookup':
                if (beat not in x['raw'] or beat in x['looked_up'] or stack in self.owner_busy
                        or now<self.owner_next.get(stack,0)):
                    raise ValueError('serial owner lookup busy/not ready')
                x['looked_up'].add(beat)
                self.owner_busy[stack]=(tag,beat,now)
                if not x['write']:self.returns[pc]-=1
            elif event=='owned_consumed':
                busy=self.owner_busy.get(stack)
                if busy is None or busy[:2]!=(tag,beat) or now<busy[2]+13*3000:
                    raise ValueError('12 lookup edges plus held output acceptance required')
                if not x['write'] and self.buffered.get(stack,0)+32>16384:
                    raise ValueError('16KiB finite response payload exhausted')
                if not x['write']:self.buffered[stack]=self.buffered.get(stack,0)+32
                self.owner_next[stack]=now+3000;del self.owner_busy[stack]
                x['consumed'].add(beat)
                if x['write']:x['visible'].add(beat)
                else:self.read_bytes+=32
            elif event=='fill':
                valid=e['valid_bytes'];a=(stack,e['assembly_slot'])
                if (x['write'] or beat not in x['consumed'] or not 0<valid<=32 or
                        x['filled'].get(beat,0)+valid>32 or now<self.fill_at+2500 or
                        not 0<=e['assembly_slot']<1024 or a in self.assembly or
                        self.windows.get((owner.rank,e['window']))!=owner or
                        not 0<=e['tile']<1536 or
                        not e['window']*54<=e['row']<(e['window']+1)*54):
                    raise ValueError('fill port/assembly credit/owner/row capacity')
                self.assembly[a]=(tag,beat,valid,now)
                x['filled'][beat]=x['filled'].get(beat,0)+valid
                self.fill_at=now;self.fill_bytes+=valid
            elif event=='visible':
                a=(stack,e['assembly_slot']);pending=self.assembly.get(a)
                if pending is None or pending[:2]!=(tag,beat) or now<pending[3]+2*2500:
                    raise ValueError('registered fill to macro visibility requires two stream edges')
                del self.assembly[a]
                self.buffered[stack]-=pending[2]
                if x['filled'].get(beat,0)==32 and not any(v[:2]==(tag,beat) for v in self.assembly.values()):
                    x['visible'].add(beat)
            elif event=='credit':
                if beat not in x['visible'] or beat in x['credit']:
                    raise ValueError('reverse credit before visible/drained fill')
                x['credit'].add(beat)
            elif event=='grant_consumed':
                if beat not in x['credit'] or beat in x['grant']:
                    raise ValueError('unbacked/duplicate reverse grant')
                x['grant'].add(beat)
            elif event=='retire':
                if x['grant']!=set(range(x['n'])):
                    raise ValueError('tag retirement before all finite debts drain')
                del self.tags[tag]
            else: raise ValueError('unknown calendar event')
        self.tick=now

    def verdict(self):
        return dict(scope='Finite resource check only; payload/DRAM/CDC/source policy joins required',
          status='PASS_FINITE_RESOURCE_REPLAY' if not self.tags and not self.windows and not self.assembly else 'INCOMPLETE_DEBTS',
          read_bytes=self.read_bytes,fill_bytes=self.fill_bytes, max_outstanding=self.max_outstanding,
          live_tags=len(self.tags),live_windows=len(self.windows),physical_build_ready=False)


def build(parent_ref):
    import arch_budget_qwen3 as Q
    import uarch_model as U
    import hdc_timing as T
    parent=subprocess.check_output(['git','rev-parse',parent_ref],cwd=ROOT,text=True).strip()
    c=contract();pins={}
    for p,h in c['source_sha256'].items():
        actual=hashlib.sha256(subprocess.check_output(['git','show',parent+':'+p],cwd=ROOT)).hexdigest()
        if actual!=h: raise ValueError('Production source changed: '+p)
        pins[p]=h
    for p in ['tools/uarch_model.py','tools/arch_budget_qwen3.py','tools/hdc_timing.py',
              'rtl/hdc/ot_qwen_me_array_w12.sv','rtl/hdc/kv/ot_hdc_kv_stream.sv',
              'configs/models/qwen3-8b.json','configs/hardware/technology.json']:
        pins[p]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
        if hashlib.sha256(subprocess.check_output(['git','show',parent+':'+p],cwd=ROOT)).hexdigest()!=pins[p]:
            raise ValueError('Unified baseline changed: '+p)
    external={}
    for p in ['results/uarch/qwen_rom_physical_context_current_20261002/model-r1.json',
              'results/uarch/qwen_rom_physical_context_current_20261002/parent-IO-next-receipt-r1.json']:
        external[p]=hashlib.sha256(subprocess.check_output(['git','show',parent+':'+p],cwd=ROOT)).hexdigest()
    phy_path='physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json'
    phy=json.loads((ROOT/phy_path).read_text());pins[phy_path]=hashlib.sha256((ROOT/phy_path).read_bytes()).hexdigest()
    if hashlib.sha256(subprocess.check_output(['git','show',parent+':'+phy_path],cwd=ROOT)).hexdigest()!=pins[phy_path]:
        raise ValueError('PHY abstract changed')
    source=(ROOT/'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv').read_text()
    for anchor in ['delay==11','state<=2','held&&ore','state<=0','(state==0)&&!held&&!av']:
        if anchor not in source: raise ValueError('owner FSM changed')
    ctx=8192;wl=Q.workload(ctx);global_bytes=Q.kv_bytes(wl,'fp8')
    per_rank=int(global_bytes)//4;per_layer=per_rank//36;writes=36*2*2*128
    index=json.loads((ROOT/'physical/asap7_memory_macros/index.json').read_text())['macros']
    macro=index['ot_sram_1r1w_128x256_m1_r2c2'];tiles=1536
    capacity=tiles*2*macro['capacity_bits']//8
    rows=54;replicas=math.ceil(36*rows/128);extra=tiles*2*(replicas-1)
    capacity_min_macros=math.ceil(per_rank/(macro['capacity_bits']//8))
    capacity_extra=capacity_min_macros-tiles*2
    r8=json.loads((ROOT/'results/uarch/qwen_rom_persistent_kv_g0_20261002/contract_r8.json').read_text())
    r=r8['candidate_resources'];tail=tail_sizing()
    owner_edges=owner_interval()['min_accept_interval_edges'];service_hz=10**9;stream_hz=1200000000
    owner_bps=Fraction(32*service_hz,owner_edges);fill_bps=64*stream_hz
    # Existing generic source keeps the last two K tiles, and the current V row
    # may be forwarded only after actual visibility. This optimistic subtraction
    # is conditional; it is not evidence that all36 source tails are connected.
    k_tail_bytes=36*2*128*32;v_new_bytes=36*2*128
    offchip_best=per_rank-k_tail_bytes-v_new_bytes
    per_stack=[36*(16320+16384)*32]*3+[36*(16320+16376)*32]
    assert sum(per_stack)==offchip_best
    # Selected8K decode position8191 closes a16-row K tile. Current source-tail
    # successor writes128 full K sectors plus8 V sectors/layer at that phase;
    # averaged across16 rows the write charge is512B/layer. Distinguish both.
    closing_writes=36*(4096+256)
    closing_stack_writes=[36*32*32]*3+[36*(32+8)*32]
    assert sum(closing_stack_writes)==closing_writes
    ideal_offchip_s=max(per_stack)/owner_bps
    owned_read_write_s=max(a+b for a,b in zip(per_stack,closing_stack_writes))/owner_bps
    fill_beats=36*(510*128*2//4+8192//4*8*2)
    fill_s=Fraction(fill_beats,stream_hz)
    point=U.qwen_tp_point(4,6144,'ucie_measured',clock_hz=stream_hz,me_lat_extra=55,ctx=ctx,su_width=64)
    k0=T.K['me_lat'];T.K['me_lat']=k0+55
    try:
        stages=Q.as_built(ctx,groups=6144,su_width=64,ucie=False,
                         shape=dict(Q.Q,NH=Q.Q['NH']//4,KV=Q.Q['KV']//4,
                                    FF=math.ceil(Q.Q['FF']/4),V=math.ceil(Q.Q['V']/4)))['layer_chain']
    finally: T.K['me_lat']=k0
    compute_s=Fraction(point['cycles'],stream_hz)
    service_tail_area=r['actual_service_macro_area_mm2_per_rank']+tail['macro_area_mm2_per_rank']
    room=67.35-service_tail_area-r['assembly_area_lower_bound_mm2']
    return dict(schema='opentallas.qwen-rom-current-R0-Q2-kv-rate-risk.v1',
      status='FAIL_3K_RATE_CURRENT_OFFCHIP_TRANSPORT_G0_BLOCKED',parent=parent,
      source_sha256=pins,parent_physical_context_sha256=external,
      extension_source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ['tools/uarch_model_qwen_kv_rate_risk.py','tests/test_qwen_rom_kv_rate_risk.py',
         'tools/qwen_rom_kv_causal_join.py','tools/qwen_rom_kv_production_join.py']},
      unified_model_extension='tools/uarch_model_qwen_kv_rate_risk.py (opt-in)',
      selected_context=ctx,tp=4,logical_bytes=dict(read_rank_token=per_rank,read_all4_ranks_token=int(global_bytes),
        read_rank_layer=per_layer,write_rank_token=writes,write_all4_ranks_token=4*writes,
        existing_read_charge_replaced_once=True,incremental_full_reload_bytes=0,
        conditional_source_K_tail_bypass=k_tail_bytes,conditional_current_V_forward=v_new_bytes,
        conditional_offchip_read_rank=offchip_best,conditional_offchip_read_stacks=per_stack,
        selected_position=8191,conditional_selected_closing_K_V_write_rank=closing_writes,
        conditional_selected_closing_K_V_write_stacks=closing_stack_writes,
        write_scope='18KiB/rank logical/average update; atposition8191 closed K tile+V requires156672B/rank.128 K sectors are128 LEN1 writes, not a128-sector hardware burst. Actual write policy/visibility requires producer receipts.'),
      actual_storage=dict(tile_count_per_rank=tiles,KV_macros_per_tile=2,KV_macros_per_rank=2*tiles,
        raw_capacity_bytes_per_rank=capacity,full36_useful_KV_bytes_per_rank=per_rank,
        current_one_window_max_rows=rows,current_row_depth=128,all36_literal_rows=36*rows,
        fully_resident_current_macro_replica_banks_per_tile=replicas,
        fully_resident_current_macro_count_per_rank=2*replicas*tiles,
        extra_current_macros_required=extra,extra_macro_area_mm2=extra*macro['area_um2']/1e6,
        useful_capacity_only_min_current_macros=capacity_min_macros,
        useful_capacity_only_additional_current_macro_area_mm2=capacity_extra*macro['area_um2']/1e6,
        conclusion='Current12MiB tile KV cannot retain144MiB/rank. Literal current-map replication fails current area envelope. No alternative macro/design study adopted.'),
      actual_ports=dict(tile_read_bytes_per_stream_edge=64,tile_read_ports=tiles,
        aggregate_tile_read_bytes_per_edge=64*tiles,
        conditional_enabled_tile_KV_read_payload_rank_token=(point['unit_busy']['attn_scores']+point['unit_busy']['attn_pv'])*tiles*64,
        enabled_read_scope='Analytical ME KV busy edges times all1536 unconditional tile read CEs. Includes repeated/padded lane reads; this is raw macro activity, not distinct offchip bytes or transport bandwidth.',
        tile_write_bytes_per_stream_edge=64, shared_fill_lanes=1,shared_fill_payload_bytes_per_edge=64,
        physical_tile_write_ports=tiles,
        shared_fill_scope='One addressed fill lane in committedr8 delivery candidate.1536 local tile write ports exist independently; no actual selected provider-to-tile parallel fill topology has been bound.',
        current_connected_production_fill_lanes=None,
        source_inventory_scope='r14 module with ENABLE1; four enabled stack copies/rank are priced candidate replication, not a connected ROM runtime receipt.',
        actual_enabled_ROM_service_replicas_verified=False,
        shared_fill_wire_bits=1048,stacks_per_rank=4,PCs_per_stack=32,owner_instances_per_stack=1,
        shared_command_buses_per_stack=1,command_bits_per_stack=339,
        column_payload_bytes_per_command=32,
        column_payload_ceiling_Bps_per_stack=32*service_hz,
        column_payload_ceiling_Bps_per_rank=4*32*service_hz,
        owner_payload_bytes_per_completed_return=32,owner_FSM=owner_interval(),
        owner_payload_ceiling_Bps_per_stack=float(owner_bps),owner_payload_ceiling_Bps_per_rank=float(4*owner_bps),
        shared_fill_ceiling_Bps=fill_bps,service_candidate_Hz=service_hz,stream_target_Hz=stream_hz,
        serial_target_Hz=900000000,
        actual_sustained_HBM_bandwidth=None,source_closed_bandwidth=None,
        historical_model_aggregate_HBM_Bps=4*U.HBM_STACK_BPS,
        old_aggregate_bound_is_selected_bandwidth=False,
        current_serial_bridge_outstanding=1,candidate_burst_sectors=32,candidate_outstanding_per_stack=16,
        candidate_response_bytes_per_stack=16384,candidate_assembly_slots_per_stack=1024,
        warning='32PCs are not32 output owners. Macro1R1W read/write ports are not independent global fill lanes. Ceilings are not sustained HBM bandwidth.'),
      token_lower_bounds=dict(full_read_owner_ceiling_s=float(Fraction(per_rank,4)/owner_bps),
        full_read_column_command_ceiling_s=float(Fraction(per_rank,4*32*service_hz)),
        optimistic_tail_bypass_owner_ceiling_s=float(ideal_offchip_s),
        selected_closing_read_plus_write_owner_slot_ceiling_s=float(owned_read_write_s),
        selected_layer_owner_slot_lower_s=float(owned_read_write_s/36),
        full_read_single_fill_s=float(Fraction(per_rank,fill_bps)),
        tail_bypass_masked_fill_beats=fill_beats,tail_bypass_masked_fill_s=float(fill_s),
        conditional_compute_s=float(compute_s),
        compute_scope='Existing uniform1.2GHz qwen_tp_point reference with explicit+55; serial0.9GHz, actual current program/arithmetic and physical paths still require joined pricing. Extra compute cannot remove the transport lower bound.',
        perfect_all_compute_overlap_s=float(max(owned_read_write_s,fill_s,compute_s)),
        conditional_max_token_rate=float(1/max(owned_read_write_s,fill_s,compute_s)),
        overlap_credited_to_admitted_rate=0,
        applies_to='Existing die-local HBM/next-layer prefetch policy with source-sized two K-tail tiles and new V-row forwarding. Actual binding and sustainable policy remain missing.'),
      three_k_requirement=dict(target_token_s=1/3000,read_Bps_per_rank=per_rank*3000,
        shared_64B_fill_lanes_min=math.ceil(per_rank*3000/fill_bps),
        owned_32B_output_lanes_per_stack_min=math.ceil(per_rank*3000/(4*32*service_hz)),
        shared_column_command_ports_per_stack_min=math.ceil(per_rank*3000/(4*32*service_hz)),
        equivalent_source_owner_instances_per_stack_min=math.ceil(Fraction(per_rank*3000,4)/owner_bps),
        maximum_offchip_bytes_per_rank_at_current_owner_ceiling=float(4*owner_bps/3000),
        conclusion='No3k+ claim with current fill/owner transport. Counts are infeasibility witnesses, not proposed optional replicas.'),
      overlap=dict(analytical_current_layer_stages=stages,
        conditional_layer_compute_s=stages['cycles']/stream_hz,
        candidate_next_layer='May overlap current matrix/attention only with a separately owned spare window, safe port arbitration, actual accepted descriptor release and reader drain. Source-selected window selector/lease trace absent.',
        current_attention='Current K must be visible for scores; V must be visible for PV. Streaming overlap needs exact supplied-prefix/consumer cadence, not whole-layer bandwidth.',
        writes='Open-tail and V writes may run behind compute only with accepted backing/credit/retirement and bounded write-port ownership.',
        initial_prefetch='No prior layer exists to hide first-layer prefetch; cross-token retention/early release require actual state.',
        conditional_compute_overlap_reference_s=float(compute_s),proved_overlap_s=0),
      area=dict(authority='Owner supplied Maxwell747.65mm2 baseline/815mm2 envelope; exact Maxwell component receipt pending.',
        baseline_mm2=747.65,envelope_mm2=815.0,other_services_budget_mm2=67.35,
        service_plus_tail_macro_mm2=service_tail_area,assembly_logic_lower_bound_mm2=r['assembly_area_lower_bound_mm2'],
        remaining_after_these_known_debits_mm2=room,
        four_PHY_abstract_footprint_mm2=4*phy['footprint']['area_mm2'],
        conditional_remaining_if_PHY_not_already_in_baseline_mm2=room-4*phy['footprint']['area_mm2'],
        inherited_unqualified_service_reservation_mm2=4*r['inherited_service_slot_mm2_per_stack'],
        inherited_reservation_is_fit_or_replacement_credit=False,
        resident_literal_macro_increment_mm2=extra*macro['area_um2']/1e6,
        useful_capacity_only_macro_increment_mm2=capacity_extra*macro['area_um2']/1e6,
        literal_resident_overflow_before_other_services_mm2=747.65+extra*macro['area_um2']/1e6-815,
        debits_already_in_Maxwell_baseline=None,complete_slot_fit=None,
        exclusions='Controller/CAM/quarantine, mask/mux/demux, PHY, CTS/hold/PGOBS, routing, SRAM/control protection. Named baseline component join prevents duplicate charges.'),
      physical_PHY=dict(scope=phy['claim_boundary'], footprint=phy['footprint'],
        source_interface=phy['interface']['controller_side'], native_r14=dict(address_bits=34,len_bits=6,beat_bits=5),
        protocol_shim_source_join=False,SS_min_period_ps=phy['timing']['ss']['min_period_ps'],
        adopted_streaming_1p2GHz=False,
        bandwidth_scope='Published DQ/nominal stack bandwidth does not qualify the abstract protocol, clock, provider-owner bottleneck or filled tile ports.'),
      corridor=dict(owner_supplied_width_um=96.768,fill_tracks_one_lane=1048,
        six_fill_lanes_tracks_before_control_clock_reset=6*1048,
        capacity_36layer_proof=False,delivery_rate_proof=False,
        route_pitch_layers_reserve_and_parent_receipt=None),
      production_calendar=dict(selected=False,fully_finite_actual_trace_present=False,
        checker='FinitePrefetchReplay',
        source_two_window_row_capacity_screen=2*54<=128,
        source_selected_second_window_read_selector=False,
        required=['Actual phase/source policy receipt and stage program pins',
          'Actual per-stack allocate/command/raw_return/lookup/owned_consumed ticks',
          'Fill data/mask and macro visibility, copy-reader credit/grant/tag retirement',
          'Window owner acquisition and actual attention drain; no overlap without timeline',
          'CausalJoin actual payload/state equality and bank/refresh/turnaround command audit',
          'Complete slot/port/CDC latency and source-selected clock admission'],
        gate='No resource replay or ceiling result qualifies missing producer/provider/policy inputs.'),
      physical_build_ready=False,production_policy_selected=False,adopted_rate=None,
      preserved_full_numerical_run=True,new_numerical_positions=0,new_RTL_PnR=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent-ref',required=True);p.add_argument('--result',required=True)
    p.add_argument('--resource-trace');args=p.parse_args();r=build(args.parent_ref)
    if args.resource_trace:
        path=Path(args.resource_trace);replay=FinitePrefetchReplay()
        r['resource_trace_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            for line in path.read_text().splitlines():
                if line.strip():replay.apply(json.loads(line))
            r['resource_replay']=replay.verdict()
        except (ValueError,KeyError,TypeError) as error:
            r['resource_replay']=dict(status='FAIL_FINITE_RESOURCE_REPLAY',failure=str(error))
    with Path(args.result).open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    if r.get('resource_replay',{}).get('status')=='FAIL_FINITE_RESOURCE_REPLAY':raise SystemExit(1)


if __name__=='__main__':main()
