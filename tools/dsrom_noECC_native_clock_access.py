#!/usr/bin/env python3
"""Native clock access construction using frozen LEF and literal setRC.

Area-equivalent metal capacitance is an analytical screen, not extracted RC.
Original receipts/geometry are immutable; this is an additive successor.
"""
import gzip,hashlib,json,re,math
from pathlib import Path
from dsrom_noECC_hold_station_geometry import pin_rects,rect_move,center
from dsrom_noECC_enable_distribution import overlap,measure
from dsrom_noECC_liberty import cell_bodies
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_native_clock_access_20261002'
CLOCK=ROOT/'results/uarch/dsrom_noECC_strip_clock_construction_20261002/model.json'
ENABLE=ROOT/'results/uarch/dsrom_noECC_enable_distribution_20261002/model.json'
HOLD=ROOT/'results/uarch/dsrom_noECC_hold_station_geometry_20261002/model.json'
CTX=ROOT/'results/uarch/dsrom_noECC_production_context_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def union_area(rects):
    if not rects:return 0
    xs=sorted({v for r in rects for v in (r[0],r[2])});a=0
    for x,y in zip(xs,xs[1:]):
        ints=sorted((r[1],r[3]) for r in rects if r[0]<y and r[2]>x);end=None;n=0
        for lo,hi in ints:
            if end is None or lo>end:n+=hi-lo;end=hi
            elif hi>end:n+=hi-end;end=hi
        a+=(y-x)*n
    return a
def components(rects):
    pending=set(range(len(rects)));groups=[]
    while pending:
        joined={pending.pop()};changed=True
        while changed:
            changed=False
            for i in list(pending):
                if any(rects[i][0]<=rects[j][2] and rects[j][0]<=rects[i][2] and rects[i][1]<=rects[j][3] and rects[j][1]<=rects[i][3] for j in joined):
                    pending.remove(i);joined.add(i);changed=True
        groups.append([rects[i] for i in joined])
    return groups

def nearest(v,o,p):return o+p*round((v-o)/p)
def move(r,x,y):return [r[0]+x,r[1]+y,r[2]+x,r[3]+y]
def wire(a,b,w):
    if a[0]!=b[0] and a[1]!=b[1]:raise ValueError('Non-Manhattan wire')
    return [min(a[0],b[0])-w//2,min(a[1],b[1])-w//2,max(a[0],b[0])+w//2,max(a[1],b[1])+w//2]
def parse_rc(text):
    layers={};vias={}
    for line in text.splitlines():
        fields=line.split()
        if fields[:2]!=['set_layer_rc','-layer'] and fields[:2]!=['set_layer_rc','-via']:continue
        if fields[1]=='-layer':layers[fields[2]]=[float(fields[4]),float(fields[6])]
        else:vias[fields[2]]=float(fields[4])
    if len(layers)!=9 or len(vias)!=9:raise ValueError('Incomplete source RC')
    return layers,vias

def build():
    old=json.loads(CLOCK.read_text());e=json.loads(ENABLE.read_text());h=json.loads(HOLD.read_text());cuts=json.loads((CTX/'local_cuts.json').read_text());lef=e['physical_master_templates']
    rcpath=CTX/'inputs/setRC.tcl';rc,vr=parse_rc(rcpath.read_text());tech=gzip.decompress((CTX/'inputs/tech.lef.gz').read_bytes()).decode();width={};minarea={};direction={}
    for l in rc:
        body=re.search(r'^LAYER '+l+r'\n(.*?)^END '+l,tech,re.M|re.S)[1];body=re.sub(r'#[^\n]*','',body)
        width[l]=round(float(re.search(r'\bWIDTH\s+(\S+)\s*;',body)[1])*1000);minarea[l]=round(float(re.search(r'\bAREA\s+(\S+)\s*;',body)[1])*1e6);direction[l]=re.search(r'\bDIRECTION\s+(\w+)',body)[1]
    vt=h['physical_native_via_templates'];libs={k:cell_bodies(k) for k in ('ss','ff')};cases={}
    for case,c in old['cases'].items():
        placements=e['cases'][case]['placements']+h['cases'][case]['placements']+c['new_clock_buffer_placements']+c['retained_original_scalar_placements'];pd={v['instance']:v for v in placements}
        # Only a construction-level OBS screen; all translated source cell
        # OBS and PG rectangles are retained, not a uniform reserve.
        obs={l:[] for l in rc}
        for p in placements:
            for r in lef[p['master']]['OBS']:
                if r['layer'] in obs:obs[r['layer']].append(dict(bbox_DBU=rect_move(r['bbox_DBU'],p),owner=p['instance'],kind='cell_OBS'))
        for r in cuts['cases'][case]['expanded_source_PDN_rectangles']+cuts['cases'][case]['source_via_enclosures_near_cut']:
            if r['layer'] in obs:obs[r['layer']].append(dict(r,kind='PG_or_existing_via'))
        result=[];all_geometry=[]
        for n in c['clock_leaf_nets']+c['clock_spine_nets']:
            endpoints=[];via_count={};metal={l:[] for l in rc};pinmetal={l:[] for l in rc};conflicts=[];landing_fails=[];minfails=[]
            target='M9' if n in c['clock_leaf_nets'] else 'M7';level=int(target[1:])
            trunk=n['segments'][0]['points_DBU'];tx=trunk[0][0];ty=trunk[0][1]
            for endpoint in [n['source']]+n['sinks']:
                item=pd[endpoint['instance']];candidates=[]
                for pr in pin_rects(item,lef[item['master']],endpoint['pin']):
                    if pr['layer']!='M1':continue
                    r=pr['bbox_DBU'];x=(r[0]+r[2])//2
                    for offset in (81,117,153,189):
                        y=item['bbox_DBU'][1]+offset
                        lower=move(vt['VIA12'][0]['bbox_DBU'],x,y)
                        if not (r[0]<=lower[0] and r[1]<=lower[1] and r[2]>=lower[2] and r[3]>=lower[3]):continue
                        x3=nearest(x,9,36)
                        probe=[move(v['bbox_DBU'],x,y) for v in vt['VIA12'] if v['layer']=='M2']+[move(v['bbox_DBU'],x3,y) for v in vt['VIA23'] if v['layer']=='M2']
                        mid=(x+x3)//2;probe.append([mid-19,y-9,mid+19,y+9])
                        if any(overlap(q,o['bbox_DBU']) for q in probe for o in obs['M2']):continue
                        candidates.append((abs(x-endpoint['point_DBU'][0])+abs(y-endpoint['point_DBU'][1]),x,y,r))
                if not candidates:raise ValueError('No OBS/PG-clear literal VIA12/VIA23 contact '+endpoint['instance'])
                _,x,y,r=min(candidates);points=[[x,y]]
                # Source pin-contact choice is mandatory geometry legalization.
                # It does not change the source pin or any clock level.
                points += [[nearest(x,9,36),y]]
                points += [[points[-1][0],nearest(y,12,48)]]
                points += [[nearest(points[-1][0],12,48),points[-1][1]]]
                want=points[-1][1];xx=points[-1][0];ycandidates={nearest(want,16,64)}
                relevant=[o['bbox_DBU'] for o in obs['M6'] if o['bbox_DBU'][0]<xx+100 and o['bbox_DBU'][2]>xx-100]
                # Source M6 width32, conservative40nm PG separation. Derive
                # nearest free track directly from blocked interval endpoints.
                for ob in relevant:
                    lo=ob[1]-56;hi=ob[3]+56
                    ycandidates.add(16+64*math.floor((lo-16)/64));ycandidates.add(16+64*math.ceil((hi-16)/64))
                free=[v for v in ycandidates if all(v<=ob[1]-56 or v>=ob[3]+56 for ob in relevant)]
                if not free:raise ValueError('No source M6 PG-clear track')
                y6=min(free,key=lambda v:(abs(v-want),v));points += [[xx,y6]]
                points += [[nearest(points[-1][0],16,64),points[-1][1]]]
                x7,y6=points[-1];y8=nearest(y6,116,80)
                if target=='M7':
                    # BUF.A and BUF.Y are distinct driven nets. The M8
                    # bridge must clear already constructed output landings.
                    low=min(x7,tx)-100;high=max(x7,tx)+100
                    blocked=[g['bbox_DBU'] for g in all_geometry if g['layer']=='M8' and g['net']!=n['name'] and g['bbox_DBU'][0]<high and g['bbox_DBU'][2]>low]
                    for ob in obs['M8']:
                        if ob['bbox_DBU'][0]<high and ob['bbox_DBU'][2]>low:blocked.append(ob['bbox_DBU'])
                    candidates={y8}
                    for bb in blocked:
                        candidates.add(116+80*math.floor((bb[1]-60-116)/80));candidates.add(116+80*math.ceil((bb[3]+60-116)/80))
                    free=[v for v in candidates if all(v<=bb[1]-60 or v>=bb[3]+60 for bb in blocked)]
                    if not free:raise ValueError('No M8 distinct-clock-net bridge track')
                    y8=min(free,key=lambda v:(abs(v-y6),v))
                points += [[x7,y8]]
                if target=='M9':
                    points += [[nearest(points[-1][0],116,80),points[-1][1]]]
                else:
                    # Lift to M8, bridge horizontally, then return to the
                    # M7 trunk using a second VIA78, charged explicitly.
                    points += [[tx,points[-1][1]]]
                own={l:[] for l in rc};vrecords=[];wire_records=[]
                for j,pt in enumerate(points):
                    name='VIA'+str(j+1)+str(j+2) if j<7 or target=='M9' else 'VIA78'
                    # M7 spine endpoint has VIA12..VIA78 plus return VIA78.
                    if target=='M7' and j==7:name='VIA78'
                    cut='V'+str(7 if target=='M7' and j==7 else j+1);via_count[cut]=via_count.get(cut,0)+1
                    vrecords.append(dict(master=name,center_DBU=pt,cut=cut))
                    for plate in vt[name]:
                        if plate['layer'] in own:own[plate['layer']].append(move(plate['bbox_DBU'],*pt))
                    if j:
                        l='M'+str(j+1)
                        if target=='M7' and j==7:l='M8'
                        rr=wire(points[j-1],pt,width[l]);own[l].append(rr);wire_records.append(dict(layer=l,bbox_DBU=rr))
                if target=='M9':
                    rr=wire(points[-1],[points[-1][0],ty],width['M9']);own['M9'].append(rr);wire_records.append(dict(layer='M9',bbox_DBU=rr))
                if target=='M7':
                    end=[tx,min(max(points[-1][1],trunk[0][1]),trunk[1][1])]
                    rr=wire(points[-1],end,width['M7']);own['M7'].append(rr);wire_records.append(dict(layer='M7',bbox_DBU=rr))
                else:
                    end=[min(max(points[-1][0],trunk[0][0]),trunk[1][0]),ty]
                    rr=wire([points[-1][0],ty],end,width['M9']);own['M9'].append(rr);wire_records.append(dict(layer='M9',bbox_DBU=rr))
                # Native min-area additions are real metal. Fixed preferred
                # direction extensions are emitted and checked, not ignored.
                extensions=[]
                for l,rs in own.items():
                    if not rs:continue
                    for comp in components(rs[:]):
                        if union_area(comp)>=minarea[l]:continue
                        # Min area applies per connected polygon on each
                        # layer, not the sum of disconnected via islands.
                        anchor=center(comp[0]);long=math.ceil(minarea[l]/width[l])
                        if direction[l]=='VERTICAL':rr=[anchor[0]-width[l]//2,anchor[1]-long//2,anchor[0]+width[l]//2,anchor[1]+math.ceil(long/2)]
                        else:rr=[anchor[0]-long//2,anchor[1]-width[l]//2,anchor[0]+math.ceil(long/2),anchor[1]+width[l]//2]
                        rs.append(rr);extensions.append(dict(layer=l,bbox_DBU=rr))
                    if any(union_area(comp)<minarea[l] for comp in components(rs)):minfails.append(dict(instance=item['instance'],pin=endpoint['pin'],layer=l))
                    for rr in rs:
                        for o in obs[l]:
                            if overlap(rr,o['bbox_DBU']):conflicts.append(dict(instance=item['instance'],pin=endpoint['pin'],layer=l,metal_bbox_DBU=rr,obstacle=o))
                    metal[l]+=rs
                for p in pin_rects(item,lef[item['master']],endpoint['pin']):
                    if p['layer'] in pinmetal:pinmetal[p['layer']].append(p['bbox_DBU'])
                lower=move(vt['VIA12'][0]['bbox_DBU'],x,y)
                contained=(r[0]<=lower[0] and r[1]<=lower[1] and r[2]>=lower[2] and r[3]>=lower[3])
                if not contained:landing_fails.append(endpoint['instance'])
                endpoints.append(dict(instance=item['instance'],pin=endpoint['pin'],native_vias=vrecords,native_join_wires=wire_records,minarea_extensions=extensions,literal_VIA12_contained=contained,chosen_literal_M1_rectangle_DBU=r,source_access_wire_R_kohm=sum(max(0,((v['bbox_DBU'][2]-v['bbox_DBU'][0])+(v['bbox_DBU'][3]-v['bbox_DBU'][1])-2*width[v['layer']]))/1000*rc[v['layer']][0] for v in wire_records)))
            for l,rs in metal.items():
                for rr in rs:all_geometry.append(dict(net=n['name'],layer=l,bbox_DBU=rr))
            for segment in n['segments']:all_geometry.append(dict(net=n['name'],layer=segment['layer'],bbox_DBU=wire(*segment['points_DBU'],width[segment['layer']])))
            # Charge only metal outside the pin-capacitance footprint and
            # existing upper wire. This does not claim EM field extraction.
            areas={};proxy=0
            for l,rs in metal.items():
                prior=pinmetal[l]+[wire(s['points_DBU'][0],s['points_DBU'][1],width[l]) for s in n['segments'] if s['layer']==l]
                added=union_area(rs+prior)-union_area(prior);a=added/1e6;cap=a/(width[l]/1000)*rc[l][1];proxy+=cap
                areas[l]=dict(native_metal_union_DBU2=union_area(rs),added_metal_after_pin_and_upper_wire_union_DBU2=added,area_equivalent_C_fF=cap)
            # Prior model used a 1fF/um M1 parser artifact for all lower
            # access. Preserve its budgets and show a literal-source column.
            literal_wire=sum(rc[l][1]*v for l,v in n['layer_wire_um'].items())+n['access_L1_um']*max(v[1] for v in rc.values())
            corners={}
            longest_via_path=sum(vr[v['cut']] for v in max(endpoints,key=lambda p:len(p['native_vias']))['native_vias']);via_R_pair=2*longest_via_path
            for corner,v in n['corners'].items():
                head=34.56-v['pin_cap_fF']-literal_wire
                actual_load=v['pin_cap_fF']+literal_wire+proxy
                mc=measure(libs[corner],'BUFx4_ASAP7_75t_R',320,actual_load)
                # Retain prior pessimistic wire R bound. Add actual series
                # cut R twice to cover driver and receiver access stacks.
                old_baseR=v['wire_RC_upper_ps']/v['total_cap_before_native_vias_fF']
                actual_access_R=endpoints[0]['source_access_wire_R_kohm']+max(p['source_access_wire_R_kohm'] for p in endpoints[1:])+n['max_path_L1_um']*max(rc[l][0] for l in n['layer_wire_um'])
                baseR=max(old_baseR,actual_access_R)
                slew=mc['slew_ps']+math.log(10)*(baseR+via_R_pair)*actual_load
                corners[corner]=dict(old_283_native_C_budget_fF=v['native_via_C_budget_fF'],old_budget_area_screen='PASS' if proxy<=v['native_via_C_budget_fF'] else 'FAIL',literal_source_wire_C_fF=literal_wire,literal_source_native_C_budget_fF=head,native_metal_area_C_proxy_fF=proxy,total_load_fF=actual_load,source_native_series_R_driver_plus_receiver_kohm=via_R_pair,loaded_source_cell=mc,output_slew_upper_with_via_R_ps=slew,source34p56_load_screen=actual_load<=34.56,slew320_screen=slew<=320)
            unique_contacts={(v['master'],*v['center_DBU']):v for ep in endpoints for v in ep['native_vias']}
            unique_counts={}
            for v in unique_contacts.values():unique_counts[v['cut']]=unique_counts.get(v['cut'],0)+1
            result.append(dict(unique_physical_via_counts=unique_counts,unique_physical_contact_count=len(unique_contacts),name=n['name'],source_target_plane=target,endpoints=endpoints,via_counts=via_count,via_cut_R_sum_over_all_contacts_kohm=sum(vr[k]*v for k,v in via_count.items()),metal_area_by_layer=areas,literal_landing_failures=landing_fails,minarea_failures=minfails,source_OBS_PG_intersection_count=len(conflicts),source_OBS_PG_intersection_examples=conflicts[:12],corners=corners,actual_extracted_C=False,inter_net_native_access_spacing_qualified=False))
        bins={};pairs=set();short_examples=[]
        for i,r in enumerate(all_geometry):
            bb=r['bbox_DBU'];keys=[(r['layer'],x,y) for x in range(bb[0]//256,(bb[2]-1)//256+1) for y in range(bb[1]//256,(bb[3]-1)//256+1)]
            prior={j for key in keys for j in bins.get(key,[])}
            for j in prior:
                other=all_geometry[j]
                if r['net']!=other['net'] and overlap(bb,other['bbox_DBU']):
                    pair=tuple(sorted((r['net'],other['net'])))
                    if pair not in pairs and len(short_examples)<12:short_examples.append(dict(a=r,b=other))
                    pairs.add(pair)
            for key in keys:bins.setdefault(key,[]).append(i)
        cases[case]=dict(raw_inter_net_short_pair_count=len(pairs),raw_inter_net_short_examples=short_examples,nets=result,native_endpoint_contact_occurrence_count=sum(sum(v['via_counts'].values()) for v in result),native_contact_count=sum(v['unique_physical_contact_count'] for v in result),native_access_endpoint_count=sum(len(v['endpoints']) for v in result),clock_area_credit_um2=0,added_buffer_or_FF_count=0,added_capture_edges=0)
    return dict(schema='opentallas.dsrom.native-clock-access.v1',candidate=old['candidate'],source_clock_model_sha256=sha(CLOCK),source_RC_sha256=sha(rcpath),source_tech_sha256=sha(CTX/'inputs/tech.lef.gz'),layer_RC_kohm_fF_per_um=rc,cut_R_kohm=vr,source_metal_width_DBU=width,source_min_metal_area_DBU2=minarea,source_native_via_templates=vt,source_parser_correction=dict(old_M1_C_fF_per_um=e['layer_RC_kohm_fF_per_um']['M1'][1],literal_M1_C_fF_per_um=rc['M1'][1],cause='Earlier [\\d.E+-]+ regex accepted prefix1 of literal1e-10; uppercase E only. No original artifact rewritten.',old_budget_retained=True),capacitance_method='Incremental union metal area / source width times source layer C. Analytical proxy, not OpenRCX extracted or coupled capacitance; cut resistance directly bound to frozen setRC.',corner_scope='Source setRC is one nominal interconnect model; SS/FF libraries separate. No extracted-corner or clock-skew credit.',cases=cases,physical_build_admitted=False,remaining=['Source-matched rootprefix/global phase and all leaf0 plus macro leaf4..7 union','Native inter-net EOL/cut-spacing and actual OBS/PG rejection remedy','Extracted/coupled RC for this actual access union and source hold/reset waveform'],old_evidence_unchanged=True)
if __name__=='__main__':
    x=build();BASE.mkdir(parents=True,exist_ok=True);(BASE/'model.json').write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:{'contacts':c['native_contact_count'],'inter_net_short_pairs':c['raw_inter_net_short_pair_count'],'OBS_PG_conflicts':sum(n['source_OBS_PG_intersection_count'] for n in c['nets']),'old_budget_FAIL_nets':sum(any(v['old_budget_area_screen']=='FAIL' for v in n['corners'].values()) for n in c['nets']),'new_load_FAIL_nets':sum(any(not v['source34p56_load_screen'] for v in n['corners'].values()) for n in c['nets']),'new_slew_FAIL_nets':sum(any(not v['slew320_screen'] for v in n['corners'].values()) for n in c['nets'])} for k,c in x['cases'].items()},indent=2))
