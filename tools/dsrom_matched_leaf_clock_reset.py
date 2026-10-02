#!/usr/bin/env python3
"""Construct one literal-pin leaf0 clock/reset proposal; never launch hardware.

Upper-plane paths are explicit geometry, not a claim of native via/PG legality.
Equal stage counts alone never qualify skew: source LUT+layer RC is evaluated
for each sink, edge and SS/FF corner with correlated common input slew.
"""
import argparse,hashlib,json,math
from pathlib import Path
from dsrom_noECC_enable_distribution import placed,overlap
from dsrom_noECC_hold_station_geometry import pin_rects,center,length,grid
from dsrom_noECC_liberty import cell_bodies
from dsrom_noECC_slew_enable_diagnosis import pin_models,lookup
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_matched_leaf_clock_reset_20261002'
E=ROOT/'results/uarch/dsrom_noECC_enable_distribution_20261002/model.json'
H=ROOT/'results/uarch/dsrom_noECC_hold_station_geometry_20261002/model.json'
C=ROOT/'results/uarch/dsrom_noECC_production_context_20261002/local_cuts.json'
BUF='BUFx4_ASAP7_75t_R'; ROOTBUF='BUFx24_ASAP7_75t_R'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def literal(item,lef,pin):
    rs=pin_rects(item,lef[item['master']],pin)
    rect=max((r for r in rs if r['layer']=='M1'),key=lambda r:r['bbox_DBU'][3]-r['bbox_DBU'][1])
    pt=center(rect['bbox_DBU'])
    return dict(instance=item['instance'],pin=pin,literal_rectangle=rect,pin_point_DBU=pt,
                upper_point_DBU=[grid(pt[0],16,64),grid(pt[1],116,80)],
                native_access_stack_qualified=False)
def path(a,b,extra=0):
    """M8 horizontal/M7 vertical dogleg, optional explicit M8 hairpin.
    No diagonal directions, nor a fabricated off-grid endpoint pin.
    """
    x,y=a['upper_point_DBU'];u,v=b['upper_point_DBU']
    # A fixed extra horizontal excursion reserves positive matching wire.
    h=24576; vv=10080
    if abs(x-u)>h or abs(y-v)>vv:raise ValueError('Fixed matching segment cannot reach literal endpoint')
    bend=grid((h+x+u+1)//2,16,64)
    turn=grid((vv+y+v+1)//2,116,80)
    seg=[dict(layer='M8',points_DBU=[[x,y],[bend,y]]),
         dict(layer='M7',points_DBU=[[bend,y],[bend,turn]]),
         dict(layer='M8',points_DBU=[[bend,turn],[u,turn]]),
         dict(layer='M7',points_DBU=[[u,turn],[u,v]])]
    seg=[s for s in seg if length(s['points_DBU'])]
    return dict(source=a,sink=b,segments=seg,
                layer_lengths_um={l:sum(length(s['points_DBU']) for s in seg if s['layer']==l)/1000 for l in ('M7','M8')},
                access_L1_um=sum(length([p['pin_point_DBU'],p['upper_point_DBU']]) for p in (a,b))/1000,
                native_landing_spacing_via_RC_qualified=False)
def routebox(s,guard=60):
    a,b=s['points_DBU'];return [min(a[0],b[0])-guard,min(a[1],b[1])-guard,max(a[0],b[0])+guard,max(a[1],b[1])+guard]
def route_rc(p,rc):
    cap=sum(n*rc[l][1] for l,n in p['layer_lengths_um'].items())+p['access_L1_um']*rc['M1'][1]
    res=sum(n*rc[l][0] for l,n in p['layer_lengths_um'].items())+p['access_L1_um']*rc['M1'][0]
    return cap,res

def construct(case,e,h,c):
    ec=e['cases'][case];hc=h['cases'][case];cc=c['cases'][case];lef=e['physical_master_templates']
    # Exact two retained source instances, selected new placement in bank gap.
    originals=[]
    for j,role in enumerate(('valid','bank')):
        v=next(s for s in ec['source_state_copies'] if s['instance'].endswith('_'+role))
        originals.append(placed(v['original_instance'],v['master'],270756,71550+j*1080,lef,'proposed_original_launch_placement'))
    sinks=[p for p in ec['placements'] if p['role']=='control_state_replica']+originals
    if len(sinks)!=10 or len({p['instance'] for p in sinks})!=10:raise ValueError('Lost source or clone endpoint')
    root=placed('matched_leaf0_root',ROOTBUF,202500,73710,lef,'new_clock_distribution')
    root2=placed('matched_leaf0_root_1',ROOTBUF,202500,73980,lef,'new_clock_distribution')
    roots=[root,root2];rp=literal(root,lef,'Y')['pin_point_DBU']
    routes=[];stations=roots[:];branches=[]
    reserved=ec['placements']+hc['placements']+[dict(v,instance=v['actual_instance']) for v in cc['source_clock_cell_slots']]+originals+roots
    gap=[0,hc['station_region_DBU'][1],cc['outline_DBU'][2],hc['station_region_DBU'][3]]
    allowed=[gap]+[v['region_DBU'] for v in ec['strips']]
    def fits(item):
        a=item['bbox_DBU'];return any(a[0]>=b[0] and a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3] for b in allowed)
    # Exactly six levels on all ten branches. Coordinate interpolation sizes
    # this one tree, not a geometry/parameter sweep. Padding is explicit wire.
    for j,sink in enumerate(sinks):
        target=literal(sink,lef,'CLK');tp=target['pin_point_DBU']; chain=[];prev=literal(roots[j//5],lef,'Y')
        for k in range(6):
            local_x=54*round((tp[0]+3834)/54)
            gap_y=71550+270*j
            if k<3:
                x=54*round((rp[0]+(k+1)/3*(local_x-rp[0]))/54);y=gap_y
            else:
                x=local_x;y=270*round((gap_y+(k-2)/4*(tp[1]-gap_y))/270)
            item=placed(f'leaf0_b{j}_l{k}',BUF,x,y,lef,'new_clock_distribution')
            # First free native row in the fixed reserved gap/strip. This is
            # body legalization of one tree, not a count/depth/timing sweep.
            start_y=y
            while not fits(item) or any(overlap(item['bbox_DBU'],v['bbox_DBU']) for v in reserved):
                y+=270
                if y-start_y>10800:raise ValueError('No legal body row in fixed source reservation')
                item=placed(f'leaf0_b{j}_l{k}',BUF,x,y,lef,'new_clock_distribution')
            reserved.append(item);stations.append(item)
            p=path(prev,literal(item,lef,'A'),extra=64*(j+1));p.update(net=f'leaf0_b{j}_l{k}',shared_root_output=(k==0));routes.append(p);chain.append(p)
            prev=literal(item,lef,'Y')
        last=path(prev,target,extra=64*(j+1));last.update(net=f'leaf0_b{j}_terminal',shared_root_output=False);routes.append(last);chain.append(last)
        branches.append(dict(sink=sink,paths=chain,buffer_levels=6,root_group=j//5))
    obstacles=cc['expanded_source_PDN_rectangles']+cc['source_via_enclosures_near_cut']
    pg=[];d_conflicts=[];cross=[]
    for p in routes:
        for s in p['segments']:
            for o in obstacles:
                if s['layer']==o['layer'] and overlap(routebox(s),o['bbox_DBU']):pg.append(dict(net=p['net'],segment=s,obstacle=o))
            for d in hc['D_distribution_paths']:
                for q in d['route_segments']:
                    if q['layer']==s['layer'] and overlap(routebox(s),routebox(q)):d_conflicts.append(dict(clock_net=p['net'],D_net=d['role'],clock_segment=s,D_segment=q))
    for i,a in enumerate(routes):
        for b in routes[i+1:]:
            if a['shared_root_output'] and b['shared_root_output'] and a['net'].split('_')[1][1:].isdigit() and int(a['net'].split('_')[1][1:])//5==int(b['net'].split('_')[1][1:])//5:continue
            for s in a['segments']:
                for t in b['segments']:
                    if s['layer']==t['layer'] and overlap(routebox(s),routebox(t)):cross.append(dict(a=a['net'],b=b['net'],layer=s['layer']))
    existing=ec['placements']+hc['placements']+[dict(v,instance=v['actual_instance']) for v in cc['source_clock_cell_slots']]
    collisions=[]
    for i,p in enumerate(stations+originals):
        for q in existing+(stations+originals)[i+1:]:
            if p['instance']!=q['instance'] and overlap(p['bbox_DBU'],q['bbox_DBU']):collisions.append([p['instance'],q['instance']])
    # Original QN->HB1 is a separate constraint from equal-clock branches.
    producer=[]
    for orig,role in zip(originals,('valid','bank')):
        q=literal(orig,lef,'QN'); hb=next(p for p in hc['placements'] if p['instance']==f'D_{role}_HB1')
        a=literal(hb,lef,'A');dist=length([q['pin_point_DBU'],a['pin_point_DBU']])/1000
        producer.append(dict(role=role,source=q,sink=a,L1_um=dist,within_original_other_wire_1um=(dist<=1),existing_bank_inverter_location_unbound=(role=='bank')))
    timings={};rc=e['layer_RC_kohm_fF_per_um']
    for corner in ('ss','ff'):
        lib=cell_bodies(corner);pm=pin_models(lib);scenarios=[]
        for edge in ('rise','fall'):
            for common in (5,10,20,40,80,160,320):
                initial_load=[sum(pm[BUF]['A']['max_cap_fF']+route_rc(b['paths'][0],rc)[0] for b in branches if b['root_group']==g) for g in (0,1)]
                rdelay=lookup(lib[ROOTBUF],'A','cell_'+edge,common,max(initial_load))
                rslew=lookup(lib[ROOTBUF],'A',edge+'_transition',common,max(initial_load))
                if rdelay['extrapolation'] or rslew['extrapolation']:raise ValueError('Root LUT extrapolation')
                results=[]
                for b in branches:
                    g=b['root_group'];rd=lookup(lib[ROOTBUF],'A','cell_'+edge,common,initial_load[g]);ss=lookup(lib[ROOTBUF],'A',edge+'_transition',common,initial_load[g])
                    delay=rd['value_ps'];sl=ss['value_ps'];maximum=sl
                    for k,p in enumerate(b['paths']):
                        cap,res=route_rc(p,rc); sinkcap=pm[BUF]['A']['max_cap_fF'] if k<6 else pm[b['sink']['master']]['CLK']['max_cap_fF']
                        loadcap=initial_load[b['root_group']] if k==0 else cap+sinkcap
                        wire=res*loadcap
                        delay+=wire;sl+=math.log(10)*wire;maximum=max(maximum,sl)
                        if k<6:
                            # Initial root arc drives the entire shared union;
                            # every later arc drives its single named next net.
                            nextp=b['paths'][k+1];nc,nr=route_rc(nextp,rc)
                            nextcap=nc+(pm[BUF]['A']['max_cap_fF'] if k+1<6 else pm[b['sink']['master']]['CLK']['max_cap_fF'])
                            lut=lookup(lib[BUF],'A','cell_'+edge,sl,nextcap);slew=lookup(lib[BUF],'A',edge+'_transition',sl,nextcap)
                            if lut['extrapolation'] or slew['extrapolation']:raise ValueError('Branch LUT extrapolation')
                            delay+=lut['value_ps'];sl=slew['value_ps'];maximum=max(maximum,sl)
                    results.append(dict(sink=b['sink']['instance'],arrival_ps=delay,max_slew_ps=maximum))
                skew=max(x['arrival_ps'] for x in results)-min(x['arrival_ps'] for x in results)
                scenarios.append(dict(edge=edge,common_input_slew_ps=common,shared_union_cap_fF=initial_load,relative_skew_ps=skew,max_slew_ps=max(x['max_slew_ps'] for x in results),sinks=results))
        timings[corner]=dict(scenarios=scenarios,worst_relative_skew_ps=max(s['relative_skew_ps'] for s in scenarios),max_slew_ps=max(s['max_slew_ps'] for s in scenarios),upstream_differential_skew_budget_ps=25-max(s['relative_skew_ps'] for s in scenarios),qualified=False,via_RC_excluded_requires_provider=True)
    # Derive an actionable reset-release interval, rather than assigning t=0.
    recovery=h['source_RESETN_constraints']['ss']['SS_recovery_with60_setup_and25_skew_ps']
    removal=h['source_RESETN_constraints']['ff']['FF_removal_with25_hold_and25_skew_ps']
    reset_sinks=[dict(instance=p['instance'],pin=literal(p,lef,'RESETN')) for p in sinks if p['master'].startswith('DFFASR')]
    clock_extent=max(z['arrival_ps'] for t in timings.values() for s in t['scenarios'] for z in s['sinks'])-min(z['arrival_ps'] for t in timings.values() for s in t['scenarios'] for z in s['sinks'])
    return dict(proposed_original_launch_placements=originals,stations=stations,branches=branches,
                body_inside_source_gap_or_capture_strips=all(fits(p) for p in stations+originals),route_PG_collisions=pg,route_D_network_conflicts=d_conflicts,distinct_clock_net_guard_conflicts=cross,cell_body_collisions=collisions,
                producer_QN_to_hold_input=producer,source_SS_FF_RC_scenarios=timings,
                corrected_hold_wire_um=sorted(set(round(n['total_wire_um'],6) for n in hc['hold_wire_constructions'])),
                reset=dict(actual_RESETN_pins=reset_sinks,source_required_recovery_ps=recovery,source_required_removal_ps=removal,
                           terminal_release_window_relative_to_previous_sink_rise_ps=[removal,2500/3-recovery],
                           reset_provider_arrival_and_slew=None,reset_route_delay_spread=None,
                           corner_clock_insertion_spread_ps=clock_extent,
                           accept_release_only_if_every_sink_in_window=True,clock_gated_release_requires_ungated_provider_protocol=True,
                           reset_release_bound=False),
                new_buffer_count=62,original_FF_new_instance_count=0,added_cycles=0,
                geometry_legal=False,physical_build_admitted=False)

def build():
    e,h,c=load(E),load(H),load(C);cases={case:construct(case,e,h,c) for case in ('q','bfcolumn')}
    # Net new bodies; already-priced WAKE,8cloneFF,hold2BUF and source FF not recharged.
    area=60*.10206+2*.4374
    return dict(schema='opentallas.dsrom.matched-leaf-clock-reset.v1',candidate=h['candidate'],
                source_hashes={str(p.relative_to(ROOT)):sha(p) for p in (E,H,C)},cases=cases,
                macro_parent_IO=dict(source=C.relative_to(ROOT).as_posix(),SS_macro_CLKQ_max_ps=c['actual_macro_timing_source']['ss']['clkQ_max_ps'],
                    capture_edges=2,lane_edges_after_capture=1,remaining_before_setup_mux_wire_skew_ps=c['actual_macro_timing_source']['constraints']['SS_data_budget_before_capture_setup_mux_wire_and_skew_ps'],
                    remaining_with_full25ps_skew_ps=c['actual_macro_timing_source']['constraints']['SS_data_budget_before_capture_setup_mux_wire_and_skew_ps']-25,
                    macro_FF_CLKQ_min_ps=c['actual_macro_timing_source']['ff']['clkQ_min_ps'],
                    macro_CE_address_SS_setup_max_ps=c['actual_macro_timing_source']['ss']['ce_in']['setup_rising']['max_ps'],
                    macro_CE_address_FF_hold_max_ps=c['actual_macro_timing_source']['ff']['ce_in']['hold_rising']['max_ps'],
                    actual_capture_setup_mux_wire_delay_ps=None,actual_macro_to_capture_clock_skew_ps=None,
                    source_bound_not_contextual_SS_FF=True),
                clock_policy=dict(period_ps=2500/3,setup_uncertainty_ps=60,hold_uncertainty_ps=25,relative_skew_limit_ps=25,slew_limit_ps=320),
                new_clock_cell_area_um2=area,conservative_new_clock_cell_reservation_per_shard_mm2=2*area*2048/1e6,
                full_leaf0_existing_sink_union_still_required=True,
                shared_leaf0_ICG_to_tree_root_route_and_drive_bound=False,
                selector_226_cycles_142_service_unchanged=True,transport_684_wire_union_placement=None,
                acknowledgment_timeout1024_FAIL_preserved=True,
                physical_build_admitted=False,SS_FF_qualified=False,full_token_latency=None,
                next_construction='Resolve emitted geometric collisions with one source-pinned legal channel assignment before clock/reset source G0. Preserve source branch count; no extra capture edge.')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
