"""Constructive full-count Engram ROM service candidate, not placement authority.

Reads committed git objects only. No checkpoint, RTL, or implementation jobs.
"""
import hashlib
import json
import math
import subprocess
from pathlib import Path

OUT = Path('results/quality/w16_engram_rom_constructive_home_20261001/final')
PINS = {
    'geometry_envelope': ('e61a5a1ee', 'results/quality/w16_w17_geometry_search_20261001/search.json'),
    'demand': ('b0cfaee4c9b4ab64606fc33d0d246e2ed685f559', 'results/quality/w16_engram_home_service_demand_20261001/demand.json'),
    'selector': ('05485a4bdbb4cf9c31603cef1fab2737dc515c23', 'results/quality/w16_engram_aperture_selector_20261001/v2/analysis.json'),
    'model': ('19c310b003f0b663b04861cbd17557832cea8e7f', 'tools/uarch_model.py'),
    'depth': ('19c310b003f0b663b04861cbd17557832cea8e7f', 'results/uarch/v41_rom_depth_study.json'),
    'macro_cost': ('dd3f54450', 'results/uarch/w11_crom_home_service_preflight_20261001/contract.json'),
    'rack': ('19c310b003f0b663b04861cbd17557832cea8e7f', 'results/arch/v41_rack.json'),
    'whole_owner': ('9345c1fc0', 'results/quality/w16_w17_whole_dsrom_candidate_20261001/candidate.json'),
}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def objects():
    pins, data = {}, {}
    for name, (commit, path) in PINS.items():
        full = subprocess.check_output(['git', 'rev-parse', commit], text=True).strip()
        raw = subprocess.check_output(['git', 'show', full + ':' + path])
        pins[name] = dict(commit=full, path=path, sha256=sha(raw))
        data[name] = raw.decode() if name == 'model' else json.loads(raw)
    return pins, data

def tree(pitch_x, pitch_y):
    """Explicit balanced binary rectangular partition; every leaf is a slot.

    Splits x,y alternately, with local index encoded by the 14 split decisions.
    Each edge has a dedicated registered request and reverse response link.
    Long edges use 504 um stage reach from the source model, not closure credit.
    """
    levels = [dict(level=i, edges=0, length_um=0., max_edge_um=0.,
                   wire_stages=0, max_path_wire_stages=0) for i in range(14)]
    paths = []
    def visit(x0, y0, nx, ny, depth, index, path):
        if depth == 14:
            assert nx == ny == 1 and index < 16384
            paths.append((index, x0, y0, path))
            return
        axis = depth % 2
        for bit in (0, 1):
            if axis == 0:
                cx0, cy0, cnx, cny = x0 + bit * nx // 2, y0, nx // 2, ny
                length = nx * pitch_x / 4
            else:
                cx0, cy0, cnx, cny = x0, y0 + bit * ny // 2, nx, ny // 2
                length = ny * pitch_y / 4
            stages = max(1, math.ceil(length / 504))
            r = levels[depth]
            r['edges'] += 1
            r['length_um'] += length
            r['max_edge_um'] = max(r['max_edge_um'], length)
            r['wire_stages'] += stages
            r['max_path_wire_stages'] = max(r['max_path_wire_stages'], stages)
            visit(cx0, cy0, cnx, cny, depth + 1, index * 2 + bit, path + stages)
    visit(0, 0, 128, 128, 0, 0, 0)
    assert len(paths) == 16384
    assert len({(x,y) for _,x,y,_ in paths}) == 16384
    assert {i for i,_,_,_ in paths} == set(range(16384))
    return dict(levels=levels, total_edges=sum(r['edges'] for r in levels),
                edge_wire_stage_sum=sum(r['wire_stages'] for r in levels),
                path_wire_cycles=min(p for _,_,_,p in paths),
                max_path_wire_cycles=max(p for _,_,_,p in paths),
                dedicated_link_length_um=sum(r['length_um'] for r in levels),
                grid_width_um=128*pitch_x, grid_height_um=128*pitch_y,
                grid_area_mm2=128*pitch_x*128*pitch_y/1e6)

def build():
    pins, d = objects()
    model = d['model']
    assert 'SS_REACH_UM = {1.2e9: 504.0' in model
    assert 'DFF_UM2 = 0.2916' in model
    macro = next(r for r in d['depth']['rows'] if r['macro']=='ot_rom_4096x274_m8')
    cost = d['macro_cost']['source_macro_cost']
    request_bits, response_bits, tag_bits = 51, 288, 24
    leaves, nodes = 16384, 16383
    analytic_macro_mm2 = 4096*274/75e6
    # Planning-density square footprint is a reservation, NOT a new LEF.
    planning_width=macro['width_um']
    planning_height=analytic_macro_mm2*1e6/planning_width
    field_bound=float(d['geometry_envelope']['supplied_geometry_envelope']['area_limit_mm2'])
    variants = {}
    for name, x, y in [('planning_75Mbit',planning_width,planning_height),
                       ('predictive_LEF_sensitivity',macro['width_um'],macro['height_um'])]:
        t = tree(x+16,y+16)
        assert t['total_edges']==2*nodes
        extra_stages = t['edge_wire_stage_sum']-t['total_edges']
        # Request capture per child; response mux capture per internal node;
        # macro captures count only populated slots below. Additional edges
        # add one request and one response register per segmentation stage.
        base_tree_FF = (2*nodes+nodes)*(request_bits+response_bits) + 2*nodes
        extra_wire_FF = extra_stages*(request_bits+response_bits)
        mux_bits = nodes*response_bits
        request_demux_gate_bits = 2*nodes*request_bits
        assumption_um2 = (base_tree_FF+extra_wire_FF+4608+64)*.2916 + mux_bits*.2 + request_demux_gate_bits*.2
        variants[name] = dict(geometry=t, macro_reservation_area_mm2_per_slot=(analytic_macro_mm2 if name=='planning_75Mbit' else cost['area_um2_per_bank']/1e6),
            base_tree_FF_bits_per_home=base_tree_FF, extra_wire_FF_bits_per_home=extra_wire_FF,
            response_mux2_bit_equivalents_per_home=mux_bits,
            request_demux_gate_bit_equivalents_per_home=request_demux_gate_bits,
            tree_FIFO_control_cell_area_mm2_assumed=assumption_um2/1e6,
            tree_FIFO_control_placed_area_mm2_at_50pct_assumed=2*assumption_um2/1e6,
            local_first_beat_cycles_proposed=2*t['max_path_wire_cycles']+28+1,
            local_complete_row_cycles_proposed=2*t['max_path_wire_cycles']+28+1+7,
            timing_scope='Charge 14 dedicated decode stages plus 14 dedicated mux stages separately from all wire endpoint captures. Conditional if each dedicated logic stage and all buffered <=504um edges close; not measured SS/FF. Macro capture is separate; never combine 744ps macro output with selector.')
    homes=[]
    rows_seen=0
    coordinate_digest=hashlib.sha256()
    def xy(local):
        return tuple(sum(((local>>(13-axis-2*k))&1)<<(6-k) for k in range(7)) for axis in (0,1))
    assert len({xy(m) for m in range(16384)})==16384
    columns=d['demand']['ROM_candidate']['columns']
    for ordinal,c in enumerate(columns):
        n=c['macros']
        assert 16384<n<=32768
        for half in (0,1):
            start=half*16384; end=min(start+16384,n); count=end-start
            homes.append(dict(home_id=ordinal*2+half,layer=c['layer'],column=c['column'],
                              column_macro_start=start,column_macro_end_exclusive=end,
                              actual_macros=count,padded_slots=leaves,unused_slots=leaves-count,
                              candidate_exclusive_die_id=ordinal*2+half,physical_assignment=None))
        # Check every physical macro (not only samples), inverse mapping and
        # leaf-selector capacity, including the partially populated tail.
        for m in range(n):
            home=ordinal*2+(m>>14); local=m&16383
            assert homes[home]['column_macro_start']+local==m
            assert local<homes[home]['actual_macros']
            x,y=xy(local)
            coordinate_digest.update(f'{home},{m},{local},{x},{y}\n'.encode())
        rows_seen+=c['rows']
    actual=sum(h['actual_macros'] for h in homes)
    assert len(homes)==96 and actual==1500067
    assert rows_seen==768022850
    full={}
    for name,v in variants.items():
        perhome=[]
        for h in homes:
            capture_bits=h['actual_macros']*(274+tag_bits)
            capture_area=capture_bits*.2916/1e6
            area=v['geometry']['grid_area_mm2']+v['tree_FIFO_control_placed_area_mm2_at_50pct_assumed']+2*capture_area
            perhome.append(dict(home_id=h['home_id'],macro_capture_FF_bits=capture_bits,
                allocated_grid_plus_placed_logic_mm2_assumed=area,
                available_after_12p5pct_of_815mm2_reserve=815*.875,
                remainder_for_IO_clock_PDN_control_mm2=815*.875-area,
                owner_field_bound_mm2=field_bound,
                remaining_owner_field_mm2=field_bound-area,
                owner_field_area_only_fits=area<field_bound,
                area_only_envelope_fits=area<815*.875))
        full[name]=dict(per_home=perhome,actual_macro_area_mm2=actual*v['macro_reservation_area_mm2_per_slot'],
                       reserved_grid_area_mm2=96*v['geometry']['grid_area_mm2'],
                       all_capture_FF_bits=actual*(274+tag_bits),
                       all_tree_and_wire_FF_bits=96*(v['base_tree_FF_bits_per_home']+v['extra_wire_FF_bits_per_home']),
                       all_dedicated_link_track_um=96*v['geometry']['dedicated_link_length_um']*341,
                       all_dedicated_link_length_m=96*v['geometry']['dedicated_link_length_um']/1e6,
                       all_tree_mux2_bit_equivalents=96*v['response_mux2_bit_equivalents_per_home'],
                       full_table_macro_leakage_W_predictive_only=actual*cost['SS_leakage_W_per_bank'],
                       max_allocated_home_area_mm2=max(p['allocated_grid_plus_placed_logic_mm2_assumed'] for p in perhome),
                       total_allocated_home_area_mm2=sum(p['allocated_grid_plus_placed_logic_mm2_assumed'] for p in perhome))
    local=variants['planning_75Mbit']['local_complete_row_cycles_proposed']
    lane_Bpc=d['rack']['lanes']['lane_net_Bps']/1.2e9
    link_calendar=[]
    for collector_lanes in (1,4):
        # Explicit proposed packet: 8 tagged288b beats plus16B header.
        request_collect=math.ceil(24*16/(collector_lanes*lane_Bpc))
        request_home=math.ceil(16/lane_Bpc)
        response_home=math.ceil(304/lane_Bpc)
        response_collect=math.ceil(24*304/(collector_lanes*lane_Bpc))
        subtotal=local+request_collect+request_home+response_home+response_collect+192
        link_calendar.append(dict(collector_lanes=collector_lanes,home_lanes_each=1,request_collector_cycles=request_collect,request_home_cycles=request_home,home_response_cycles=response_home,collector_response_cycles=response_collect,local_plus_serializations_plus_decoder_cycles_no_overlap=subtotal,subtotal_ns_excluding_flight_CDC=subtotal/1.2,proposed_two_board_legs_each_direction_fixed_ns=520,total_ns_including_only_fixed_board_hops=subtotal/1.2+520,qualification='Conditional conservative serial calendar; no free overlap. Fixed260ns request +260ns response from two130ns baseline legs each direction. On-die endpoint routes, link protocol implementation and actual slot allocation remain unbound.'))
    return dict(schema='opentallas.engram.constructive-ROM-home.v1',source_pins=pins,
        generator_sha256=sha(Path(__file__).read_bytes()),owner_authority='Ramanujan whole-placement join; this is additive service candidate only',
        verdict='CAPACITY_AND_GRAPH_CONSTRUCTED_NOT_ADMITTED',supersedes_preliminary=dict(path='results/quality/w16_engram_rom_constructive_home_20261001/candidate.json',sha256='d69837f163de21416363ef2cbdfd2ac989e8994b82f19469ff71c68f89e49f6b',correction='Separate decode/mux logic stages from wire stages; charge all endpoint captures and ready tracks. Preliminary retained, no admission granted.'),actual_macro_count=actual,
        homes=homes,total_proposed_exclusive_table_dies=96,physical_home_assignments=None,
        coordinate_inventory=dict(all1500067_home_macro_local_x_y_tuple_SHA256=coordinate_digest.hexdigest(),canonical_tuple_encoding='ASCII home,column_macro,local_macro,x,y followed by LF; source column order then macro ascending',x_bits='local[13,11,9,7,5,3,1]',y_bits='local[12,10,8,6,4,2,0]',cell_origin_um='(x*(macro_reservation_width+16),y*(macro_reservation_height+16)); reservation origin=cell+8um; actual macro capture/escape not yet placed',planning_reservation_macro_width_um=planning_width,planning_reservation_macro_height_um=planning_height,representatives=[dict(home_id=h['home_id'],first_local_xy=xy(0),last_local_xy=xy(h['actual_macros']-1)) for h in homes]),
        rejected_48_home_alternative=dict(max_column_macros=max(c['macros'] for c in columns),raw_macro_planning_area_mm2=max(c['macros'] for c in columns)*analytic_macro_mm2,owner_field_bound_mm2=field_bound,status='FAIL_75MBIT_RAW_MACROS_EXCEED_OWNER_FIELD_BEFORE_SELECT_CAPTURE_ROUTING'),
        copies=dict(full_table_copies=1,TP_replicated_table_copies=0,TP_decoded_view_replication_unbound=True),
        mapping=dict(validated_word27='(globalrow-column_offset)*8+beat',macro15='word27 >> 12',row12='word27 & 4095',
            home='2*(layer_ordinal*24+column)+(macro15>>14)',local_macro14='macro15 & 16383',
            placement='128x128 recursive binary x/y partition; bits13..0 select split decisions; zero-filled unpopulated slots do not answer valid reads',
            request_guard='Validate layer/column/globalrow prime range; reject unpopulated macro or out-of-range beat. Every eight-word valid row stays within one macro.'),
        selector=dict(levels=14,request_bits=request_bits,response_bits=response_bits,
            response_payload_bits=264,physical_macro_capture_bits=274,tag_bits=tag_bits,
            tag_recipe='epoch8,column5,layer1,beat3,valid1,rowlease6; bounded one token in flight; reject reuse until all consumers acknowledge',
            request_recipe='word27 plus tag24; carry full address to selected macro only',
            max_logical_fanout_per_bit=2,request_demux='one registered binary demux per node',
            response_mux='one registered binary 2:1 mux per node, selected-child valid and stall held',
            macs_per_cycle=0,MACs_per_byte=0,
            macro_read_port_Bpc=274/8,root_useful_response_Bpc=33,
            root_response_with_identity_Bpc=36,request_Bpc=51/8,
            parallel_active_homes_per_layer=24,all_active_root_response_bits_pc=24*288,
            simultaneous_unrelated_read_ports_per_home=1),
        assumptions=dict(mux2_or_demux_gate_um2=.2,DFF_um2=.2916,logic_placement_utilisation=.5,
            macro_planning_density_Mbit_mm2=75,die_envelope_mm2=815,global_overhead_fraction=.125,
            channel_width_um=16,signal_layers=4,track_pitch_um=.08,wire_stage_reach_um=504,
            caveat='Mux/gate unit price and channel layers/pitch are explicit model assumptions, not library extraction or available routed resources.'),
        routing=dict(each_edge_request_plus_return_tracks=341,two_child_junction_tracks=682,
            assumed_channel_capacity_tracks=800,assumed_two_layers_per_direction_tracks=400,
            channel_sizing_arithmetic_fits=True,
            global_shared_bus=False,topology='Dedicated recursively partitioned corridors; edges never share a broadcast bus. Track capacity arithmetic does not prove physical escape, intersections, power/clock layer exclusion, or routing closure.',
            macro_pin_capture_residual_ps=1e12/1.2e9-744-25-60,
            macro_to_capture_wire_allowance_um_if_linear_fit=(1e12/1.2e9-744-25-60)/1.135,
            physical_signal_layers_and_macro_escape=None,clock_reset_fanout='Clock/epoch/reset are NOT covered by data-tree fanout2; CTS and reset distribution unqualified.'),
        variants=variants,full_cost=full,
        row_response_placement=dict(per_home_root_double_row_FIFO_bits=4608,
            FIFO='Two 8x288b row FIFOs per home; all eight matching scale beats retained with lease under backpressure.',
            consumer='Layer collector/gather decoder, not free local-to-layer delivery',
            full_table_row_payload_B_per_token=12672,decoded_BF16_B_per_token=24576,
            active_layer_root_payload_B=6336,root_parallel_response_Bpc=864,
            single_33Bpc_collector_serialization_cycles_per_layer=192,
            existing_decoder_service_cycles_per_layer=192,
            decoded_double_buffer_B_one_logical_copy=49152,
            consumer_TP_copy_count=None,actual_die_links_and_multicast=None,
            one_home_FIFO_capture_Bpc=36,collector_proposed_payload_Bpc=33,decoder_BF16_output_Bpc=64,
            layer_response_ingress_pins_parallel_option=24*288,
            sequential_collector_physical_link='33B/fast-cycle payload =39.6GB/s; one112G lane (13.176GB/s net) insufficient. Requires separately priced multi-lane/package or on-chip placement; no free remote link.',
            instantaneous_macro_ports_read_bits_pc=24*274,
            credit_return='Return per-edge ready/credit separately; local reverse tree wire+logic path costs 58 cycles on planning grid after upstream consumption, plus unbound external consumer acknowledgement. Root lease is retained until final TP consumer acknowledgement.',
            macro_control='Hold macro request address/enable and tree path until capture; stall cannot overwrite accepted response; clock-gating implementation unqualified.'),
        transport_candidate=dict(one_die_per_proposed_home_package=96,home_112G_lanes_total=96,collector_lane_alternatives_per_active_layer=[1,4],net112G_lane_Bpc=lane_Bpc,proposed_request_packet_B=16,proposed_response_packet_B=304,per_home_two_response_packets_storage_bits=4864,additional_packet_header_FIFO_bits_per_home=256,additional_packet_header_FF_cell_area_mm2_all96=96*256*.2916/1e6,metadata_identity='Proposed16B header must bind home/column/layer/epoch/rowlease and framing; not existing producer wire contract.',calendar=link_calendar,actual_package_or_lane_reservations=None,PHY_IO_area_power=None,root_to_PHY_route='Root at grid center to nearest edge-midpoint is8668um on planning grid: >=18 wire stages each direction at504um reach; add36cycles/row-service roundtrip if this proposed location is used, plus pipeline FF and actual endpoint capture. Not included silently in calendar.'),
        latency=dict(local_row_cycles_proposed=local,local_row_ns_proposed=local/1.2,
            serial_no_overlap_local_plus_collector_plus_decoder_cycles_per_layer=local+192+192,
            serial_no_overlap_both_layers_ns_excluding_external_transport=2*(local+192+192)/1.2,
            qualification='Candidate schedule arithmetic, conditional on stated pipeline stage closure. Collector serialization and decoder may overlap only with a proved source schedule. Both table gathers charged; external request/response hops, CDC, visibility and TP multicast still NULL.',
            external_transport_cycles=None,full_token_critical_path_cycles=None),
        admission_blockers=['Actual packing/image producer for 1500067 macros with matching eight scales',
            'Library-sized mux/demux/tag/valid/clock gating and contextual SS/FF closure',
            'Local macro capture within 4.33ps residual; no free mux or wire after macro',
            'Available layers, pin escape, intersections, PDN/CTS/reset and return-credit layout',
            '96 table-die placement/package/link/consumer mapping and correct full-program DAG join',
            'Clock/dynamic/IR budget: predictive macro leakage is only a component',
            'L1 generated operand sources remain NULL; no substitute from L14'],
        verification=dict(all1500067_macro_home_inverse_mappings=True,
            all16384_leaf_indices_and_coordinates_bijective=True,
            no_free_selectors_or_response_links=True,track_capacity_scope='assumed channel arithmetic only'),
        L1_generated_source=None,checkpoint_reads=0,RTL_changes=False,RTL_or_PnR_runs=False,
        composed_admission=False,physical_fit_proven=False,headline_rate=None)

if __name__=='__main__':
    assert not OUT.exists(),'immutable evidence: use a fresh version path'
    result=build()
    OUT.mkdir(parents=True)
    raw=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode()
    (OUT/'candidate.json').write_bytes(raw)
    (OUT/'SHA256SUMS').write_text(sha(raw)+'  candidate.json\n')
    print(json.dumps(dict(macros=result['actual_macro_count'],homes=96,
        planning=result['full_cost']['planning_75Mbit'],latency=result['latency']),indent=2))
