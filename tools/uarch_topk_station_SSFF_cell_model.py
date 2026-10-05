"""Conservative one-cell-family selector station screen; no STA/physical credit."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import uarch_topk_finite_track_turn_model as T
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/topk_station_SSFF_cell_model_20261002'
MANIFEST='e2fb1e9421187fe523615dbb1475003746c302f15a6fdbf3f607687776db28bd'
PROBE_LOG_SHA='94a32ec0ad653a6862d7d2ec94634c4aab3d8b9885a4598401a1fede4027da00'

def groups(text,kind):
    for m in re.finditer(r'\b'+kind+r'\s*\(([^)]*)\)\s*\{',text):
        start=m.end();depth=1;quote=False;escape=False;i=start
        while depth and i<len(text):
            ch=text[i]
            if escape:escape=False
            elif ch=='\\':escape=True
            elif ch=='"':quote=not quote
            elif not quote:
                if ch=='{':depth+=1
                elif ch=='}':depth-=1
            i+=1
        if depth:raise ValueError('unbalanced Liberty group')
        yield m[1].strip(' "'),text[start:i-1]

def group(text,kind,name):
    choices=[b for n,b in groups(text,kind) if n==name]
    if len(choices)!=1:raise ValueError('unique Liberty group absent '+kind+' '+name)
    return choices[0]

def number(text,name):
    m=re.search(r'\b'+name+r'\s*:\s*([-+\d.eE]+)',text)
    if not m:raise ValueError('Liberty scalar absent '+name)
    return float(m[1])

def table(text,name):
    choices=list(groups(text,name))
    if len(choices)!=1:raise ValueError('unique timing table absent '+name)
    b=choices[0][1]
    def index(n):
        m=re.search(r'index_'+str(n)+r'\s*\("([^"]+)"\)',b)
        if not m:raise ValueError('table index absent')
        return [float(x) for x in m[1].split(',')]
    a=index(1);c=index(2)
    vals=re.search(r'values\s*\((.*?)\)\s*;',b,re.S)
    rows=[[float(v) for v in row.split(',')] for row in re.findall(r'"([^"]+)"',vals[1])]
    if len(rows)!=len(a) or any(len(row)!=len(c) for row in rows):raise ValueError('table dimensions changed')
    return {'index1':a,'index2':c,'values':rows}

def timing(cell,kind):
    choices=[b for _,b in groups(cell,'timing') if re.search(r'timing_type\s*:\s*'+kind+r'\s*;',b)]
    if len(choices)!=1:raise ValueError('unique arc absent '+kind)
    return choices[0]

def cell_facts(text,name,seq=False):
    cell=group(text,'cell',name);pins=dict(groups(cell,'pin'))
    output='QN' if seq else 'Y'
    kind='rising_edge' if seq else 'combinational'
    arcs=[b for _,b in groups(cell,'timing') if re.search(r'timing_type\s*:\s*'+kind+r'\s*;',b)]
    if not arcs:raise ValueError('missing cell arcs')
    tables={}
    for arc in arcs:
        related=re.search(r'related_pin\s*:\s*"([^"]+)"',arc)[1]
        for n in ['cell_rise','cell_fall','rise_transition','fall_transition']:
            key=n if len(arcs)==1 else related+'.'+n
            if key in tables:raise ValueError('duplicate arc table')
            tables[key]=table(arc,n)
    facts={'output_function':re.search(r'function\s*:\s*"([^"]+)"',pins[output])[1],'master':name,'area_um2':number(cell,'area'),'max_output_cap_fF':number(pins[output],'max_capacitance'),
       'input_cap_fF':{n:number(p,'capacitance') for n,p in pins.items() if 'direction : input;' in p},'delay_transition_tables':tables}
    if seq:
        for kind in ['setup_rising','hold_rising']:
            a=timing(cell,kind);facts[kind]={n:table(a,n) for n in ['rise_constraint','fall_constraint']}
        facts['inverted_QN_requires_restoring_INV']=bool(re.search(r'function\s*:\s*"IQN"',pins[output]))
    return facts

def bound(tables,key,load=None,minimum=False):
    selected=[t for n,t in tables.items() if key in n]
    values=[]
    for t in selected:
        if load is None:values.extend(v for r in t['values'] for v in r)
        else:
            # Load ceiling, not extrapolation or favorable interpolation.
            cols=[i for i,x in enumerate(t['index2']) if x>=load]
            if not cols:raise ValueError('load outside characterized table')
            values.extend(row[cols[0]] for row in t['values'])
    if not values:raise ValueError('no selected tables')
    return min(values) if minimum else max(values)

def build():
    probe=(BASE/'unit_probe.log').read_bytes()
    if hashlib.sha256(probe).hexdigest()!=PROBE_LOG_SHA:raise ValueError('unit probe changed')
    raw=(BASE/'source_manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST:raise ValueError('manifest changed')
    pins=json.loads(raw);texts={}
    for name,e in pins.items():
        if name=='read_only_tool_probe':continue
        data=(BASE/'inputs'/name).read_bytes()
        if len(data)!=e['bytes'] or hashlib.sha256(data).hexdigest()!=e['sha256']:raise ValueError('source bytes changed')
        texts[name.removesuffix('.gz')]=(gzip.decompress(data) if name.endswith('.gz') else data).decode()
    corners={}
    for c in ['SS','FF']:
        seq=texts[f'asap7sc7p5t_SEQ_RVT_{c}_nldm_220123.lib'];inv=texts[f'asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib'];simple=texts[f'asap7sc7p5t_SIMPLE_RVT_{c}_nldm_211120.lib']
        for text in [seq,inv,simple]:
            if not re.search(r'time_unit\s*:\s*"1ps"',text) or not re.search(r'capacitive_load_unit\s*\(1,ff\)',text):raise ValueError('units changed')
        corners[c]={'ff':cell_facts(seq,'DFFHQNx1_ASAP7_75t_R',True),'inv':cell_facts(inv,'INVx1_ASAP7_75t_R'),
                    'reset_mask':cell_facts(simple,'AND2x2_ASAP7_75t_R')}
    ss=corners['SS'];ff=corners['FF']
    # One explicit structural proposal: FF QN -> INV -> wire -> reset-mask AND
    # -> destination D. Conservatively charge AND on every bit, not just valid.
    # No enable feedback mux, since the station shifts each streaming edge.
    receiver=max(ss['reset_mask']['input_cap_fF'].values())
    cap_tables=ss['inv']['delay_transition_tables'];caps=cap_tables['rise_transition']['index2']
    limit=320.0
    safe=[x for x in caps if x<=ss['inv']['max_output_cap_fF'] and all(bound(cap_tables,'transition',lower)<=limit for lower in caps if lower<=x)]
    if not safe:raise ValueError('no characterized slew-safe driver load')
    load_ceiling=max(safe)
    cap_per_um={layer:float(value) for layer,value in re.findall(r'set_layer_rc -layer (M[2345]) -resistance [\d.Ee+-]+ -capacitance ([\d.Ee+-]+)',texts['setRC.tcl'])}
    if len(cap_per_um)!=4:raise ValueError('RC layer source absent')
    resistance_per_um={layer:float(value) for layer,value in re.findall(r'set_layer_rc -layer (M[2345]) -resistance ([\d.Ee+-]+) -capacitance [\d.Ee+-]+',texts['setRC.tcl'])}
    wire_cap_density=max(cap_per_um.values());cap_hop=(load_ceiling-receiver)/wire_cap_density
    clkq=bound(ss['ff']['delay_transition_tables'],'cell_',max(ss['inv']['input_cap_fF'].values()))
    inv_delay=bound(cap_tables,'cell_',load_ceiling)
    mask_delay=bound(ss['reset_mask']['delay_transition_tables'],'cell_',ss['ff']['input_cap_fF']['D'])
    setup=bound(ss['ff']['setup_rising'],'constraint')
    native=T.build();wire_ps_per_um=0.76
    # Unknown signed clock skew not removed: report maximum allowable residual.
    time_hop=(833-60-clkq-inv_delay-mask_delay-setup)/wire_ps_per_um
    if min(time_hop,cap_hop)<=0:raise ValueError('no positive timing/capacity hop')
    hop=min(time_hop,cap_hop)
    length=native['full_allocated_lane_path']['maximum_length_um'];n=math.ceil(length/hop)
    actual_hop=length/n
    # Existing formed write path also gets station cell/load treatment.
    base_data,_=T.F.A.replay(ROOT,mode='archive-only');base=json.loads(base_data)
    c=base['placement']['collective_reserved_bbox_DBU'];v=base['placement']['VM_reserved_bbox_DBU']
    sink_length=(max(c[2],v[2])-min(c[0],v[0])+max(c[3],v[3])-min(c[1],v[1]))/1000
    sn=math.ceil(sink_length/hop)
    inp=2122;out=2088;write=2112;bits=(inp+out)*(n-1)+(write+1)*(sn-1)
    area_per=sum(x['area_um2'] for x in ss.values())
    setup_cost=clkq+inv_delay+mask_delay+setup+wire_ps_per_um*actual_hop+60
    early_clkq=bound(ff['ff']['delay_transition_tables'],'cell_',minimum=True)
    early_inv=bound(ff['inv']['delay_transition_tables'],'cell_',minimum=True)
    early_mask=bound(ff['reset_mask']['delay_transition_tables'],'cell_',minimum=True)
    hold=bound(ff['ff']['hold_rising'],'constraint')
    minimum_path=early_clkq+early_inv+early_mask
    return {'schema':'FULL_SELECTOR_ONE_STATION_SSFF_CELL_CAP_MODEL_V1','sourcepins':pins,'unit_probe_sha256':PROBE_LOG_SHA,'cell_facts':corners,
      'geometry':native['fixed_geometry'],'selector_bits_unchanged':698354,'clock':{'period_ps':833,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'frequency_relaxed':False},
      'station_structure':'DFFHQNx1 QN -> INVx1 -> characterized wire -> AND2x2 reset mask -> D; shifts every edge; no added command context',
      'reset_contract':{'mask_is_synchronous_station_proposal':True,'actual_asynchronous_source_reset_requires_immediate_sink_enable_suppression':True,'late_payload_after_reset_must_not_write':True,'reset_tree_and_sink_suppression_logic_not_qualified':True},
      'fullbit_reset_mask_is_conservative_price':True,'old189_5ps_combined_allowance_replaced_not_added':True,
      'SS_bounds_ps':{'clkq':clkq,'restoring_INV':inv_delay,'reset_mask_AND':mask_delay,'setup':setup},
      'wire_load':{'RC_capacitance_fF_per_um':cap_per_um,'units_readonly_probe':'unit_probe.log:1fF/1um and set_layer_rc ui conversion',
          'max_density_fF_per_um':wire_cap_density,'receiver_input_fF':receiver,'characterized_slew_safe_INV_load_ceiling_fF':load_ceiling,
          'cap_limited_hop_um':cap_hop,'timing_limited_hop_um':time_hop,'load_extrapolation':False,'slew_ceiling_ps':limit,
          'unbuffered20segment_wire_plus_receiver_fF':native['full_allocated_lane_path']['maximum_equal_segment_length_um']*wire_cap_density+receiver,
          '20segment_without_repeater_station_load_proof':False,'RC_coupling_and_via_cap_not_in_template':True,'RC_resistance_kohm_per_um':resistance_per_um,
          'uniform_wire_Elmore_at_max_segment_ps':max(resistance_per_um.values())*actual_hop*(wire_cap_density*actual_hop/2+receiver),
          'loaded_0_76ps_per_um_is_retained_empirical_screen_not_unbuffered_SPEF':True},
      'finite_segmentation':{'maximum_hop_um':hop,'full_corridor_length_um':length,'segments_each_direction':n,'maximum_segment_um':actual_hop,
          'formed_write_rectangle_length_um':sink_length,'formed_write_segments':sn,'station_coordinates':'Use prior deterministic station_coordinates with this segment count; actual footprint and clock PG still required',
          'SS_path_plus_setup_uncertainty_ps':setup_cost,'remaining_for_clock_skew_and_unpriced_parasitics_ps':833-setup_cost,
          'no_context_setup_claim':True},
      'FF_hold_screen':{'earliest_clkq_ps':early_clkq,'earliest_INV_ps':early_inv,'earliest_AND_ps':early_mask,'minimum_zero_wire_path_ps':minimum_path,
          'worst_hold_constraint_ps':hold,'hold_uncertainty_ps':25,'remaining_for_adverse_capture_skew_ps':minimum_path-hold-25,
          'actual_min_wire_clock_skew_hold_cells_unknown':True,'no_context_hold_claim':True,
          'table_minima_are_characterized_points_not_guaranteed_subgrid_early_bounds':True,
          'sub0_72fF_load_earliest_arcs_unqualified':True,'even_characterized_zero_wire_screen_requires_hold_repair':minimum_path<hold+25},
      'cost':{'additional_station_bits':bits,'additional_clock_pin_capacitance_fF':bits*ss['ff']['input_cap_fF']['CLK'],'cell_area_per_bit_um2':area_per,'FF_INV_AND_cell_area_um2':bits*area_per,
          'FF_INV_AND_reservation_mm2_at50pct':bits*area_per/0.5/1e6,'additional_cycles_per_call':2*(n-1)+(sn-1),
          'ninecall_extra_cycles':9*(2*(n-1)+(sn-1)),
          'ninecall_selector_plus_transport_extra_cycles':1278+9*(2*(n-1)+(sn-1)),
          'source_load_plus_service_envelope_before_transport_cycles':4299,
          'source_load_service_plus_this_transport_envelope_cycles':4299+9*(2*(n-1)+(sn-1)),
          'calendar_scope':'Same nine source calls and reduction/order; envelope not observed deadlines or fulltoken return bound','ninecall_extra_ns_policyclock':9*(2*(n-1)+(sn-1))/1.2,
          'latest_owner_corridor_inclusive_plus_cell_floor_mm2':native['source_transport_price']['latest_owner_screen_already_including_corridor_mm2']+bits*area_per/0.5/1e6,
          'clocktree_reset_tree_hold_repair_repeater_wire_coupling_via_cost_unpriced':True},
      'G0':{'RTL_admitted':False,'PR_admitted':False,'scope':'Conservative finite unbuffered cell-station proposal, not a measured or adopted depth. Maxwell can bind an explicit repeater architecture instead; do not claim20depth from loaded-wire fit alone.'},
      'physical_jobs_launched':0,'read_only_library_tool_probe':True,'new_PVE2_PVE3_jobs':0,'optional_variant_sweep':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh model path required')
    model=build()
    with a.out.open('x') as f:json.dump(model,f,indent=2,sort_keys=True);f.write('\n')
