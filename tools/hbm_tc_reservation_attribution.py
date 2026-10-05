#!/usr/bin/env python3
"""Source-pinned geometry witness and attribution; no hardware/die adoption.

A placement witness establishes disjoint rectangles/halos only, not routability,
cell/PDN fit, timing or full-SM admission. Previous evidence is immutable.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from hbm_tc_geometry_prerequisite import (ROOT, BASE, SOURCE, SX, SY, ceilgrid,
    conflicts, lef, platform, pdn, need_span, capacity)
from hbm_tc_nested_dot_delta import selected_grid

PREV='abd91bff16eb9b927d0140f94bcb6c4d13d7b90c'
BDREV='283c3d1d9e71a3727acace329ff322ce14a928a5'
BDPATH='results/physical_abi3/asap7/chip/abstracts/ot_gpu_bd_col/ot_gpu_bd_col.lef'
OLD='results/uarch/hbm_tc_geometry_prerequisite_20261001'
DEST='results/uarch/hbm_tc_reservation_attribution_20261001'


def shelf(items, width, x0, y0, gap, per_row=None, uniform_pitch=None):
    rows=[];x=x0;y=y0;rh=0;count=0
    for name,kind,w,h in items:
        if count and ((per_row is not None and count>=per_row) or x+w>width-gap+1e-8):
            y=ceilgrid(y+rh+gap,SY);x=x0;rh=0;count=0
        if x+w>width-gap+1e-8:raise ValueError('rectangle cannot fit width')
        rows.append(dict(name=name,kind=kind,x=x,y=y,w=w,h=h))
        rh=max(rh,h);count+=1;x=ceilgrid(x+(uniform_pitch or w)+gap,SX)
    return rows,ceilgrid(y+rh+gap,SY)


def compact(tc,bd,memories,grid,width,halo):
    x=ceilgrid(halo,SX);y=ceilgrid(halo,SY);rows=[]
    t=[n for n,_,_ in grid if n.endswith('u_tc')];b=[n for n,_,_ in grid if n.endswith('u_bd')]
    def band(names,kind,sz):
        nonlocal y
        r,y=shelf([(n,kind,*sz) for n in names],width,x,y,2*halo)
        rows.extend(r)
    if not b:band(t,'failed_source_TC',tc)
    else:
        for i in range(0,32,8):
            band(b[i:i+8],'same_source_BD',bd);band(t[i:i+8],'failed_source_TC',tc)
    ms=[]
    for name,_,_ in grid:
        if name.endswith(('u_tc','u_bd')):continue
        k='small' if name.startswith('g_xm') else 'scale' if 'scale' in name else 'big'
        ms.append((name,'SRAM_'+k,*memories[k]))
    groups=[ms] if not b else [[i for i in ms if i[1]=='SRAM_small'],[i for i in ms if i[1]!='SRAM_small']]
    for group in groups:
        r,y=shelf(group,width,x,y,2*halo);rows.extend(r)
    return rows,[ceilgrid(max(r['x']+r['w'] for r in rows)+halo,SX),ceilgrid(max(r['y']+r['h'] for r in rows)+halo,SY)]


def reservation_box(model, policy, memories, layers, rails):
    # Re-evaluate precisely the predecessor's declared 8-wide procedure.
    # Independent terms can be ablated without mutating its implementation.
    m=model;L=32 if len(m['lane_predecode_cut_banks'])==32 else 16;q=L==32
    stock=m['bounded_added_overhead']['area_bound_source'];caps=m['bounded_added_overhead']['count_caps']
    area=sum(caps[k]*(stock['largest_DFF_um2'] if k=='predecode_and_alignment_FF' else stock['largest_stock_cell_um2']) for k in policy['cell_terms'])
    ann=ceilgrid(area/(policy['util']*m['failed_source_outline_um'][1]),SX) if area else 0
    tw=max(m['failed_source_outline_um'][0],m['retained_global_outline_um'][0]) if policy['legacy_TC'] else m['failed_source_outline_um'][0]
    th=max(m['failed_source_outline_um'][1],m['retained_global_outline_um'][1]) if policy['legacy_TC'] else m['failed_source_outline_um'][1]
    shape=[ceilgrid(tw+ann,SX),ceilgrid(th,SY)];halo=policy['halo'];edge=policy['edge']
    frag=32768 if q else 25216
    vterms={'fragment_slice':math.ceil(frag/8),'whole_weight_bus_on_each_spoke':2048 if q else 1088,'result_bundle_all_eight':400,'metadata':19,'whole_predecode_escape':40*L}
    hterms={'eight_unshared_weight_branches':8*max(16*L,0 if q else 532),'eight_result_bundles':400,'eight_metadata_bundles':160,'whole_predecode_escape':40*L}
    vd=sum(vterms[k] for k in policy['vterms']);hd=sum(hterms[k] for k in policy['hterms'])
    # Full policy also imposes a local two-neighbor escape bound.
    local=72*L+138 if policy['local_escape'] else 0
    vd=max(vd,local);hd=max(hd,local)
    cx=need_span(vd,'VERTICAL',layers,rails) if vd else 0;cy=need_span(hd,'HORIZONTAL',layers,rails) if hd else 0
    gx=ceilgrid(2*halo+cx,SX);gy=ceilgrid(2*halo+cy,SY)
    x0=ceilgrid(edge,SX);y=ceilgrid(edge,SY);rows=[]
    def add(n,w,h):
        nonlocal y
        x=x0
        for i in range(n):
            rows.append((x,y,w,h));x=ceilgrid(x+(shape[0] if policy['uniform_pitch'] else w)+gx,SX)
        y=ceilgrid(y+h+gy,SY)
    if q:
        for _ in range(8):add(8,*shape)
        for n in [8,8,5]:add(n,*memories['big'])
    else:
        for _ in range(4):add(8,*(150 if policy['legacy_BD'] else 104,)*2);add(8,*shape)
        for n in [8]*12+[3]:add(n,*memories['small'])
        add(5,*memories['big'])
    w=ceilgrid(max(x+w for x,y,w,h in rows)+edge+(cx+halo if policy['east_spoke'] else 0),SX)
    h=ceilgrid(max(y+h for x,y,w,h in rows)+edge,SY)
    return dict(box_um=[w,h],fits_existing_slot=w<=m['existing_slot_um'][0] and h<=m['existing_slot_um'][1],excess_um=[max(0,w-m['existing_slot_um'][0]),max(0,h-m['existing_slot_um'][1])],added_cell_area_um2=area,annex_um=ann,vertical_demand_bits=vd,horizontal_demand_bits=hd,clear_corridor_um=[cx,cy],area_um2=w*h)


def build():
    pins=[]
    def raw(rev,path):
        b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT);pins.append(dict(git=rev,path=path,sha256=hashlib.sha256(b).hexdigest()));return b
    def rec(rev,path):return json.loads(raw(rev,path))
    for p in ['tools/hbm_tc_geometry_prerequisite.py','tools/hbm_tc_nested_dot_delta.py']:
        if (ROOT/p).read_bytes()!=raw(PREV,p):raise ValueError('pinned helper changed')
    old=rec(PREV,OLD+'/model.json');pdata=rec(PREV,OLD+'/platform_source.json')
    lock=rec(BASE,'configs/pdk/asap7_physical_lock.json');layers,stock=platform(pdata,lock['toolchain']['asap7']['files'])
    rails=pdn(raw(BASE,'tools/chip_assembly/tcl/pdn_sm.tcl').decode());fp=raw(BASE,'tools/chip_assembly/floorplans.py').decode()
    bdb=raw(BDREV,BDPATH);bd=lef(bdb.decode());bdr=rec(BASE,'results/physical_abi3/asap7/gpu/w13_followup_20261001/terminal_snapshot/ot_gpu_bd_col/blocks.json')
    if hashlib.sha256(bdb).hexdigest()!=bdr['abstract']['lef']['sha256'] or bdr['git']['commit']!=SOURCE or bd['size_um']!=bdr['die_um']:raise ValueError('same-source BD identity')
    memories={k:v['size_um'] for k,v in old['memory_abstracts'].items()};out={}
    allcell=['predecode_and_alignment_FF','extra_control_two_input_cells_cap','extra_clock_buffers_cap','extra_hold_buffers_cap']
    for name,m in old['models'].items():
        q=name=='qwen';halo=6 if q else 4;slot=m['existing_slot_um'];grid=selected_grid(fp,'q' if q else 'v');tc=m['failed_source_outline_um']
        # Check source-matched failed LEF against immutable terminal receipt.
        term='results/physical_abi3/asap7/gpu/'+('w13_tc_col_terminal_20261001T2112Z' if q else 'w13_tc16_terminal_20261001T120346Z')
        macro='ot_gpu_tc_col' if q else 'ot_gpu_tc16'
        p='records/results/physical_abi3/asap7/chip/abstracts/'+macro+'/'+macro+'.lef'
        receipt=rec(BASE,term+'/receipt.json');tcb=raw(BASE,term+'/'+p)
        block=rec(BASE,term+'/records/results/physical_abi3/asap7/chip/blocks/'+macro+'.json')
        if receipt['source_git']!=SOURCE or hashlib.sha256(tcb).hexdigest()!=receipt['files'][p] or lef(tcb.decode())['size_um']!=tc:raise ValueError('failed TC identity')
        witness,box=compact(tc,bd['size_um'],memories,grid,slot[0],halo)
        if conflicts(witness,halo):raise ValueError('witness halo conflict')
        if any(box[i]>slot[i] for i in [0,1]):raise ValueError('claimed witness does not fit slot')
        legacy=[];same=[]
        for n,x,y in grid:
            kind='tc' if n.endswith('u_tc') else 'bd' if n.endswith('u_bd') else 'small' if n.startswith('g_xm') else 'scale' if 'scale' in n else 'big'
            sz=m['retained_global_outline_um'] if kind=='tc' else [150,150] if kind=='bd' else memories[kind]
            actual=tc if kind=='tc' else bd['size_um'] if kind=='bd' else memories[kind]
            legacy.append(dict(name=n,x=x,y=y,w=sz[0],h=sz[1]));same.append(dict(name=n,x=x,y=y,w=actual[0],h=actual[1]))
        macrosarea=sum(r['w']*r['h'] for r in witness);haloarea=sum((r['w']+2*halo)*(r['h']+2*halo) for r in witness)
        legacyhalo=sum((r['w']+2*halo)*(r['h']+2*halo) for r in legacy)
        full=dict(cell_terms=allcell,util=.45,legacy_TC=True,legacy_BD=True,halo=6,edge=24,uniform_pitch=True,east_spoke=True,local_escape=True,vterms=['fragment_slice','whole_weight_bus_on_each_spoke','result_bundle_all_eight','metadata','whole_predecode_escape'],hterms=['eight_unshared_weight_branches','eight_result_bundles','eight_metadata_bundles','whole_predecode_escape'])
        reproduced=reservation_box(m,full,memories,layers,rails)
        if reproduced['box_um']!=m['minimum_slot_for_declared_grid_um']:raise ValueError('predecessor reservation not reproduced')
        # One-term counterfactuals are against the exact prior upper policy;
        # neither their area differences nor order-specific marginal costs
        # should be mistaken for globally additive physical requirements.
        ablations=[]
        options=[('legacy_TC_envelope',{'legacy_TC':False}),('legacy_BD_envelope',{'legacy_BD':False}),('DS_halo_6_instead_of_4',{'halo':halo}),('edge_24_instead_of_required_halo',{'edge':halo}),('all_added_cell_annex',{'cell_terms':[]}),('uniform_TC_pitch_for_every_memory_and_BD',{'uniform_pitch':False}),('whole_local_predecode_on_every_spoke_and_row',{'vterms':full['vterms'][:-1],'hterms':full['hterms'][:-1],'local_escape':False}),('all_dedicated_signal_corridors',{'vterms':[],'hterms':[],'local_escape':False,'east_spoke':False}),('eighth_east_spoke',{'east_spoke':False})]
        for label,patch in options:
            p={**full,**patch};b=reservation_box(m,p,memories,layers,rails)
            ablations.append(dict(term=label,patch=patch,result=b,delta_box_from_full_um=[round(reproduced['box_um'][i]-b['box_um'][i],6) for i in [0,1]],marginal_area_from_full_um2=reproduced['area_um2']-b['area_um2']))
        cellterms=[]
        for k in allcell:
            p={**full,'cell_terms':[c for c in allcell if c!=k]};b=reservation_box(m,p,memories,layers,rails)
            count=m['bounded_added_overhead']['count_caps'][k];area=count*(stock['largest_DFF_um2'] if k=='predecode_and_alignment_FF' else stock['largest_stock_cell_um2'])
            cellterms.append(dict(term=k,count=count,area_cap_um2=area,annex_width_continuous_contribution_um=area/(.45*tc[1]),remove_this_term_result=b))
        sequence=[];p={**full};previous=reproduced
        for label,patch in options:
            p={**p,**patch};b=reservation_box(m,p,memories,layers,rails)
            sequence.append(dict(remove_policy_term=label,box_um=b['box_um'],delta_from_previous_um=[round(previous['box_um'][i]-b['box_um'][i],6) for i in [0,1]],fits=b['fits_existing_slot']));previous=b
        sequence.append(dict(remove_policy_term='Use actual scale SRAM, maximal memory rows and row-local pitch: explicit compact witness',box_um=box,delta_from_previous_um=[round(previous['box_um'][i]-box[i],6) for i in [0,1]],fits=all(box[i]<=slot[i] for i in [0,1])))
        physical=block['metrics'];core=physical['core_area_um2'];cell=physical['stdcell_area_um2']
        ffarea=m['bounded_added_overhead']['count_caps']['predecode_and_alignment_FF']*stock['largest_DFF_um2']
        out[name]=dict(failed_source_cell_area_accounting=dict(core_area_um2=core,routed_stdcell_area_um2=cell,unused_core_area_arithmetic_um2=core-cell,proposed_predecode_FF_stock_LEF_upper_area_um2=ffarea,FF_only_exceeds_unused_core_area=ffarea>core-cell,internal_spare_area_is_not_legal_placement_or_timing=True,annex_is_not_proven_necessary='Internal whitespace arithmetic does not force the proposed FF-only cut to enlarge the failed outline. Control/clock/hold caps,45percent annex density and west-only form factor are reservation choices. Lane coordinates/repair/clock counts and source-matched routes are needed to prove any smaller successor.'),existing_slot_um=slot,failed_source_TC_outline_um=tc,same_source_BD_outline_um=bd['size_um'] if not q else 'not instantiated',mandatory_halo_each_side_um=halo,compact_unchanged_column_placement=witness,compact_box_um=box,compact_fits_existing_slot=all(box[i]<=slot[i] for i in [0,1]),slack_um=[round(slot[i]-box[i],6) for i in [0,1]],source_grid_same_source_hard_overlaps=len(conflicts(same)),source_grid_same_source_halo_overlaps=len(conflicts(same,halo)),source_grid_legacy_hard_overlaps=len(conflicts(legacy)),source_grid_legacy_halo_overlaps=len(conflicts(legacy,halo)),corrected_hard_overlaps=0,corrected_halo_overlaps=0,macro_area_lower_bound_um2=macrosarea,contained_disjoint_halo_area_lower_bound_um2=haloarea,legacy_inventory_halo_area_um2=legacyhalo,slot_area_um2=slot[0]*slot[1],slot_area_less_macros_um2=slot[0]*slot[1]-macrosarea,slot_area_less_contained_disjoint_halos_um2=slot[0]*slot[1]-haloarea,area_bound_condition='Each full halo contained in slot and disjoint; no claim if halo clipping/overlap is permitted. Necessary condition only, not sufficient routing/packing test.',prior_channel_demand_ledger=dict(fragment_bits=32768 if q else 25216,vertical_spoke={'fragment_divided_by8':4096 if q else 3152,'whole_weight_bus_repeated_per_spoke':2048 if q else 1088,'eight_results_repeated_per_spoke':400,'metadata':19,'whole_local_cut_repeated_per_spoke':1280 if q else 640},horizontal_row={'eight_weight_branches_without_shared_net_credit':4096 if q else 4256,'eight_results':400,'eight_metadata':160,'whole_local_cut':1280 if q else 640},capacity_policy='Directional track counting + worst-phase two-rail debit +0.1um keepout +50percent remaining signal share. These policies imply widths; they do not establish actual free track availability.'),predecessor_upper_policy_reproduced=reproduced,one_term_ablations=ablations,added_cell_cap_breakdown=cellterms,ordered_policy_removal=sequence,ordered_deltas_are_path_dependent=True,geometric_witness_is_not_global_minimum=True,geometric_witness_admits_routing=False,geometric_witness_admits_failed_hardware=False,die_resize_adopted=False,token_delta='No new latency assigned to the unchanged placement witness. Failed hardware remains inadmissible. Successor retains proposed +1 TC drain; local/die route stages need endpoint-specific composition, not previous upper sensitivity as a mandatory cost.',wire_evidence='Compact clear gaps only provide geometric room: LEF M1-M6 OBS persist; no extracted occupancy or free M7-M9 tracks asserted.')
    return dict(schema='opentallas.hbm-tc-reservation-attribution.v1',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parent_evidence_git=PREV,source_git=SOURCE,pins=pins,recovered_same_source_BD=dict(git=BDREV,path=BDPATH,sha256=hashlib.sha256(bdb).hexdigest(),outline_um=bd['size_um'],record_git=bdr['git']['commit'],record_LEF_sha256=bdr['abstract']['lef']['sha256'],qualified_timing_transfer=False),models=out,failed_unchanged=old['failure_unchanged'],no_admission=True,no_die_adoption=True,conclusion='Both unchanged same-source column/memory inventories have explicit halo-clear witnesses inside existing slots. Prior non-fit is a result of declared successor and channel reservation policy, not an architectural impossibility. Legacy/global abstracts are a different inventory; never silently substitute them.',smaller_successor_evidence=[dict(term='legacy TC/BD envelope',needed='Exact source-matched LEF identity and dimensions: TC terminal LEFs and recovered104BD now bound unchanged geometry. Any successor needs its own outline model and ultimately its own abstract; failed timing does not transfer.'),dict(term='FF/control/clock/hold annex and utilization',needed='Source cut-width proof and precise primitive-cell list/areas, counted control load and clock tree fanout, localized hold endpoint inventory. Bound counts and allowed local density; do not use average FF area as a maximum or treat caps as necessary repair. Explicitly price reset/tag/first/valid alignment. New SS/FF contextual signoff remains later gate.'),dict(term='full local cut charged to every long spine/row',needed='Lane-local bank boxes and source producer/consumer edge map showing which40L bits stay local and which cross each cut. Internal locations are not present in archived LEFs. Provide each register endpoint and stage latency before eliminating global escape credit.'),dict(term='fragment/8 + full shared weights on each of eight spokes',needed='Compiler/RTL-source net identity and distinct-sink placement: Q32768 and DS25216 fragment bits, shared weight nets and subpartition identities. Count unique nets per geometric cut and actual fanout branches; model multicast buffer area/delay. SRAM2buffer service/availability and no hidden serialization, II or dependency changes.'),dict(term='row branches, 50percent signal share, worst-phase PDN debit',needed='Source-matched layer-grid origin/direction, actual OBS and PDN rail/via occupancy, ring/halo keepouts and congestion margins by channel rectangle. May use new empty-corridor reservation contracts; do not infer free tracks from LEF upper layers or transfer occupancy from another source.'),dict(term='eight-wide memory grouping/uniform pitch and24edge',needed='Explicit legal per-instance coordinates using actual SRAM shapes, source PDN ring/connection footprint and standard-cell/glue slots. Compact witness removes eight-wide uniform memory pitch but does not establish ring or glue feasibility.'),dict(term='full parent/token/die upper cost',needed='Parent compose SIMD/RF/glue with these geometry witnesses, then join actual endpoint distances to Qwen and DS complete event calendars, including four WK nested nodes; price only exposed wire-stage changes. Existing die is retained until a fully composed alternative is qualified.')])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output');ap.add_argument('--check');a=ap.parse_args();b=(json.dumps(build(),sort_keys=True,indent=2)+'\n').encode()
    if a.check:
        if Path(a.check).read_bytes()!=b:raise SystemExit('attribution reproduction mismatch')
        print('PASS attribution reproduction; no admission/die adoption; FAIL unchanged')
    elif a.output:
        p=Path(a.output)
        if p.exists():raise SystemExit('refuse evidence overwrite')
        p.write_bytes(b)
    else:print(b.decode(),end='')

if __name__=='__main__':main()
