#!/usr/bin/env python3
"""Size ONE d187/2b897 adjacent-hub native indexed-stream implementation.

No mapping search/metadata replay, DUT measurement, scalar-copy modification,
or clock-signoff prerequisite. Conservative explicit staged calendar only.
"""
import argparse
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from dsrom_s81_unified_components import solve_events

A='results/uarch/dsrom_s81_level2_service_stream_20261004/model.json'
B='results/uarch/dsrom_s81_service_capacity_split_20261004/r1/transport_movements.jsonl.gz'
G='results/uarch/dsrom_s81_minimum_protected_group_20261004/'
U='results/uarch/dsrom_s81_unified_components_20261004/inputs/vm_r4.json'
L='results/rtl/dsrom_1m_allmeasured_20261004/links.json'
PHYSICAL='results/uarch/dsrom_s81_adjacent_stream_price_20261005/physical_slot.json'
PINS=[PHYSICAL,A,B,G+'model.json',G+'inputs/cell_prices.json',
      G+'evidence/selected_held_landing/record.json',U,L,
      'tools/dsrom_s81_unified_components.py','tools/dsrom_s81_adjacent_stream_price.py',
      'rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv',
      'rtl/dsrom_sys/rd64_capture/ot_dsrom_s81_phase_capture_profile.sv',
      'rtl/dsrom_sys/s81_capture_parent/ot_hdc_core_v41x.sv',
      'rtl/dsrom_sys/s81_capture_parent/ot_v41_spine_w17w10.sv',
      'rtl/dsrom_sys/s81_capture_parent/ot_chip_v41x_tile.sv',
      'rtl/dsrom_sys/ot_dsrom_link_rt.sv']

def code(n):return math.ceil(n/64)*72
def tree(n):
    total=0
    while n>1:n=math.ceil(n/8);total+=n
    return total

def build(root):
    load=lambda p:json.loads((root/p).read_text())
    a,g,r4,link=[load(p) for p in (A,G+'model.json',U,L)]
    physical=load(PHYSICAL)
    prices={k:v['SS']['area_um2'] for k,v in load(G+'inputs/cell_prices.json')['facts'].items()}
    leaves=load(G+'evidence/selected_held_landing/record.json')['results']
    anchors={h['layer']:h['adjacent_field_stage'] for h in a['homes']}
    assert anchors[20]==37 and a['added_rank_dies']==160
    old_fixed=link['hop']['total_cycles']-link['hop']['payload_flits']+1
    assert old_fixed==269
    # Replace old90wire edges ONCE. Keep179 nonwire source PHY/CRC endpoint
    # edges conservatively, plus chosen95 and planned33mm package flight.
    flight_edges=math.ceil(33*.16*1.2)
    fixed=old_fixed-90+physical['route']['one_way_wire_plus_two_meso_crossings_cycles_candidate']+flight_edges
    rows=r4['source_suffix']['max_actual_fragment_rows'];assert rows==4608
    quotas=[2*(rows//256)+int(rows%256>2*r)+int(rows%256>2*r+1) for r in range(128)]
    capacity=max(quotas);assert sum(quotas)==rows and capacity==36
    # Native69 +root selector7 fits two64-bit stripes. Full169 context
    # is held separately; output values use native capture fmt/address rules.
    record_bits=code(69+7)
    header_raw=169+10+30+30+3+2+16+2+128*19
    header_bits=code(header_raw);header_flits=math.ceil(header_bits/512)
    # Full-context row payload, absolute VM19 row/mask and phase. No alias.
    row_packet_bits=code(169+10+19+8+256+3)
    row_flits=math.ceil(row_packet_bits/512)
    reverse_bits=code(169+10+128*19+2)
    reverse_flits=math.ceil(reverse_bits/512)
    assert(record_bits,row_packet_bits,row_flits)==(144,576,2)
    # One nondestructive indexed read /edge. Six36:1 levels +seven128:1
    # levels, registered. Positive bound: logical ordinal in[committed,received).
    indexed_stages=6+7
    # Existing held codec cuts: encode2fast/decode2fast. Two pipelines per
    # root stripe sustain NOREADY write1/root/edge; no reused II2 fiction.
    codec_fast_edges=4
    # Planned16x~2.06mm slow stations over33mm; no measured route credit.
    route_ns=16/.9 # ALREADY in original W11 head charge, not added again
    gear_ns=2*3/.9 # meso4fast already in Maxwell95; positive slow gear extra
    reply_ns=(fixed+reverse_flits-1)/1.2
    # W11 original active bank capacity1, II28. Preserve II and additionally
    # retain remote phase/ACK debt in charged storage until remote retirement.
    bank_ii=g['service']['bank_service_II_ns']
    head=g['service']['accepted_head_to_captured_retirement_ns_bound']
    # Current indexed interface has no eight-way read: each word charged once.
    # Actual low7 group map:64consecutive words use64DIFFERENT groups/banks.
    # ONE native checked request class in each, 12slow held edges; area existing
    # physical group decode plus a NEW charged64lane assembler/held issuer.
    input_ii_fast=12/.9*1.2
    layer=defaultdict(lambda:defaultdict(float));rank_source_bytes=0
    rows_total=phases=0
    with gzip.open(root/B,'rt') as f:
        for line in f:
            n=json.loads(line);l=int(n['node'].split('.')[0][1:]);ranks=[defaultdict(float) for _ in range(4)]
            for t in n['transfers']:
                d=ranks[t['rank']];ib,ob=t['input_bytes'],t['output_bytes']
                ni,no=ib//4,ob//4
                if ni>6144 or no>rows:raise ValueError('P1 sized phase exceeded; no truncation/free credits')
                hops=1+abs(t['source_stage']-anchors[l])
                input_beats=math.ceil(ni/64)
                # Full native PHW10 broadcast1632bits, unchanged tuple/order.
                # Protected1872bit beat requires4flits; no FP4 compression credit.
                input_stream_edges=max(0,input_beats-1)*max(input_ii_fast,4)+4
                input_ns=(header_flits+input_stream_edges+hops*fixed+indexed_stages+codec_fast_edges)/1.2+gear_ns
                # Read all actual retained columns before coalescing, no head pop.
                gather_ns=(no+indexed_stages+codec_fast_edges)/1.2
                # One chosen8word row schedule; first/last partial rows are real
                # masked RMW, no optimistic complete64B mask bandwidth used.
                # DO NOT pretend8adjacent addresses form a physical row.
                # Actual columns differ by128, bank by1024, row by2048.
                # Worst partial case: ONE RMW head per captured word. Each
                # physical bank has256rows and one active head. Positive full
                # phase bank grants/exclusion are mandatory, not idle inference.
                heads=no
                heads_per_bank=min(256,heads)
                output_ns=(header_flits+hops*(fixed+row_flits*heads-1))/1.2+gear_ns
                publication_ns=max(0,heads_per_bank-1)*bank_ii+head
                # Remote wholephase receipt repays old heads one/root/edge,
                # not all CAP36 records simultaneously. Upper charge every
                # modeled P1 phase by its reserved maximum36 head edges.
                retire_ns=capacity/1.2
                total=input_ns+gather_ns+output_ns+publication_ns+reply_ns+retire_ns
                d['input_ns']+=input_ns;d['indexed_gather_ns']+=gather_ns
                d['output_link_ns']+=output_ns;d['protected_publication_ns']+=publication_ns
                d['matched_return_ns']+=reply_ns;d['root_head_repayment_ns']+=retire_ns;d['sum_ns']+=total
                d['raw_branch_bytes']+=ib+ob;d['retained_reads']+=no;d['heads']+=heads;d['phases']+=1
            critical=max(ranks,key=lambda r:r['sum_ns'])
            for k,v in critical.items():layer[l][k]+=v
            rank_source_bytes+=max(r['raw_branch_bytes'] for r in ranks)
            rows_total+=max(r['retained_reads'] for r in ranks)
            phases+=max(r['phases'] for r in ranks)
    totals={k:sum(d[k] for d in layer.values()) for k in next(iter(layer.values()))}
    assert rank_source_bytes==a['cut']['unavoidable_one_branch_raw_bytes']==26105344
    # Exact finite phase state including non-destructive sent/ACK bitmaps.
    control_per_root=code(4*19+6+3*6+2*capacity)
    capture_state=rows*record_bits+128*control_per_root+header_bits
    activation_state=96*code(1632) # native KMAX6144 /64, P1 only
    # Two actual data directions, each replay512 +RX512, CRC/SEQ sized555.
    link_state=2*(2*512*555+90*555)
    cdc_state=2*8*code(512)+2*code(169+10) # finite8flit gear FIFOs plus held owner
    # Native coalescer capacity:4owned rows/bank including active,256banks.
    coalescer_state=256*4*row_packet_bits
    indexed_map_state=rows*code(19+7+6+3) # actualaddress/root/ordinal/column
    wide_input_state=64*(code(216)+code(32+83))
    ff=capture_state+activation_state+link_state+cdc_state+coalescer_state+indexed_map_state+wide_input_state
    holdmux_bits=ff
    indexed_mux_bits=128*(capacity-1)*record_bits+127*record_bits
    input_mux_bits=95*code(1632)
    mux_bits=holdmux_bits+indexed_mux_bits+input_mux_bits
    ff_body=ff*(prices['DFFHQNx1_ASAP7_75t_R']+prices['INVx1_ASAP7_75t_R'])
    mux_body=mux_bits*(3*prices['NAND2x1_ASAP7_75t_R']+prices['INVx1_ASAP7_75t_R']+2*prices['BUFx4_ASAP7_75t_R'])
    enc=512+26;dec=6+26
    codec_body=sum(sum(prices[c]*count for c,count in leaves[k]['cell_counts'].items())*rep for k,rep in [('encode',enc),('decode',dec)])
    # State FF and codec leaf FF are separate; leaf figures include their cuts.
    clock_reset_body=(tree(ff)*2+4096)*prices['BUFx4_ASAP7_75t_R']
    cells50=2*(ff_body+mux_body+codec_body+clock_reset_body)/1e6
    overlay=8.0 # extra electronics annex, ADD Maxwell known island/PHY/route
    reserve=overlay-cells50
    assert reserve>0
    budget=a['placement']['field_overlay_budget_mm2']
    field_total=physical['field_overlay']['selected_known_gross_mm2']+overlay
    fit=field_total<=budget
    # Planned conservative critical cut schedule: source/field compute costs
    # are unknown but these transfer/services are explicit nonoverlapped cuts.
    events=[{'id':'source_native_production','deps':[],'duration_ns':None},
            {'id':'bounded_native_cut_schedule','deps':['source_native_production'],'duration_ns':totals['sum_ns']},
            {'id':'remaining_native_services_HEAD','deps':['bounded_native_cut_schedule'],'duration_ns':None}]
    return dict(schema='opentallas.S81.d187.adjacent_stream_price.v1',
        selection='SELECT_DEFAULT_OFF_NATIVE_STREAM_COMPONENT_IMPLEMENTATION',
        adopted=False,default_enabled=False,RTL_selected=fit,
        candidate=a['candidate'],mapping_commit='2b89764bc',field37_38_unchanged=True,original_field_mapping_unchanged=True,
        source_pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in PINS},
        homes=a['homes'],scope=a['scope'],raw_branch_bytes_worst_rank_frozen_schedule=rank_source_bytes,
        exact_P1_max_phase=dict(rows=rows,root_counts=quotas,capacity_by_root_required=quotas,
            quotas_are_not_grants=True,positions=1,record_with_root_bits=76,coded_record_bits=record_bits,
            capture_CAP1_ALWAYS_ACCEPT1_not_used=True,phase_header_raw_bits=header_raw,
            phase_header_coded_bits=header_bits,header_flits=header_flits,
            record_and_control_coded_FF=capture_state,activation_coded_FF=activation_state),
        ports=dict(indexed_read_requests_per_fast_edge=1,indexed_return_pipeline_edges=indexed_stages,
            nondestructive=True,no_pop_on_linkready=True,logical_range='[committed,received) SAME held root/id/phase; no unchecked slot',
            indexed_read_write_collision='gather starts only after full actual phase capture; NOREADY writes are never clockskipped',
            result_coalescing_words_per_row_at_most=8,row_packet_coded_bits=row_packet_bits,row_packet_flits=row_flits,
            coalescing='only exact samephysicalrow/sameowner; original fmt/rsplit data32 and VM19 addresses, maskactualcolumns; no numerical reorder',
            planned_checked_input_words=64,planned_input_distinct_groups=64,
            planned_input_II_slow_edges=12,planned_native_broadcast_bits=1632,native_beat_flits=4,
            planned_input_wide_read_is_new_assembler_not_existing_scalar_sourceIO=True,
            bank_mapping=dict(group='addr[6:0]',column='addr[9:7]',bank='addr[10]',row='addr[18:11]'),
            coalescing_map_coded_FF=indexed_map_state,
            coalescing_worst_case_no_gain_credited=True,
            actual_row_masks_required_before_GO=True,
            bank_active_capacity=1,bank_II_slow_edges=28,bank_head_ns=head,bank_queue_owned_rows=4,
            full64B_complete_mask_bandwidth_NOT_used=True,
            physical_bank_parallelism='256existing modeled physical banks, eachcapacity1II28 and positive sameowner grants. Not128behavioral VM write ports. Perbank256distinct row bound requires unique output addresses; duplicate/colliding writes reject beforeGO'),
        credits=dict(link_fifo_flits=512,replay_flits=512,cdc_flits_per_direction=8,
            coalescer_owned_rows_per_bank=4,phase_rows_reserved_before_GO=rows,
            positively_reserved=False,
            rule='phase seats held through VM all6copy visibility, actual consumer lease and matching reverse. Link freed count only on real FIFO consumer, never VMACK.',
            out_ready='same held owner/address/mask has actual row seats and exclusive bank ports; otherwise stall',
            debt='reserved/unproduced ->captured ->launched ->remoteaccepted ->all6visible ->readerheld ->reverse/allcopyretired; no localreset clearing',
            local_bank_release='II28 requires SAME original positive counted local retirement. Remote phase debt stays in charged source phase/control and service WQD/ACK seats. If implementation holds active bank pending interdie return, II28 is invalid: model requires independent retained counted phase return after checked bank commit and cannot silently stretch timing or clear debt.'),
        planned_route=dict(fast_GHz=1.2,slow_GHz=.9,indexed_mux_levels=indexed_stages,
            encode_decode_fast_edges=codec_fast_edges,service_registered_stations=16,
            service_netlength_mm_bound=33.0,max_segment_mm=33/16,route_ns_already_in_W11_head=route_ns,
            positive_forward_reverse_CDC_ns=gear_ns,link_first_arrival_edges=fixed,
            field_wire_stages=53,hub_wire_stages=38,meso_fast_edges=4,
            package_flight_mm_bound=33,package_flight_ns_per_mm_planned=.16,package_flight_fast_edges=flight_edges,
            old90wire_replaced_once=True,source_PHY_CRC_endpoint_nonwire_edges_retained=179,
            link_forward_frame_bits=555,reverse_frame_bits=53,one_bit_per_track_cut_demand=608,
            planned_bounded_annex_route_reserve_mm2=reserve,
            physical_reply=physical,
            planned_tracks=1236,estimated_horizontal_budget=1477,estimated_margin=241,
            SS_FF_measured_after_RTL=True,signoff_pass=False,physical_adoption=False),
        area=dict(coded_storage_and_link_FF=ff,hold_and_selection_mux_bits=mux_bits,
            FF_cell50_mm2=2*ff_body/1e6,mux_cell50_mm2=2*mux_body/1e6,
            codec_cell50_mm2=2*codec_body/1e6,clock_reset_cell50_mm2=2*clock_reset_body/1e6,
            sized_cells50_mm2=cells50,overlay_reserved_mm2=overlay,
            additional_controller_route_PG_DFT_reserve_mm2=reserve,
            Maxwell_known_field_overlay_mm2=physical['field_overlay']['selected_known_gross_mm2'],
            field_total_overlay_mm2=field_total,
            field_budget_mm2=budget,modeled_field_overlay_fit=fit,
            field_screen_plus_overlay_mm2=a['placement']['field_mm2_before_new_overlays']+field_total,
            hub_budget_mm2=a['placement']['hub_overlay_budget_mm2'],
            hub_total_overlay_mm2=physical['hub_overlay']['selected_known_gross_mm2']+overlay,
            allocation='ADD full8mm2 electronics to each Maxwell known island/PHY/route gross; no containment subtraction, some wireFF conservatively doublecharged',actual_placed_fit=False),
        totals=totals,layers={str(k):dict(v) for k,v in sorted(layer.items())},
        dependency_cuts=events,composed=solve_events(events),composed_native_full_token_calendar=None,
        decision='SELECT bounded mandatory native-stream component for Nash DEFAULT_OFF implementation: finite phase/coded/indexed/credit/bank schedule and overlay sized; estimated clocks/route signoff follow RTL. This is NOT adopted executable wholeplan or a subms performance selection. Conservative frozen cut costs are explicit, no overlap/coalescing gain credited; full native source service calendar remains UNKNOWN and token-rate adoption is blocked. Neither validates nor disproves old725us headline. Any missing positive phase/bank/owner authority refuses GO; no actual token job edits or metadata sweep.',
        physical_closure_not_a_prebuild_prerequisite=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    x=ap.parse_args();m=build(x.root);x.out.parent.mkdir(parents=True,exist_ok=True)
    x.out.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'selection':m['selection'],'totals':m['totals'],'area':m['area']}))
