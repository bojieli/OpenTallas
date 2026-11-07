#!/usr/bin/env python3
"""Private geometry event: real embedding SRAM, no existing reservation moves."""
import argparse, json, re, sys
from pathlib import Path
from collections import defaultdict

ap=argparse.ArgumentParser()
ap.add_argument('inputs', type=Path)
ap.add_argument('out', type=Path)
args=ap.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import form_geometry as FG

p=json.loads((args.inputs/'wi_type.json').read_text())
for h in p['hard_cores']:
    if h['inst']=='host__qkd_hr_cdc_hi': h['origin_um']=[225.984,1003.392]
reservations=FG.placement_reservations(p)
# The generated physical scripts supply the actual retained FT/reset sites.
groups=defaultdict(list)
sizes={}
for line in (args.inputs/'ft_bit_sites.tcl').read_text().splitlines():
    m=re.match(r'dict set ff_bit_site_cells \{([^}]+)\} \{([\d.]+) ([\d.]+)\}',line)
    if m: sizes[m[1]]=[float(m[2]),float(m[3])]
    m=re.match(r'dict set ff_bit_sites \{([^,]+),(\d+),\d+\} \{([\d.]+) ([\d.]+)\}',line)
    if m: groups[m[1]+':'+m[2]].append([float(m[3]),float(m[4])])
for n,pts in groups.items():
    fw,fh=sizes[n.split(':')[0]]
    reservations['actual_ft:'+n]=[min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts)+fw,max(y for x,y in pts)+fh]
for line in (args.inputs/'reset_tree.tcl').read_text().splitlines():
    m=re.match(r'rtr_place (\S+) \{.*?\} ([\d.]+) ([\d.]+)',line)
    if m:
        x,y=float(m[2]),float(m[3]);reservations['actual_reset:'+m[1]]=FG.grow([x,y,x,y],2.16)
for tap in p['clock'].get('taps',[]):
    x,y=tap['xy']
    if tap['name'].startswith('host__qkd_hr_cdc_hi.'): x,y=295.128,1072.536
    reservations['actual_clock:'+tap['name']]=FG.grow([x,y,x,y],8.64)

w,h=171.288,77.784
# Propose a reserved site near the free eastern central glue area; all old
# macros, FT bands, clock entries and reset sites retain their exact positions.
candidates=[]
for iy in range(65,92):
    for ix in range(110,145):
        x,y=round(ix*8.64,6),round(iy*8.64,6)
        box=[x,y,x+w,y+h]
        if box[2]+5>p['outline_um'][0]-4.32 or box[3]+5>p['outline_um'][1]-4.32: continue
        collisions=[n for n,r in reservations.items() if FG.overlap(FG.grow(box,5),r)]
        if not collisions: candidates.append((abs(x-1062.72)+abs(y-622.08),box))
assert candidates, 'No legal private SRAM site in the proposed free region'
box=min(candidates)[1]
result=dict(instance='u_bound.u_kvs_emb.u_rowtx.u_row',master='ot_sram_1r1w_64x512_m1_r2c2',
    provider='physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2',
    bbox_um=box,origin_um=box[:2],outline_um=[w,h],orientation='R0',
    reservations=len(reservations),collisions=[],macro_halo_um=5,
    clock_halo_um=8.64,reset_halo_um=2.16,scope='PRIVATE PLACE ONLY; pin reach/PG/phase unqualified')
args.out.mkdir(parents=True,exist_ok=True)
(args.out/'sram_site.json').write_text(json.dumps(result,indent=2)+'\n')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(8,10))
for n,r in reservations.items():
    ax.add_patch(Rectangle(r[:2],r[2]-r[0],r[3]-r[1],color='#aab5c0',alpha=.45))
ax.add_patch(Rectangle(box[:2],w,h,color='#39a46d',alpha=.7))
ax.text(box[0]+w/2,box[1]+h/2,'embedding SRAM',ha='center',fontsize=8)
ax.set(xlim=(0,p['outline_um'][0]),ylim=(0,p['outline_um'][1]),aspect='equal',
    title=f'Private Wi actual SRAM site; {len(reservations)} retained reservations\n5um site halo clear; no other reservation moved',xlabel='microns',ylabel='microns')
fig.tight_layout();fig.savefig(args.out/'sram_site_review.png',dpi=130)
print(json.dumps(result))
