#!/usr/bin/env python3
"""Emit review-only reset netlist/place fragments, never modify the input case."""
import argparse,copy,hashlib,json
from pathlib import Path

def emit(c,m,p,out):
    if p.get('qualified_release') is not False:raise ValueError('Unexpected reset qualification')
    outputs={(n['root_id'],n['instance']):f"{n['output_bit'][0]}[{n['output_bit'][1]}]" for n in m['existing_reset_nodes']}
    lines=['// REVIEW ONLY: clock phase/geometry, POR/admission and reset contracts OPEN.']
    places=['# REVIEW ONLY: exact new reset cells; native clock tree not generated.','set _blk [ord::get_db_block]']
    for n in p['stations']:
        key=(n['root_id'],n['id']);source=outputs[(n['root_id'],n['source'])];net='n_'+n['id'];outputs[key]=net+'[0]'
        lines.append(f"wire [0:0] {net};")
        lines.append(f"qkd_rlys_1 {n['id']} (.ck({n['clock']}), .a({source}), .b({net}));")
        pl=n['placement'];places.append(f"ot_mts::place [$_blk findInst {n['id']}] {pl['x']:.6f} {pl['y']:.6f} R0")
    rewrites={t['node']:outputs[(t['root_id'],t['source'])] for t in p['targets']}
    candidate=copy.deepcopy(c)
    for n in candidate['nodes']:n['reset']=rewrites[n['id']]
    candidate['reset_branch_review_only']=True
    candidate['reset_branch_requirements']=p['requirements']
    out.mkdir(parents=True,exist_ok=True)
    (out/'fault_reset_branches.vh').write_text('\n'.join(lines)+'\n')
    (out/'fault_reset_branches.place.tcl').write_text('\n'.join(places)+'\n')
    (out/'candidate_with_reset_branches.json').write_text(json.dumps(candidate,indent=1)+'\n')
    receipt=dict(qualified_release=False,status='REVIEW_ONLY_FRAGMENTS_NOT_INSTALLED',stations=len(p['stations']),rewired_new_fault_reset_ports=len(rewrites),old_case_modified=False,clock_pin_connections='Named original clock nets only; no native branch clock tree or phase qualification',files={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in ('fault_reset_branches.vh','fault_reset_branches.place.tcl','candidate_with_reset_branches.json')})
    (out/'fragment_receipt.json').write_text(json.dumps(receipt,indent=1)+'\n');return receipt

def main():
    a=argparse.ArgumentParser();a.add_argument('--dir',type=Path,required=True);v=a.parse_args();d=v.dir
    print(json.dumps(emit(json.loads((d/'candidate.json').read_text()),json.loads((d/'reset_loads.json').read_text()),json.loads((d/'reset_branch_candidate.json').read_text()),d/'review_fragments')))
if __name__=='__main__':main()
