#!/usr/bin/env python3
"""Construct actual capture/metadata clock leaves. No RTL, CTS or P&R."""
import json, hashlib, math
from pathlib import Path
from collections import Counter
from dsrom_noECC_enable_distribution import trace, placed, overlap, measure
from dsrom_noECC_hold_station_geometry import pin_rects, center, grid, length
from dsrom_noECC_liberty import cell_bodies
from dsrom_noECC_slew_enable_diagnosis import pin_models
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_strip_clock_construction_20261002'
ENABLE=ROOT/'results/uarch/dsrom_noECC_enable_distribution_20261002/model.json'
HOLD=ROOT/'results/uarch/dsrom_noECC_hold_station_geometry_20261002/model.json'
CUT=ROOT/'results/uarch/dsrom_noECC_production_context_20261002/local_cuts.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    e=json.loads(ENABLE.read_text());h=json.loads(HOLD.read_text());cuts=json.loads(CUT.read_text())
    lef=e['physical_master_templates'];libs={c:cell_bodies(c) for c in ('ss','ff')};pins={c:pin_models(l) for c,l in libs.items()};rc=e['layer_RC_kohm_fF_per_um'];master='BUFx4_ASAP7_75t_R';out={}
    def pin(item,name):
        rect=max((v for v in pin_rects(item,lef[item['master']],name) if v['layer']=='M1'),key=lambda v:v['bbox_DBU'][3]-v['bbox_DBU'][1])
        return dict(instance=item['instance'],pin=name,master=item['master'],literal_rectangle=rect,point_DBU=center(rect['bbox_DBU']))
    for case,c in e['cases'].items():
        cs,ps,groups,mapped=trace(case);old={p['instance']:p for p in c['placements']};new=[];nets=[];spines=[];source_ff=[]
        # Seventeen groups of sixteen actual capture FF, not constant stubs.
        # All 1088 captures and all eight metadata clones use source leaf_clk[0].
        for (mb,bk),g in sorted(groups.items()):
            region=next(s['region_DBU'] for s in c['strips'] if (s['MB'],s['bank'])==(mb,bk));x=region[0]+3564
            leaves=[]
            for j in range(17):
                names=[b['FF'] for b in g[j*16:(j+1)*16]];targets=[old[n] for n in names]
                y=round(sum(p['bbox_DBU'][1] for p in targets)/len(targets)/270)*270
                buf=placed(f'capture_clock_s{mb}b{bk}_g{j}',master,x,y,lef,'source_sized_clock_leaf');new.append(buf);leaves.append(buf)
                # Metadata FF attach to the nearest capture leaf, rather than
                # creating an unmatched independent extra clock level.
                if j==8:
                    targets += [p for p in c['placements'] if p['role']=='control_state_replica' and p['instance'].startswith(f'enable_s{mb}b{bk}_')]
                src=pin(buf,'Y');sinks=[pin(p,'CLK') for p in targets]
                for s in sinks:
                    if s['instance'] in ps and ps[s['instance']]['CLK']!='leaf_clk[0]':raise ValueError('Capture belongs to different source clock')
                ytrack=grid(src['point_DBU'][1],116,80);segments=[]
                # M9 horizontal output spine plus literal lower-layer access.
                xs=[src['point_DBU'][0]]+[s['point_DBU'][0] for s in sinks]
                segments.append(dict(layer='M9',points_DBU=[[min(xs),ytrack],[max(xs),ytrack]]))
                access=sum(abs(s['point_DBU'][1]-ytrack) for s in [src]+sinks)/1000
                wire9=(max(xs)-min(xs))/1000
                net=dict(name=buf['instance']+'_Y',source=src,sinks=sinks,segments=segments,access_L1_um=access,layer_wire_um={'M9':wire9},max_path_L1_um=max(abs(src['point_DBU'][0]-s['point_DBU'][0])+abs(src['point_DBU'][1]-ytrack)+abs(s['point_DBU'][1]-ytrack) for s in sinks)/1000)
                nets.append(net)
            # Fixed bank-gap root site, with separate upper-plane x tracks.
            root=placed(f'capture_clock_s{mb}b{bk}_root',master,x,67500+bk*7830,lef,'source_sized_clock_spine');new.append(root)
            src=pin(root,'Y');sinks=[pin(v,'A') for v in leaves];tx=grid(x+540+bk*192,16,64)
            ys=[src['point_DBU'][1]]+[s['point_DBU'][1] for s in sinks]
            segments=[dict(layer='M7',points_DBU=[[tx,min(ys)],[tx,max(ys)]])]
            access=sum(abs(s['point_DBU'][0]-tx) for s in [src]+sinks)/1000
            spines.append(dict(MB=mb,bank=bk,name=root['instance']+'_Y',source=src,sinks=sinks,segments=segments,access_L1_um=access,layer_wire_um={'M7':(max(ys)-min(ys))/1000},max_path_L1_um=max(abs(src['point_DBU'][0]-tx)+abs(src['point_DBU'][1]-s['point_DBU'][1])+abs(s['point_DBU'][0]-tx) for s in sinks)/1000))
        # Relocate exact original producer and receiver FF (not additional state).
        # Their source D/CLK/reset identity is retained in the receipt.
        original_names={'q':['_276688_','_277809_','_276689_','_277261_'], 'bfcolumn':['_740188_','_741311_','_740189_','_740763_']}[case]
        for j,name in enumerate(original_names):
            p=placed(name,cs[name]['master'],274320,67500+j*540,lef,'retained_original_scalar_FF');p['source_connections']=ps[name]
            if ps[name]['CLK']!='leaf_clk[0]':raise ValueError('Original scalar phase differs')
            source_ff.append(p)
        # Original producer/receiver FF share bank0's first-level root and
        # one added real leaf, matching the two local levels of every clone.
        scalar_leaf=placed('original_scalar_clock_leaf',master,272214,69930,lef,'original_source_clock_leaf');new.append(scalar_leaf)
        src=pin(scalar_leaf,'Y');sinks=[pin(v,'CLK') for v in source_ff];yt=grid(src['point_DBU'][1],116,80)
        xs=[src['point_DBU'][0]]+[v['point_DBU'][0] for v in sinks]
        nets.append(dict(name=scalar_leaf['instance']+'_Y',source=src,sinks=sinks,segments=[dict(layer='M9',points_DBU=[[min(xs),yt],[max(xs),yt]])],access_L1_um=sum(abs(v['point_DBU'][1]-yt) for v in [src]+sinks)/1000,layer_wire_um={'M9':(max(xs)-min(xs))/1000},max_path_L1_um=max(abs(src['point_DBU'][0]-v['point_DBU'][0])+abs(src['point_DBU'][1]-yt)+abs(v['point_DBU'][1]-yt) for v in sinks)/1000))
        parent=next(v for v in spines if (v['MB'],v['bank'])==(1,0));sink=pin(scalar_leaf,'A');parent['sinks'].append(sink)
        tx=parent['segments'][0]['points_DBU'][0][0];parent['access_L1_um']+=abs(sink['point_DBU'][0]-tx)/1000
        seg=parent['segments'][0]['points_DBU'];seg[0][1]=min(seg[0][1],sink['point_DBU'][1]);seg[1][1]=max(seg[1][1],sink['point_DBU'][1]);parent['layer_wire_um']['M7']=length(seg)/1000
        parent['max_path_L1_um']=max(parent['max_path_L1_um'],(abs(parent['source']['point_DBU'][0]-tx)+abs(parent['source']['point_DBU'][1]-sink['point_DBU'][1])+abs(sink['point_DBU'][0]-tx))/1000)
        allplacements=c['placements']+h['cases'][case]['placements']+cuts['cases'][case]['source_clock_cell_slots']
        collisions=[]
        additions=new+source_ff
        for i,a in enumerate(additions):
            for b in allplacements+additions[:i]:
                if overlap(a['bbox_DBU'],b['bbox_DBU']):collisions.append([a['instance'],b.get('instance',b.get('actual_instance'))])
        pg=[]
        for item in additions:
            for pname in ('VDD','VSS'):
                for r in pin_rects(item,lef[item['master']],pname):
                    pt=center(r['bbox_DBU'])
                    if not any(v['layer']=='M2' and v.get('net')==pname and v['bbox_DBU'][0]<=pt[0]<=v['bbox_DBU'][2] and v['bbox_DBU'][1]<=pt[1]<=v['bbox_DBU'][3] for v in cuts['cases'][case]['expanded_source_PDN_rectangles']):pg.append(dict(instance=item['instance'],pin=pname,point_DBU=pt))
        for net in nets+spines:
            net['corners']={}
            for corner in ('ss','ff'):
                pin_cap=sum(pins[corner][s['master']][s['pin']]['max_cap_fF'] for s in net['sinks'])
                # Positive lower-plane access cap: worst source layer, not zero.
                wire_cap=sum(rc[l][1]*v for l,v in net['layer_wire_um'].items())+net['access_L1_um']*max(v[1] for v in rc.values())
                total=pin_cap+wire_cap
                m=measure(libs[corner],master,320,total)
                upperR=net['max_path_L1_um']*max(rc[l][0] for l in net['layer_wire_um'])+net['access_L1_um']*rc['M1'][0]
                wire_delay=upperR*total
                at_budget=measure(libs[corner],master,320,34.56)
                via_R_budget=(320-at_budget['slew_ps'])/(math.log(10)*34.56)-upperR
                net['corners'][corner]=dict(native_via_C_budget_fF=34.56-total,native_via_extra_R_budget_kohm_at_full_C_budget=via_R_budget,source_cell_at_34p56_fF=at_budget,pin_cap_fF=pin_cap,wire_cap_fF=wire_cap,total_cap_before_native_vias_fF=total,source_cell=m,wire_RC_upper_ps=wire_delay,output_slew_plus_ln10RC_ps=m['slew_ps']+math.log(10)*wire_delay,native_via_R_C_included=False)
        # Raw upper-plane exclusions, including the existing D-route union.
        wire_exclusions=[];same_layer_shorts=[]
        def box(seg):
            a,b=seg['points_DBU'];return [min(a[0],b[0])-60,min(a[1],b[1])-60,max(a[0],b[0])+60,max(a[1],b[1])+60]
        for n in nets+spines:
            for seg in n['segments']:
                bb=box(seg)
                for obs in cuts['cases'][case]['expanded_source_PDN_rectangles']+cuts['cases'][case]['source_via_enclosures_near_cut']:
                    if seg['layer']==obs['layer'] and overlap(bb,obs['bbox_DBU']):wire_exclusions.append(dict(net=n['name'],segment=seg,obstacle=obs))
                for d in h['cases'][case]['D_distribution_paths']:
                    for other in d['route_segments']:
                        if seg['layer']==other['layer'] and overlap(bb,box(other)):same_layer_shorts.append([n['name'],'D_'+d['role']])
        nn=nets+spines
        for i,n in enumerate(nn):
            for m in nn[:i]:
                for a in n['segments']:
                    for b in m['segments']:
                        if a['layer']==b['layer'] and overlap(box(a),box(b)):same_layer_shorts.append([n['name'],m['name']])
        fanouts=[]
        for f in source_ff:
            qnet=f['source_connections']['QN'];sinks=[]
            for name,p in ps.items():
                for port,net in p.items():
                    if net==qnet and name!=f['instance']:
                        sinks.append(dict(instance=name,pin=port,master=cs[name]['master'],source_pin_caps_SS_FF_fF={corner:pins[corner].get(cs[name]['master'],{}).get(port,{}).get('max_cap_fF') for corner in ('ss','ff')}))
            fanouts.append(dict(source_instance=f['instance'],QN_net=qnet,retained_sinks=sinks,all_original_D_and_QN_routes_closed=False))
        reset_items=[p for p in source_ff+c['placements'] if p['master'].startswith('DFFASR') and (p in source_ff or p['role']=='control_state_replica')]
        reset_endpoints=[pin(p,'RESETN') for p in reset_items]
        counts=Counter(s['master'] for n in nets for s in n['sinks'])
        out[case]=dict(full_retained_map_sha256=sha(mapped),clock='leaf_clk[0]',new_clock_buffer_placements=new,retained_original_scalar_placements=source_ff,clock_leaf_nets=nets,clock_spine_nets=spines,reset_literal_endpoints=reset_endpoints,source_RESETN_constraints=h['source_RESETN_constraints'],reset_waveform_provider_bound=False,clocked_capture_and_clone_counts=dict(counts),clocked_capture_and_clone_total=sum(counts.values())-4,full_source_clock_endpoint_total=sum(counts.values()),all_original_capture_count=1088,new_metadata_FF_count=8,original_scalar_FF_count=4,body_collisions=collisions,PG_rail_projection_failures=pg,upper_plane_PG_via_exclusion_intersections=wire_exclusions,upper_plane_clock_and_D_inter_net_guard_conflicts=same_layer_shorts,source_original_QN_fanout_contracts=fanouts,clock_buffer_count=len(new),clock_cell_area_um2=len(new)*lef[master]['area_um2'],clock_50pct_core_reserve_um2=2*len(new)*lef[master]['area_um2'],already_priced_single_clone_clock_leaf_cells=1,credit_against_other_Maxwell_clock_cells=0,clock_reserve_accounting='These buffers serve source leaf0 FF already included in Maxwell aggregate pin/tree floors. Conservative additional reserve is an upper allowance, not a demonstrated necessary delta: deduct/reconcile only after the whole named clock-instance union is composed. No automatic embedding credit.',incremental_conservative_clock_reserve_vs_one_leaf_um2=2*(len(new)-1)*lef[master]['area_um2'],source_original_FF_area_credit=0,matching_clock_levels_local_root_to_capture=2,source_original_scalar_clock_route_constructed=True,original_QN_and_D_other_fanouts_relocation_not_yet_closed=True,arithmetic_capture_CLK_same_source_net=True,arithmetic_capture_D_minmax_not_qualified=True,clock_slew_320_screen_before_via=all(n['corners'][k]['output_slew_plus_ln10RC_ps']<=320 for n in nets+spines for k in ('ss','ff')))
    return dict(schema='opentallas.dsrom.strip-clock-construction.v1',candidate=e['candidate'],source_enable_model_sha256=sha(ENABLE),source_hold_model_sha256=sha(HOLD),source_PG_cut_sha256=sha(CUT),DBU_per_um=1000,period_ps=2500/3,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,relative_clock_skew_budget_ps=25,added_capture_edges=0,selector_successor=dict(commit='3ea65964199521f67724386dfd59c184afe9a745',model_sha256='526b640282104e8b95a2b35dfbad6be3d12b8656b29bb10333835fe28a2830f3',new_terminal='BUFx4_ASAP7_75t_R',separate_core_reserve_delta_mm2=0.027770817600000004,element_PG_not_transferred=True),cases=out,physical_build_admitted=False,not_qualified=['Native lower-layer clock pin access/via RC/spacing and M7-M9 spine tap union','Actual ICG root prefix and matched original producer/receiver clock routes: 25ps bound not certified','Source root phase/8WAKE ICG duty cycle and all other full leaf0 endpoints','Original scalar QN/D fanout relocation wire and arithmetic capture D hold','Reset provider edge/slew waveform must meet frozen RESETN recovery/removal, not only pin capacitance'],old_failures_untouched=True)
if __name__=='__main__':
    x=build();BASE.mkdir(parents=True,exist_ok=True);(BASE/'model.json').write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:{v:c[v] for v in ('clock_buffer_count','clocked_capture_and_clone_total','body_collisions','PG_rail_projection_failures','clock_slew_320_screen_before_via','incremental_conservative_clock_reserve_vs_one_leaf_um2')} for k,c in x['cases'].items()},indent=2))
