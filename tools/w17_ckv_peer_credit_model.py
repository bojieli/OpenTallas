#!/usr/bin/env python3
"""Finite peer ownership model; actual CKV ACK/route binding remains prerequisite."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Protocol:
 def __init__(self,bits=2):
  self.bits=bits;self.active=None;self.pending=set();self.hops=set();self.accepted=set();self.final=False
 def begin(self,g):
  if self.active is not None or self.pending or self.hops or not 0<=g<2**self.bits:raise ValueError('epoch reuse before actual drain')
  self.active=g;self.accepted=set();self.final=False
 def reserve(self,s,row):
  if self.active is None or not 0<=s<4 or not 0<=row<512:raise ValueError('invalid source')
  tokens={(self.active,s,d,row) for d in range(4) if d!=s}
  if tokens&(self.pending|self.accepted):raise ValueError('duplicate row copies')
  self.pending|=tokens;self.hops|=tokens
  return tokens
 def depart(self,t):
  if t not in self.hops:raise ValueError('unowned hop departure')
  self.hops.remove(t) # FIFO departure never releases endpoint-held credit.
 def store_ack(self,t):
  if t[0]!=self.active or t not in self.pending or t in self.hops:raise ValueError('stale/duplicate/premature stored ACK')
  self.pending.remove(t);self.accepted.add(t)
 def close(self):
  if self.pending or self.hops or not self.final:raise ValueError('prelease before endpoint ACK/final attention')
  self.active=None

def build():
 p=Protocol();p.begin(0);tokens=p.reserve(0,16)
 for t in tokens:p.depart(t)
 assert len(p.pending)==3 and not p.hops
 rejects=[]
 def reject(name,fn):
  try:fn()
  except ValueError:rejects.append(name);return
  raise AssertionError(name)
 reject('FIFOdeparture_not_rowACK',p.close);reject('no_epoch_wrap_while_pending',lambda:p.begin(0));reject('wrong_generation_ACK',lambda:p.store_ack((1,0,1,16)))
 for t in tokens:p.store_ack(t)
 reject('duplicate_ACK',lambda:p.store_ack(next(iter(tokens))));reject('ACKs_without_final_attention',p.close)
 p.final=True;p.close();p.begin(0) # Wrap safe only after all ACKs and final consumer.
 total=0
 for row in range(512):
  # Actual ownership may be skewed; selected global row belongs to one source.
  ts=p.reserve(row%4,row)
  for t in ts:p.depart(t);p.store_ack(t);total+=1
 assert total==1536;p.final=True;p.close()
 source='d879422df';path='results/rtl/w17_connected_token_preparation_20261001/ckv_peer_epoch_options.json';raw=subprocess.check_output(['git','show',source+':'+path],cwd=ROOT)
 return dict(status='PASS_FINITE_OWNERSHIP_MODEL_ACTUAL_ACK_BINDING_REQUIRED',source_options=dict(commit=source,path=path,sha256=hashlib.sha256(raw).hexdigest()),model_cases=dict(rejected=rejects,completed_destination_ACKs=total,wrap_allowed_only_after_drained_and_final=True),storage_and_ports=dict(existing_collector_rows_per_rank=512,row_bits=2304,no_new_row_buffer_claim=True,copy_tracking_alternatives='Per source 512x3 outstanding bits=1536bits maximum, or ordered per-destination counters with proved lossless exactly-once ACK; counters alone cannot reject duplicate/stale ACK.',per_copy_ACK_fields='generation E + source2 + destination2 + selectionrank10 + status; GID21 if actual identity requires it',RX='3 actual acceptance ports need atomic valid/ready+epoch compare before collector write; currently no ACK/ready/generation',actual_physical_ack_ports=None,actual_epoch_width=None),serialization=dict(payload_bits_per_row=2304,rank_gid_bits=31,copies=1536,payload_total_bits=3538944,formula='For each directed edge e, row_flits=ceil((2335+E+framing_bits)/payload_flit_bits[e]); sum row_flits*copy_route_incidence[e] + ACKflits on actual reverse edges. Service cycles require reserved finite VC calendar, receiver seats, CDC/hop latency and final stored ACK. No transfer rate chosen.',all_directed_routes=None,flit_widths=None,ACK_reverse_calendar=None,credits_and_reassembly_cost=None),whole_latency=dict(composition='old C/P/W/B retirement + all old peer destination stored ACKs/hop/reverse credits + all4 clear barrier + 9 actual burst-visible WR fence + new fetch/peer service + final descriptor/attention/output/collective drain + reverse consumer credit',finite_service_bound=None,can_overlap=False,reason='No actual event provider or reserved service calendar bound yet; no free overlap or guessed timeout.'),actual_path_qualified=False,RTL_changed=False,launch_allowed=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();r=build();assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r['model_cases'])
