#!/usr/bin/env python3
"""Conditional own-SM XC carve against exact RP4b child rectangles.

The single-row full-SM composition is a lower-bound candidate, not source-adopted.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def overlap(a,b):
    return a['x']<b['x']+b['w']-1e-6 and b['x']<a['x']+a['w']-1e-6 and a['y']<b['y']+b['h']-1e-6 and b['y']<a['y']+a['h']-1e-6
def main():
    source=Path('/home/ubuntu/wt/hsm-rp4-0030/physical/ref_tile/smh_tile_rp4b/floorplan.json');raw=source.read_bytes();f=json.loads(raw)
    parents=[];children=[]
    for k in range(16):
        x=k*427.68 if k<8 else 3788.64+(k-8)*427.68
        parents.append(dict(name='rp4b_'+str(k),x=x,y=0,w=406.08,h=1434.24))
        for j,b in enumerate(f['blocks']):children.append(dict(name=f'rp4b_{k}/{j}',x=x+b['x'],y=b['y'],w=b['w'],h=b['h'],source_master=b['master']))
    front=dict(name='central_front',x=3421.44,y=0,w=345.6,h=1765.44)
    xc=dict(name='own_sm_xc',x=3788.64,y=1455.84,w=224.64,h=216)
    frames=parents+[front];hits=[b['name'] for b in frames+children if overlap(xc,b)]
    assert not hits and xc['x']+xc['w']<=7200 and xc['y']+xc['h']<=1800
    globals=[]
    for candidate in ['core4_sfu2','core4_sfu2_wide']:
        p=json.loads((ROOT/'results/arch/hbm_die_v15'/candidate/'compact.P.json').read_text())
        for q in ['SW','SE','NW','NE']:
            for k in range(8):
                b=p[f'sm_{q}{k}'];assert b['w']==7200 and b['h']==1800
                globals.append(dict(candidate=candidate,instance=f'xc_{q}{k}',destination=f'sm_{q}{k}',rect=dict(x=b['x']+xc['x'],y=b['y']+xc['y'],w=xc['w'],h=xc['h']),orientation_scope='R0 planning parent frame only; source transformation not adopted'))
    out=dict(schema='opentallas.hbm.xc_rp4b_frame.v1',qualification='CONDITIONAL_SINGLE_ROW_LOWER_BOUND_NOT_ADOPTED',
             source_manifest=str(source),source_manifest_sha256=hashlib.sha256(raw).hexdigest(),parents=parents,front=front,xc=xc,
             actual_child_count=len(children),child_rects=children,xc_overlap_hits=hits,body_clearance_um=21.6,front_clearance_um=21.6,roof_clearance_um=128.16,
             die_candidate_homes=globals,open=['actual eight-by-two source connected parent geometry','all incident links and relays/calendar','XC actual routed ETM/native view','parent clock/pins/layer/PG and native gate','programme476/SKV/collective homes unaffected and unplaced'])
    d=ROOT/'results/arch/hbm_die_v15/xc_rp4b_frame_1016';d.mkdir(exist_ok=True);(d/'witness.json').write_text(json.dumps(out,indent=1)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(18,5))
    for b in parents:
        ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#edf2f5',edgecolor='#708090',linewidth=.6))
    for b in children:
        ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#b9cde0',edgecolor='#708090',linewidth=.2))
    for b,color in [(front,'#d8ead2'),(xc,'#f4a64c')]:
        ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor=color,edgecolor='black'))
        ax.text(b['x']+b['w']/2,b['y']+b['h']/2,b['name'],fontsize=7,rotation=90 if b==front else 0,ha='center',va='center')
    ax.set(xlim=(0,7200),ylim=(0,1800),aspect='equal',xlabel='um',ylabel='um',title='Conditional SM7200x1800 carve:16 actual RP4b18-child layouts /central front /native XC224.64x216\nXC y1455.84 leaves21.6um above body1434.24 and128.16um below roof; full source-connected SM remains OPEN')
    fig.tight_layout();fig.savefig(d/'witness.png',dpi=160);plt.close(fig)
    print(json.dumps(dict(xc_overlap_hits=hits,actual_child_count=len(children),global_homes=len(globals),qualification=out['qualification'])))
if __name__=='__main__':main()
