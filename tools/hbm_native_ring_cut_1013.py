#!/usr/bin/env python3
"""Actual native-child OBS/PG cut bounds; no route or timing qualification."""
import collections, hashlib, json, math, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/arch/hbm_native_ring_cut_1013'
LAYERS={'M6':('H',.064,.016,.088),'M7':('V',.064,.016,.088),
        'M8':('H',.080,.116,.060),'M9':('V',.080,.116,.060)}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def shapes(path):
    text=path.read_text()
    if re.search(r'\b(?:POLYGON|PATH)\b',text):raise ValueError(f'unsupported LEF geometry in {path}')
    out=collections.defaultdict(list); pg=collections.Counter(); obs=collections.Counter()
    bodies=[('obs',m[1]) for m in re.finditer(r'\n\s*OBS\n(.*?)\n\s*END\s*\n',text,re.S)]
    for m in re.finditer(r'\n\s*PIN (\S+)\n(.*?)\n\s*END \1[ \t]*(?=\n|$)',text,re.S):
        bodies.append(('pg' if 'USE POWER' in m[2] or 'USE GROUND' in m[2] else 'pin',m[2]))
    for kind,body in bodies:
        layer=None
        for ln in body.splitlines():
            m=re.search(r'\bLAYER (M\d+)\s*;',ln)
            if m: layer=m[1]
            m=re.search(r'\bRECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',ln)
            if m and layer:
                out[layer].append(tuple(map(float,m.groups())))
                if kind=='pg':pg[layer]+=1
                if kind=='obs':obs[layer]+=1
    return dict(out),dict(pg),dict(obs)
def union(intervals):
    out=[]
    for a,b in sorted(intervals):
        if b<=a:continue
        if out and a<=out[-1][1]:out[-1][1]=max(b,out[-1][1])
        else:out.append([a,b])
    return out
def count_tracks(a,b,pitch,offset,blocked):
    total=max(0,math.floor((b-offset)/pitch)-math.ceil((a-offset)/pitch)+1)
    lost=0
    for lo,hi in union([(max(a,x),min(b,y)) for x,y in blocked]):
        lost+=max(0,math.floor((hi-offset)/pitch)-math.ceil((lo-offset)/pitch)+1)
    return max(0,total-lost),total

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cp=ROOT/'results/arch/hbm_native_1013/die_v12/candidate.json'
    tp=ROOT/'results/arch/hbm_native_1013/die_v12/transport_requirements.json'
    c=json.loads(cp.read_text());t=json.loads(tp.read_text());cache={};inventory=[];world=collections.defaultdict(list)
    for row in c['children']:
        x,y=row['xy_um'];w,h=row['w_um'],row['h_um'];p=row.get('view_lef')
        if p:
            if p not in cache:
                data,pg,obs=shapes(ROOT/p);cache[p]=data
                inventory.append(dict(master=row['logical_module'],path=p,sha256=sha(ROOT/p),
                                      pg_rectangles=pg,obs_rectangles=obs,
                                      protected_rectangles={ly:len(rs) for ly,rs in data.items()}))
            data=cache[p]
        else:data={f'M{k}':[(0,0,w,h)] for k in range(1,8)}
        for ly,rs in data.items():
            if ly not in LAYERS:continue
            for a,b,d,e in rs:
                if row['orientation'] in ('MY','R180'):a,d=w-d,w-a
                if row['orientation'] in ('MX','R180'):b,e=h-e,h-b
                world[ly].append((x+a,y+b,x+d,y+e))
    corridors=[
        dict(name='existing_SW_SM_column_gap',direction='V',rect=[6035.04,21.6,6177.6,10568.88]),
        dict(name='existing_SW_SM_row_gap',direction='H',rect=[21.6,2630.88,12191.04,2667.6]),
        dict(name='SW_attention_strip_over_macro',direction='V',rect=[12355.2,21.6,15955.464,9028.8]),
        dict(name='W_attention_VM_full_height',direction='V',rect=[12355.2,21.6,15955.464,25958.928]),
        dict(name='E_attention_VM_full_height',direction='V',rect=[28847.232,21.6,32447.496,25958.928]),
        dict(name='SW_reserved_service_band_1000',direction='H',rect=[21.6,11821.6,32962.688,12821.6]),
        dict(name='SW_reserved_service_band_1100',direction='H',rect=[21.6,11721.6,32962.688,12821.6]),
        dict(name='NW_reserved_service_band_1100',direction='H',rect=[21.6,24703.2,32962.688,25803.2]),
        dict(name='NW_reserved_service_band_1000',direction='H',rect=[21.6,24803.2,32962.688,25803.2]),
    ]
    reports=[]
    for r in corridors:
        d=r['direction'];x0,y0,x1,y1=r['rect'];axis=0 if d=='V' else 1
        a,b=(x0,x1) if axis==0 else (y0,y1);lo,hi=(y0,y1) if axis==0 else (x0,x1)
        rec=dict(r,layers={})
        for ly,(direction,pitch,offset,halo) in LAYERS.items():
            if direction!=d:continue
            intervals=[];hits=0
            for z in world[ly]:
                if z[1-axis]<hi and z[3-axis]>lo and z[axis]<b and z[axis+2]>a:
                    hits+=1;intervals.append((z[axis]-halo,z[axis+2]+halo))
            free,total=count_tracks(a,b,pitch,offset,intervals)
            # PDN pilot recipe is conditional: no native whole-die PG/via export exists.
            if ly in ('M7','M8','M9'):
                half_exclusion=.36 if ly=='M7' else .30
                pg=[]
                for netphase in (2.16,2.16+4.896/2):
                    for k in range(math.floor((a-netphase)/4.896)-1,math.ceil((b-netphase)/4.896)+1):
                        centre=netphase+k*4.896;pg.append((centre-half_exclusion,centre+half_exclusion))
                withpg,_=count_tracks(a,b,pitch,offset,intervals+pg)
            else:withpg=None
            rec['layers'][ly]=dict(total_tracks=total,protected_shapes_intersecting=hits,
                continuous_straight_tracks_after_child_geometry=free,
                bits_at_55pct_after_child_geometry=math.floor(free*.55),
                conditional_pilot_pg_tracks=withpg,
                conditional_pilot_pg_bits_at_55pct=None if withpg is None else math.floor(withpg*.55),
                native_die_pg_vias_missing=True)
        reports.append(rec)
    pairs={}
    for link in t['ring_links']:
        edge=tuple(sorted((link['source_sid'],link['target_sid'])))
        pairs[edge]=pairs.get(edge,0)+link['forward_bits']+link['reverse_credit_bits']
    sidq={sid:q for q,sid in t['quarter_to_sid_candidate'].items()}
    qxy={r['instance'].removeprefix('hb_vms_'):r['xy_um'] for r in c['component_regions'] if r['component']=='vm'}
    cuts=[]
    for axis,pos in [(0,c['die_um'][0]/2),(1,c['die_um'][1]/2)]:
        crossing=[(edge,bits) for edge,bits in pairs.items() if (qxy[sidq[edge[0]]][axis]-pos)*(qxy[sidq[edge[1]]][axis]-pos)<0]
        bits=sum(v for _,v in crossing)
        cuts.append(dict(axis='x' if axis==0 else 'y',position_um=pos,paired_edges=crossing,
                         signal_bits=bits,usable_tracks_at_55pct=math.ceil(bits/.55),
                         excludes_clock_reset_and_other_clients=True))
    rp=ROOT/'physical/ref_tile/vms_rstop/views/ot_vms_rstop/ot_vms_rstop.lef'
    endpoint={};text=rp.read_text()
    for m in re.finditer(r'\n\s*PIN (\S+)\n(.*?)\n\s*END \1[ \t]*(?=\n|$)',text,re.S):
        name,body=m.groups();base=re.sub(r'\[\d+\]$','',name)
        if base not in ('l_in','l_out','l_in_cr','l_out_cr'):continue
        d=re.search(r'DIRECTION (\S+)',body)[1];ly=re.search(r'LAYER (M\d+)',body)[1]
        z=tuple(map(float,re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',body).groups()))
        e=endpoint.setdefault(base,dict(direction=d,bit_count=0,layers={},bbox=[1e9,1e9,-1e9,-1e9]))
        e['bit_count']+=1;e['layers'][ly]=e['layers'].get(ly,0)+1
        e['bbox']=[min(e['bbox'][0],z[0]),min(e['bbox'][1],z[1]),max(e['bbox'][2],z[2]),max(e['bbox'][3],z[3])]
    sizing=[]
    for bits in (4452,8904,13356,17808):
        sizing.append(dict(signal_bits=bits,usable_tracks_required=math.ceil(bits/.55),
            minimum_one_M6_or_M7_empty_width_um=round(bits*.064/.55,6),
            minimum_one_M8_or_M9_no_pg_width_um=round(bits*.080/.55,6),
            conditional_upper_only_pilot_pg_width_um=round(bits*.080/(.55*(1-2*.60/4.896)),6),
            conditional_dual_same_direction_M6_M8_or_M7_M9_width_um=round(bits/(.55*(1/.064+(1-2*.60/4.896)/.080)),6)))
    # Geometric price for the corridor proposal; not a routed path or timing result.
    from hbm_native_vm_component import leaf
    _,_,endpoint_bits,_=leaf(rp)
    children={r['logical_instance']:r for r in c['children']}
    lengths=[];ys=12271.6;yn=25253.2;xw=14155.332
    for link in t['ring_links']:
        a=children[link['source_leaf'][0]];b=children[link['target_leaf'][0]]
        if a['orientation']!='R0' or b['orientation']!='R0':raise ValueError('VM endpoint transform needs update')
        sid=link['source_sid'];target=link['target_sid'];edge=tuple(sorted((sid,target)));worst=0
        for bit in range(link['forward_bits']):
            av=[a['xy_um'][i]+endpoint_bits['l_out']['bits'][bit][i] for i in (0,1)]
            bv=[b['xy_um'][i]+endpoint_bits['l_in']['bits'][bit][i] for i in (0,1)]
            if edge==(0,1):way=[(av[0],ys),(bv[0],ys)]
            elif edge==(2,3):way=[(av[0],yn),(bv[0],yn)]
            elif edge==(1,2):way=[(av[0],ys),(xw,ys),(xw,bv[1])] if sid==1 else [(xw,av[1]),(xw,ys),(bv[0],ys)]
            else:way=[(av[0],yn),(xw,yn),(xw,bv[1])] if sid==3 else [(xw,av[1]),(xw,yn),(bv[0],yn)]
            pts=[av]+way+[bv];length=sum(abs(v[0]-u[0])+abs(v[1]-u[1]) for u,v in zip(pts,pts[1:]))
            worst=max(worst,length)
        lengths.append(dict(direction=link['direction'],source_sid=sid,target_sid=target,
            geometric_polyline_max_um=round(worst,6),
            minimum_500um_register_segments=math.ceil(worst/500),
            prior_direct_pin_minimum_relay_stages=link['minimum_flop_relay_stages_at_500um'],
            latency_pricing_pending=True,physical_route_proven=False))
    # Compatible footprint proposal on the existing die: widen every SM column gap,
    # move the second column and attention/VM right; retain child geometry/count.
    moved=[]
    for row in c['children']:
        r=dict(row);r['xy_um']=list(row['xy_um']);ns=r['component_namespace']
        if ns.startswith('hb_sm_') and int(ns.rsplit('_',1)[1])%2:r['xy_um'][0]+=508.464
        elif ns.startswith(('hb_attn_','hb_vms_')):r['xy_um'][0]+=444.528
        moved.append(r)
    from hbm_native_integration_1013 import overlaps,rect
    collisions=overlaps(moved)
    outside=[r['instance'] for r in moved if rect(r)[2]>c['die_um'][0] or rect(r)[3]>c['die_um'][1]]
    proposal=dict(name='same_die_651um_SM_column_corridor',SM_column_gap_um=651.024,
        second_SM_column_dx_um=508.464,attention_VM_dx_um=444.528,
        original_children=len(c['children']),retained_children=len(moved),
        child_overlap_count=len(collisions),outside_count=len(outside),
        M7_empty_corridor_tracks=math.floor(651.024/.064),
        M7_signal_bits_at_55pct=math.floor(651.024/.064*.55),
        one_paired_edge_fit=math.floor(651.024/.064*.55)>=4452,
        two_paired_edges_fit=math.floor(651.024/.064*.55)>=8904,
        status='footprint-compatible proposal only; fixed PHY/service/HC/VM8, seam/station and PG coverage remain open')
    bands=[r for r in corridors if r['name'].endswith('service_band_1100')]
    bandcollisions=[]
    for band in bands:
        bx=band['rect']
        for row in c['children']+c['unresolved_regions']:
            z=rect(row)
            if min(bx[2],z[2])>max(bx[0],z[0]) and min(bx[3],z[3])>max(bx[1],z[1]):
                bandcollisions.append([band['name'],row['instance']])
    allocation=dict(name='two_horizontal_bands_and_actual_M7_attention_windows',
        SID_mapping_changed=False,children_moved=False,band_child_or_HC_reservation_collisions=bandcollisions,
        southern_band_paired_edges=[[0,1],[1,2]],northern_band_paired_edges=[[2,3],[0,3]],
        W_vertical_spine_paired_edges=[[1,2],[0,3]],
        horizontal_band_signal_demand=8904,W_vertical_spine_signal_demand=8904,
        other_native_client_reservations_pending=True,native_PDN_vias_pending=True,
        qualified_transport_views_pending=True,physical_route_proven=False)
    out=dict(schema='opentallas.hbm.native_ring_cut_study.v1',
        sources={str(p.relative_to(ROOT)):sha(p) for p in (cp,tp,ROOT/'rtl/hbm_accel/generic/vm/b2/ot_vms_rstop.sv',ROOT/'tools/hbm_die_pg_assembly.py',OUT/'routing_rules.json')},
        source_tree_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        corridor_geometric_pricing=lengths,
        scope=dict(children=len(c['children']),real_LEF_refs=sum(bool(r.get('view_lef')) for r in c['children']),
                   open_footprint_refs=sum(not r.get('view_lef') for r in c['children']),native_whole_die_PDN=False,
                   candidate_missing=c['coverage']),
        actual_ringstop_ports=endpoint,
        preferred_allocation=allocation,
        typed_ring_edges=[dict(sids=edge,signal_bits=bits) for edge,bits in pairs.items()],
        global_cuts=cuts,layer_inventory=inventory,corridors=reports,sizing=sizing,proposal=proposal,
        closed=False,launch_GRT=False)
    (OUT/'study.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(global_cuts=cuts,corridors=reports,proposal=proposal),indent=2))
if __name__=='__main__':main()
