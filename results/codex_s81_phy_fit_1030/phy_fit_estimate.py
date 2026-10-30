"""S81 ES0/ES1 internal PHY placement estimates; no plan mutation."""
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent
source = json.loads((ROOT / 'phy_source.json').read_text())
W, H = 2885.76, 1226.88
MW, MH = 2608.48, 924.48
GUARD = 10.8
Y = 86.4
ROW = 70.0
FACE = 4.32

def overlap(a,b):
    return min(a[2],b[2]) > max(a[0],b[0]) and min(a[3],b[3]) > max(a[1],b[1])

def chain(y, intervals):
    """Equal-Manhattan subdivision of a macro-free bottom U path."""
    points = [(FACE,y),(FACE,ROW),(W-FACE,ROW),(W-FACE,y)]
    lengths = [abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:])]
    total = sum(lengths)
    out=[]
    for j in range(intervals+1):
        distance = total*j/intervals
        for a,b,length in zip(points,points[1:],lengths):
            if distance <= length+1e-8:
                f=distance/length if length else 0
                out.append([a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])])
                break
            distance -= length
    return out,total

fig, axes = plt.subplots(2,2,figsize=(16,10),constrained_layout=True)
records=[]
for col,(name,x) in enumerate([('A',63.64),('B',138.24)]):
    macro=[x,Y,x+MW,Y+MH]
    pg=[x-GUARD,Y-GUARD,x+MW+GUARD,Y+MH+GUARD]
    for row,pn in enumerate(['lk_ES0','lk_ES1']):
        ax=axes[row,col]
        t=source[pn]['type']
        bands=t['clock']['landing_contract']['bands']
        band_clashes=[n for n,b in bands.items() if overlap(pg,b['rect_um'])]
        old=[63.64,302.4,63.64+MW,302.4+MH]
        ax.add_patch(Rectangle((0,0),W,H,fill=False,ec='black',lw=1.3))
        ax.add_patch(Rectangle((old[0],old[1]),MW,MH,fill=False,ec='gray',ls='--',label='old PHY outline'))
        ax.add_patch(Rectangle((pg[0],pg[1]),pg[2]-pg[0],pg[3]-pg[1],fc='#efb8b8',alpha=.45,label='candidate PHY PG domain'))
        ax.add_patch(Rectangle((x,Y),MW,MH,fc='#9991c7',alpha=.65,label='candidate physical PHY'))
        for n,b in bands.items():
            a=b['rect_um']
            ax.add_patch(Rectangle((a[0],a[1]),a[2]-a[0],a[3]-a[1],fc='#e8c463',label='existing landing band' if n==next(iter(bands)) else None))
        for b in t['buses']:
            lo,hi=b['window_um']
            ax.plot([W,W],[lo,hi],lw=4,color='#3978b9')
        rec={'variant':name,'part':pn,'macro_local_um':macro,'pg_local_um':pg,
             'shoreline_um':103.68+Y,'landing_pg_collisions':band_clashes,
             'outline_unchanged':True,'external_pin_windows_unchanged':True,
             'phy_area_mm2':MW*MH/1e6,'io_sites_150um':int(MW//150)*int(MH//150),
             'io_signals':26,'clock_reset_estimate':'separate shared-clock report; not a timing PASS',
             'ir':'NOT RUN on candidate; old406um-placement IR is historical only'}
        if pn=='lk_ES0':
            worst_y=max(t['ft_slots'][0]['in_window_um'][1],t['ft_slots'][0]['out_window_um'][1])
            pts,total=chain(worst_y,8)
            wire=[pts[0],(FACE,ROW),*pts[1:-1],(W-FACE,ROW),pts[-1]]
            ax.plot(*zip(*wire),color='#b13b32',lw=1.2,label='FT0 U route, 9 flops / 8 timed hops')
            ax.scatter(*zip(*pts),color='#b13b32',s=10)
            hop=max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(pts,pts[1:]))
            rec.update(ft0_old_flops=8,ft0_old_timed_intervals=7,
                       old_straight_hop_lower_bound_um=(W-2*FACE)/7,
                       ft0_candidate_flops=9,ft0_added_cycles=1,
                       ft0_u_path_um=total,ft0_worst_point_hop_um=hop,
                       ft0_point_sites_um=pts,
                       point_sites_only='native bit allocation/legality and RTL+calendar qualification NOT RUN',
                       ft_width_including_epochs=1028,
                       horizontal_tracks=75.6*(1/.048+1/.064),
                       track_demand_ratio=1028/(75.6*(1/.048+1/.064)))
        ax.set_title(f'{pn} / variant {name}: shore190.08um, guard10.8um')
        ax.set_aspect('equal'); ax.set_xlim(-35,W+35); ax.set_ylim(-35,H+35)
        ax.set_xlabel('local x (um)'); ax.set_ylabel('local y (um)')
        if row==0 and col==0:ax.legend(loc='upper left',fontsize=7)
        records.append(rec)
fig.savefig(ROOT/'phy_fit_variants.png',dpi=150)
report={'verdict':'ESTIMATE ONLY: physical/IO/FT/timing/IR gates not run',
        'source':'plan_h2_2249 candidate geometry; exact targets from source PHY contents',
        'period_ps':833,'constraints_unchanged':True,'new_plan_written':False,
        'pg_guard_changed_explicitly':[63.64,10.8],
        'ir_area_scaling_only_mv':9.82*((MW+127.28)*(MH+127.28))/((MW+21.6)*(MH+21.6)),
        'ir_bound_limit':'area scaling is a sizing estimate, not a PDNSim bound or PASS',
        'variants':records}
(ROOT/'phy_fit_estimate.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({'variants':len(records),'ft0_hop':records[0]['ft0_worst_point_hop_um'],
                 'band_collisions':sum(len(r['landing_pg_collisions']) for r in records),
                 'track_ratio':records[0]['track_demand_ratio']}))
