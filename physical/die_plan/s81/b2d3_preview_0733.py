#!/usr/bin/env python3
"""Preview the S' bk_sel egress with real 276+epoch FF banks, not centroids.

Plan event only. No RTL/kit/route authorization. Neighbor FT stations must be
reallocated and complete latency regenerated before this preview is adopted.
"""
import gzip
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

repo=Path(sys.argv[1]); out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
raw=json.load(gzip.open(repo/'physical/die_plan/s81/b2d2_1026/die_plan_b2d2.json.gz'))
tn='bk_sel__t2_phy1026_bk_sel';t=raw['partition_types'][tn]
before={h['inst']:list(h['origin_um']) for h in t['hard_cores']}
for h in t['hard_cores']:
    if '.g_q[' in h['inst']: h['origin_um'][0]+=8.64
    if h['inst']=='u_bk_sel.u_tx': h['origin_um'][1]+=17.28
    tap=next(x for x in t['clock']['taps'] if x['name']==h['inst'])
    tap['xy']=[round(h['origin_um'][k]+h['outline_um'][k]/2,6) for k in (0,1)]
bus=next(b for b in t['buses'] if b['name']=='xtier_o0')
old_window=bus['window_um'][:]
bus['window_um']=[606.96,round(606.96+old_window[1]-old_window[0],6)]
# FF envelope is the current FT implementation's conservative measured cell.
cw,ch=1.404,.27
stage1=[[round(834.84+(i%8)*2.16,6),round(513.54+(i//8)*.27,6)] for i in range(277)]
stage2=[[round(644.004+(i%2)*1.62,6),round(326.7+(i//2)*.27,6)] for i in range(277)]
pinregs=[[round(606.96+int(i*25/277)*1.62,6),round(4.32+(i%12)*.27,6)] for i in range(277)]
bays=[[834.84,513.27,852.12,523.53],[643.842,324,648,367.2],[606.96,3.24,648,8.64]]
centres=lambda bank:[[x+cw/2,y+ch/2] for x,y in bank]
pins=json.load(open(repo/'physical/die_plan/s81/inputs/core_pins/dsdv_bk_g.json'))['pins']
src=[[p['x']+1002.24+.108,p['y']+501.12+.012] for p in pins if p['name'].startswith('vo_s[')]
# Independent extrema cover ANY payload-bit permutation; epoch uses the full
# source bundle box conservatively until the bound epoch source is named.
def worst(a,b): return max(abs(x-u)+abs(y-v) for x,y in a for u,v in b)
cs1,cs2,cp=map(centres,(stage1,stage2,pinregs))
hops=[worst(src,cs1),worst(cs1,cs2),worst(cs2,cp)]
fills=[277*cw*ch/((r-l)*(u-b)) for l,b,r,u in bays]
boxes=[]
for h in t['hard_cores']:
    x,y=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);w,z=h['outline_um']
    boxes.append((h['inst'],[x+dx,y+dy,x+dx+w,y+dy+z]))
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-6 and min(a[3],b[3])>max(a[1],b[1])+1e-6
hits=[]
for k,bank in enumerate((stage1,stage2,pinregs)):
    for i,(x,y) in enumerate(bank):
        cell=[x,y,x+cw,y+ch]
        for name,z in boxes:
            if overlap(cell,[z[0]-8.64,z[1]-8.64,z[2]+8.64,z[3]+8.64]):hits.append([k,i,name])
loop_boxes={name:z for name,z in boxes}
uc=loop_boxes['u_bk_sel.u_sel.u_c']
dist=lambda a,b:max(a[0]-b[2],b[0]-a[2],0)+max(a[1]-b[3],b[1]-a[3],0)
loop_reach={n:dist(z,uc) for n,z in boxes if '.g_q[' in n}
core_overlap=[(a,c) for i,(a,b) in enumerate(boxes) for c,d in boxes[i+1:] if overlap(b,d)]
ledger={'state':'PREVIEW ONLY; neighbor FT allocation and gen latency owed',
        'type':tn,'source_plan':'claude/path-s81-b2d2-1026@d355478bee',
        'core_moves':{h['inst']:{'from':before[h['inst']],'to':h['origin_um']} for h in t['hard_cores'] if before[h['inst']]!=h['origin_um']},
        'window':{'from':old_window,'to':bus['window_um']},
        'cell_um':[cw,ch],'banks_ll_um':[stage1,stage2,pinregs],'bays_um':bays,
        'bank_fill':fills,'worst_any_bit_permutation_hops_um':hops,'source_pin_escape_extra_um':.5,
        'worst_with_ff_pin_envelope_um':[hops[0]+.702+.5,hops[1]+1.404,hops[2]+1.404],
        'epoch_first_source':'INCOMPLETE: generated source ea=rst_n; local delivered-reset leaf at bank1 must come from master-plan reset slice, not the vo_s data pins.',
        'core_halo_hits':hits,'core_overlaps':core_overlap,'q_control_box_reach_um':loop_reach,
        'added_source_cycles':2,'added_q_control_cycles':0,
        'verdict':'PASS_PREVIEW' if max([hops[0]+.5]+hops[1:])<=405 and max(fills)<=.6 and not hits and not core_overlap else 'FAIL_PREVIEW'}
json.dump(ledger,open(out/'ledger.json','w'),indent=2)
with gzip.open(out/'die_plan_b2d3_preview.json.gz','wt') as f:json.dump(raw,f,separators=(',',':'))
fig,(a,z)=plt.subplots(1,2,figsize=(17,9),gridspec_kw={'width_ratios':[2,1]})
for ax in (a,z):
    for name,(l,b,r,u) in boxes:
        ax.add_patch(Rectangle((l,b),r-l,u-b,fc='lightgrey',ec='black'))
        ax.text(l+4,u-25,name.split('.')[-1],fontsize=9,clip_on=True)
    for (l,b,r,u),bank,color in zip(bays,(stage1,stage2,pinregs),('orange','green','purple')):
        ax.add_patch(Rectangle((l,b),r-l,u-b,fill=False,ec=color,lw=2))
        for x,y in bank:ax.add_patch(Rectangle((x,y),cw,ch,fc=color,ec=None))
    ax.plot([sum(p[0] for p in src)/len(src),sum(p[0] for p in src)/len(src),842.04,842.04,645.8,645.8,645.8,637],
            [501.15,501.0,501.0,518.4,518.4,345.6,5.4,5.4],'-r',lw=2)
a.set(xlim=(0,2885.76),ylim=(0,1226.88),aspect='equal',title='bk_sel S-prime preview: actual FF banks + opened pin-reg strip')
z.set(xlim=(620,865),ylim=(0,590),aspect='equal',title='TX/q0 channel and 276+epoch banks')
fig.tight_layout();fig.savefig(out/'preview.png',dpi=160)
print(json.dumps({k:v for k,v in ledger.items() if k not in ('banks_ll_um','core_moves')},indent=1))
