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


def cli():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage-dir',type=Path,help='allocator point (stage_map.json + inventory.json); default = released 2417-pair binding')
    ap.add_argument('--remove-columns',default='',help='x-sorted indices of the 22 canonical field columns to remove (wide hub), e.g. 9,10,11')
    ap.add_argument('--io-to-hub',action='store_true',help='SW PHY/CTRL/SVC band moves to the hub foot (centred) and the six HCP homes to the hub head: every kept field column runs full height')
    ap.add_argument('--stub-inner',action='store_true',help='leave the spare root positions as one short hub-adjacent column instead of spreading them')
    ap.add_argument('--out',type=Path,help='output directory (default results/physical/die_iter_1012/s81/canonical_capacity_1015)')
    ap.add_argument('--name',default='capacity.json')
    return ap.parse_args()


def pack_columns(cols,frames,first_gap,between,stub=False):
    """Generic root re-pack (S-DIE 10-15 wide hub): roots stay in id order, W outer->inner then E inner->outer;
    each column takes the next roots while they fit; any spare positions are left at the hub-adjacent columns.
    Returns {column index: [frames]} or raises with the shortfall."""
    order=sorted(range(len(cols)),key=lambda i:cols[i]['x_um'])
    if stub:   # E filled outer->inner so the leftover roots form a stub in the hub-adjacent E column
        order=[i for i in order if cols[i]['x_um']<16000]+[i for i in order if cols[i]['x_um']>=16000][::-1]
    def fill(caps):
        out={i:[] for i in order};k=0
        for i in order:
            c=cols[i];used=first_gap-between
            while k<len(frames) and len(out[i])<caps[i] and used+between+frames[k]['height_um']<=c['height_um']+1e-6:
                used+=between+frames[k]['height_um'];out[i].append(frames[k]);k+=1
        return out,k
    caps={i:10**6 for i in order}
    out,k=fill(caps)
    if k<len(frames):
        # id-order fill short: worst-fit decreasing by height (roots keep their ids; columns list them by id)
        rem={i:cols[i]['height_um']-first_gap+between for i in order};wf={i:[] for i in order};ok=True
        for f in sorted(frames,key=lambda f:(-f['height_um'],f['root'])):
            i=max(order,key=lambda j:rem[j])
            if rem[i]<f['height_um']+between-1e-6:ok=False;break
            rem[i]-=f['height_um']+between;wf[i].append(f)
        if ok:return {i:sorted(v,key=lambda f:f['root']) for i,v in wf.items()}
        k=sum(len(v) for v in wf.values())
        raise SystemExit(json.dumps(dict(status='CANONICAL_REPACK_INFEASIBLE',roots_placed=k,roots=len(frames),
            columns=len(cols),column_heights_um=[round(cols[i]['height_um'],1) for i in order],
            frame_heights_um=sorted({f['height_um'] for f in frames}))))
    # spare positions: by default one per hub-adjacent column (alternating W/E inward-out) so no column is left with a
    # stub; --stub-inner keeps the spare as one short inner column (its free height becomes hub room)
    if not stub:
        west=[i for i in order if cols[i]['x_um']<16000][::-1];east=[i for i in order if cols[i]['x_um']>=16000]
        inner=[x for pair in zip(west,east) for x in pair]+west[len(east):]+east[len(west):]
        for i in inner:
            trial=dict(caps);trial[i]=len(out[i])-1
            if trial[i]<1:continue
            o2,k2=fill(trial)
            if k2==len(frames):caps,out=trial,o2
    return out


def main():
    a=cli()
    default_src=R/'results/uarch/dsrom_s81_released_binding_20261004/canonical'
    src=a.stage_dir if a.stage_dir else default_src
    src=src if src.is_absolute() else R/src
    stage_path=src/'stage_map.json';inv_path=src/'inventory.json'
    stage=json.loads(stage_path.read_text());inv=json.loads(inv_path.read_text())
    bf=set(stage['BF_site_IDs']);bounds=stage['region_bounds']
    PAIRS=bounds[-1];NBF=len(bf);NSTAGES=inv['stages']
    assert len(bounds)==129 and bounds[0]==0 and all(b<c for b,c in zip(bounds,bounds[1:]))
    assert inv['pairs_per_rank_die']==PAIRS and len(stage['PHW_required_by_stage'])==NSTAGES
    assert len(stage['rank_dies'])==NSTAGES*4
    if src==default_src:
        assert NBF==519 and PAIRS==2417 and NSTAGES==81
        assert all(bounds[r]==(r*2417)//128 for r in range(129))
        assert stage['PHW_required_by_stage'][:74]==[10]*74
    remove=sorted({int(x) for x in a.remove_columns.split(',') if x.strip()})
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
    assert sum(f['pair_count'] for f in frames)==PAIRS and sum(f['bf'] for f in frames)==NBF
    plan_path=R/'results/physical/die_iter_1012/s81/hcp_home_growth_1015/plan_r8c.json.gz'
    plan=json.load(gzip.open(plan_path))
    fixed=[(i[0],i[2],i[3],i[4],i[5]) for i in plan['insts'] if i[7] in ('hub','phy','ctrl','svc','svcj','band_blk','link')]
    homes=json.loads((R/'physical/s81_die_pins/v20_hcx_partition/homes.json').read_text())
    xs=sorted({r['rect'][0] for r in plan['regions'] if r.get('kind')=='field'})
    assert len(xs)==22
    assert all(0<=i<22 for i in remove) and not (set(remove)-set(range(5,17))),('only hub-adjacent columns',remove)
    kept=[x for i,x in enumerate(xs) if i not in remove]
    west=[x for x in kept if x<16000];east=[x for x in kept if x>=16000]
    hub_x0=max(west)+G.COL_W8;hub_x1=min(east)
    io_moves=[]
    if a.io_to_hub:
        sw=[f for f in fixed if f[0] in ('phy_SW','ctrl_SW','svc_SW','svcj')]
        assert {f[0] for f in sw}>={'phy_SW','ctrl_SW','svc_SW'},sw
        bx0=min(f[1] for f in sw);bx1=max(f[1]+f[3] for f in sw)
        assert bx1-bx0<=hub_x1-hub_x0-2*20,('SW IO band wider than the hub',bx1-bx0,hub_x1-hub_x0)
        dx=round(((hub_x0+hub_x1)/2-(bx0+bx1)/2)/0.054)*0.054
        nf=[]
        for f in fixed:
            if f in sw:
                g=(f[0],round(f[1]+dx,3),*f[2:]);io_moves.append(dict(name=f[0],from_um=[f[1],f[2]],to_um=[g[1],g[2]],size_um=[f[3],f[4]]));nf.append(g)
            elif f[1]>=hub_x0-1e-6 and f[1]+f[3]<=hub_x1+1e-6:
                continue   # hub blocks are re-laid by the generator's wide-hub mode; not field obstacles
            else:nf.append(f)
        fixed=nf
    moved=[]
    for i,h in enumerate(homes['hc_projection']):
        nh=copy.deepcopy(h);nh['outline']=dict(w=1728.,h=1296.)
        if a.io_to_hub:
            # two rows of three at the hub head, E end (the HC tower keeps the W side of the hub)
            r_,c_=divmod(i,3);nh['at_um']=[round(hub_x1-20-(3-c_)*1814.4+86.4,3),round(24624.-r_*(1296.+43.2),3)]
        else:nh['at_um']=[9417.6+1814.4*i,24624.]
        nh['qualification']=f'COARSE_FULL{PAIRS}_CANDIDATE: native46root size/pins/cuts and physical calendar not proven'
        moved.append(nh)
    home_boxes=[(h['name'],*h['at_um'],h['outline']['w'],h['outline']['h']) for h in moved]
    def overlap(a,b):
        return a[1]<b[1]+b[3]-1e-6 and a[1]+a[3]>b[1]+1e-6 and a[2]<b[2]+b[4]-1e-6 and a[2]+a[4]>b[2]+1e-6
    home_collisions=[(a[0],b[0]) for a in home_boxes for b in fixed if overlap(a,b)]
    assert not home_collisions,home_collisions
    assert all(h[1]>=20 and h[2]>=20 and h[1]+h[3]<=32980 and h[2]+h[4]<=25980 for h in home_boxes)
    obstacles=fixed+home_boxes
    cols=[]
    for x in kept:
        intervals=free_intervals(x,G.COL_W8,obstacles)
        lo,hi=max(intervals,key=lambda ab:ab[1]-ab[0])
        cols.append(dict(x_um=x,y0_um=lo,y1_um=hi,height_um=hi-lo,roots=6))
    first_gap,between=259.2,388.8
    if remove or a.io_to_hub or src!=default_src:
        packed=pack_columns(cols,sorted(frames,key=lambda f:f['root']),first_gap,between,a.stub_inner)
        placements=[]
        for i,fs in packed.items():
            c=cols[i];c['roots']=len(fs);y=c['y0_um']+first_gap
            for f in fs:
                placements.append(dict(**f,origin_um=[c['x_um'],round(y,6)],outline_um=[G.COL_W8,f['height_um']]));y+=f['height_um']+between
            assert y-between<=c['y1_um']+1e-6
        return finish(a,src,stage,inv,stage_path,inv_path,opts_path,plan_path,frames,cols,placements,moved,fixed,obstacles,
                      overlap,first_gap,between,PAIRS,NBF,NSTAGES,remove,io_moves,hub_x0,hub_x1)
    # 132 geometrical positions,128 real roots. Spend the four empty positions
    # on the four tightest columns, preserving all immutable root/pair IDs.
    for c in sorted(cols,key=lambda c:c['height_um'])[:4]:c['roots']=5
    short=sorted([f for f in frames if f['pair_count']==18],key=lambda f:f['height_um'])
    long=sorted([f for f in frames if f['pair_count']==19],key=lambda f:-f['height_um'])
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
    out=a.out if a.out else R/'results/physical/die_iter_1012/s81/canonical_capacity_1015'
    out=out if out.is_absolute() else R/out
    out.mkdir(parents=True,exist_ok=True)
    (out/a.name).write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:report[k] for k in ['status','root_count','pair_count','bf_pairs','q_pairs','fields_reserved_area_mm2','collisions']}))


def finish(a,src,stage,inv,stage_path,inv_path,opts_path,plan_path,frames,cols,placements,moved,fixed,obstacles,overlap,
           first_gap,between,PAIRS,NBF,NSTAGES,remove,io_moves,hub_x0,hub_x1):
    """Wide-hub / re-cut capacity record (same schema as the 2417 record + wide_hub block)."""
    assert sorted(f['root'] for f in placements)==list(range(128))
    boxes=[(f'root{f["root"]}',*f['origin_um'],*f['outline_um']) for f in placements]
    collisions=[(x[0],y[0]) for x in boxes for y in obstacles if overlap(x,y)]
    collisions +=[(x[0],y[0]) for i,x in enumerate(boxes) for y in boxes[i+1:] if overlap(x,y)]
    assert not collisions,collisions
    hist=collections.Counter((f['pair_count'],f['bf'],f['packed_slots'],f['height_um']) for f in frames)
    stage_rows=[dict(stage=i,occupied_pairs=inv['occupied_pairs_per_stage'][i],physical_pair_slots_per_rank_die=PAIRS,
                     phase_width=stage['PHW_required_by_stage'][i]) for i in range(NSTAGES)]
    report=dict(status=f'COARSE_FULL{PAIRS}_CAPACITY_PASS',
        scope=f'Exact allocator {PAIRS}pair/{NBF}BF IDs in 128 roots, coarse frame placement only; NOT native routing/latency qualification',
        source_pins={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [stage_path,inv_path,opts_path,plan_path]},
        stage_map=str(stage_path.relative_to(R)),
        die_outline_um=[33000,26000],die_area_mm2=858,root_count=128,pair_count=PAIRS,bf_pairs=NBF,q_pairs=PAIRS-NBF,
        fields_reserved_area_mm2=sum(f['height_um']*G.COL_W8 for f in frames)/1e6,
        frame_histogram=[dict(pair_count=k[0],bf=k[1],slots=k[2],height_um=k[3],roots=v) for k,v in sorted(hist.items())],
        stages=stage_rows,physical_ROM4096_per_rank_die=inv.get('physical_ROM4096_per_layer_die'),
        configuration_capacity=dict(macros_per_pair=G.CFG_PER_PAIR,rows_per_macro=4096,payload_bits=48,words_per_pair=G.CFG_PER_PAIR*4096,
            note='Native source images must actually populate this resident capacity; zero/filler CFG is not execution'),
        columns=cols,placements=placements,hcp_homes=moved,collisions=collisions,hard_fixed_boxes=fixed,
        interframe_channels_um=dict(first=first_gap,between=between),
        wide_hub=dict(removed_columns=remove,field_columns=len(cols),hub_x_um=[round(hub_x0,3),round(hub_x1,3)],
                      hub_width_um=round(hub_x1-hub_x0,3),io_to_hub=bool(a.io_to_hub),io_moves=io_moves,
                      positions_used=len(placements),roots_per_column=[c['roots'] for c in sorted(cols,key=lambda c:c['x_um'])]),
        changes=[f'remove field columns {remove} (x-sorted indices of the 22 canonical columns): wide hub {hub_x1-hub_x0:.1f} um',
                 f'128 allocator roots ({PAIRS} pairs, {NBF} BF) re-packed in id order into {len(cols)} columns'] +
                (['SW PHY/CTRL/SVC band centred at the hub foot; six HCP homes at the hub head (E end)'] if a.io_to_hub else []),
        open=['generator wide-hub mode (hub blocks side by side), roads/pins, GEN/port-bind/GRT/STA',
              'actual 46-root HCP sizes/native pins/cuts and physical calendar',
              'regenerate canonical CFG/data ROM images for the allocator point'])
    out=a.out if a.out else R/'results/physical/die_iter_1012/s81/canonical_capacity_1015'
    out=out if out.is_absolute() else R/out
    out.mkdir(parents=True,exist_ok=True)
    (out/a.name).write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:report[k] for k in ['status','root_count','pair_count','bf_pairs','fields_reserved_area_mm2','collisions','wide_hub'] if k!='wide_hub'} | dict(wide_hub={k:v for k,v in report['wide_hub'].items() if k!='io_moves'})))
if __name__=='__main__':main()
