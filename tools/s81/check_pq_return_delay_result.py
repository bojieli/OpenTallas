#!/usr/bin/env python3
"""Record timing, topology and extracted wire-bound checks for one explicit ECO."""
import argparse,json,re
from pathlib import Path


def wire_caps(path,targets):
    names={};found={};factor=None;mapping=False
    with path.open() as f:
        for line in f:
            s=line.split()
            if not s:continue
            if s[0]=='*C_UNIT':
                factor=float(s[1])*{'PF':1000,'FF':1,'NF':1e6}[s[2].upper()]
            elif s[0]=='*NAME_MAP':mapping=True
            elif mapping and re.fullmatch(r'\*\d+',s[0]) and len(s)>1:
                if s[1] in targets:names[s[0]]=s[1]
            elif s[0]=='*D_NET':
                mapping=False;n=names.get(s[1],s[1])
                if n in targets:
                    if factor is None:raise ValueError('Missing SPEF capacitance unit')
                    found[n]=float(s[2])*factor
    missing=targets-set(found)
    if missing:raise ValueError('Missing extracted station nets: '+repr(sorted(missing)[:10]))
    return found


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();w=a.work
    plan=json.loads((w/'plan.json').read_text());cs=json.loads((w/'corner_sta.json').read_text());log=(w/'eco.log').read_text()
    base=w/'orfs/results/asap7/pq_return_delay/base';targets=set()
    for i,row in enumerate(plan['selected']):
        targets.add(row['original_net']);targets.update(f'pq_return_hold_e{i:05d}_n{k}' for k in range(row['cells']))
    cap=wire_caps(base/'6_final.spef',targets)
    new_caps={k:v for k,v in cap.items() if k.startswith('pq_return_hold_')}
    retained={r['original_net']:r['original_extracted_cap_fF'] for r in plan['selected']}
    delta={k:cap[k]-v for k,v in retained.items()}
    deviations={k:dict(measured_fF=v,kind='new_link_over_bound') for k,v in new_caps.items() if v>.78}
    deviations.update({k:dict(delta_fF=v,kind='retained_link_delta_outside_bound') for k,v in delta.items() if abs(v)>.78})
    nv=re.findall(r'Number of violations = (\d+)',log)
    topology=f"PQ_DELAY_TOPOLOGY_PASS endpoints={len(plan['selected'])} cells={plan['model']['area']['cell_count']} placement_checked=1" in log and 'PQ_DELAY_ROUTE_DONE' in log
    r=dict(ss_ps=cs['setup_ss']['worst_slack_ps'],ff_ps=cs['hold_ff']['worst_slack_ps'],drc=int(nv[-1]) if nv else None,
        source_odb_sha256=plan['original_odb_sha256'],added_cells=plan['model']['area']['cell_count'],
        added_cell_area_um2=plan['model']['area']['added_cell_um2'],added_cycles=0,
        topology_and_placement_pass=topology,extracted_station_nets=len(cap),max_station_wire_cap_fF=max(cap.values()),
        model_wire_bound_met=not deviations,
        max_new_link_cap_fF=max(new_caps.values()),max_abs_retained_cap_delta_fF=max(abs(v) for v in delta.values()),
        model_bound_deviations=deviations,
        errors=cs['setup_ss'].get('errors',[])+cs['hold_ff'].get('errors',[]),
        orfs_dir=str(w/'orfs'),corner_sta=str(w/'corner_sta.json'),
        post_sdc=['physical/s81_pq_return_delay/signoff.sdc'],adopted=False,
        production_hold='Standalone PHW6/SAW8/KMAX256 screen; no production parent binding or performance adoption')
    r['timing_drc_closed']=r['ss_ps'] is not None and r['ff_ps'] is not None and r['ss_ps']>=15 and r['ff_ps']>=15 and r['drc']==0 and not r['errors']
    r['verdict']='PASS_STANDALONE_MECHANISM' if r['timing_drc_closed'] and topology and r['model_wire_bound_met'] else 'FAIL_OR_MODEL_BOUND_DEVIATION'
    dest=w/'result.json'
    if dest.exists():raise FileExistsError('Do not overwrite prior verdict')
    dest.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
