#!/usr/bin/env python3
"""Audit generic synthesized DMR storage, not a placed/library signoff proof."""
import argparse,json

def audit(path):
 d=json.load(open(path));top=d['modules']['ot_qwen_ctrl_write_ledger'];roots=[]
 for g in range(2):
  name=f'g_copy[{g}].u';c=top['cells'][name];leaf=d['modules'][c['type']]
  ff=[v for v in leaf['cells'].values() if 'DFF' in v['type']]
  bits=sum(len(v['connections'].get('Q',[])) for v in ff)
  assert bits==7419,(g,bits)
  state=c['connections']['state'];assert len(state)==7419
  assert len(set(state))==7419,'aliased state within replica'
  roots.append(set(state))
 assert not(roots[0]&roots[1]),'shared/aliased replica state'
 guards=[top['netnames'][s]['bits'][0] for s in ['trip_seen','permit_state']]
 assert len(set(guards))==2 and not(set(guards)&(roots[0]|roots[1]))
 return {'pass':True,'stage':'generic synth -noabc; not placed independence','replicas':2,'ff_per_replica':7419,'guard_ff':2,'total_ff':14840,'independent_state_bits':14838,'library_mapped_check_required':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('json');a=p.parse_args();print(json.dumps(audit(a.json),indent=2,sort_keys=True))
