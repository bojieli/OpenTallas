#!/usr/bin/env python3
"""One named source-sized six-lane channel/shoreline allocation; no build.

Dedicated channel rectangles consume die area. The existing tile corridor is
not widened or credited twice. This constructs capacity, not routed signoff.
"""
import hashlib
import json
import math
import re
from pathlib import Path
import uarch_model as BASELINE
import qwen_rom_native_local_release as J
R=J.R;M=J.M
OUT=Path('results/uarch/qwen_rom_kv_channel_shoreline_20261002')


def price():
    dependency=R.obj(OUT/'inputs/ampere-dependency-r1.json');kv=R.obj(OUT/'inputs/model-r4.json')
    assert R.sha(OUT/'inputs/model-r4.json')==dependency['model_sha256']
    successor=R.obj(OUT/'inputs/Russell-successor-observed-model-r3.json')
    observed=R.obj(OUT/'inputs/Russell-successor-observation-r1.json')
    assert successor['configuration']['global_fill_lanes']==7
    service_known=successor['cells']['total_known_service_mm2']
    #Carry every predecessor debit, including the unitemized inherited service
    #reservation. Rebuilding a short subtotal must not silently refund it.
    inherited_other=815-kv['slot']['baseline_array_mm2']-kv['slot']['known_service_mm2']-kv['slot']['parent_interface_mm2']-kv['PHY']['existing_physical_footprint_rank_mm2']-kv['slot']['conditional_remaining_before_new_routes_PG_unknowns_mm2']
    phy=R.obj(Path('physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json'))
    lef=(R.ROOT/'physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.lef').read_text()
    symmetry=lef.split('SYMMETRY',1)[1].split(';',1)[0]
    assert 'X' in symmetry and 'Y' in symmetry
    area=R.obj(Path('configs/hardware/technology.json'))['reticle']['area_mm2']['value']
    w,h=357.696,1360.8;beach=phy['footprint']['width_um'];depth=phy['footprint']['height_um'];band=96.768
    # Native PHY requires two12mm beachfronts at each of top/bottom. The
    #minimum whole-column field width is ceil(2*beach/tile_width)=68columns.
    columns=math.ceil(2*beach/w);rows=math.ceil(1536/columns);half=columns//2
    fieldw=columns*w;dieh=rows*h+2*depth;diew=area*1e6/dieh
    fieldx=(diew-fieldw)/2
    assert diew<=26000 and diew>2*beach+1.08
    rectangles=[];tiles=[];channels=[]
    occupancy=[0,0]
    for lane in range(7):
        block=lane//2;side=lane%2
        count=successor['configuration']['tiles_per_lane'][lane]
        for i in range(count):
            side_here=side if lane<6 else (0 if i<109 else 1)
            row,col=divmod(occupancy[side_here],half);occupancy[side_here]+=1
            tiles.append(dict(tile=7*i+lane,fill_lane=lane,origin_um=[fieldx+side_here*half*w+col*w,depth+row*h],size_um=[w,h],orientation='R0'))
        xbase=fieldx+side*half*w if lane<6 else fieldx
        ybase=depth+(block*8 if lane<6 else rows-1)*h+700
        rect=[xbase,ybase,xbase+(half*w if lane<6 else fieldw),ybase+band]
        channels.append(dict(name=f'KV_FILL_CHANNEL_{lane}',fill_lane=lane,rectangle_um=rect,destinations=count,
            payload_B_per_stream_edge=64,fill_tracks=1048,clock_tracks=64,reset_ACK_tracks=64,spare_tracks=184,
            capacity=1360,layers=['M5','M6','M7','M8'],PG_pitch_um=5.376,
            within_prepaid_tile_upper_metal=True,macro_OBS_max_layer='M4',
            clocks_reset_and_all_other_signal_exclusivity_at_new_bands_proven=False,
            endpoint_pin_landing_and_vias_complete=False))
        own=[t for t in tiles if t['fill_lane']==lane]
        rectangles.append(dict(name=f'FIELD_LANE_{lane}_ENVELOPE',rectangle_um=[min(t['origin_um'][0] for t in own),min(t['origin_um'][1] for t in own),max(t['origin_um'][0]+w for t in own),max(t['origin_um'][1]+h for t in own)],envelope_is_not_an_exclusive_macro=True))
    assert occupancy==[768,768]
    slots=[];phy_slots=[]
    # Four service slots occupy the28empty native tile footprints in lastrow.
    #No empty tile is counted as hardware; these are physical unused sites.
    service_y=depth+(rows-1)*h
    occupied_last_row_per_half=768-(rows-1)*half
    service_width=(half-occupied_last_row_per_half)*w/2
    phy_x=(diew-2*beach-1.08)/2
    for stack in range(4):
        edge,side=divmod(stack,2);x=phy_x+side*(beach+1.08);y=0 if edge==0 else dieh-depth
        phy_slots.append(dict(stack=stack,rectangle_um=[x,y,x+beach,y+depth],
            orientation='R0' if edge==0 else 'R180',source_macro='ot_hbm3e_phy',signal_pins=9209,
            physical_abstract_only=True,clock_pin_M4_external_escape_apron_um=.54,
            actual_sustained_Bps=None,required_sustained_Bps=113135616000))
        ctrl_side,order=side,edge
        sx=fieldx+ctrl_side*half*w+occupied_last_row_per_half*w+order*service_width
        slots.append(dict(name=f'KV_CONTROLLER_STACK_{stack}',stack=stack,
            rectangle_um=[sx,service_y,sx+service_width,service_y+h],
            service_known_reservation_mm2=service_known/4,
            extension_rectangle_um=[0 if ctrl_side==0 else diew-fieldx,depth+order*rows*h/2,fieldx if ctrl_side==0 else diew,depth+(order+1)*rows*h/2],
            inherited_other_service_debit_reserved_mm2=inherited_other/4,
            minimum_cell_macro_utilization=((service_known+inherited_other)/4)*1e6/(service_width*h+fieldx*rows*h/2),
            domain_ports=['service_1GHz_unqualified','stream_1.2GHz','serial_0.9GHz_readiness'],
            new_bank_groups=8,new_command_paths=4,physical_context_RAMs=32,context_RAM_replicas_added=0))
    # A distinct vertical shoreline reservation on actual right-way M5/M7/M9.
    #The 50% share includes PG. No unreserved M6/M8 track credit is borrowed.
    layers=M.tech();tech=(R.ROOT/M.OUT/'inputs/tech.lef').read_text()
    body=re.search(r'^LAYER M9\n(.*?)^END M9$',tech,re.M|re.S)[1]
    assert 'DIRECTION VERTICAL' in body
    layers['M9']=dict(pitch=.080,offset=.116,direction='VERTICAL')
    shore=[]
    family_bits={k:kv['PHY'][k] for k in ('request_header_bits','command_total_bits_per_stack','owned_receipt_total_bits_per_stack','reverse_total_bits_per_stack')}
    source_bits=sum(family_bits.values());perstack=max(source_bits,phy['pins']['signal_pins'])
    for side in range(2):
        demand=2*perstack+128
        #Dedicated upper-metal trunks consume the M9 half-share explicitly.
        #M5/M7 stay owned by existing tile feeds and PG; no double credit.
        trunk_width=(demand+1)*2*layers['M9']['pitch']
        center=phy_x+side*(beach+1.08)+beach/2
        left=center-trunk_width/2;right=center+trunk_width/2
        capacities={'M9':len(M.centers(left,right,layers['M9']['pitch'],layers['M9']['offset']))//2}
        shore.append(dict(side=side,band_x_um=[left,right],capacity_by_layer=capacities,
            source_family_bits_per_stack=family_bits,source_bits_per_stack=source_bits,
            actual_PHY_pin_count_per_stack=phy['pins']['signal_pins'],two_stack_mid_cut_demand=demand,
            clock_and_reset_ACK_tracks=128,capacity=sum(capacities.values()),capacity_margin=sum(capacities.values())-demand,
            pin_to_controller_local_cut_demand=perstack+128,
            source_PHY_signal_pin_span_um=phy['pins']['pin_span_um'],
            PHY_pin_spread_layers=['M6','M8'],PHY_pin_spread_50percent_capacity=math.floor(depth/2*(1/.064+1/.080)),
            PG_half_share_reserved=True,actual_routed_pin_access=False))
    assert all(x['capacity_margin']>=0 for x in shore)
    # Explicit finite source-port -> corresponding controller spans. Per-bit
    #fanout-one isolation and segments are lower bounds, never free global IO.
    routes=[];buffers=0;wire=0
    for p,s in zip(phy_slots,slots):
        a=[sum(p['rectangle_um'][i::2])/2 for i in (0,1)];b=[sum(s['rectangle_um'][i::2])/2 for i in (0,1)]
        distance=sum(abs(x-y) for x,y in zip(a,b));segments=math.ceil(distance/128)
        routes.append(dict(stack=p['stack'],nominal_endpoint_distance_um=distance,source_signal_bits=perstack,
            maximum_segment_um=128,fanout=1,segments_per_bit=segments,buffer_reservation=perstack*(segments+1)))
        buffers+=perstack*(segments+1);wire+=perstack*(distance+16)
    clockfeed={}
    for corner in ('ss','ff'):
        _,lib,caps=R.library(corner);typ='BUFx12_ASAP7_75t_R';cap=phy['timing'][corner]['clk_cap_ff']+16*J.C
        rise=R.envelope(lib[typ],'cell_rise',cap,5,80);fall=R.envelope(lib[typ],'cell_fall',cap,5,80)
        slew=R.envelope(lib[typ],'rise_transition',cap,5,80)
        clockfeed[corner]=dict(cell=typ,PHY_CLK_cap_fF=phy['timing'][corner]['clk_cap_ff'],load_fF=cap,
            rise_delay_ps=rise,rise_slew_ps=slew,unchanged_80ps_slew_demand_met=slew[1]<=80,
            input_half_period_ps=500,PHY_min_pulse_ps=phy['timing'][corner]['min_pulse_ps'],
            output_low_pulse_lower_ps=500+rise[0]-fall[1],output_high_pulse_lower_ps=500+fall[0]-rise[1],
            root_arrival_observed=False,source_1GHz_SSFF_admitted=False)
    delta=dependency['cells'];newff=delta['delta_reset_sink_upper'];assembly=delta['retained_recomposed_assembly_clock_sinks']
    channel_area=0;reserved_upper_metal_area=4*band*fieldw/1e6
    clockdriver_area=4*J.A.abstracts()['BUFx12_ASAP7_75t_R']['size_um'][0]*.270
    PHY_release_area=4*(2*(.37908+.04374)+2*.10206)
    known=kv['slot']['baseline_array_mm2']+service_known+inherited_other+kv['slot']['parent_interface_mm2']+kv['PHY']['existing_physical_footprint_rank_mm2']+channel_area+buffers*.10206/1e6+(clockdriver_area+PHY_release_area)/1e6
    return dict(schema='QWEN_KV7_NATIVEPHY_68C_CHANNEL_R5',name='QROM-SMIN6-KV7-NATIVEPHY-68C',default_enabled=False,
        parent='28d01b35a',Russell_model_sha256=dependency['model_sha256'],selected_map_sha256=J.M.MAP_SHA,
        die=dict(width_um=diew,height_um=dieh,area_mm2=area,width_limit_um=26000,columns=columns,rows=rows,unused_tile_footprints=columns*rows-1536),field_islands=rectangles,tiles=tiles,
        dedicated_fill_channels=channels,PHY_slots=phy_slots,controller_slots=slots,shoreline_cuts=shore,
        new_channel_area_mm2=channel_area,reserved_upper_metal_channel_footprint_mm2=reserved_upper_metal_area,
        service_known_reservation_mm2=service_known,controller_extension_slots_prepaid_in_die_margin=True,source_to_controller_route_lower_bounds=routes,
        inherited_other_service_debit_mm2=inherited_other,inherited_component_names_parent_join_complete=False,
        route_buffer_reservation=buffers,route_buffer_area_mm2=buffers*.10206/1e6,route_wire_um=wire,
        known_composed_area_mm2=known,remaining_area_before_unknown_placements_mm2=area-known,
        four_PHY_clock_feeds=clockfeed,PHY_clock_driver_area_um2=clockdriver_area,
        PHY_local_release_FFs=8,PHY_local_release_reserved_area_um2=PHY_release_area,
        PHY_release_recovery_removal_and_ACK_return_qualified=False,extra_PHY_replicas=0,source_request_ports_per_stack=1,
        PHY_stack_bandwidth_required_Bps=113135616000,actual_sustained_PHY_Bps=None,
        delta_service_domain_FFs=delta['delta_clock_sinks_by_domain']['service'],delta_stream_domain_FFs=delta['delta_clock_sinks_by_domain']['stream'],
        retained_assembly_FFs=assembly,assembly_clock_domain_source_binding=None,
        successor_added_FF_count=sum(successor['cells']['successor_delta_FF'].values()),
        successor_added_collector_buffers=successor['cells']['collector_buffers'],
        successor_replica_counts=successor['cells']['replicas'],
        source_sized_clock_pins=newff+assembly+sum(successor['cells']['successor_delta_FF'].values())+48+512+4+8,
        source_reset_upper=newff+assembly+sum(successor['cells']['successor_delta_FF'].values())+8,
        collector_replica_counts=delta['clock_reset_replicas'],collector_buffers_by_family=delta['collector_buffers_by_local_replica_family'],
        fill_fanout_buffers=successor['cells']['total_fill_distribution_buffers'],fill_fanout_cells_already_in_service_debit=True,
        original_tile_corridor_um=96.768,original_tile_clock_reset_model_sha256=hashlib.sha256(J.model_bytes('model-r3.json')).hexdigest(),
        historical_shared_cut=dict(required=6925,available=1360,deficit=5565,verdict='FAIL_PRESERVED'),
        historical_uniform_widening_width_um=48234.375529411765,
        six_fill_constructive_calendar_ps=339296633.3333333,target_token_ps=333333333.3333333,
        six_fill_calendar_admitted=False,minimum_fill_integer_under_preserved_overhead=7,minimum_fill_integer_full_schedule=None,
        successor_observed_conditional_calendar_s=successor['calendar']['composed_conditional_s'],
        successor_model_and_live_source_match=observed['model_matches_observed_live_source'],
        source_matched_successor_calendar_admitted=False,
        Russell_next_contract='Six misses even before physical transport. Return the single source-sized minimum integer plus full ordered producer/demand calendar; changing fill_lane=tile%6 requires a new source-matched destination/visibility record.',
        missing_physical_bindings=['shoreline-to-eight-assembly-cohort-pools-and-seven-fill-roots cuts and routes',
            'M9 PG/via/OBS and actual pin landing plus exclusive ownership of new prepaid M6/M8 bands', 'controller placed utilization and metadata/mux/protection logic',
            'transport buffer slew and capture stages against retained39-edge contract',
            'local and field balanced clock plus reset/ACK feeds for controller domains',
            'actual binary initialization and parent held launch/epoch abort/current-V producer journal',
            'named baseline component debits and actual sustainable PHY calendar'],
        legal_rectangle_and_nominal_capacity_allocation=True,complete_route_allocation=False,source_map_admission=False,PnR=False,
        actual_contextual_SSFF=False,status='CONSTRUCTED_CHANNEL_RECTANGLES_CAPACITY_ONLY_NOT_ADMITTED',
        levels_used=[1,2,3,4,5],new_SU_spatial_redistribution=False,second_decode=False)


if __name__=='__main__':
    path=R.ROOT/OUT/'model-r5.json'
    if path.exists():raise ValueError('preserve verdict')
    result=price();M.write(path,result)
    print(json.dumps({k:result[k] for k in ('name','die','new_channel_area_mm2','known_composed_area_mm2','remaining_area_before_unknown_placements_mm2','route_buffer_reservation')},indent=2))
