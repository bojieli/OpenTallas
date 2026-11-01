#!/usr/bin/env python3
"""Plan-only pslice NCX macro locality candidate; writes no source/parent plan in place."""
import argparse, gzip, json, re
from pathlib import Path

CORE='ot_hbm_su_programme_pslice_c5'
W,H=939.6,760.32
MW,MH=94.824,41.064


def column_id(name):
    return int(re.search(r'g_c\\?\[(\d+)\\?\]',name)[1])


def ncx_name(name,c):
    name=name.replace(chr(92),'')
    root=f'g_c[{c}].u_c.'
    if c in (1,2,3):
        m=re.search(r'\.(dt|ix)\\?\[0\\?\]\.mem\.g\\?\[(\d+)\\?\]\.mem$',name)
        if not m: raise ValueError('unrecognised bank '+name)
        kind,k=m.groups()
        return name[:name.index(root)+len(root)]+f'g_pn.u_p.u_{kind}.g[{k}].mem'
    return name.replace(root+'u_p.',root+'g_p.u_p.')


def plan(entry):
    groups={c:[] for c in range(10)}
    for m in entry['macros']:groups[column_id(m['name'])].append(m)
    expected={c:17 if c in (1,2,3) else 7 for c in range(10)}
    if {c:len(v) for c,v in groups.items()}!=expected:raise ValueError('wrong production shape')
    slots={}
    for c,pair in [(1,0),(2,2),(3,4)]:
        slots[c]=[(pair+side,row) for side in range(2) for row in (range(9) if side==0 else range(7,-1,-1))]
    slots[0]=[(6,r) for r in range(7)]
    slots[4]=[(6,r) for r in range(7,14)]
    rest=[(col,row) for col in range(6) for row in range(9,15)]
    for i,c in enumerate(range(5,10)):slots[c]=rest[7*i:7*(i+1)]
    rows=[]
    for c in range(10):
        for m,(col,row) in zip(sorted(groups[c],key=lambda q:q['name']),slots[c],strict=True):
            x=32.4+129.888*col; y=H-8.64-MH-49.728*row
            q=dict(m);q.update(name=ncx_name(m['name'],c),rect_um=[round(x,3),round(y,3),round(x+MW,3),round(y+MH,3)])
            rows.append(q)
    # One local root per street/three macro rows, on actual whitespace; precise sink loads come from synth.
    taps=[]
    for col in range(6):
        x=32.4+129.888*col+MW+17.52
        for row in (1,4,7,10,13):taps.append([round(round(x/4.32)*4.32,3),round(round((H-8.64-49.728*row)/4.32)*4.32,3)])
    return dict(schema='opentallas.hbm-pslice-column-plan.v1',candidate=True,core=CORE,
      outline_um=[W,H],source_recipe='NCX1 + pgcol c5e763929',added_cycles=0,
      macro_placement=rows,clock_tap_sites_um=taps,
      pin_proposal=dict(start=['W',405.0],length=['W',410.0,430.0]),
      clock_entry_delta=dict(old_effective_um=[470.88,380.16],new_um=[535.68,380.16],reason='old entry falls on macro in new grid; move into V street'),
      rationale='Preserve 10 logical groups, L banks in adjacent paired columns; widen V channels to35.064um',
      remaining='Integrate start/length pin point with parent, distribute existing head export registers, then prototype reach census; no route approval yet')


def draw(p,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(12,10))
    for q in p['macro_placement']:
        x,y,x1,y1=q['rect_um'];c=column_id(q['name'])
        ax.add_patch(Rectangle((x,y),x1-x,y1-y,facecolor=plt.get_cmap('tab10')(c),edgecolor='black',lw=.4,alpha=.7))
        ax.text((x+x1)/2,(y+y1)/2,str(c),ha='center',va='center',fontsize=7)
    xy=p['clock_tap_sites_um'];ax.scatter([q[0] for q in xy],[q[1] for q in xy],marker='+',c='black',s=40,label='proposed local clock root')
    ax.scatter([535.68],[380.16],c='gold',edgecolors='black',marker='*',s=160,label='clock entry in V street')
    ax.scatter([0],[405],c='red',marker='>',s=80,label='start/length entry proposal')
    ax.set(xlim=(-15,W+15),ylim=(-15,H+15),aspect='equal',xlabel='um',ylabel='um',title='HBM pslice NCX column-local macro candidate (not approved for route)')
    ax.legend(loc='lower left');fig.tight_layout();fig.savefig(path,dpi=130);plt.close(fig)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--core-macros',required=True);ap.add_argument('--out',required=True);ap.add_argument('--pin-source',required=True);a=ap.parse_args()
    f=gzip.open(a.core_macros,'rt') if a.core_macros.endswith('.gz') else open(a.core_macros)
    with f:d=json.load(f)
    p=plan(d['cores'][CORE]);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    pf=gzip.open(a.pin_source,'rt') if a.pin_source.endswith('.gz') else open(a.pin_source)
    with pf: old_pins=json.load(pf)
    new_pins=[dict(q) for q in old_pins]
    occupied=[q['y'] for q in old_pins if q['layer']=='M4' and q['x']<1 and q['name']!='start' and not q['name'].startswith('length[')]
    delta=[]
    for q in new_pins:
        if q['name']=='start': target=405.0
        elif q['name'].startswith('length['): target=410.04+1.296*int(q['name'][7:-1])
        elif q['name']=='clk':
            delta.append(dict(name='clk',old=dict(q),new=dict(q,x=535.68,y=380.16),reason='clock entry in whitespace'))
            q.update(x=535.68,y=380.16);continue
        else: continue
        target=round((round((target-.024)/.048)*.048+.024),3)
        while any(abs(target-y)<.12 for y in occupied):target=round(target+.048,3)
        old=dict(q);q['y']=target;occupied.append(target)
        delta.append(dict(name=q['name'],old=old,new=dict(q),reason='localise existing capture stages; zero added cycles'))
    (out/'pins_old.json').write_text(json.dumps(old_pins,indent=1)+'\n')
    (out/'pins_new.json').write_text(json.dumps(new_pins,indent=1)+'\n')
    (out/'pin_delta.json').write_text(json.dumps(delta,indent=1)+'\n')
    (out/'column_plan.json').write_text(json.dumps(p,indent=2)+'\n');draw(p,out/'column_plan.png')
    print('PLAN',len(p['macro_placement']),'macros',len(p['clock_tap_sites_um']),'tap proposals; route held')


if __name__=='__main__':main()
