#!/usr/bin/env python3
"""RD64 old-state/control calendar and native VM batch census; no FP arithmetic/RTL/job."""
from collections import Counter, deque
from pathlib import Path
import argparse, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'results/uarch/dsrom_rd64_vm_calendar_20261003'

def norm(t):
 p,r,lo,k,n=t
 for _ in range(5):
  if not(lo==0 and ((1<<k)&63)>=n) and not((lo>>k)&1) and lo+((1<<k)&63)>=n:k=(k+1)&7
 return p,r,lo,k,n

def complete(t):return t[2]==0 and ((1<<t[3])&63)>=t[4]
def sibling(a,b):return a[:2]==b[:2] and a[3:]==b[3:] and (a[2]^b[2])==((1<<a[3])&31)
def parent(a,b):return norm((a[0],a[1],min(a[2],b[2]),(a[3]+1)&7,a[4]))

def tag(t):
 if not isinstance(t,tuple) or len(t)!=5:raise ValueError('tag fields')
 for v,upper in zip(t,(8,65536,32,8,32)):
  if type(v) is not int or not 0<=v<upper:raise ValueError('tag width')
 if t[4]==0:raise ValueError('healthy schedule requires positive actual nseg certificate')
 return norm(t)

class Node:
 """Input accepted at edgeN; step returns RST1 output sampled by next stage at this edge."""
 def __init__(self):
  self.q=[deque(),deque()];self.age=[0,0];self.pipe=[None]*5;self.ap=[False]*5
  self.by=None;self.rst=None;self.peak=[0,0];self.edge=0
 def step(self,a=None,b=None):
  output=self.rst;old_wire=self.pipe[4] if self.pipe[4] is not None else self.by
  aa=self.q[0][0] if self.q[0] else None;bb=self.q[1][0] if self.q[1] else None
  add=aa is not None and bb is not None and sibling(aa,bb);free=not self.ap[3]
  fa=not add and aa is not None and free and (complete(aa) or bb is not None or self.age[0]>=2 or len(self.q[0])==64)
  fb=not add and not fa and bb is not None and free and (complete(bb) or self.age[0]>=2 or self.age[1]>=2 or len(self.q[1])==64)
  # Capture old pipeline/bypass before NBA-like updates; never use same-edge push.
  newpipe=parent(aa,bb) if add else None;newby=aa if fa else bb if fb else None
  for i,(incoming,pop) in enumerate(zip((a,b),(add or fa,add or fb))):
   old=len(self.q[i])
   if incoming is not None and old==64 and not pop:raise ValueError('RD64 overflow')
   self.age[i]=0 if pop or not old else min(31,self.age[i]+1)
   if pop:self.q[i].popleft()
   if incoming is not None:self.q[i].append(tag(incoming))
   self.peak[i]=max(self.peak[i],len(self.q[i]))
  self.rst=old_wire;self.pipe=[newpipe]+self.pipe[:4];self.ap=[bool(add)]+self.ap[:4];self.by=newby;self.edge+=1
  return output

class ReturnRoot:
 """Root D/QD128. step returns r_v sampled by spine at this edge, not post-NBA r_v."""
 def __init__(self):
  self.q=deque();self.buf={};self.pipe=[None]*5;self.launch=None;self.row=None;self.peakq=0;self.peakbuf=0
 def step(self,incoming=None):
  out=self.row;sv=self.pipe[4];useq=sv is None and bool(self.q);ct=sv if sv is not None else self.q[0] if self.q else None
  oldq=len(self.q);newrow=None;newlaunch=None
  if useq:self.q.popleft()
  if ct is not None:
   if complete(ct):newrow=ct
   else:
    hit=next((i for i in sorted(self.buf) if sibling(self.buf[i],ct)),None)
    if hit is not None:newlaunch=parent(self.buf.pop(hit),ct)
    else:
     free=next((i for i in range(128) if i not in self.buf),None)
     if free is None:raise ValueError('root D128 overflow')
     self.buf[free]=ct
  if incoming is not None:
   if oldq==128 and not useq:raise ValueError('root QD128 overflow')
   self.q.append(tag(incoming))
  self.pipe=[self.launch]+self.pipe[:4];self.launch=newlaunch;self.row=newrow
  self.peakq=max(self.peakq,len(self.q));self.peakbuf=max(self.peakbuf,len(self.buf))
  return out

def batch_waves(addresses):
 """Actual provider wa bits[5:4] bank; address>>4 is a sixteen-lane 512bit word."""
 if not isinstance(addresses,list) or not 1<=len(addresses)<=128:raise ValueError('one native field packet has1..128 enabled lanes')
 words=[set() for _ in range(4)]
 for a in addresses:
  if type(a) is not int or not 0<=a<1<<19:raise ValueError('19-bit VM address; no truncation alias')
  word=a>>4;words[word&3].add(word)
 batches=max(map(len,words))
 return {'distinct_words_per_bank':list(map(len,words)),'native_batches':batches,
         'provider_elapsed_accept_to_earliest_retire_edges':1+6*batches,
         'provider_inclusive_service_edge_bound':2+6*batches,
         'scope':'raw provider only, no grant wait/forward or reverse CDC/protected validation/consumer stall'}

def bursts(events,roots=128):
 """Complete accepted root journal metadata only: [{'edge', 'root','row','pos'}]."""
 if type(roots) is not int or not 1<=roots<=128:raise ValueError('root count1..128')
 per_edge=Counter();per_root=Counter();seen=set();rows=set()
 for e in events:
  if set(e)!=set(('edge','root','row','pos')):raise ValueError('exact root event schema')
  for k,limit in [('edge',1<<64),('root',roots),('row',1<<16),('pos',8)]:
   if type(e[k]) is not int or not 0<=e[k]<limit:raise ValueError('event field bounds')
  key=(e['edge'],e['root'])
  if key in seen:raise ValueError('root emits at most1 row per edge')
  identity=(e['root'],e['pos'],e['row'])
  if identity in rows:raise ValueError('duplicate row in one admitted phase')
  rows.add(identity)
  seen.add(key);per_edge[e['edge']]+=1;per_root[e['root']]+=1
 return {'events':len(events),'peak_simultaneous_rows':max(per_edge.values(),default=0),
         'root_rows':dict(sorted(per_root.items())),
         'capacity_if_no_visibility_credit_returns_before_phase_end':len(events),
         'actual_current_program':False}

def capture_calendar(events, releases, seats, roots=128):
 """One phase, one enrolled source clock. Release edge is captured positive feedback.

 Caller must bind clocks/reset/context before using on actual journals. This checker
 neither synthesizes callbacks nor qualifies raw ACK as checked winning visibility.
 At edge E arrivals use old occupied seats; release at E becomes reusable at E+1.
 """
 census=bursts(events,roots)
 if type(seats) is not int or seats<1:raise ValueError('positive actual reserved seats')
 captured={(e['root'],e['pos'],e['row']):e['edge'] for e in events}
 release_map={};actions={}
 for e in events:actions.setdefault(e['edge'],{'arrive':[],'release':[]})['arrive'].append((e['root'],e['pos'],e['row']))
 for r in releases:
  if set(r)!=set(('root','pos','row','checked_visible_edge','captured_credit_edge')):raise ValueError('checked visibility/positive captured credit required')
  for k,upper in [('root',roots),('pos',8),('row',65536),('checked_visible_edge',1<<64),('captured_credit_edge',1<<64)]:
   if type(r[k]) is not int or not 0<=r[k]<upper:raise ValueError('release field bounds')
  key=(r['root'],r['pos'],r['row'])
  if key not in captured:raise ValueError('release without same phase row capture')
  if key in release_map:raise ValueError('duplicate credit')
  v=r['checked_visible_edge'];c=r['captured_credit_edge']
  if not captured[key]<v<c:raise ValueError('capture precedes checked visibility; credit must be positive later captured feedback')
  release_map[key]=c;actions.setdefault(c,{'arrive':[],'release':[]})['release'].append(key)
 occupied=set();peak=0;calendar=[]
 for edge,a in sorted(actions.items()):
  # Deliberately check old occupancy before removing this edge's credits.
  if len(occupied)+len(a['arrive'])>seats:raise ValueError('capture overflow before same-edge credit reuse')
  occupied.update(a['arrive']);peak=max(peak,len(occupied))
  for key in a['release']:
   if key not in occupied:raise ValueError('release before live seat')
   occupied.remove(key)
  calendar.append({'edge':edge,'arrivals':len(a['arrive']),'captured_credits':len(a['release']),'post_edge_debt':len(occupied)})
 return {'scope':'supplied single-phase source-domain calendar, not connected-top qualification',
         'reserved_seats':seats,'peak_seats_before_edge_release':peak,'remaining_row_debt':len(occupied),
         'all_supplied_rows_retired':len(occupied)==0,'source_burst':census,'calendar':calendar,
         'actual_source_context_clock_enrollment':False}

def legal_burst_calibration():
 """Legal source-control stimulus, deliberately not an accepted program journal."""
 roots=[ReturnRoot() for _ in range(128)];events=[]
 for edge in range(5):
  for i,r in enumerate(roots):
   t=r.step((0,128*edge+i,0,0,1) if edge<2 else None)
   if t is not None:events.append({'edge':edge,'root':i,'row':t[1],'pos':t[0]})
 try:
  capture_calendar(events,[],128)
 except ValueError as exc:
  negative={'seats':128,'verdict':'REJECT','reason':str(exc)}
 else:raise ValueError('negative control unexpectedly accepted')
 return {'scope':'generated legal old-state root control stimulus, not combined RTL execution or current phase enrollment',
         'root_events':events,'aligned_first_packet_native_service':batch_waves(list(range(128))),
         'peak_only_capacity_negative':negative,'phase_capacity_control':capture_calendar(events,[],256)}

def generate():
 pins=json.loads((E/'source_pins.json').read_text())
 for n,p in pins['sources'].items():
  if hashlib.sha256((ROOT/p['snapshot']).read_bytes()).hexdigest()!=p['sha256']:raise ValueError('snapshot drift '+n)
 return {'scope':'Source-owned RD64 return-to-VM acceptance calendar; not an actual combined-top trace',
 'source_pins':pins,'parameters':{'RD':64,'RST':1,'BYPASS':1,'rootD':128,'rootQD':128,'adder_pipeline':5},
 'edge_convention':'N is PRE-edge acceptance. NBA changes visible afterN, available to next synchronous consumer only atN+1.',
 'node':{'sibling_inputs_accept_to_next_stage_accept_edges':7,'complete_bypass_input_to_next_stage_accept_edges':3,
         'lone_incomplete_input_WAIT2_to_next_stage_accept_edges':5,'decision_to_next_stage_add_edges':6,
         'two_input_FIFOs_bits':2*64*65,'output_max_per_edge':1,'inputs_max_per_edge':2,'ready_port':False,
         'queue_wait':'additional actual queue residence and ap[3] bypass collision; RD64 is not a latency deadline'},
 'root':{'complete_input_accept_to_root_rv_postNBA_edges':1,'complete_input_accept_to_spine_capture_edges':2,
         'complete_input_accept_to_legacy_VM_postNBA_edges':3,
         'second_sibling_accept_to_legacy_VM_postNBA_edges_no_queue':9,
         'result_priority':'sv takes precedence over FIFO head; adds have a registered launch before5-stage pipe',
         'input_ready':False,'queue128_bits':128*65,'sibling_buffer128_bits':128*65,'output_max_per_edge':1},
 'path_examples':{'six_levels_all_siblings_no_queue_input_to_legacy_VM_edges':6*7+3,
                  'seven_levels_all_siblings_no_queue_input_to_legacy_VM_edges':7*7+3,
                  'scope':'first node input acceptance origin, aligned siblings; not absolute GO deadline; no leaf/CDC/protectedbackend delay'},
 'source_burst_ceiling':{'global_R128_rows_per_edge':128,'PAR2_local_R64_rows_per_edge':64,
                        'global_R128_record_bits_per_edge':128*69,'local_R64_record_bits_per_edge':64*69,
                        'continuous_burst_length':'actual complete selected phase journal/row-root mapping required; source has no return-ready',
                        'finite_capture_requirement':'phase-owned seats reserved before GO; if VM stalls through whole burst, seats cover every phase row, not only128 peak'},
 'native_provider':{'raw_accept_to_raw_postNBA_visibility_event_edges':3,'raw_read_reply_edges':4,
                    'maximum_field_packet_lanes':128,'maximum_distinct_word_batches':128,
                    'inclusive_no_external_stall_service_bound_edges':770,
                    'elapsed_accept_to_earliest_retire_worst_edges':769,
                    'bank_map':'(FP32addr>>4)&3; same512bitword merges lanes in source order, not bank=FP32addr&3',
                    'source_transaction_credits':1,'CDC_D4_equals_four_transaction_credits':False,
                    'field_boundary_payload_bits':8064,'field_boundary_owner_bits':228,
                    'protection':'N+3 is raw visible receipt, not ECC-checked/winning publication; no automatic consumer credit',
                    'positive_forward_reverse_domain_delays':'source-related3:4 interface owns2destination edges each way; bind reset/phase and actual selected implementation before addingtime',
                    'source_rearm':'owned boundary waits actual provider retire, reverse captured receipt and local release; no sameedge reuse'},
 'acceptance_required':['current PHW10 source/program/context enrollment','each RD64 push/pop and root input/result recorded from oldstate',
                        'every source root pulse captured without requiring a new ready port','matching field owner/address/lane mask accepted by provider',
                        'actual matching raw visibility ACK and separately checked winning publication','positive captured return before source seat release',
                        'spine rows_left0 or native idle is not VM debt retirement'],
 'combined_top_finite_capture_result':None,'accepted_current_journal':None,'maximum_legal_burst_rows':None,
 'no_new_RTL_or_tree_or_leafgate_or_job':True,'clock_or_rate_admission':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--root-journal',type=Path);p.add_argument('--capture-journal',type=Path);p.add_argument('--calibration-output',type=Path);a=p.parse_args()
 d=generate()
 if a.root_journal:d['supplied_root_burst']=bursts([json.loads(x) for x in a.root_journal.read_text().splitlines() if x.strip()])
 if a.capture_journal:
  c=json.loads(a.capture_journal.read_text())
  if set(c)!=set(('events','releases','seats','roots')):raise ValueError('capture calendar envelope')
  d['supplied_capture_calendar']=capture_calendar(c['events'],c['releases'],c['seats'],c['roots'])
 if a.calibration_output:a.calibration_output.write_text(json.dumps(legal_burst_calibration(),indent=2,sort_keys=True)+'\n')
 s=json.dumps(d,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(s)
 else:print(s,end='')
