#!/usr/bin/env python3
"""HEAD local CTS COPY: one regional input, actual signed core means, no early external ports."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import schema as S
import gen_phys as G


def apply(raw, tt_ps=700., ff_ps=570.):
    if not raw.get('clock',{}).get('landing_network'):
        raise ValueError('one-entry COPY requires the composed fixed-latency landing network')
    if not 0<ff_ps<=tt_ps:
        raise ValueError('require0 < FF <= TT insertion budget')
    out=copy.deepcopy(raw);out['budgets']['tap_pitch_um']=100000.
    out['clock']['insertion_ps']=tt_ps;out['clock']['insertion_ff_ps']=ff_ps
    report={}
    for tn,t in out['partition_types'].items():
        c=t.setdefault('clock',{});before=copy.deepcopy(c)
        cores=[q for q in c.get('taps',[]) if q.get('kind')=='core']
        for k in ('taps','core_taps','tap_mode','sink_sites_um','tap_pitch_um','tap_edge_y_um','tap_recentre','note'):
            c.pop(k,None)
        if t.get('hard_cores'):
            if not cores or any('insertion_ff_ps' not in q or not q.get('budget_owner','').startswith('SIGNED') for q in cores):
                raise ValueError(f'{tn}: actual SIGNED TT/FF core means required')
            c.update(taps=cores,core_taps='internal')
        c['insertion_ps']=tt_ps;c['insertion_ff_ps']=ff_ps
        c['insertion_basis']='parent_budget one-entry regional CTS trial; publish actual routed mean before release'
        moved=[]
        for q in c.get('landing_contract',{}).get('pins',[]):
            if q.get('kind')=='clock' and q.get('dir')=='out':
                old=q.get('source_clock_port','clk')
                if old=='clk' or old.startswith(('clk_t','clk_c')):
                    q['source_clock_port']='clk';moved.append([q['name'],old,'clk'])
                else:raise ValueError(f'{tn}: export source {old} is not a removed region tap')
        t['note']=t.get('note','')+' | HEAD one-entry local CTS COPY (trial); data cycles unchanged'
        report[tn]=dict(internal_core_means=len(cores),exports=moved,tap_um=c.get('tap_um'))
    p=S.Plan(out)
    for tn in out['partition_types']:
        if len(S.tap_grid(p,tn))!=1 or S.core_taps(p,tn):
            raise ValueError(f'{tn}: still has multiple external clock inputs')
        G.core_mean_contract_options(p,tn,trial=True)
    err=S.validate(out)
    if err:raise ValueError(err[:10])
    return out,report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--tt-ps',type=float,default=700.);ap.add_argument('--ff-ps',type=float,default=570.)
    a=ap.parse_args();raw,report=apply(json.loads(a.plan.read_text()),a.tt_ps,a.ff_ps)
    a.out.write_text(json.dumps(raw,indent=1)+'\n')
    a.out.with_suffix('.one_entry.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
