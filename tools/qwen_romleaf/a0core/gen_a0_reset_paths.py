#!/usr/bin/env python3
"""Plan equally deep, macro-free synchronous reset paths for an A0 core before physical implementation."""
import argparse
import csv
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import reset_tree as RT


def plan(floorplan, table, root, stages=4, copies=32):
    w,h=floorplan['die'][2:]
    boxes=[(b['x']-2.16,b['y']-2.16,b['x']+b['w']+2.16,b['y']+b['h']+2.16) for b in floorplan['blocks']]
    targets={}
    for row in csv.reader(table.splitlines(),delimiter='\t'):
        if not row or row[0].startswith('#'):continue
        m=re.search(r'__ot_rlv__c([0-9]+)',row[0]);k=int(m[1]) if m else 0
        targets[k]=tuple(map(float,row[2:4]))
    result=[];maxhop=0;root_site=None
    for k in range(copies):
        dst=targets.get(k,root)
        topo=RT.topology([(f'copy{k}',*dst)],root,reach=405,margin=25,boxes=boxes,box_out=(2.16,2.16,w-2.16,h-2.16))
        nodes=topo['nodes'];chain=[];j=0
        while j>=0:chain.append(tuple(nodes[j]['xy']));j=nodes[j]['par']
        chain.reverse()
        if len(chain)>stages-1:raise ValueError(f'copy{k} needs {len(chain)+1} reset stages, configured {stages}')
        chain += [chain[-1]]*(stages-1-len(chain))
        root_site=topo['root'];points=[tuple(root_site)]+chain
        for lev,xy in enumerate(points):
            if not RT._free(xy,boxes,(2.16,2.16,w-2.16,h-2.16)):raise ValueError(f'blocked reset copy{k} stage{lev}: {xy}')
            if lev:maxhop=max(maxhop,RT._man(points[lev-1],xy))
            result.append(dict(copy=k,stage=lev,xy=list(xy)))
    return dict(stages=stages,old_stages=2,added_boot_cycles=stages-2,data_cycles_added=0,copies=copies,
                max_hop_um=round(maxhop,3),root_um=list(root_site),paths=result)


def main():
    p=argparse.ArgumentParser();p.add_argument('floorplan');p.add_argument('tap_table');p.add_argument('--root',nargs=2,type=float,required=True);p.add_argument('--out',required=True)
    a=p.parse_args();fp=json.loads(Path(a.floorplan).read_text());r=plan(fp,Path(a.tap_table).read_text(),a.root)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.with_suffix('.json').write_text(json.dumps(r,indent=1)+'\n')
    out.with_suffix('.tsv').write_text('# copy\tstage\tx_um\ty_um\n'+''.join(f"{q['copy']}\t{q['stage']}\t{q['xy'][0]:.5f}\t{q['xy'][1]:.5f}\n" for q in r['paths']))
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(6,12))
    for b in fp['blocks']:ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#dedede',edgecolor='#777',lw=.4))
    for k in range(r['copies']):
        pp=[q['xy'] for q in r['paths'] if q['copy']==k];ax.plot(*zip(*pp),color='#357abd',alpha=.4,lw=.7)
        ax.scatter(*zip(*pp),c=range(r['stages']),cmap='viridis',s=15,zorder=3)
    ax.scatter(*r['root_um'],marker='*',s=160,c='red',zorder=5)
    ax.set(xlim=(0,fp['die'][2]),ylim=(0,fp['die'][3]),aspect='equal',xlabel='um',ylabel='um',title=f"{fp['name']} reset: {r['stages']} cycles; max hop {r['max_hop_um']} um")
    fig.tight_layout();fig.savefig(out.with_suffix('.png'),dpi=130);plt.close(fig)
    print(json.dumps({k:v for k,v in r.items() if k!='paths'}))
if __name__=='__main__':main()
