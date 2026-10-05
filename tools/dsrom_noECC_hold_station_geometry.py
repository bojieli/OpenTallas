#!/usr/bin/env python3
"""Construct the already-priced HB2/D-root station; never emit engine RTL.

This is a pin/route construction, not a routed-DRC or timing certificate.
"""
import gzip,hashlib,json,re
from pathlib import Path
from dsrom_noECC_enable_distribution import overlap,placed,measure,domain,bound,rc
from dsrom_noECC_liberty import cell_bodies,block
from dsrom_noECC_slew_enable_diagnosis import pin_models
import math
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_hold_station_geometry_20261002'
ENABLE=ROOT/'results/uarch/dsrom_noECC_enable_distribution_20261002'
CTX=ROOT/'results/uarch/dsrom_noECC_production_context_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rect_move(rect,item):
    x,y,_,_=item['bbox_DBU'];a,b,c,d=rect;h=item['bbox_DBU'][3]-y
    return [x+a,y+(h-d if item['orientation']=='MX' else b),x+c,y+(h-b if item['orientation']=='MX' else d)]
def pin_rects(item,master,pin):
    return [dict(layer=r['layer'],bbox_DBU=rect_move(r['bbox_DBU'],item)) for p in master['pins'] if p['name']==pin for r in p['rectangles']]
def center(rect):
    a,b,c,d=rect;return [(a+c)//2,(b+d)//2]
def length(points):return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:]))
def grid(v,offset,pitch):return offset+pitch*((v-offset+pitch-1)//pitch)
def build():
    source=json.loads((ENABLE/'model.json').read_text());cuts=json.loads((CTX/'local_cuts.json').read_text());lef=source['physical_master_templates']
    techpath=CTX/'inputs/tech.lef.gz';tech=gzip.decompress(techpath.read_bytes()).decode()
    if not re.search(r'DATABASE MICRONS 1000',tech):raise ValueError('Unexpected DBU units')
    m2_block=re.search(r'^LAYER M2\n(.*?)^END M2',tech,re.M|re.S)[1]
    m2_min=re.search(r'MINSIZE\s+([\d.]+)\s+([\d.]+)',re.sub(r'#[^\n]*','',m2_block))
    if tuple(round(float(v)*1000) for v in m2_min.groups())!=(37,18):raise ValueError('Source M2 landing minimum changed')
    vias={}
    for m in re.finditer(r'^VIA (VIA\d+) Default\n(.*?)^END \1',tech,re.M|re.S):
        rectangles=[];layer=None
        for line in m[2].splitlines():
            if 'LAYER ' in line:layer=line.split()[1]
            if 'RECT ' in line:rectangles.append(dict(layer=layer,bbox_DBU=[round(float(x)*1000) for x in line.split()[1:5]]))
        vias[m[1]]=rectangles
    out={};libs={c:cell_bodies(c) for c in ("ss","ff")};pm={c:pin_models(lib) for c,lib in libs.items()};layer_rc=source["layer_RC_kohm_fF_per_um"]
    for case,c in source['cases'].items():
        regions={(v['MB'],v['bank']):v['region_DBU'] for v in c['strips']};x0=regions[1,0][0];bottom=regions[1,0][3];top=regions[1,1][1]
        station_region=[x0,bottom,x0+4320,top];station=[];paths=[];pinmanifest=[];exclusions=[];holdnets=[]
        # Fixed sites inside the actual 8.64um bank gap, not an NP/count sweep.
        # The root midpoint keeps both remote source-to-sink paths below200um.
        for j,d in enumerate(c['proposed_D_distribution']):
            role=d['role'];y=grid((bottom+top)//2,0,270)+j*1080
            for tag,master,xx,yy in [('HB1','BUFx4_ASAP7_75t_R',x0+54,y),('HB2','BUFx4_ASAP7_75t_R',x0+54,y+270),('root','BUFx24_ASAP7_75t_R',x0+540,y+540)]:
                station.append(placed('D_'+role+'_'+tag,master,xx,yy,lef,'already_priced_D_distribution'))
        for d in c['proposed_D_distribution']:
            role=d['role'];nodes={tag:next(p for p in station if p['instance']=='D_'+role+'_'+tag) for tag in ('HB1','HB2','root')}
            for name,start,end,passes,span in [('H1',nodes['HB1'],nodes['HB2'],5,3600),('H2',nodes['HB2'],nodes['root'],3,1800)]:
                def literal_access(item,pin):
                    rect=next(r for r in pin_rects(item,lef[item['master']],pin) if r['layer']=='M1' and r['bbox_DBU'][3]-r['bbox_DBU'][1]>100)
                    # A native M2 horizontal track through the literal pin;
                    # VIA12 at the pin and VIA23 at the native M3 x track.
                    b=rect['bbox_DBU'];x=(b[0]+b[2])//2
                    ys=[item['bbox_DBU'][1]+z for z in (81,117,153,189) if b[1]+11<=item['bbox_DBU'][1]+z<=b[3]-11]
                    y=ys[len(ys)//2];m2=[x,y];m3=[grid(x,9,36),y]
                    stub=abs(m2[0]-m3[0]);extension=max(0,37-(28+stub))
                    return dict(instance=item['instance'],pin=pin,literal_pin=rect,VIA12_point_DBU=m2,VIA23_point_DBU=m3,M2_stub_DBU=stub,M2_minarea_extension_DBU=extension,M2_minimum_landing_union_length_DBU=28+stub+extension)
                a=literal_access(start,'Y');b=literal_access(end,'A');pt=a['VIA23_point_DBU'];bx,by=b['VIA23_point_DBU'];sy=grid(pt[1],9,36);xs=pt[0];xe=xs+span;segments=[]
                if sy!=pt[1]:segments.append([pt,[xs,sy]])
                # Connected union: final return retraces the final pass. Merge
                # it, rather than counting the same physical wire twice.
                for z in range(passes):
                    y=sy+z*108;left=min(xs,bx) if z==passes-1 else xs
                    segments.append([[left,y],[xe,y]])
                    if z<passes-1:
                        x=xe if z%2==0 else xs;segments.append([[x,y],[x,y+108]])
                ey=sy+(passes-1)*108
                if ey!=by:segments.append([[bx,min(ey,by)],[bx,max(ey,by)]])
                total3=sum(length(v) for v in segments);total2=sum(z['M2_stub_DBU']+z['M2_minarea_extension_DBU'] for z in (a,b))
                holdnets.append(dict(role=role,net=name,source=a,sink=b,M3_segments_DBU=segments,M3_wire_um=total3/1000,M2_wire_um=total2/1000,total_wire_um=(total3+total2)/1000,frozen_nominal_wire_um=18.432 if name=='H1' else 5.4,frozen_nominal_wire_upper_violated=(total3+total2)>(18432 if name=='H1' else 5400),native_via_landing_union_legalized=False))
        landing_checks=[]
        for net in holdnets:
            for access in (net['source'],net['sink']):
                item=next(p for p in station if p['instance']==access['instance']);records=[];conflicts=[]
                for via,pointkey in [('VIA12','VIA12_point_DBU'),('VIA23','VIA23_point_DBU')]:
                    xx,yy=access[pointkey]
                    for v in vias[via]:
                        a,b,cx,dy=v['bbox_DBU'];r=dict(via=via,layer=v['layer'],bbox_DBU=[xx+a,yy+b,xx+cx,yy+dy]);records.append(r)
                        for obs in lef[item['master']]['OBS']:
                            if obs['layer']==r['layer'] and overlap(r['bbox_DBU'],rect_move(obs['bbox_DBU'],item)):conflicts.append(dict(kind='own_source_OBS',obstacle=obs,via_rectangle=r))
                        for obs in cuts['cases'][case]['expanded_source_PDN_rectangles']+cuts['cases'][case]['source_via_enclosures_near_cut']:
                            if obs['layer']==r['layer'] and overlap(r['bbox_DBU'],obs['bbox_DBU']):conflicts.append(dict(kind='source_PG_or_via',obstacle=obs,via_rectangle=r))
                lower=next(v['bbox_DBU'] for v in records if v['via']=='VIA12' and v['layer']=='M1');pin=access['literal_pin']['bbox_DBU']
                contained=all((lower[0]>=pin[0],lower[1]>=pin[1],lower[2]<=pin[2],lower[3]<=pin[3]))
                landing_checks.append(dict(instance=access['instance'],pin=access['pin'],native_via_rectangles=records,literal_M1_landing_contained=contained,OBS_PG_intersection_failures=conflicts,M2_minimum_landing_union_length_DBU=access['M2_minimum_landing_union_length_DBU'],M2_minarea_extension_DBU=access['M2_minarea_extension_DBU'],EOL_spacing_cut_spacing_full_union_qualified=False))
        # Every pin is delivered as literal translated geometry. No invented
        # parent driving cell or silent off-grid/native-via legalization.
        for item in station:
            for pin in ('A','Y','VDD','VSS'):
                pinmanifest.append(dict(instance=item['instance'],pin=pin,rectangles=pin_rects(item,lef[item['master']],pin)))
        body_conflicts=[[a['instance'],b['instance']] for a in station for b in c['placements']+cuts['cases'][case]['source_clock_cell_slots'] if overlap(a['bbox_DBU'],b['bbox_DBU'])]
        body_conflicts += [[a['instance'],b['instance']] for i,a in enumerate(station) for b in station[i+1:] if overlap(a['bbox_DBU'],b['bbox_DBU'])]
        for j,d in enumerate(c['proposed_D_distribution']):
            role=d['role'];root=next(p for p in station if p['instance']=='D_'+role+'_root')
            rootpoint=center(pin_rects(root,lef[root['master']],'Y')[1]['bbox_DBU'])
            rootgrid=[grid(rootpoint[0],116,80),grid(rootpoint[1],116,80)]
            trunks={};sinks=[]
            for p in c['placements']:
                if p['role']!='control_state_replica' or not p['instance'].endswith('_'+role):continue
                r=next(r for r in pin_rects(p,lef[p['master']],'D') if r['layer']=='M1' and r['bbox_DBU'][3]-r['bbox_DBU'][1]>100)
                point=center(r['bbox_DBU']);mb=int(p['instance'].split('s')[1][0]);tx=grid(p['bbox_DBU'][0]+360+j*192,16,64);ty=grid(point[1],116,80)
                sinks.append(dict(instance=p['instance'],pin='D',literal_pin_rectangle=r,pin_point_DBU=point,upper_plane_access_DBU=[tx,ty],access_L1_DBU=abs(tx-point[0])+abs(ty-point[1])))
                trunks.setdefault(tx,[]).append(ty)
            if len(sinks)!=4 or len(trunks)!=2:raise ValueError('Lost a real replica sink')
            segments=[]
            lo=min([rootgrid[0]]+list(trunks));hi=max([rootgrid[0]]+list(trunks))
            segments.append(dict(layer='M8',points_DBU=[[lo,rootgrid[1]],[hi,rootgrid[1]]]))
            for x,ys in sorted(trunks.items()):segments.append(dict(layer='M7',points_DBU=[[x,min(ys+[rootgrid[1]])],[x,max(ys+[rootgrid[1]])]]))
            wire_DBU=sum(length(p['points_DBU']) for p in segments)+sum(s['access_L1_DBU'] for s in sinks)+length([rootpoint,rootgrid])
            longest=max(abs(rootpoint[0]-s['pin_point_DBU'][0])+abs(rootpoint[1]-s['pin_point_DBU'][1])+2*s['access_L1_DBU']+length([rootpoint,rootgrid]) for s in sinks)
            pg8=cuts['cases'][case]['expanded_source_PDN_rectangles']+cuts['cases'][case]['source_via_enclosures_near_cut']
            for p in segments:
                a,b=p['points_DBU'];bbox=[min(a[0],b[0])-60,min(a[1],b[1])-60,max(a[0],b[0])+60,max(a[1],b[1])+60]
                for obstacle in pg8:
                    if p['layer']==obstacle['layer'] and overlap(bbox,obstacle['bbox_DBU']):exclusions.append(dict(net=role,obstacle=obstacle))
            # Pin-access lift lengths are charged as L1; native via definitions
            # are archived below, but their complete landing/DRC is not presumed.
            paths.append(dict(role=role,root_instance=root['instance'],root_pin_point_DBU=rootpoint,root_upper_plane_access_DBU=rootgrid,sinks=sinks,route_segments=segments,total_L1_wire_um=wire_DBU/1000,maximum_pin_to_pin_L1_upper_um=longest/1000,total_bound_um=d['maximum_total_network_wire_um'],maximum_path_bound_um=d['maximum_source_to_replica_L1_um'],wire_bounds_screen=(wire_DBU<=400000 and longest<=200000),actual_pin_via_stack_legalized=False,hold_wires=dict(d['hold_wire_construction'],HB1='D_'+role+'_HB1',HB2='D_'+role+'_HB2',root='D_'+role+'_root',native_M3_meander_reserved=False)))
        shorts=[]
        for a in paths[0]['route_segments']:
            for b in paths[1]['route_segments']:
                def box(segment):
                    a,b=segment['points_DBU'];return [min(a[0],b[0])-60,min(a[1],b[1])-60,max(a[0],b[0])+60,max(a[1],b[1])+60]
                if a['layer']==b['layer'] and overlap(box(a),box(b)):shorts.append([a,b])
        for path in paths:
            layers={layer:sum(length(s['points_DBU']) for s in path['route_segments'] if s['layer']==layer)/1000 for layer in ('M7','M8')}
            access=(path['total_L1_wire_um']-sum(layers.values()))
            source_d=next(d for d in c['proposed_D_distribution'] if d['role']==path['role'])
            cap=max(source_d['added_D_load_SS_fF'],source_d['added_D_load_FF_fF'])+sum(layers[l]*layer_rc[l][1] for l in layers)+access*max(layer_rc[l][1] for l in ('M1','M2','M3','M4','M5','M6','M7','M8'))
            load_grid=[float(v) for v in re.search(r'index_2\s*\(\s*"([^"]+)"',libs['ss']['BUFx24_ASAP7_75t_R'])[1].split(',')]
            next_source_grid=next(v for v in load_grid if v>=cap)
            if next_source_grid!=46.08:raise ValueError('Prospective root budget no longer matches smallest covering source grid; reprice before launch')
            path.update(root_source_load_grid_fF=load_grid,smallest_covering_source_load_grid_fF=next_source_grid,actual_route_layer_lengths_um=layers,lower_access_L1_upper_um=access,prospective_root_load_budget_fF=46.08,route_and_pin_cap_upper_before_native_via_fF=cap,remaining_native_via_cap_budget_fF=46.08-cap,plane_bridge_source_via='VIA78',native_via_RC_provider_qualified=False)
        hold_timing={}
        for d in c['proposed_D_distribution']:
            role=d['role'];hn=[h for h in holdnets if h['role']==role];hold_timing[role]={}
            for corner in ('ss','ff'):
                lib=libs[corner];pins=pm[corner];old=d['SS_FF_complete_D_path'][corner];f=old['actual_predecessor_FF'];inv=old['actual_source_inverter'];wirecaps=[h['M3_wire_um']*layer_rc['M3'][1]+h['M2_wire_um']*layer_rc['M2'][1] for h in hn]
                h1=measure(lib,'BUFx4_ASAP7_75t_R',domain(inv['slew_ps']),pins['BUFx4_ASAP7_75t_R']['A']['max_cap_fF']+wirecaps[0]);wd1=(hn[0]['M3_wire_um']*layer_rc['M3'][0]+hn[0]['M2_wire_um']*layer_rc['M2'][0])*h1['load_envelope_fF']
                h2=measure(lib,'BUFx4_ASAP7_75t_R',domain(h1['slew_ps']+math.log(10)*wd1),pins['BUFx24_ASAP7_75t_R']['A']['max_cap_fF']+wirecaps[1]);wd2=(hn[1]['M3_wire_um']*layer_rc['M3'][0]+hn[1]['M2_wire_um']*layer_rc['M2'][0])*h2['load_envelope_fF']
                rb=measure(lib,'BUFx24_ASAP7_75t_R',domain(h2['slew_ps']+math.log(10)*wd2),46.08);sinkmaster=next(x['master'] for x in c['source_state_copies'] if x['instance'].endswith('_'+role));setup=old['setup_upper_ps']
                new_path=next(p for p in paths if p['role']==role)
                actual_root_wire_upper=(new_path['maximum_pin_to_pin_L1_upper_um']*max(layer_rc[l][0] for l in ('M7','M8'))+sum(s['access_L1_DBU'] for s in new_path['sinks'])/1000*layer_rc['M1'][0])*46.08
                root_slew_with_old_wire=rb['slew_ps']+math.log(10)*actual_root_wire_upper
                if domain(root_slew_with_old_wire)>320:raise ValueError('Sink slew escaped source domain')
                total=sum(x['delay_ps'] for x in (f,inv,h1,h2,rb))+wd1+wd2+actual_root_wire_upper+setup
                mindelay=sum(bound(lib[t['master']],('cell_rise','cell_fall'),t['input_slew_envelope_ps'],t['load_envelope_fF'],minimum=True,related='CLK' if t['master'].startswith('DFF') else None) for t in (f,inv,h1,h2,rb))
                hold_timing[role][corner]=dict(hold_buffers=[h1,h2],actual_geometry_wire_cap_fF=wirecaps,SS_remaining_ps=2500/3-60-25-total if corner=='ss' else None,FF_hold_remaining_ps=mindelay-old['FF_hold_upper_ps']-25-25 if corner=='ff' else None,root_output_slew_ps=rb['slew_ps'],root_input_load_budget_fF=46.08,actual_mixed_plane_wire_delay_upper_ps=actual_root_wire_upper,sink_data_slew_bound_ps=domain(root_slew_with_old_wire),frozen_root_slew_upper_ps=old['root_buffer']['slew_ps'],source_400um_L1_bound_retained=True,native_via_extra_resistance_budget_NOT_bound=True,no_qualification_transfer=True)
        pgfails=[]
        for p in station:
            for pin in ('VDD','VSS'):
                for r in pin_rects(p,lef[p['master']],pin):
                    pt=center(r['bbox_DBU'])
                    if not any(o['layer']=='M2' and o.get('net')==pin and o['bbox_DBU'][0]<=pt[0]<=o['bbox_DBU'][2] and o['bbox_DBU'][1]<=pt[1]<=o['bbox_DBU'][3] for o in cuts['cases'][case]['expanded_source_PDN_rectangles']):pgfails.append(dict(instance=p['instance'],pin=pin,point_DBU=pt))
        bounds_ok=all(p['wire_bounds_screen'] for p in paths)
        out[case]=dict(station_region_DBU=station_region,placements=station,pins=pinmanifest,existing_3422_plus_station_instance_count=len(c['placements'])+len(station),body_collisions=body_conflicts,PG_rail_projection_failures=pgfails,M8_PG_exclusion_collisions=exclusions,D_distribution_paths=paths,inter_net_same_plane_guard_conflicts=shorts,hold_wire_constructions=holdnets,hold_pin_native_landing_checks=landing_checks,endpoint_aware_hold_timing=hold_timing,frozen_nominal_hold_wire_screen="FAIL" if any(h["frozen_nominal_wire_upper_violated"] for h in holdnets) else "PASS",source_wire_envelope_screen='PASS' if bounds_ok else 'FAIL',added_cells_beyond_8d_price=0,added_capture_cycles=0,clock_reset_extra_beyond_8d=0,new_original_predecessor_placement_assumed=False)
    reset_constraints={}
    for corner,lib in libs.items():
        cell=lib['DFFASRHQNx1_ASAP7_75t_R'];pin=block(cell,re.search(r'\bpin\s*\(\s*RESETN\s*\)',cell).start())
        recovery=bound(pin,('rise_constraint','fall_constraint'),320,320,timing_type='recovery_rising');removal=bound(pin,('rise_constraint','fall_constraint'),320,320,timing_type='removal_rising')
        reset_constraints[corner]=dict(literal_RESETN_pin_sha256=hashlib.sha256(pin.encode()).hexdigest(),literal_RESETN_pin=pin,input_reset_slew_envelope_ps=320,input_clock_slew_envelope_ps=320,recovery_upper_ps=recovery,removal_upper_ps=removal,SS_recovery_with60_setup_and25_skew_ps=recovery+60+25 if corner=='ss' else None,FF_removal_with25_hold_and25_skew_ps=removal+25+25 if corner=='ff' else None,provider_reset_edges_bound=False)
    return dict(schema='opentallas.dsrom.hold-station-geometry.v1',candidate=source['candidate'],parent_main_pin='cb623dae42b378b05d6a36999ee234680021cbe0',source_enable_commit='8d6baed75d4beb596c02b10de6242b3fa43a6237',source_enable_model_sha256=sha(ENABLE/'model.json'),source_RESETN_constraints=reset_constraints,clock_constraint_scope='Existing leaf0 ICG, original valid/bank launch FF, and8 same-edge clone CLK endpoints must receive matched same-level clock branches with relative skew<=25ps and clock slew<=320ps. This is a construction constraint, not installed CTS proof.',source_tech_sha256=sha(techpath),source_cut_sha256=sha(CTX/'local_cuts.json'),DBU_per_um=1000,physical_native_via_templates=vias,cases=out,G0_physical_build_admitted=False,new_engine_RTL=False,new_PnR=False,negative_criteria=['Any cell/PG/OBS collision, native landing/spacing/grid violation, or source400/200um D-wire bound violation blocks frontend','Frozen18.432/5.4um nominal hold-wire upper bounds fail endpoint-aware connected construction; successor must consume the emitted actual layer-specific RC/timing, not the old nominal bounds. Native pin-via/spacing/EOL union remains open','Predecessor and all existing fanout sink placement must realize the source1um other-wire envelope, or compose the exact enlarged RC before launch','Eight new FF clock/reset source union must join finite leaf0 clock loads/slew<=320ps/skew<=25ps and reset recovery/removal; installed CTS is downstream','M8 pairwise net spacing, lower-layer access stacks, macro PG pin escape, source OBS and native via arrays require full union before context'])
if __name__=='__main__':
    x=build();BASE.mkdir(parents=True,exist_ok=True);(BASE/'model.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');print(json.dumps({k:dict(collisions=len(c['body_collisions']),PG_failures=len(c['PG_rail_projection_failures']),paths=[dict(role=p['role'],wire_um=p['total_L1_wire_um'],max_path_um=p['maximum_pin_to_pin_L1_upper_um'],screen=p['wire_bounds_screen']) for p in c['D_distribution_paths']]) for k,c in x['cases'].items()},indent=2))
