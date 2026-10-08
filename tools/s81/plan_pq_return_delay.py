#!/usr/bin/env python3
"""Join same-ODB return endpoint timing/topology into a selective HB4 sizing plan."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))


def plan(regions, timing, topology):
    if len(timing) != topology['count'] or len(timing) != 69*regions:
        raise ValueError('Expected every front-return capture in same-sized timing and topology inventory')
    rows={r['endpoint'].replace('\\',''):r for r in topology['endpoints']}
    if set(rows) != set(timing): raise ValueError('Timing/topology endpoint identity mismatch')
    selected=[];unsupported=[];already_met=[]
    # Worst slack changes across the retained actual-library loaded sweep.
    cases=[(3,119.108183,334.881317),(4,156.516676,454.61435)]
    for ep,t in sorted(timing.items()):
        row=rows[ep]
        if t['ff_ps'] >= 15:
            already_met.append(ep);continue
        if row['endpoint_master']!='DFFHQNx1_ASAP7_75t_R' or row['load_iterms']!=1 or row['bterm_count']!=0 or len(row['drivers'])!=1 or row['drivers'][0].get('master')!='BUFx2_ASAP7_75t_R':
            unsupported.append(dict(endpoint=ep,reason='Driver/load topology outside characterized bound',topology=row));continue
        for n,gain,cost in cases:
            # Reserve 1ps per new link for unmodeled local wire resistance;
            # final route must still meet actual +15ps SS/FF and link geometry.
            setup=t['ss_ps']-cost-n
            hold=t['ff_ps']+gain
            if setup>=15 and hold>=15:
                selected.append(dict(endpoint=ep,odb_endpoint=row['endpoint'],original_net=row['net'],
                    original_driver=row['drivers'][0],cells=n,master='HB4xp67_ASAP7_75t_R',
                    original_ss_ps=t['ss_ps'],original_ff_ps=t['ff_ps'],
                    screening_ss_ps=setup,screening_ff_ps=hold))
                break
        else: unsupported.append(dict(endpoint=ep,reason='No characterized chain fits both +15ps bounds',timing=t))
    import uarch_model
    model=uarch_model.s81_pq_return_delay_model(regions,dict(Counter(r['cells'] for r in selected)))
    return dict(schema='opentallas.s81.pq_return_delay_plan.v1',
        status='READY_FOR_PHYSICAL_CANDIDATE' if not unsupported else 'UNRESOLVED_ENDPOINTS',
        original_odb_sha256=topology['sha256'],regions=regions,minimum_slack_ps=15,
        selected=selected,already_met=already_met,unsupported=unsupported,model=model,
        physical_closed=False,adopted=False,
        limitations=['Cell sweep uses original BUFx2 and actual DFF load, input slew0..20ps, each new link capacitance<=0.78fF',
          'Keep original boundary clock contract; actual CTS/source arrival is not altered or presumed',
          'Remaining R2R hold and all other paths must independently pass',
          'Source-file hash binding does not by itself prove SS/FF refer to same ODB; retained query source manifest is required'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--regions',type=int,choices=(16,128),required=True)
    p.add_argument('--timing',type=Path,required=True);p.add_argument('--topology',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--retained-wire',action='store_true');a=p.parse_args()
    if a.output.exists():raise FileExistsError('Do not overwrite a prior verdict: '+str(a.output))
    r=plan(a.regions,json.loads(a.timing.read_text()),json.loads(a.topology.read_text()))
    source_paths=[a.timing,a.topology]
    if a.retained_wire:
        if a.regions!=16 or r['unsupported']:raise ValueError('Retained-wire plan only supports fully matched R16')
        gp=a.topology.parent/'r16_geometry.json';cp=a.topology.parent/'r16_selected_caps.json'
        geometry=json.loads(gp.read_text());caps=json.loads(cp.read_text());source_paths += [gp,cp]
        if geometry['sha256']!=r['original_odb_sha256'] or caps['source_odb_sha256']!=r['original_odb_sha256'] or caps['missing']:
            raise ValueError('Retained input inventory identity mismatch')
        factor=float(caps['C_UNIT'][0])*{'PF':1000,'FF':1}[caps['C_UNIT'][1]]
        cm={v['endpoint'].replace('\\',''):v['total_net_cap']*factor for v in caps['rows']}
        gm={v['endpoint'].replace('\\',''):v for v in geometry['endpoints']}
        for row in r['selected']:
            if row['cells']!=3 or not 0<=cm[row['endpoint']]<=5.75:raise ValueError('Outside retained-wire characterization')
            row['original_extracted_cap_fF']=cm[row['endpoint']]
            g=gm[row['endpoint']]
            row['original_capture_center_um']=g['capture_center_um']
            row['original_driver_center_um']=g['drivers'][0]['center_um']
            row['screening_ff_ps']=row['original_ff_ps']+117.875009
            row['screening_ss_ps']=row['original_ss_ps']-339.820038-row['cells']
            if min(row['screening_ff_ps'],row['screening_ss_ps'])<15:raise ValueError('Retained-wire screening bound failed')
        r['retained_wire_contract']=dict(original_cap_max_fF=5.75,retained_cap_delta_limit_fF=.78,new_net_cap_limit_fF=.78,new_link_span_limit_um=5,source='results/uarch/s81_pq_delay_chain_20261007/retained_wire_sweep/record.json')
    r['inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(status=r['status'],selected=len(r['selected']),unresolved=len(r['unsupported']),area=r['model']['area'])))
    return 0 if not r['unsupported'] else 1
if __name__=='__main__':raise SystemExit(main())
