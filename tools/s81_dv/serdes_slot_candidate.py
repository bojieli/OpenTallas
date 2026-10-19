#!/usr/bin/env python3
"""Source-pinned SerDes slot diagnostic; never changes the default planner.

Global translation preserves all relay ages. Snap real die-facing endpoints to
new slot faces and check every actual hop/band. Reticle margin is reported using
the existing policy; this tool cannot approve an outline or child implementation.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
import dv_plan as D


def candidate(original):
    p=copy.deepcopy(original)
    width,height=518.4,3844.8
    old_width=p['facts']['die_um'][0]
    bounds={}
    for link in p['links']:
        half=link['b']*.096/2+1.5
        for end in link['e']:
            name=p['blocks'][end[0]]['name']
            if name.startswith('lk_'):
                low,high=bounds.get(name,(float('inf'),float('-inf')))
                bounds[name]=(min(low,end[3]-half),max(high,end[3]+half))
    pair_top={(side,tier):(bounds[f'lk_{side}{tier}0'][1]+bounds[f'lk_{side}{tier}1'][0]-100)/2
              for side in 'WE' for tier in 'SN'}
    face_clearance=[]
    for b in p['blocks']:
        b['x']+=259.2
        if b['name'].startswith('lk_'):
            b['w'],b['h']=width,height
            if b['name'].startswith('lk_W'):b['x']=0.0
            tier=b['name'][4]
            suffix=b['name'][-1]
            if suffix not in '01':raise ValueError('copy-B extra slots need explicit six-slot repack proof')
            # 100um gap, with both actual tx/rx rows inside the real facing edge.
            top=pair_top[(b['name'][3],tier)]
            b['y']=top-height if suffix=='0' else top+100
    byidx=p['blocks']
    for l in p['links']:
        for e in l['e']:e[2]+=259.2
        for pt in l['sp']:pt[0]+=259.2
        for h in l['h']:h[0]+=259.2;h[2]+=259.2
        for side,e in enumerate(l['e']):
            b=byidx[e[0]]
            if not b['name'].startswith('lk_'):continue
            face=b['x']+b['w'] if b['name'].startswith('lk_W') else b['x']
            half=l['b']*.096/2+1.5
            clearance=min(e[3]-half-b['y'],b['y']+b['h']-e[3]-half)
            assert clearance>=0,(b['name'],e,clearance)
            face_clearance.append(clearance)
            e[2]=face
            if side==0:l['h'][0][0]=face
            else:l['h'][-1][2]=face
        l['L']=round(sum(abs(h[2]-h[0])+abs(h[3]-h[1]) for h in l['h']),2)
    p['facts']['die_um']=[round(old_width+518.4,2),25000.0]
    p['facts']['die_mm2']=(old_width+518.4)*25000/1e6
    p['facts']['reticle_margin_um']=[(D.RETICLE_W-old_width-518.4)/2,500.0]
    obj=D.Plan();obj.blocks=p['blocks'];obj.links=p['links'];obj.idx={b['name']:i for i,b in enumerate(obj.blocks)}
    bands,relays=D.lane_band_over_block(obj)
    overlaps=[]
    for i,a in enumerate(p['blocks']):
        for b in p['blocks'][i+1:]:
            if min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x'])+.001 and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+.001:
                overlaps.append([a['name'],b['name']])
    maxhop=max(abs(h[2]-h[0])+abs(h[3]-h[1]) for l in p['links'] for h in l['h'])
    changed=[a['i'] for a,b in zip(p['links'],original['links']) if a['s']!=b['s']]
    proof=dict(scope='DIAGNOSTIC_NOT_FIT_OR_CLOCK_CLOSURE',slots=sum(b['name'].startswith('lk_') for b in p['blocks']),
        slot_um=[width,height],min_data_face_band_clearance_um=min(face_clearance),array_shift_x_um=259.2,die_width_add_um=518.4,
        max_hop_um=maxhop,over_405=sum(abs(h[2]-h[0])+abs(h[3]-h[1])>405.0001 for l in p['links'] for h in l['h']),
        changed_station_ages=changed,block_overlaps=overlaps,lane_band_um=sum(bands.values()),relay_overlap_count=sum(relays.values()),
        old_reticle_margin_um=original['facts']['reticle_margin_um'],new_reticle_margin_um=p['facts']['reticle_margin_um'],
        margin_policy_um=D.RETICLE_MARGIN,margin_policy_pass=min(p['facts']['reticle_margin_um'])>=D.RETICLE_MARGIN,
        native_children_and_parent_clock='OWED: actual per-root TT/FF, reset/status and <=405um internal timed transport',
        coll_storage_successor=dict(status='prospective_not_qualified',required_um=[561.6,561.6],std_um2=7357.69494,macros=15))
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'fleet_viz'))
    import dataflow_links as DL
    def metrics(q):
        links=[dict(l,mh=max(abs(h[2]-h[0])+abs(h[3]-h[1]) for h in l['h']),
                    bu=sum(abs(h[2]-h[0])+abs(h[3]-h[1]) for h in l['h'])*l['b']) for l in q['links']]
        return DL.metrics(dict(outline=[0,0,*q['facts']['die_um']],reach_um=405,stages_explicit=True),links)
    before,after=metrics(original),metrics(p)
    proof['global_routing_metrics']={key:dict(before=before[key],after=after[key]) for key in
        ('worst_cut','over_reach_bits','relays','relay_bit_stages','sum_bit_um_hops','cut_windows_over_limit')}
    for key in ('worst_cut','over_reach_bits','relays','relay_bit_stages','cut_windows_over_limit'):
        p['facts'][key]=after[key]
    p['facts']['bit_mm']=round(after['sum_bit_um_hops']/1000)
    p['facts']['serdes_slot_candidate']=proof
    return p,proof

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    src=Path(a.plan);p,proof=candidate(json.loads(src.read_text()));out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    proof['source_plan_sha256']=hashlib.sha256(src.read_bytes()).hexdigest()
    (out/'plan.json').write_text(json.dumps(p,indent=1)+'\n');(out/'geometry.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))
