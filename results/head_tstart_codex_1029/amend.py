#!/usr/bin/env python3
"""Attach current canonical external START declaration to an already composed HEAD copy. No compose rerun."""
import argparse, copy, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S
import landing_contract as LC

def amend(raw,side):
    out=copy.deepcopy(raw)
    net=out['clock']['landing_network']
    decl=LC.start_declaration(side['count_aligned']['start_pins'],
      {p['name']:p['type'] for p in out['partitions']},
      {tn:{q['name']:q['dir'] for q in t.get('clock',{}).get('landing_contract',{}).get('pins',[])} for tn,t in out['partition_types'].items()},
      {(e[s]['part'],e[s]['bus']) for e in net['edges'] for s in ('src','dst')})
    net['start_tree']=decl
    back=copy.deepcopy(out);back['clock']['landing_network'].pop('start_tree')
    before=copy.deepcopy(raw);before['clock']['landing_network'].pop('start_tree',None)
    assert back==before, 'only declaration may change'
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('sidecar');ap.add_argument('out');a=ap.parse_args()
    plan=Path(a.plan);side=json.loads(Path(a.sidecar).read_text()); raw=json.loads(plan.read_text());before=LC.check(S.Plan(raw,str(plan)),sidecar=side)
    out=amend(raw,side); after=LC.check(S.Plan(out,str(plan)),sidecar=side)
    Path(a.out).write_text(json.dumps(out,indent=1)+'\n')
    receipt=dict(schema='opentallas.head_tstart_receipt.v1',source_commit='c0fb5e87570dd796f66bd43a61a249dcd0573f5d',input_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),sidecar_sha256=hashlib.sha256(Path(a.sidecar).read_bytes()).hexdigest(),output_sha256=hashlib.sha256(Path(a.out).read_bytes()).hexdigest(),changed_only='clock.landing_network.start_tree',before=before,after=after)
    Path(a.out).with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    print(json.dumps(dict(before_errors=len(before['errors']),after_errors=len(after['errors']),start_tree=after.get('start_tree'))))
    if after['errors']:sys.exit(1)
