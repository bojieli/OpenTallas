"""Retained q-frame PDN extension, proposed clock cuts and endpoint budgets.

Source geometry only. Default vias are a constructive lower geometry option,
not an electrical/EM array qualification. A row-blocking bound is kept separate
from metal occupancy: metal projection must never silently remove cell capacity.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import dsrom_retained_WAKE_context_admission as C
BASE=C.G.P.ROOT/'results/uarch/dsrom_q_PDN_clock_endpoint_model_20261002'

def overlap(a,b):
    return [max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
def area(r):return max(0,r[2]-r[0])*max(0,r[3]-r[1])
def union_length(intervals):
    end=None;total=0
    for a,b in sorted(intervals):
        if b<=a:continue
        if end is None or a>end:total+=b-a;end=b
        elif b>end:total+=b-end;end=b
    return total

def union_area(rects):
    rects=[r for r in rects if area(r)]
    xs=sorted({x for r in rects for x in (r[0],r[2])})
    return sum((b-a)*union_length([(r[1],r[3]) for r in rects if r[0]<b and r[2]>a]) for a,b in zip(xs,xs[1:]))

def via_rects(tech,name):
    m=re.search(r'^VIA '+re.escape(name)+r' Default\s*$(.*?)^END '+re.escape(name)+r'\s*$',tech,re.M|re.S)
    if not m:raise ValueError('missing exact default via '+name)
    out={}
    for layer,a,b,c,d in re.findall(r'LAYER (\w+)\s*;\s*RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)\s*;',m[1]):
        out[layer]=[round(float(x)*1000) for x in (a,b,c,d)]
    return out

def stripes(width,height):
    out=[]
    for y in range(0,height,270):out.append(dict(layer='M2',rect=[0,max(0,y-9),width,min(height,y+9)]))
    for layer,d,w,sp,pitch,offset in [('M5','V',120,72,2700,300),('M6','H',288,96,5400,513),('M7','V',288,96,10800,1000)]:
        limit=width if d=='V' else height
        for origin in range(offset,limit,pitch):
            for n in (0,w+sp):
                lo=origin+n-w//2;hi=origin+n+w//2
                if lo<0 or hi>limit:continue
                out.append(dict(layer=layer,rect=[lo,0,hi,height] if d=='V' else [0,lo,width,hi]))
    return out

def phased_tracks(grid,layer,axis,lo,hi):
    # Unique source phases; count extends an existing phase, never its density.
    phases={(s,step) for g in grid['grids'] if g['layer']==layer for s,_,step in g[axis]}
    return sorted({s+i*step for s,step in phases for i in range(max(0,math.ceil((lo-s)/step)),max(0,math.ceil((hi-s)/step)))})

def build():
    inp=BASE/'inputs';origins=json.loads((inp/'origins.json').read_text())
    for n,r in origins.items():
        if hashlib.sha256((inp/n).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('input source pin '+n)
    old=C.build();geo=json.loads((C.BASE/'inputs/geometry.json').read_text())['q'];ret=json.loads((C.BASE/'inputs/model.json').read_text())['cases']['q']
    selector=json.loads((inp/'selector.json').read_text());grid=json.loads((inp/'grid.json').read_text());tech=(inp/'tech.lef').read_text()
    width,height=ret['outline_DBU'][2:];strip=ret['PG_template_growth_required_strip_DBU'];core=[276480,0,width,height]
    old_pdn=geo['source_PDN_template_rectangles'];new_pdn=stripes(width,height)
    # Template consistency is checked before extending its height.
    for l in ('M2','M5','M6','M7'):
        old_rects=[p['bbox_DBU'] for p in old_pdn if p['layer']==l]
        regenerated=[p['rect'] for p in stripes(width,strip[1]) if p['layer']==l]
        if sorted(old_rects)!=sorted(regenerated):raise ValueError('old PDN source template changed '+l)
    vias={n:via_rects(tech,n) for n in ('VIA23','VIA34','VIA45','VIA56','VIA67')}
    layers={}
    for l in ('M2','M3','M4','M5','M6','M7'):
        b=re.search(r'^LAYER '+l+r'\s*$(.*?)^END '+l+r'\s*$',tech,re.M|re.S)[1]
        layers[l]={'minimum_spacing_DBU':round(float(re.search(r'\bSPACING ([\d.]+)\s*;',b)[1])*1000)}
    # Stack VIA23/34/45 at M2 x M5 crossings; geometry only. Larger arrays
    # require their own enclosing reservation, current-carrying proof and cuts.
    envelope=[]
    for n in ('VIA23','VIA34','VIA45'):
        for l,r in vias[n].items():
            if l.startswith('M'):
                sp=layers[l]['minimum_spacing_DBU'];envelope.append([r[0]-sp,r[1]-sp,r[2]+sp,r[3]+sp])
    e=[min(r[0] for r in envelope),min(r[1] for r in envelope),max(r[2] for r in envelope),max(r[3] for r in envelope)]
    xcenters=[(p['rect'][0]+p['rect'][2])//2 for p in new_pdn if p['layer']=='M5' and core[0]<=sum(p['rect'][::2])//2<core[2]]
    # Rail centers from source template including boundaries, not stripe edge.
    ycenters=list(range(0,height,270))
    xs=[(max(core[0],x+e[0]),min(core[2],x+e[2])) for x in xcenters]
    def ys(bounds,snap):
        out=[]
        for y in ycenters:
            lo,hi=y+e[1],y+e[3]
            if snap:lo=math.floor(lo/270)*270;hi=math.ceil(hi/270)*270
            out.append((max(bounds[1],lo),min(bounds[3],hi)))
        return out
    def reservation(bounds,snap):return union_length(xs)*union_length(ys(bounds,snap))/1e6
    lower_full=reservation(core,False);upper_full=reservation(core,True)
    lower_strip=reservation(overlap(core,strip),False);upper_strip=reservation(overlap(core,strip),True)
    # Planned clock landing boxes on the real newly available compute strip.
    # Boxes reserve complete space; mapped WAKE/ICG and BUF84 floors are not
    # new instances. This policy bound intentionally gives no containment credit.
    cuts=[]
    branches=ret['SS_FF_clock_pin_loads']['ff']
    for i in range(8):
        cell=f'g_wake.g_leaf[{i}].u_cg.u_icg';net=ret['actual_ICG_cells'][cell]['connections']['GCLK'][0]
        w=5400 if i<4 else 2700;x=280800+27000*i
        box=[x,148500,x+w,150660]
        if area(overlap(box,core))!=area(box) or area(overlap(box,strip))!=area(box):raise ValueError('clock cut outside owned core strip')
        sinks=branches[str(net)];cuts.append(dict(leaf=i,ICG=cell,net=net,rect=box,source_sinks=sinks['sinks'],BUF4_floor=sinks['BUF4_capacitance_only']['cell_count'],wire_budget_at_ICG_fF=sinks['BUF4_capacitance_only']['wire_budget_at_ICG_fF'],placement='proposed constraint, not installed CTS'))
    root=[496800,148500,499500,150660]
    boxes=[x['rect'] for x in cuts]+[root]
    cut_area=union_area(boxes)/1e6
    margin=old['retained_WAKE_context']['classes']['q']['residual_after_clock_floor_at50pct_um2']
    # Incremental growth-strip policy and complete-frame counterfactual MUST
    # remain distinct. Old frame had no proven via/cell containment either.
    policy_growth=margin-upper_strip-cut_area
    policy_full=margin-upper_full-cut_area
    clock_macro_reach=[]
    for leaf in range(4,8):
        macro=geo['macro_instances'][leaf-4]
        # body corner reach bound, no invented pin placement or wire timing.
        body=macro.get('body',macro.get('body_DBU',macro.get('rect')))
        if body is None:body=list(macro['bbox_DBU'])
        b=cuts[leaf]['rect'];center=((b[0]+b[2])/2,(b[1]+b[3])/2)
        pin=next(p for p in geo['translated_macro_pin_OBS_PG'] if p.get('instance')==macro['instance'] and p.get('pin')=='clk')
        pr=pin['bbox_DBU'];pincenter=((pr[0]+pr[2])/2,(pr[1]+pr[3])/2)
        clock_macro_reach.append(dict(leaf=leaf,macro=macro,actual_macro_clock_pin=pin,planned_anchor_to_pin_L1_um=(abs(center[0]-pincenter[0])+abs(center[1]-pincenter[1]))/1000,maximum_L1_body_corner_reach_um=max(abs(center[0]-x)+abs(center[1]-y) for x in (body[0],body[2]) for y in (body[1],body[3]))/1000,not_pin_delay=True))
    upper_via_connections=[]
    for low,up,name in [('M5','M6','VIA56'),('M6','M7','VIA67')]:
        verts=[p['rect'] for p in new_pdn if p['layer'] in (low,up) and p['layer'] in ('M5','M7')]
        horizontals=[p['rect'] for p in new_pdn if p['layer']=='M6']
        full=sum(area(overlap(v,h))>0 for v in verts for h in horizontals)
        growth=sum(area(overlap(overlap(v,h),strip))>0 for v in verts for h in horizontals)
        upper_via_connections.append(dict(layers=[low,up],default_via=name,full_template_crossings=full,growth_strip_crossings=growth,metal_layers_only=True,no_automatic_cell_row_debit=True,selected_array_and_current_requirement_unbound=True))
    track_cuts=[]
    for axis,l,lo,hi in [('Y','M2',0,height),('Y','M4',0,height),('Y','M6',0,height)]:
        tr=phased_tracks(grid,l,axis,lo,hi);blocks=[p['rect'] for p in new_pdn if p['layer']==l and p['rect'][0]<=core[0]<p['rect'][2]]
        blocked=sum(any(r[1]<=t<r[3] for r in blocks) for t in tr)
        track_cuts.append(dict(layer=l,unique_phase_tracks=len(tr),PG_shadow_blocked=blocked,remaining_before_signal_vias_and_clock_escape=len(tr)-blocked))
    selcuts={}
    for name in ('horizontal_escape','vertical_escape'):
        cap=selector['tracks'][name]['signal_tracks_after_50pct_reserve'];need=selector['ports']['signal_pin_tracks']+selector['ports']['clock_reset_pins']
        selcuts[name]=dict(capacity_under_declared_50pct_policy=cap,signal=4210,clock_reset=2,remaining_for_unpriced_pin_escape=cap-need,additional_exclusions_from_existing_50pct_reserve_not_double_debited=True,physical_allocated_tracks=None)
    corridor=selector['area']['new_escape_corridor_union_mm2'];screen=old['area']['combined_noncontainment_policy_screen_mm2']+corridor
    return dict(schema='opentallas.dsrom.q-PDN-clock-endpoint.v1',candidate=old['candidate'],sourcepins=origins,
      predecessor='5cc5b1029a686446f5c726e64f94a0c993afc99c',generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      q=dict(outline_DBU=[width,height],compute_region_DBU=core,growth_strip_DBU=strip,PDN_template=new_pdn,default_via_shapes=vias,layer_minimum_spacing=layers,
        upper_PDN_connections=upper_via_connections,macro_M4_M5_power_via_array_provider_unbound=True,
        via_option=dict(stack='VIA23 -> VIA34 -> VIA45',landing_spacing_envelope_DBU=e,crossings=len(xcenters)*len(ycenters),electrical_current_array_qualification=False,source_tech_identity_needs_same_PDK_confirmation=True),
        via_exclusion=dict(metal_projection_full_core_um2=lower_full,metal_projection_new_strip_um2=lower_strip,row_blocking_full_core_policy_um2=upper_full,row_blocking_new_strip_policy_um2=upper_strip,metal_is_not_automatically_cell_blockage=True,stack_compatible_cell_PG_overlay_not_proved=True),
        branch_cuts=cuts,root_clock_cut_DBU=root,whole_cut_policy_um2=cut_area,actual_clock_master_fit_within_cuts_unproven=True,macro_clock_reach=clock_macro_reach,
        residual_um2=margin,new_strip_policy_remaining_for_hold_um2=policy_growth,full_frame_row_blocking_policy_remaining_um2=policy_full,
        full_frame_policy_nonfit_is_not_architectural_impossibility=True,source_crossing_tracks=track_cuts,
        max_additional_hold_cell_area_at50pct_if_growth_policy_sufficient_um2=max(0,policy_growth)/2,
        next_exact_provider='Arch: source-matched stdcell LEF/site rails and legal VIA23/34/45 landing overlay or bounded selected PDN arrays; eight cut master/density fit and positive hold buffer budget. Installed CTS not required.'),
      selector=dict(cuts=selcuts,corridor_union_once_mm2=corridor,slot_unchanged=selector['placement']['complete_bbox_DBU'],no_input_output_alias_credit=True,actual_endpoint_wire_delta_cycles=None,
        endpoint_contract=dict(load_B_per_accepted_edge=256,result_B_per_edge=256,input_and_output_tracks_separate=True,completion='tk_done clears DMA busy; core waits coll_busy low; result pulses synchronously write VM4; no invented ACK',shared_hub_ports_and_ready_calendar_required=True)),
      parent_IO=dict(actual_element_ports=old['retained_WAKE_context']['classes']['q']['actual_top_port_widths'],period_ps=833.3333333333334,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        actual_driver_arrival_slew_and_output_load=None,generated_clock_relationship='root + eight retained ICG outputs; no virtual-only clock credit',
        equations={'macro_capture':'2*T - 60 - macro_SS_clkq - route - capture_setup - signed_skew >= 0; FF hold uses actual launch edge', 'lane':'T - 60 - capture_clkq - mux_route - lane_setup - signed_skew >= 0', 'input':'T - 60 - actual_parent_arrival - input_route - endpoint_setup - signed_skew >= 0', 'output':'T - 60 - output_clkq - output_route - actual_parent_setup - signed_skew >= 0'},
        observed_source_edges=dict(first_CE=85,first_capture=87,first_lane=88,last_root=419,last_VM_visible=420,adapter_retire=422),
        narrow_multicycle_only='macro to matched PP capture SETUP2; corresponding source hold edge, no blanket control/data exceptions'),
      area=dict(predecessor_screen_mm2=old['area']['combined_noncontainment_policy_screen_mm2'],escape_corridor_increment_mm2=corridor,screen_with_corridor_mm2=screen,remaining_mm2=858-screen,
        all_compiled2048_sites_and8192_macros_unchanged=True,WAKE_and_BUF_floors_already_charged=True,cut_policy_no_containment_credit=True,PG_and_hold_extra_global_debit_not_yet_bound=True),
      latency=dict(new_clock_cut_pipeline_cycles=0,zero_is_placement_constraint_not_measured_closure=True,selector_added_cycles_per_position=1278,six_verify_serial_added_cycles=7668,endpoint_transport_delta_cycles=None,fulltoken_MTP_admitted=False),
      admission=dict(extended_PDN_geometry=True,eight_branch_constraint_boxes=True,installed_CTS_required_before_build=False,full_frame_legal_via_cell_overlay=False,actual_parent_IO_bound=False,selector_actual_pin_escape=False,PnR_admitted=False,RTL_changed=False,old_FAIL_preserved=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('immutable record')
    a.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
