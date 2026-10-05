#!/usr/bin/env python3
"""W6 receiver protocol SPEC/oracle; not a producer, adapter RTL or live proof."""
import argparse,json
from pathlib import Path
ORDER=('rf_write_accept','mirror0_write','mirror1_write','W4_ACK_publish','W4_ACK_take','W6_visible','consumer','child_reverse','parent_reverse','reverse_CDC','drain_request','drain_response','retire')
def need(ok,msg):
 if not ok:raise ValueError(msg)
def identity(owner,slot):
 need(type(owner)is int and 0<=owner<2**46 and ((owner>>36)&7)<6,'owner46 NC6')
 need(type(slot)is int and 0<=slot<512,'RFslot9')
 return owner*512+slot

def verify(rows,*,expected_owner,expected_slot):
 """Single accepted frame SPEC trace; epoch is not synthesized into owner.

 Events must be captured from source ports/WCE in an admitted connected bench.
 Passing these consistency checks alone proves neither producer binding nor RTL.
 Reset-aborted traces must close reset/drain, never claim numerical retirement.
 """
 wanted=identity(expected_owner,expected_slot);seen={};prev=-1
 for r in rows:
  k=r['event'];c=r['edge'];need(type(c)is int and c>=0 and c>=prev,'ordered clock edges');prev=c
  need(identity(r['owner'],r['slot'])==wanted,'exact physical tuple mismatch')
  need(k not in seen,'duplicate event')
  if k=='runtime_reset':
   need(seen and 'retire' not in seen,'reset must name retained pending owner');seen[k]=c;continue
  if 'runtime_reset' in seen:
   sequence=('RF_reset_abort','reset_drain_request','reset_drain_response','reset_release')
   index=sum(x in seen for x in sequence);need(index<len(sequence) and k==sequence[index],'reset quarantine rejects stale normal ACK/consumer/reverse')
   need(c>max(seen.values()),'positive reset boundary')
   if k=='reset_drain_response':
    need(r.get('has_owner') is True and r.get('reset_scope') is True,'reset drain scope');need(r.get('levels')==[True]*9 and all(type(x)is bool for x in r['levels']),'all9 current source debts')
   seen[k]=c;continue
  index=len(seen);need(index<len(ORDER) and k==ORDER[index],'ordered physical ACK visibility consumer reverse')
  if k in ('mirror0_write','mirror1_write'):need(c==seen['rf_write_accept'],'both mirror WCE on actual accepted RF edge')
  elif index:
   need(c>max(seen.values()),'positive boundary edges')
  if k=='drain_response':
   need(r.get('has_owner') is True and r.get('reset_scope') is False,'normal drain scope');need(r.get('levels')==[True]*9 and all(type(x)is bool for x in r['levels']),'all9 current source debts')
  seen[k]=c
 need('retire' in seen or 'reset_release' in seen,'incomplete source boundary coverage')
 return dict(verdict='PASS_SPEC_TRACE_CONSISTENCY_ONLY',reset_aborted='runtime_reset' in seen,numerical_retirement='retire' in seen,hardware_qualified=False,producer_binding_verified=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--owner',type=lambda s:int(s,0),required=True);p.add_argument('--slot',type=int,required=True);a=p.parse_args();print(json.dumps(verify(json.loads(a.trace.read_text()),expected_owner=a.owner,expected_slot=a.slot),indent=2))
