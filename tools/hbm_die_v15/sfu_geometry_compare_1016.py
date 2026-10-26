#!/usr/bin/env python3
"""Compare complete incident rectangle gaps for SFU/RF quarter alternatives.

Actual source624 transport is596 forward bits and516 return bits per group.
Rectangle gaps are lower bounds, never a substitute for source-pin route/STA.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hbm_globalfp as F


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract',default='/home/ubuntu/wt/hnl-0030/results/arch/hbm_die_v16/source_compact_0253/contract.json')
    ap.add_argument('--out',default='results/arch/hbm_die_v15/sfu_geometry_compare_1016.json')
    a=ap.parse_args();raw=Path(a.contract).read_bytes();c=json.loads(raw)
    rows=[];plans={}
    for name in ['compact_v6b_recovery','core4_rf36','core4_sfu2']:
        d=ROOT/'results/arch/hbm_die_v15'/name
        p=json.loads((d/'compact.P.json').read_text())
        # Corrected source-bound provisional exchange windows follow COLL.
        for q in ['SW','SE','NW','NE']:
            b=p['coll_'+q];x=b['x'] if q.endswith('W') else b['x']+b['w']-720
            y=b['y']+b['h']+742 if q.startswith('S') else b['y']-1462
            p['sucx_'+q]=dict(x=x,y=y,w=720,h=720)
        plans[name]=p
        sfr=[];ro=[];local=[]
        for q in ['SW','SE','NW','NE']:
            for g in range(4):
                gap=F.gap(p['sfucore_'+q],p[f'sfu_{q}{g}'])[0]
                # Even optimistic endpoints each get500um; interior48 relays
                # use their best measured stream reach420.977um.
                lower=max(1,math.ceil(max(0,gap-1000)/420.977)+1)
                sfr.append(dict(quarter=q,group=g,forward_bits=596,return_bits=516,
                                rectangle_gap_um=round(gap,3),
                                min_relays_at_universal500um=max(0,math.ceil(gap/500)-1),
                                min_relays_with_best_native48_interior=lower))
            gap=F.gap(p['sfucore_'+q],p['sucx_'+q])[0]
            ro.append(dict(quarter=q,bits=528,rectangle_gap_um=round(gap,3)))
        # All actual source quarter-core/pgslice data edges, not the old
        # aggregate SU_CORE links pointing at the firstslice placeholder.
        for e in c['edges']:
            s,t=e['source'][0],e['sink'][0]
            if ((s.startswith('sucore_') and t.startswith('su_')) or
                (t.startswith('sucore_') and s.startswith('su_'))) and s in p and t in p:
                gap=F.gap(p[s],p[t])[0]
                local.append(dict(source=e['source'],sink=e['sink'],bits=e['bits'],rectangle_gap_um=round(gap,3)))
        rows.append(dict(candidate=name,sfr=sfr,sfu_result_to_exchange=ro,actual_core_slice_edges=local,
                         sfr_bit_mm=sum(1112*x['rectangle_gap_um']/1000 for x in sfr),
                         ro_bit_mm=sum(528*x['rectangle_gap_um']/1000 for x in ro),
                         core_slice_bit_mm=sum(x['bits']*x['rectangle_gap_um']/1000 for x in local),
                         worst_sfr_gap_um=max(x['rectangle_gap_um'] for x in sfr),
                         worst_ro_gap_um=max(x['rectangle_gap_um'] for x in ro),
                         worst_core_slice_gap_um=max(x['rectangle_gap_um'] for x in local)))
    out=dict(schema='opentallas.hbm.sfu_geometry_compare.v1',qualification='LOWER_BOUNDS_ONLY_NOT_ADOPTED',
             source_contract=a.contract,source_contract_sha256=hashlib.sha256(raw).hexdigest(),
             candidates=rows,open=['actual source/sink pins and leaf views','obstacle-aware per-bit routes/clockreach',
                                  'full current cut and relay footprint allocation','compiler exact static cycles and measured native token cost'])
    (ROOT/a.out).write_text(json.dumps(out,indent=1)+'\n')
    for r in rows:
        print(json.dumps({k:v for k,v in r.items() if not isinstance(v,list)}))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(1,3,figsize=(21,9))
    for ax,row in zip(axes,rows):
        p=plans[row['candidate']]
        for n,b in p.items():
            if b['x']>14520 or b['y']>11820:continue
            special=n.startswith(('sfucore_SW','sucx_SW','sucore_SW','sfu_SW'))
            color='#f4cccc' if n.startswith('sfucore_SW') else '#fce5cd' if special else '#e6edf2'
            ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor=color,edgecolor='#667788',linewidth=.45))
            if special:ax.text(b['x']+b['w']/2,b['y']+b['h']/2,n,fontsize=6,ha='center')
        for g in range(4):
            _,s,t=F.gap(p['sfucore_SW'],p[f'sfu_SW{g}'])
            ax.plot([s[0],t[0]],[s[1],t[1]],color='#0066cc',linewidth=1.5)
        _,s,t=F.gap(p['sfucore_SW'],p['sucx_SW'])
        ax.plot([s[0],t[0]],[s[1],t[1]],color='#cc0000',linewidth=1.5)
        ax.set(xlim=(0,14520),ylim=(0,11820),aspect='equal',xlabel='um',ylabel='um',
               title=row['candidate']+'\nSFR max '+str(round(row['worst_sfr_gap_um']))+'um / RO max '+str(round(row['worst_ro_gap_um']))+'um')
    fig.suptitle('HBM 780mm2 coherent quarter alternatives: blue596+516-bit LG legs; red528-bit result leg\nStraight rectangle gaps are LOWER BOUNDS; crossings of hard frames are NOT admissible routes')
    fig.tight_layout();fig.savefig(ROOT/'results/arch/hbm_die_v15/sfu_geometry_compare_1016.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
