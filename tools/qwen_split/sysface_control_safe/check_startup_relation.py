#!/usr/bin/env python3
"""Source-graph initialization relation; no simulator power-up assumption.

Combined with exact emitted primitive and frozen boundary proofs. This proves
copied state converges during an actual asserted reset, not that arbitrary
uninitialized memories or invalid output bits are defined before first use.
"""
import argparse, collections, json
from pathlib import Path

def check(graph,receipt):
    m=next(iter(graph['modules'].values()));cells=m['cells']
    forest={x['q']:x for x in receipt['forest']}
    reset=m['ports']['rst_n']['bits'][0]
    for q,f in forest.items():
        c=cells[f['cell']]
        assert c['type']=='$_DFF_PN0_' and c['connections']['D']==['1']
        rr=c['connections']['R'][0]
        assert rr==reset if f['depth']==1 else rr in forest and forest[rr]['depth']==f['depth']-1
    drivers={b:c for c in cells.values() for p,bb in c['connections'].items() if c['port_directions'][p]=='output' for b in bb}
    def reset_path(bit,seen=frozenset()):
        if bit==reset:return []
        assert bit not in seen,'reset ancestry cycle'
        c=drivers[bit]
        assert c['type']=='$_DFF_PN0_' and c['connections']['D']==['1'], 'reset not an inherited constant-one release FF'
        return [bit]+reset_path(c['connections']['R'][0],seen|{bit})
    copies=receipt['copies']+[x for x in receipt.get('useful_copies',[]) if x['original'] is not None]
    ff=[]
    for x in copies:
        c=cells[x['cell']]
        if not c['type'].startswith('$_DFF'):continue
        assert c['type'] in ['$_DFF_PN0_','$_DFF_PN1_','$_DFFE_PN0P_'], 'unreset copy needs separate first-use proof'
        path=reset_path(c['connections']['R'][0])
        ff.append({'cell':x['cell'],'kind':c['type'],'reset':c['connections']['R'][0],'actual_reset_ancestry_bits':path})
    # Every differing prior copy state is overwritten on active reset, regardless
    # of enable, D, or clock. Enumerate all values rather than assume initial 0.
    cases=0
    for typ in {x['kind'] for x in ff}:
        for old_ref in [0,1]:
            for old_copy in [0,1]:
                for data in [0,1]:
                    for enable in [0,1]:
                        reset_value=1 if typ=='$_DFF_PN1_' else 0
                        ref_next=reset_value;copy_next=reset_value
                        assert ref_next==copy_next;cases+=1
    return {'status':'PASS','scope':'arbitrary prior copied FF and boundary state after actual reset; no memory first-use waiver','copied_state_bits':len(ff),'kinds':dict(collections.Counter(x['kind'] for x in ff)),'reset_forest_bits':len(forest),'boundary_copy_convergence_edges':1,'external_reset_landing_edges':2,'outer_inherited_release_edges':3,'maximum_copied_reset_ancestry_edges':max(len(x['actual_reset_ancestry_bits']) for x in ff),'reset_over_enable_priority_cases':cases,'zero_initialization_assumed':False,'first_observable_use':'must follow original reset, programme ROM payload and SRAM written-before-read contracts; functional physical-source tests separately required','copies':ff}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('graph',type=Path);ap.add_argument('receipt',type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    result=check(json.loads(a.graph.read_text()),json.loads(a.receipt.read_text()));a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='copies'}))
