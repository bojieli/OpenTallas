#!/usr/bin/env python3
"""Conditional own-SM XC carve against exact RP4b child rectangles.

The single-row full-SM composition is a lower-bound candidate, not source-adopted.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def overlap(a,b):
    return a['x']<b['x']+b['w']-1e-6 and b['x']<a['x']+a['w']-1e-6 and a['y']<b['y']+b['h']-1e-6 and b['y']<a['y']+a['h']-1e-6
def main():
    # H-DIE-V790 10-16: --tile rp4c --ref e15f1ee76 reads the RP4c floorplan (body 1529.28) from git; defaults reproduce RP4b
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tile',default='rp4b');ap.add_argument('--ref',help='git ref holding physical/ref_tile/smh_tile_<tile>/floorplan.json')
    ap.add_argument('--candidates',nargs='*',default=['core4_sfu2','core4_sfu2_wide']);ap.add_argument('--out',default='results/arch/hbm_die_v15/xc_rp4b_frame_1016')
    a=ap.parse_args()
    rel=f'physical/ref_tile/smh_tile_{a.tile}/floorplan.json'
    if a.ref:
        source=f'{a.ref}:{rel}';raw=subprocess.check_output(['git','-C',str(ROOT),'show',source])
    else:
        source=Path('/home/ubuntu/wt/hsm-rp4-0030')/rel;raw=source.read_bytes()
    f=json.loads(raw)
    BODY=1434.24 if a.tile=='rp4b' else f['die'][3]
    parents=[];children=[]
    for k in range(16):
        x=k*427.68 if k<8 else 3788.64+(k-8)*427.68
        parents.append(dict(name=f'{a.tile}_'+str(k),x=x,y=0,w=406.08,h=BODY))
        for j,b in enumerate(f['blocks']):children.append(dict(name=f'{a.tile}_{k}/{j}',x=x+b['x'],y=b['y'],w=b['w'],h=b['h'],source_master=b['master']))
    front=dict(name='central_front',x=3421.44,y=0,w=345.6,h=1765.44)
    xc=dict(name='own_sm_xc',x=3788.64,y=round(BODY+21.6,3),w=224.64,h=216)
    frames=parents+[front];hits=[b['name'] for b in frames+children if overlap(xc,b)]
    assert not hits and xc['x']+xc['w']<=7200 and xc['y']+xc['h']<=1800
    globals=[]
    for candidate in a.candidates:
        p=json.loads((ROOT/'results/arch/hbm_die_v15'/candidate/'compact.P.json').read_text())
        for q in ['SW','SE','NW','NE']:
            for k in range(8):
                b=p[f'sm_{q}{k}'];assert b['w']==7200 and b['h']==1800
                globals.append(dict(candidate=candidate,instance=f'xc_{q}{k}',destination=f'sm_{q}{k}',rect=dict(x=b['x']+xc['x'],y=b['y']+xc['y'],w=xc['w'],h=xc['h']),orientation_scope='R0 planning parent frame only; source transformation not adopted'))
    logical_source='rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv'
    logical_raw=subprocess.check_output(['git','-C',str(ROOT),'show','a89a10d1f:'+logical_source])
    mapping=[dict(candidate_index=k,logical_column=k//2,logical_row=k%2,source_instance=f'g_c[{k//2}].g_p[{k%2}].u_t',physical_x=parents[k]['x']) for k in range(16)]
    roof_total=7200*(1800-BODY)
    front_obstructed=front['w']*(front['h']-BODY)
    xc_obstructed=xc['w']*xc['h']
    R,FR,XA=round(1800-BODY,3),round(1800-front['h'],3),round(1800-xc['y']-xc['h'],3)
    roof=dict(roof_base_y_um=BODY,total_mm2=roof_total/1e6,front_obstructed_mm2=front_obstructed/1e6,xc_obstructed_mm2=xc_obstructed/1e6,conditional_free_mm2=(roof_total-front_obstructed-xc_obstructed)/1e6,
              segments=[dict(x_um=[0,3421.44],free_height_um=R),dict(x_um=[3421.44,3767.04],free_height_um=FR),dict(x_um=[3767.04,3788.64],free_height_um=R),dict(x_um=[3788.64,4013.28],free_height_um=XA),dict(x_um=[4013.28,7200],free_height_um=R)],
              connected_scope='Adjacent band may borrow lower-SM roof from its north side only after actual source-connected parent OBS/PG proof; centralfront and XC reduce the roof locally.',
              physically_qualified_usable_mm2=None,programme_status='476 local candidate macros remain UNPLACED; free roof is not a programme grant')
    out=dict(schema='opentallas.hbm.xc_rp4b_frame.v1',qualification='CONDITIONAL_SINGLE_ROW_LOWER_BOUND_NOT_ADOPTED',
             source_manifest=str(source),source_manifest_sha256=hashlib.sha256(raw).hexdigest(),parents=parents,front=front,xc=xc,roof=roof,
             logical_source=logical_source,logical_source_ref='a89a10d1f',logical_source_sha256=hashlib.sha256(logical_raw).hexdigest(),logical_shape=[8,2],logical_candidate_mapping=mapping,
             logical_mapping_scope='Enumeration only; actual source eight-by-two neighbor links, pins, clocks and relays are not rebound. Same-row column neighbors are855.36um apart at candidate centers; p0-to-p1 neighbors427.68um apart.',
             actual_child_count=len(children),child_rects=children,xc_overlap_hits=hits,body_clearance_um=21.6,front_clearance_um=21.6,roof_clearance_um=XA,**(dict(tile=a.tile,body_h_um=BODY) if a.ref else {}),
             die_candidate_homes=globals,open=['actual eight-by-two source connected parent geometry','all incident links and relays/calendar','XC actual routed ETM/native view','parent clock/pins/layer/PG and native gate','programme476/SKV/collective homes unaffected and unplaced'])
    d=ROOT/a.out;d.mkdir(exist_ok=True);(d/'witness.json').write_text(json.dumps(out,indent=1)+'\n')
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
    ax.set(xlim=(0,7200),ylim=(0,1800),aspect='equal',xlabel='um',ylabel='um',title=f'Conditional SM7200x1800 carve:16 actual {a.tile} child layouts /central front /candidate XC224.64x216\nXC y{xc["y"]:g} leaves21.6um above body{BODY:g} and{XA:g}um below the slot top; full source-connected SM remains OPEN')
    fig.tight_layout();fig.savefig(d/'witness.png',dpi=160);plt.close(fig)
    print(json.dumps(dict(xc_overlap_hits=hits,actual_child_count=len(children),global_homes=len(globals),qualification=out['qualification'])))
if __name__=='__main__':main()
