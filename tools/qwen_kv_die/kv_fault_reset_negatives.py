#!/usr/bin/env python3
"""Causal corruption controls against the actual proposed reset branch graph."""
import argparse,copy,json
from pathlib import Path
from kv_fault_reset_validate import validate

def main():
    a=argparse.ArgumentParser();a.add_argument('--dir',type=Path,required=True);a.add_argument('--run',type=Path,required=True);v=a.parse_args();d=v.dir
    inv=json.loads((d/'inventory.json').read_text());c=json.loads((d/'candidate.json').read_text());m=json.loads((d/'reset_loads.json').read_text());p=json.loads((d/'reset_branch_candidate.json').read_text())
    cases=[]
    for mode in ('missing_target','wrong_depth','wrong_clock','wrong_native_pin','overlap','wrong_root'):
        bad=copy.deepcopy(p)
        if mode=='missing_target':bad['targets'].pop()
        elif mode=='wrong_depth':bad['stations'][0]['depth']+=1
        elif mode=='wrong_clock':bad['stations'][0]['clock']='n_clk_wrong'
        elif mode=='wrong_native_pin':bad['stations'][0]['input_xy'][0]+=1
        elif mode=='overlap':bad['stations'][1]['placement']=dict(bad['stations'][0]['placement'])
        elif mode=='wrong_root':bad['targets'][0]['root_id']='unknown_root'
        try:validate(v.run,inv,c,m,bad)
        except ValueError as e:cases.append(dict(mutant=mode,status='EXPECTED_REFUSAL',witness=str(e)));continue
        raise AssertionError('MUTANT_ACCEPTED '+mode)
    out=dict(status='SIX_ACTUAL_GRAPH_CORRUPTIONS_REFUSED',cases=cases,qualified_release=False)
    (d/'reset_geometry_negatives.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
