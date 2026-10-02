"""One source-correct repeater/hold station proposal joined to Maxwell37cc.
No RTL/STA/PR. Conditional load, slew, skew and reset contracts stay explicit.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import uarch_topk_station_SSFF_cell_model as C
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/topk_buffered_station_source_model_20261002'
OWNER_MANIFEST='9062014351640cfe0b25ca8e3c67ec5935030b3d1fcfe9e5bf6c7f6fa30a8f83'


def owner_inputs():
    b=(BASE/'owner_input_manifest.json').read_bytes()
    if hashlib.sha256(b).hexdigest()!=OWNER_MANIFEST:raise ValueError('owner manifest changed')
    pins=json.loads(b);records={}
    for name,e in pins.items():
        data=(BASE/'inputs'/name).read_bytes()
        if len(data)!=e['bytes'] or hashlib.sha256(data).hexdigest()!=e['sha256']:raise ValueError('owner bytes changed')
        records[name]=data
    return records,pins


def seq(text,name):
    body=C.group(text,'cell',name);pin=dict(C.groups(body,'pin'));qn=pin['QN']
    output_arc=C.timing(qn,'rising_edge')
    tables={key:C.table(output_arc,key) for key in ['cell_rise','cell_fall','rise_transition','fall_transition']}
    constraints={}
    for kind in ['setup_rising','hold_rising']:
        arcs=[a for _,a in C.groups(pin['D'],'timing') if re.search(r'timing_type\s*:\s*'+kind+r'\s*;',a)]
        if not arcs:raise ValueError('data constraint absent')
        constraints[kind]={str(i)+'.'+key:C.table(a,key) for i,a in enumerate(arcs) for key in ['rise_constraint','fall_constraint']}
    states=list(C.groups(body,'ff'))
    if len(states)!=1:raise ValueError('unique FF state absent')
    state_names,state=states[0]
    function=re.search(r'function\s*:\s*"([^"]+)"',qn)[1]
    next_state=re.search(r'next_state\s*:\s*"([^"]+)"',state)[1]
    if state_names!='IQN,IQNN' or function!='IQN' or next_state!='!D':raise ValueError('FF transfer polarity changed')
    extra={}
    if name.startswith('DFFASR'):
        for key in ['clear','preset']:
            extra[key]=re.search(r'\b'+key+r'\s*:\s*"([^"]+)"',state)[1]
        if extra!=dict(clear='!SETN',preset='!RESETN'):raise ValueError('ASR reset semantics changed')
    return {'master':name,'area_um2':C.number(body,'area'),'input_cap_fF':{n:C.number(p,'capacitance') for n,p in pin.items() if 'direction : input;' in p},
      'delay_transition_tables':tables,**constraints,'source_state':{'names':state_names,'next_state':next_state,'output_function':function,**extra}}


def lut(tables,kind,slew,cap,minimum=False):
    vals=[]
    for name,t in tables.items():
        if kind not in name:continue
        rows=[i for i,v in enumerate(t['index1']) if v>=slew];cols=[i for i,v in enumerate(t['index2']) if v>=cap]
        if not rows or not cols:raise ValueError('outside characterized station domain')
        vals.extend(t['values'][i][j] for i in range(rows[0]+1) for j in range(cols[0]+1))
    if not vals:raise ValueError('timing table absent')
    return min(vals) if minimum else max(vals)


def clock_tree(load,pin_budget,input_cap):
    if not 0<input_cap<pin_budget:raise ValueError('clock tree cannot converge')
    n=math.ceil(load/pin_budget);levels=[n]
    while n>1:
        n=math.ceil(n*input_cap/pin_budget);levels.append(n)
    return {'leaf_to_root_counts':levels,'BUF_cells':sum(levels),'max_levels':len(levels),
            'unequal_depth_branches_must_be_padded_and_priced':True,'actual_clock_skew_unqualified':True}


def build():
    old=C.build();raw,pins=owner_inputs();owner=json.loads(raw['owner_model.json'])
    if owner['transport']['nine_call_cycles']!=918 or owner['transport']['segments_each_direction']!=46:raise ValueError('Maxwell proposal changed')
    corners={}
    for corner in ['SS','FF']:
        path=C.BASE/'inputs'/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib';s=path.read_text()
        inv=gzip.decompress((C.BASE/'inputs'/f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz').read_bytes()).decode()
        corners[corner]={'data_FF':seq(s,'DFFHQNx1_ASAP7_75t_R'),'valid_FF':seq(s,'DFFASRHQNx1_ASAP7_75t_R')}
        for label,name in [('INV','INVx1_ASAP7_75t_R'),('BUF','BUFx4_ASAP7_75t_R'),('hold','HB2xp67_ASAP7_75t_R')]:
            corners[corner][label]=C.cell_facts(inv,name)
    ss=corners['SS'];ff=corners['FF'];cells=ss
    def pin_max(label,p):return max(corners[k][label]['input_cap_fF'][p] for k in corners)
    bcap=pin_max('BUF','A');icap=pin_max('INV','A');hcap=pin_max('hold','A')
    dcap=max(pin_max(label,'D') for label in ['data_FF','valid_FF'])
    R=max(old['wire_load']['RC_resistance_kohm_per_um'].values());W=max(old['wire_load']['RC_capacitance_fF_per_um'].values())
    # Explicit four load budgets from actual LUT indices, same two via R bounds.
    qload=1.44;firstload=5.76;repeatload=11.52;lastload=1.44
    sink_regular=max(bcap,hcap);via_R=2*0.0172
    def wire(load,sink):
        length=(load-sink)/W
        if length<=0:raise ValueError('no wire capacitance budget')
        upper_rc=(R*length+via_R)*load
        return {'load_ceiling_fF':load,'sink_cap_fF':sink,'length_ceiling_um':length,
          'RC_delay_upper_ps_uniform_template':upper_rc,'slew_growth_ps_2p2_RC_screen':2.2*upper_rc}
    links={'FF_to_INV_local':wire(qload,icap),'INV_to_first_BUF':wire(firstload,bcap),
           'BUF_to_BUF_or_HB':wire(repeatload,sink_regular),'HB_to_FF_local':wire(lastload,dcap)}
    qmax=max(lut(ss[label]['delay_transition_tables'],'cell_',320,qload) for label in ['data_FF','valid_FF'])
    qslew=max(lut(ss[label]['delay_transition_tables'],'transition',320,qload) for label in ['data_FF','valid_FF'])
    inv_delay=lut(ss['INV']['delay_transition_tables'],'cell_',80,firstload)
    inv_slew=lut(ss['INV']['delay_transition_tables'],'transition',80,firstload)
    buf_delay=lut(ss['BUF']['delay_transition_tables'],'cell_',160,repeatload)
    buf_slew=lut(ss['BUF']['delay_transition_tables'],'transition',160,repeatload)
    hb_delay=lut(ss['hold']['delay_transition_tables'],'cell_',160,lastload)
    hb_slew=lut(ss['hold']['delay_transition_tables'],'transition',160,lastload)
    receiver_slews={'INV_input':qslew+links['FF_to_INV_local']['slew_growth_ps_2p2_RC_screen'],
        'first_BUF_input':inv_slew+links['INV_to_first_BUF']['slew_growth_ps_2p2_RC_screen'],
        'repeated_BUF_or_HB_input':buf_slew+links['BUF_to_BUF_or_HB']['slew_growth_ps_2p2_RC_screen'],
        'destination_FF_input':hb_slew+links['HB_to_FF_local']['slew_growth_ps_2p2_RC_screen']}
    if any(receiver_slews[k]>limit for k,limit in [('INV_input',80),('first_BUF_input',160),('repeated_BUF_or_HB_input',160),('destination_FF_input',320)]):raise ValueError('receiver slew leaves declared domain')
    setup=max(C.bound(ss[label]['setup_rising'],'constraint') for label in ['data_FF','valid_FF'])
    # Clock root/leaf domains are constraints, not an inferred measured skew.
    def stage(n):return qmax+inv_delay+n*buf_delay+hb_delay+setup+60+25+sum(links[k]['RC_delay_upper_ps_uniform_template'] for k in ['FF_to_INV_local','INV_to_first_BUF','HB_to_FF_local'])+n*links['BUF_to_BUF_or_HB']['RC_delay_upper_ps_uniform_template']
    n=1
    if stage(n)>833:raise ValueError('no source-correct station fits period screen')
    while stage(n+1)<=833:n+=1
    # Local FF/INV/HB interconnect budgets not used as remote corridor reach.
    span=links['INV_to_first_BUF']['length_ceiling_um']+n*links['BUF_to_BUF_or_HB']['length_ceiling_um']
    length=old['finite_segmentation']['full_corridor_length_um'];sink_length=old['finite_segmentation']['formed_write_rectangle_length_um']
    segments=math.ceil(length/span);sn=math.ceil(sink_length/span)
    cycles=2*(segments-1)+(sn-1)
    data_bits=4210*(segments-1)+2113*(sn-1);valid_bits=2*(segments-1)+(sn-1)
    routed=(4210+2)*segments+(2113+1)*sn
    buf_cells=n*routed;hold_cells=data_bits+valid_bits;inv_cells=data_bits+valid_bits
    clock_cap=data_bits*pin_max('data_FF','CLK')+valid_bits*pin_max('valid_FF','CLK')
    clock=clock_tree(clock_cap,5.76,bcap)
    clock.update(load_ceiling_per_BUF_fF=11.52,pin_load_budget_fF=5.76,wire_load_budget_fF=5.76,
      clock_wire_hop_ceiling_um=5.76/W,root_input_slew_ps_max=160,matching_launch_and_capture_clock_tree_required=True,
      maximum_buffer_output_plus_wire_slew_ps=buf_slew+2.2*(R*(5.76/W)+via_R)*11.52)
    # Global minima valid only inside the explicitly characterized load/slew domain.
    mins={label:C.bound(ff[label]['delay_transition_tables'],'cell_',minimum=True) for label in ['data_FF','valid_FF','INV','BUF','hold']}
    holds={label:C.bound(ff[label]['hold_rising'],'constraint') for label in ['data_FF','valid_FF']}
    hold_margins={label:mins[label]+mins['INV']+n*mins['BUF']+mins['hold']-holds[label]-25-25 for label in ['data_FF','valid_FF']}
    lef=gzip.decompress(raw['cells.lef.gz']).decode()
    areas={}
    for label,f in ss.items():
        body=re.search(r'^MACRO '+f['master']+r'\s*$(.*?)^END '+f['master']+r'\s*$',lef,re.M|re.S)
        if body is None:raise ValueError('actual station LEF master absent')
        w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',body[1]).groups())
        area=w*h
        if abs(area-f['area_um2'])>1e-10:raise ValueError('LEF/Liberty area disagrees')
        areas[label]={'area_um2':area,'width_um':w,'height_um':h,'master':f['master']}
    area=data_bits*areas['data_FF']['area_um2']+valid_bits*areas['valid_FF']['area_um2']+inv_cells*areas['INV']['area_um2']+buf_cells*areas['BUF']['area_um2']+hold_cells*areas['hold']['area_um2']+clock['BUF_cells']*areas['BUF']['area_um2']
    # Reset two-level fence source primitives, not a new external ACK.
    reset_tables={}
    for corner in ['SS','FF']:
        text=(C.BASE/'inputs'/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib').read_text();cell=C.group(text,'cell','DFFASRHQNx1_ASAP7_75t_R');p=C.group(cell,'pin','RESETN')
        reset_tables[corner]={}
        for kind in ['recovery_rising','removal_rising']:
            values=[float(v) for _,a in C.groups(p,'timing') if re.search(r'timing_type\s*:\s*'+kind+r'\s*;',a) for n,t in C.groups(a,'rise_constraint') for row in re.findall(r'"([^"]+)"',re.search(r'values\s*\((.*?)\);',t,re.S)[1]) for v in row.split(',')]
            if not values:raise ValueError('reset constraints absent')
            reset_tables[corner][kind+'_max_ps']=max(values)
    baseline_bytes,_=C.T.F.A.replay(ROOT,mode='archive-only');baseline=json.loads(baseline_bytes)
    calls=[dict(c,additional_transport_cycles=cycles,load_service_plus_transport_cycles=c['burst_load_plus_service_envelope_edges']+cycles) for c in baseline['latency']['calls']]
    if len(calls)!=9 or sum(c['load_service_plus_transport_cycles'] for c in calls)!=4299+9*cycles:raise ValueError('nine source calls not conserved')
    clock['declared_fanout_tree_only_max_spatial_reach_um']=clock['max_levels']*clock['clock_wire_hop_ceiling_um']
    clock['global_root_to_station_wire_paths_not_in_pin_fanout_floor']=True
    clock['clock_spatial_distribution_and_matching_launch_tree_unpriced']=True
    return {'schema':'FULL_SELECTOR_SOURCE_CORRECT_BUFFERED_STATION_PROPOSAL_V1','owner_pins':pins,'library_source_manifest':str(C.BASE.relative_to(ROOT)/'source_manifest.json'),
      'library_source_manifest_sha256':C.MANIFEST,'cell_facts':corners,'fixed_geometry':old['geometry'],'selector_bits_unchanged':698354,
      'owner37cc_proposal_preserved':{'segments_each_direction':46,'formed_write_segments':13,'ninecall_cycles':918,'status':'conditional prior; no polarity or wire-slew correction retroactively applied'},
      'architecture':{'sequence':'DFF QN -> restoring INVx1 -> first wire -> BUFx4 repeated chain -> terminal HB2xp67 -> local wire -> destination DFF',
          'repeaters_per_segment':n,'mandatory_restoring_INV':True,'no_alternating_data_encoding':True,'terminal_hold_master':'HB2xp67_ASAP7_75t_R',
          'additional_valid_FF_master':'DFFASRHQNx1_ASAP7_75t_R','valid_RESETN_asserted_low_sets_IQN_high_restored_output_low':True,'valid_SETN_tied_high':True,
          'no_new_command_contexts':True,'no_new_external_ACK_or_ready':True,'formed_write_busy_retirement_delay_edges':sn-1,'all_data_tags_flags_done_retimed_together':True},
      'SS_conditional_screen':{'period_ps':833,'setup_uncertainty_ps':60,'additional_skew_budget_ps':25,'source_clock_slew_ps_max':320,
          'clkq_ps':qmax,'INV_delay_ps':inv_delay,'BUF_delay_ps':buf_delay,'HB_delay_ps':hb_delay,'setup_ps':setup,
          'stage_upper_ps':stage(n),'one_more_repeater_stage_upper_ps':stage(n+1),'receiver_slew_ps':receiver_slews,
          'wire_links':links,'R_kohm_per_um':R,'C_fF_per_um':W,'2p2_RC_is_conservative_singlepole_screen_not_extracted_waveform_proof':True,
          'actual_RC_coupling_via_pin_detours_waveforms_unqualified':True,'59bb_propagated_dcalc_slew_disagreement_not_resolved_by_model':True},
      'FF_conditional_screen':{'hold_uncertainty_ps':25,'additional_capture_skew_budget_ps':25,'minimum_characterized_cell_delays_ps':mins,
          'hold_max_constraints_ps':holds,'zero_wire_hold_margins_ps':hold_margins,'minimum_actual_net_cap_must_be_at_least0p72fF':True,
          'minimum_actual_input_slew_must_be_at_least5ps':True,'no_subgrid_earliest_extrapolation_credit':True,'actual_min_wire_and_clock_skew_unqualified':True},
      'placement_contract':{'maximum_remote_span_um':span,'segments_each_direction':segments,'formed_write_segments':sn,'LEF_master_dimensions':areas,
          'source_geometric_stations_use_prior_station_coordinates':True,'actual_disjoint_cell_sites_not_placed':True,'local_cell_pin_offsets_must_fit_wire_links':True,
          'track_signals_clock_reset':4212,'additional_internal_group_valid_wires':2,'product_port_count_unchanged':True,
          'external_half_pool_remaining_after_two_internal_valid_wires':[28,38],'PG_clock_reset_via_LEF58_allocation_unqualified':True},
      'clock_contract':clock,'reset_contract':{'ASR_source_constraints':reset_tables,'async_assert_fences_all_pending_VM_enables':True,
          'deassertion_must_meet_recovery_removal_on_actual_clock_tree':True,'no_steady_state_extra_reset_edge_credit':True,'reset_distribution_wire_and_sink_guard_logic_unpriced':True},
      'cost':{'intermediate_data_FF_bits':data_bits,'additional_ASR_valid_FF_bits':valid_bits,'INV_cells':inv_cells,'data_BUF_cells':buf_cells,'terminal_HB_cells':hold_cells,
          'clock_BUF_floor_cells':clock['BUF_cells'],'station_cell_area_um2':area,'station_cell_reservation_mm2_at50pct':area*2/1e6,
          'additional_cycles_per_call':cycles,'ninecall_cycles':9*cycles,'ninecall_ns_policyclock':9*cycles/1.2,
          'ninecall_selector_plus_transport_increment_cycles':1278+9*cycles,'source_ninecall_load_service_plus_transport_envelope_cycles':4299+9*cycles,
          'source_calendar_calls':calls,'source_deadline_acceptance_not_proven':True,'latest_owner_corridor_screen_plus_station_cell_floor_mm2':owner['area']['predecessor_no_station_screen_mm2']+area*2/1e6,
          'prior_station_floor_replaced_not_added':True,'clock_route_reset_guard_PG_hold_repair_detour_cost_unpriced':True},
      'G0':{'RTL_admitted':False,'PR_admitted':False,'remaining':['Maxwell exact parent clock and accepted command/write-drain contract','Arch actual cell/PG/clock/pin/via station construction','source slew diagnostic resolved with actual mapped timing','full-instance SSsetup FFhold with actual RC and reset recovery/removal']},
      'jobs_launched':0,'new_PVE2_PVE3_jobs':0,'no_variant_sweep':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output required')
    m=build()
    with a.out.open('x') as f:json.dump(m,f,indent=2,sort_keys=True);f.write('\n')
