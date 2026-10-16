#!/usr/bin/env python3
"""Necessary SU-band cuts for obstacle-avoiding SFU station placement.

This diagnostic treats parent hard frames as routing blockages; higher-metal
feedthrough needs actual OBS/layer/PG evidence before that assumption can change.
"""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',default='results/arch/hbm_die_v15/core4_sfu2')
    ap.add_argument('--contract',default='/home/ubuntu/wt/hnl-0030/results/arch/hbm_die_v16/source_compact_0253/contract.json')
    ap.add_argument('--out',default='results/arch/hbm_die_v15/core4_sfu2/sfu_barrier_cuts.json')
    a=ap.parse_args();p=json.loads((ROOT/a.plan/'compact.P.json').read_text());raw=Path(a.contract).read_bytes();c=json.loads(raw)
    for q in ['SW','SE','NW','NE']:
        b=p['coll_'+q];p['sucx_'+q]=dict(x=b['x'] if q.endswith('W') else b['x']+b['w']-720,y=b['y']+b['h']+742 if q.startswith('S') else b['y']-1462,w=720,h=720)
    links=[]
    for q in ['SW','SE','NW','NE']:
        for g in range(4):links.append(dict(source='sfucore_'+q,sink=f'sfu_{q}{g}',bits=1112,kind='596 forward +516 return SFR payload'))
        links.append(dict(source='sfucore_'+q,sink='sucx_'+q,bits=528,kind='SFU result; new fixed transport required'))
    for e in c['edges']:
        s,t=e['source'][0],e['sink'][0]
        if ((s.startswith('sucore_') and t.startswith('su_')) or (t.startswith('sucore_') and s.startswith('su_'))) and s in p and t in p:
            links.append(dict(source=s,sink=t,bits=e['bits'],kind='actual core/slice '+e['source'][1]))
    rows=[]
    for q in ['SW','SE','NW','NE']:
        # Adjacent SM rows bound the entire band; a SU frame leaves only top
        # and bottom channels at a vertical cut through its interior.
        su=p['su_'+q+'1'];xc=su['x']+su['w']/2
        below=[b['y']+b['h'] for n,b in p.items() if n.startswith('sm_') and b['x']<xc<b['x']+b['w'] and b['y']+b['h']<=su['y']]
        above=[b['y'] for n,b in p.items() if n.startswith('sm_') and b['x']<xc<b['x']+b['w'] and b['y']>=su['y']+su['h']]
        low=max(below);high=min(above);free=(su['y']-low)+(high-su['y']-su['h'])
        crossing=[]
        for e in links:
            if not e['source'].startswith(('sfucore_'+q,'sucore_'+q,'su_'+q)):continue
            s,t=p[e['source']],p[e['sink']]
            def side(b):return -1 if b['x']+b['w']<xc else 1 if b['x']>xc else 0
            if side(s)*side(t)==-1:crossing.append(e)
        demand=sum(e['bits'] for e in crossing);ratio=demand/(14.0625*free)
        rows.append(dict(quarter=q,cut_x_um=xc,sm_bounded_y_um=[low,high],hard_su_y_um=[su['y'],su['y']+su['h']],
                         free_channel_um=round(free,6),crossing=crossing,known_demand_bits=demand,
                         tracks_per_um=14.0625,utilization=round(ratio,6),passes_060=ratio<=.6,
                         channel_needed_at_060_um=round(demand/(14.0625*.6),6)))
    out=dict(schema='opentallas.hbm.sfu_barrier_cut.v1',qualification='CONDITIONAL_NECESSARY_CUT_ONLY_NO_ADOPTION',
             source_contract_sha256=hashlib.sha256(raw).hexdigest(),rows=rows,
             station_leaf_count=736*13,station_reset_ff_added=736*15,
             scope='Hard frames obstruct the selected obstacle-avoiding route plane. No higher-metal feedthrough is qualified.',
             excluded=['other incident traffic and clocks','programme474 macro candidate homes and local clocks','SKV/collective source homes and roots','actual endpoint views/OBS/PG','reset glue footprint and mapped timing','fixed result transport stages and compiler/cost'])
    (ROOT/a.out).write_text(json.dumps(out,indent=1)+'\n')
    for row in rows:print(row['quarter'],row['known_demand_bits'],row['free_channel_um'],row['utilization'],row['passes_060'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(15,5))
    for n,b in p.items():
        if b['x']>14520 or not 5000<b['y']<8500:continue
        ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#dce6ef',edgecolor='#586e7d',linewidth=.7))
        if n.endswith('SW') or n.startswith(('su_SW','sfu_SW')):ax.text(b['x']+b['w']/2,b['y']+b['h']/2,n,ha='center',fontsize=7)
    row=rows[0];x=row['cut_x_um'];lo,hi=row['sm_bounded_y_um'];yb,yt=row['hard_su_y_um']
    ax.plot([x,x],[lo,hi],color='red',linewidth=2)
    ax.plot([x,x],[lo,yb],color='green',linewidth=6);ax.plot([x,x],[yt,hi],color='green',linewidth=6)
    ax.set(xlim=(0,14520),ylim=(lo-200,hi+200),aspect='equal',xlabel='um',ylabel='um',title=f"Middle-SFU SW hard-frame cut: known{row['known_demand_bits']} bits /{row['free_channel_um']:g}um channel /14.0625 tracks per um ={row['utilization']:.3f} (limit0.60)\nNecessary cut only; programme474 macros, SKV/collective clocks, other traffic, reset glue not yet included")
    fig.tight_layout();fig.savefig((ROOT/a.out).with_suffix('.png'),dpi=160);plt.close(fig)
if __name__=='__main__':main()
