#!/usr/bin/env python3
"""Exact FULL2417 typed frame capacity against actual die hard rectangles.

This is a constructive coarse floorplan, not a pin/cut/timing release proof.
It removes symmetric empty IO bands and explicitly re-places all six HCP homes.
"""
import argparse
import collections
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tools'))
import dsrom_s81_fulldie as G


def free_intervals(x,w,obstacles):
    intervals=[(20.,25980.)]
    for name,xx,yy,ww,hh in obstacles:
        if x>=xx+ww+20-1e-6 or x+w<=xx-20+1e-6:continue
        cut=(max(20.,yy-20),min(25980.,yy+hh+20))
        result=[]
        for a,b in intervals:
            if cut[1]<=a or cut[0]>=b:result.append((a,b));continue
            if cut[0]>a:result.append((a,cut[0]))
            if cut[1]<b:result.append((cut[1],b))
        intervals=result
    return intervals


def main():
    src=R/'results/uarch/dsrom_s81_released_binding_20261004/canonical'
    stage_path=src/'stage_map.json';inv_path=src/'inventory.json'
    stage=json.loads(stage_path.read_text());inv=json.loads(inv_path.read_text())
    bf=set(stage['BF_site_IDs']);bounds=stage['region_bounds']
    assert len(bf)==519 and len(bounds)==129 and bounds[0]==0 and bounds[-1]==2417
    assert all(bounds[r]==(r*2417)//128 for r in range(129))
    assert inv['stages']==81 and inv['pairs_per_rank_die']==2417
    assert len(stage['PHW_required_by_stage'])==81 and stage['PHW_required_by_stage'][:74]==[10]*74
    assert len(stage['rank_dies'])==81*4
    opts_path=R/'results/physical/die_iter_1012/s81/s81_layer1_jog8.opts'
    ap=argparse.ArgumentParser();ap.add_argument('mode');ap.add_argument('--k',type=int,default=16);G.die_options(ap)
    G.apply_options(ap.parse_args(['real']+shlex.split(opts_path.read_text())))
    frames=[]
    for root,(lo,hi) in enumerate(zip(bounds,bounds[1:])):
        elems,offsets,heights=G.pack_frame(range(lo,hi),bf,set())
        assert sorted(e[0] for e in elems)==list(range(lo,hi))
        frames.append(dict(root=root,pairs=[lo,hi],pair_count=hi-lo,bf=sum(p in bf for p in range(lo,hi)),
                           q=sum(p not in bf for p in range(lo,hi)),height_um=round(sum(heights),6),
                           packed_slots=len(heights),slot_offsets_um=offsets,slot_heights_um=heights,
                           packed_elements=[list(e) for e in elems]))
    assert sum(f['pair_count'] for f in frames)==2417 and sum(f['bf'] for f in frames)==519
    plan_path=R/'results/physical/die_iter_1012/s81/hcp_home_growth_1015/plan_r8c.json.gz'
    plan=json.load(gzip.open(plan_path))
    fixed=[(i[0],i[2],i[3],i[4],i[5]) for i in plan['insts'] if i[7] in ('hub','phy','ctrl','svc','svcj','band_blk','link')]
    homes=json.loads((R/'physical/s81_die_pins/v20_hcx_partition/homes.json').read_text())
    moved=[]
    for i,h in enumerate(homes['hc_projection']):
        nh=copy.deepcopy(h);nh['at_um']=[9417.6+1814.4*i,24624.];nh['outline']=dict(w=1728.,h=1296.)
        nh['qualification']='COARSE_FULL2417_CANDIDATE: native46root size/pins/cuts and physical calendar not proven'
        moved.append(nh)
    home_boxes=[(h['name'],*h['at_um'],h['outline']['w'],h['outline']['h']) for h in moved]
    def overlap(a,b):
        return a[1]<b[1]+b[3]-1e-6 and a[1]+a[3]>b[1]+1e-6 and a[2]<b[2]+b[4]-1e-6 and a[2]+a[4]>b[2]+1e-6
    home_collisions=[(a[0],b[0]) for a in home_boxes for b in fixed if overlap(a,b)]
    assert not home_collisions,home_collisions
    assert all(h[1]>=20 and h[2]>=20 and h[1]+h[3]<=32980 and h[2]+h[4]<=25980 for h in home_boxes)
    obstacles=fixed+home_boxes
    xs=sorted({r['rect'][0] for r in plan['regions'] if r.get('kind')=='field'})
    assert len(xs)==22
    cols=[]
    for x in xs:
        intervals=free_intervals(x,G.COL_W8,obstacles)
        lo,hi=max(intervals,key=lambda ab:ab[1]-ab[0])
        cols.append(dict(x_um=x,y0_um=lo,y1_um=hi,height_um=hi-lo,roots=6))
    # 132 geometrical positions,128 real roots. Spend the four empty positions
    # on the four tightest columns, preserving all immutable root/pair IDs.
    for c in sorted(cols,key=lambda c:c['height_um'])[:4]:c['roots']=5
    short=sorted([f for f in frames if f['pair_count']==18],key=lambda f:f['height_um'])
    long=sorted([f for f in frames if f['pair_count']==19],key=lambda f:-f['height_um'])
    first_gap,between=259.2,388.8
    placements=[]
    for c in sorted(cols,key=lambda c:c['height_um']-c['roots']*3594.24):
        n=c['roots'];gap=first_gap+(n-1)*between
        chosen=[]
        while len(chosen)<n:
            remain=n-len(chosen)
            if len(long)<remain and short:
                chosen.append(short.pop(0));continue
            worst=sum(f['height_um'] for f in chosen)+sum(f['height_um'] for f in long[:remain])+gap
            if worst>c['height_um']+1e-6 and short:
                chosen.append(short.pop(0))
            else:
                assert len(long)>=remain,(c,len(long),len(short))
                chosen.extend(long[:remain]);long=long[remain:];break
        assert len(chosen)==n
        y=c['y0_um']+first_gap
        for f in chosen:
            p=dict(**f,origin_um=[c['x_um'],round(y,6)],outline_um=[G.COL_W8,f['height_um']])
            placements.append(p);y+=f['height_um']+between
        assert y-between<=c['y1_um']+1e-6,(c,y-between)
    assert not long and not short,(len(long),len(short))
    assert sorted(f['root'] for f in placements)==list(range(128))
    boxes=[(f'root{f["root"]}',*f['origin_um'],*f['outline_um']) for f in placements]
    collisions=[(a[0],b[0]) for a in boxes for b in obstacles if overlap(a,b)]
    collisions +=[(a[0],b[0]) for i,a in enumerate(boxes) for b in boxes[i+1:] if overlap(a,b)]
    assert not collisions,collisions
    stage_rows=[dict(stage=i,occupied_pairs=inv['occupied_pairs_per_stage'][i],
                     physical_pair_slots_per_rank_die=2417,phase_width=stage['PHW_required_by_stage'][i]) for i in range(81)]
    hist=collections.Counter((f['pair_count'],f['bf'],f['packed_slots'],f['height_um']) for f in frames)
    report=dict(status='COARSE_FULL2417_CAPACITY_PASS',scope='Exact immutable2417pair/519BF IDs in128 roots, coarseframe placement only; NOT native routing/latency qualification',
        source_pins={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [stage_path,inv_path,opts_path,plan_path]},
        die_outline_um=[33000,26000],die_area_mm2=858,root_count=128,pair_count=2417,bf_pairs=519,q_pairs=1898,
        fields_reserved_area_mm2=sum(f['height_um']*G.COL_W8 for f in frames)/1e6,
        frame_histogram=[dict(pair_count=k[0],bf=k[1],slots=k[2],height_um=k[3],roots=v) for k,v in sorted(hist.items())],
        stages=stage_rows,physical_ROM4096_per_rank_die=inv['physical_ROM4096_per_layer_die'],
        configuration_capacity=dict(macros_per_pair=G.CFG_PER_PAIR,rows_per_macro=4096,payload_bits=48,
            words_per_pair=G.CFG_PER_PAIR*4096,words_for_entire_10bit_phase_space=1024*25,
            native_producer_reported_max_phase=642,words_per_phase=25,
            note='Native source images must actually populate this resident capacity; zero/filler CFG is not execution'),
        columns=cols,placements=placements,hcp_homes=moved,collisions=collisions,
        hard_fixed_boxes= fixed,interframe_channels_um=dict(first=first_gap,between=between),
        changes=['remove symmetrical wholewidth IO exclusion: retain exactactualSW hardPHY/CTRL/SVC rectangles',
                 'place128 exacttyped rootframes irregularly in22existingXcolumns;4columns have5roots,18have6',
                 'all6HCP homes move into explicit northrow; no diecount/area reduction/target truncation'],
        open=['actual46root HCP sizes/nativepins/cuts and physical calendar',
              'regenerate real canonical CFG/dataROM images, BF519 allocation and PHW10nativeallpaths',
              'full real field-child placement/clock/reset delivery, returningrootorder and static physical stage calendar',
              'every per-bit intertile<=500um and ownphi-R/pairbudget, allfine routingcuts<=0.60',
              'actual allrealview binding, GRT/TTsetup/FFhold/DRC0, throughput+ownedmutants'])
    out=R/'results/physical/die_iter_1012/s81/canonical_capacity_1015';out.mkdir(parents=True,exist_ok=True)
    (out/'capacity.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:report[k] for k in ['status','root_count','pair_count','bf_pairs','q_pairs','fields_reserved_area_mm2','collisions']}))
if __name__=='__main__':main()
