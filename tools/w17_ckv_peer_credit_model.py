#!/usr/bin/env python3
"""Finite peer ownership model; actual CKV ACK/route binding remains prerequisite."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Protocol:
 """Synthetic requirements oracle, never an actual consumer or route provider."""
 def __init__(self,bits=2):
  self.bits=bits;self.active=None
 def begin(self,g,owners,forward,reverse):
  if self.active is not None or not 0<=g<2**self.bits:raise ValueError('epoch reuse before drain')
  if set(owners)!=set(range(512)) or any(type(v)!=int or not 0<=v<4 for v in owners.values()):raise ValueError('expected512 selected IDs/owners missing')
  pairs={(a,b) for a in range(4) for b in range(4) if a!=b}
  if set(forward)!=pairs or set(reverse)!=pairs or any(not x for x in list(forward.values())+list(reverse.values())):raise ValueError('all directed forward/reverse routes required')
  self.active=g;self.owners=dict(owners);self.forward=forward;self.reverse=reverse
  self.expected={(g,s,d,row) for row,s in owners.items() for d in range(4) if d!=s}
  self.pending=set();self.sent=set();self.accepted=set();self.forward_pending={};self.reverse_pending={};self.visible=set();self.consumer_requirements=False
 def reserve(self,s,row):
  if self.active is None or self.owners.get(row)!=s:raise ValueError('unexpected selected row/owner')
  tokens={(self.active,s,d,row) for d in range(4) if d!=s}
  if tokens&self.sent:raise ValueError('duplicate copies')
  self.sent|=tokens;self.pending|=tokens
  for t in tokens:self.forward_pending[t]=list(self.forward[(s,t[2])])
  return tokens
 def depart(self,t,hop):
  q=self.forward_pending.get(t,[])
  if not q or q[0]!=hop:raise ValueError('wrong/unowned forward hop')
  q.pop(0)
 def stored(self,t):
  if t[0]!=self.active or t not in self.pending or self.forward_pending[t] or t in self.reverse_pending:raise ValueError('stale RX or premature/duplicate stored ACK')
  self.reverse_pending[t]=list(self.reverse[(t[2],t[1])])
 def ack_depart(self,t,hop):
  q=self.reverse_pending.get(t,[])
  if not q or q[0]!=hop:raise ValueError('wrong/unowned reverse ACK hop')
  q.pop(0)
 def store_ack(self,t):
  if t not in self.reverse_pending or self.reverse_pending[t] or t not in self.pending:raise ValueError('missing reverse ACK drain')
  self.pending.remove(t);self.accepted.add(t)
 def write_visible_requirement(self,sector):
  if type(sector)!=int or not 0<=sector<9 or sector in self.visible:raise ValueError('duplicate/range visible fence')
  self.visible.add(sector)
 def close(self):
  if self.accepted!=self.expected or self.pending or any(self.forward_pending.values()) or any(self.reverse_pending.values()):raise ValueError('missing expected row/ACK/hop drain')
  if self.visible!=set(range(9)):raise ValueError('missing nine actual visible WR requirements')
  if not self.consumer_requirements:raise ValueError('final consumer requirements not supplied')
  self.active=None

def build():
 # Three-hop forward and reverse fixtures stress ordering, NOT actual product routes.
 routes={(a,b):['fixture0','fixture1','fixture2'] for a in range(4) for b in range(4) if a!=b}
 owners={r:r%4 for r in range(512)};p=Protocol();p.begin(0,owners,routes,routes);rejects=[]
 def reject(name,fn):
  try:fn()
  except ValueError:rejects.append(name);return
  raise AssertionError(name)
 p.consumer_requirements=True;reject('zero_reserved_rows',p.close)
 for i in range(9):p.write_visible_requirement(i)
 reject('missing_row_coverage_even_with_fences',p.close)
 ts=p.reserve(0,0);t=next(iter(ts));p.depart(t,'fixture0')
 reject('one_hop_departure_not_all_hops',lambda:p.stored(t))
 reject('stale_RX',lambda:p.stored((1,0,t[2],0)))
 reject('wrong_owner',lambda:p.reserve(1,0))
 reject('no_wrap_pending',lambda:p.begin(0,owners,routes,routes))
 total=0
 for row in range(512):
  tokens=ts if row==0 else p.reserve(row%4,row)
  for token in tokens:
   while p.forward_pending[token]:p.depart(token,p.forward_pending[token][0])
   p.stored(token)
   reject('reverse_ACK_not_drained' if total==0 else 'reverse_pending_'+str(total),lambda token=token:p.store_ack(token)) if total==0 else None
   while p.reverse_pending[token]:p.ack_depart(token,p.reverse_pending[token][0])
   p.store_ack(token);total+=1
  if row==0:reject('only_one_row_three_ACKs_not_full_coverage',p.close)
 reject('duplicate_ACK',lambda:p.store_ack(t));p.visible.remove(8);reject('missing_ninth_visible_WR',p.close);p.write_visible_requirement(8)
 p.consumer_requirements=False;reject('missing_final_consumer_requirements',p.close);p.consumer_requirements=True;p.close()
 p.begin(0,owners,routes,routes);reject('reused_epoch_still_requires_full_coverage',p.close)
 source='d879422df';path='results/rtl/w17_connected_token_preparation_20261001/ckv_peer_epoch_options.json';raw=subprocess.check_output(['git','show',source+':'+path],cwd=ROOT)
 return dict(status='PASS_SYNTHETIC_COVERAGE_FENCE_REVERSE_ACK_REQUIREMENTS_ACTUAL_PROVIDERS_UNBOUND',source_options=dict(commit=source,path=path,sha256=hashlib.sha256(raw).hexdigest()),model_cases=dict(rejected=rejects,completed_destination_ACKs=total,wrap_allowed_only_after_drained_and_final=True,route_fixture='Three synthetic ordered hops each way, not product topology',consumer_fixture='Boolean requirements only, NOT actual final completion provider',coverage_fixture='Synthetic512 ID-to-owner map, actual program selection/ownership binding required',historical_model='316884ae0 copy ownership was insufficient for barrier: zero-row closure possible; original receipt retained'),storage_and_ports=dict(existing_collector_rows_per_rank=512,row_bits=2304,no_new_row_buffer_claim=True,copy_tracking_alternatives='Per source 512x3 outstanding bits=1536bits maximum, or ordered per-destination counters with proved lossless exactly-once ACK; counters alone cannot reject duplicate/stale ACK.',per_copy_ACK_fields='generation E + source2 + destination2 + selectionrank10 + status; GID21 if actual identity requires it',RX='3 actual acceptance ports need atomic valid/ready+epoch compare before collector write; currently no ACK/ready/generation',actual_physical_ack_ports=None,actual_epoch_width=None),serialization=dict(payload_bits_per_row=2304,rank_gid_bits=31,copies=1536,payload_total_bits=3538944,formula='For each directed edge e, row_flits=ceil((2335+E+framing_bits)/payload_flit_bits[e]); sum row_flits*copy_route_incidence[e] + ACKflits on actual reverse edges. Service cycles require reserved finite VC calendar, receiver seats, CDC/hop latency and final stored ACK. No transfer rate chosen.',all_directed_routes=None,flit_widths=None,ACK_reverse_calendar=None,credits_and_reassembly_cost=None),whole_latency=dict(composition='old C/P/W/B retirement + all old peer destination stored ACKs/hop/reverse credits + all4 clear barrier + 9 actual burst-visible WR fence + new fetch/peer service + final descriptor/attention/output/collective drain + reverse consumer credit',finite_service_bound=None,can_overlap=False,reason='No actual event provider or reserved service calendar bound yet; no free overlap or guessed timeout.'),actual_path_qualified=False,RTL_changed=False,launch_allowed=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();r=build();assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r['model_cases'])
