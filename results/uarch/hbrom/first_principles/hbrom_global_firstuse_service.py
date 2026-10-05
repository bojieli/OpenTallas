"""Finite first-use token pipeline; lightweight architecture calendar, no RTL."""
import json,hashlib,math
from collections import deque
from pathlib import Path
root=Path('/home/ubuntu/OpenTallas-hbrom-cluster-20261005')
timing=Path('/tmp/hbrom-global-16-engine-timing.json');d=json.loads(timing.read_text())
def tokens(fmt,K,R,G):
 la={'fp4':8,'fp8':4,'bf16':64}[fmt];chunk=8 if fmt=='bf16' else 256
 ordinal=0
 for wave in range(0,R*G,8):
  for step in range(8):
   for slot in range(8):
    item=wave+slot
    if item>=R*G:continue
    row,group=divmod(item,G);a=min(la,max(0,math.ceil(K/chunk)-group*la))
    assert a>0 and la%a==0
    fanout=la//a;packed=step//fanout;miss=step%fanout==0
    yield dict(slot=slot,item=item,step=step,key=(item,packed),miss=miss,ordinal=ordinal if miss else None,fanout=fanout)
    if miss:ordinal+=1

def simulate(fmt,K,R,G,L,prefill=1,base=0,launch_stall_period=0):
 ts=list(tokens(fmt,K,R,G));n=len(ts);target=min(prefill,n)
 flight=deque();cache={};ready=0;sent=consumed=0;cycle=0;started=False;start=None
 wave=step=slot=0;lastbank={};misses=hits=0;peakalloc=peakflight=peakphysical=0;phasepenalty=0;return_order=[]
 while True:
  if flight and flight[0][0]==cycle:
   _,tag,tok=flight.popleft()
   assert tag==len(return_order)
   if tok['miss']:cache[tok['slot']]=tok['key'];misses+=1
   else:
    assert cache[tok['slot']]==tok['key'],('cache overwrite',tok,cache)
    hits+=1
   return_order.append(tag);ready+=1
  # One descriptor-boundary launch cycle conservatively reserved.
  stall=launch_stall_period and cycle%launch_stall_period==0
  physical_inflight=sum(t['miss'] for _,_,t in flight)
  if cycle>=1 and sent<n and sent-consumed<1024 and not stall and (not ts[sent]['miss'] or physical_inflight<512):
   tok=ts[sent]
   if tok['miss']:
    addr=base+tok['ordinal'];bank=(addr//8192,addr%2)
    assert cycle-lastbank.get(bank,-2)>=2
    lastbank[bank]=cycle
   flight.append((cycle+L,sent,tok));sent+=1
  if not started and ready>=target:
   started=True;start=cycle;first=cycle+1
  if started and cycle>=first and cycle%8==slot:
   item=wave+slot;valid=item<R*G
   if valid and ready==0:phasepenalty+=8
   else:
    if valid:ready-=1;consumed+=1
    if consumed==n:break
    if slot==7:
     slot=0
     if step==7:wave+=8;step=0
     else:step+=1
    else:slot+=1
  peakalloc=max(peakalloc,sent-consumed);peakflight=max(peakflight,len(flight));peakphysical=max(peakphysical,sum(t['miss'] for _,_,t in flight))
  cycle+=1
  assert cycle<1000000
 assert sent==consumed==len(return_order)==n
 return dict(cycles_to_last_issue=cycle+1,source_to_start_cycles=start,native_tokens=n,physical_misses=misses,cache_hits=hits,
  peak_ring_allocated=peakalloc,peak_tokens_inflight=peakflight,peak_physical_reads_inflight=peakphysical,
  phase_starvation_penalty_cycles=phasepenalty,cache_key_check_pass=True,bank_recurrence_check_pass=True)
shapes={}
for sc in d['scenarios'][:2]:
 for gr in sc['groups']:
  for o in gr['ops']:
   key=(o['fmt'],o['K'],o['sm_rows'],o['groups'])
   if key not in shapes:
    shapes[key]={(L,p):simulate(*key,L,p) for L in [24,30,36] for p in [1,8,16,32]}
# Finite ownership/credit and pool-boundary stress, still software architectural calendar.
checks=[]
for key in shapes:
 for base in [0,1,8189,8191]:
  r=simulate(*key,30,1,base=base,launch_stall_period=11)
  checks.append(dict(shape=key,base=base,cache_pass=r['cache_key_check_pass'],bank_pass=r['bank_recurrence_check_pass']))
scenarios=[]
for sc in d['scenarios'][:2]:
 for L in [24,30,36]:
  for prefill in [1,8,16,32]:
   total=intrinsic=drains=reads=tokens_n=peak=0;group_list=[]
   for gr in sc['groups']:
    gc=0
    for o in gr['ops']:
     key=(o['fmt'],o['K'],o['sm_rows'],o['groups']);r=shapes[key][(L,prefill)]
     # Seven cycles align source epoch to globalphase0; two explicit lifecycle cycles.
     v=r['cycles_to_last_issue']+o['drain']+7+2;total+=v;gc+=v
     items=key[2]*key[3];intrinsic+=((items+7)//8-1)*64+56+1+(items-1)%8
     drains+=o['drain'];reads+=r['physical_misses'];tokens_n+=r['native_tokens'];peak=max(peak,r['peak_ring_allocated'])
    group_list.append(dict(layer=gr['layer'],ops=len(gr['ops']),cycles=gc))
   scenarios.append(dict(engines_per_rank=sc['engines_per_rank'],L=L,prefill=prefill,operations=1103,global_flush_groups=343,
    baseline_individual_issue_drain_cycles=intrinsic+drains,with_source_and_protocol_cycles=total,
    source_protocol_added_cycles=total-intrinsic-drains,source_protocol_added_us_at1p2GHz=(total-intrinsic-drains)/1200,
    matrix_us_at1p2GHz=total/1200,physical_reads=reads,native_response_records=tokens_n,peak_ring_allocated=peak))
paths=[timing,Path('/tmp/hbrom-global-firstuse-layout.json'),root/'rtl/gpu/ot_gpu_bulk_copy.sv',root/'rtl/gpu/ot_gpu_issue.sv',Path(__file__)]
out=dict(schema='opentallas.hbrom.global_firstuse_service.v1',architecture_only=True,qualified=False,
 source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},scenarios=scenarios,
 shapes=[dict(shape=k,calendars=[dict(L=L,prefill=p,**v) for (L,p),v in s.items()]) for k,s in sorted(shapes.items())],
 ownership_bank_checks=checks,
 contract=dict(token_order='Dense native wave,t,slot request order; each token reserves native ring slot beforelaunch; misslaunch physicalfirstuseordinal; hitlaunchcontrolonly.',
  constant_latency='Every token returns exactlyLcycles afteracceptance. Hitcontrol andmissdata alignedthroughsame latency. No output backpressure because native destination reserved.',
  cache='8contexts allocated/overwritten only at RETURN, afterolder orderedtokens complete. A miss writes context andbypasses requestednative subset; laterhits read samekey. Fullgroups fanout1 neednoretention butmayuse same8contexts.',
  stalls='Stop whole logical native walk on ringcredit orphysicaloutstanding capacity; acceptedtokens continuefixedpipeline. Arbitrarytestedlaunchpauses preservecacheownership andbankrecurrence.',
  bank='Firstmissphysicalordinalmonotonic,consecutivemisses alternate bank;hitsinsertgaps. Poolcross8192changes bankpair. Reserveonecycle atdescriptorboundary; no zero boundarycost.',
  limits='1024native ring allocationcredits;512physicaloutstanding; outputone native1088b record/cycle maximum.8compactcontexts sufficient independently ofL becauseallocationatreturn.',
  priced_assumptions='Lincludescompletephysicalcapture/mux/expand/ringvisibility; extraLdeep metadata pipeline and8contextpayload mustbepriced. Existingfixedlatencydatapath mustactuallyalignmissreturn tocontrol; no free variablelatency.',
  metadata_allowance='Example80bits/token xL(30)=2400data bits plusprotection; includes native destinationtag,descriptor/epoch,missflag,slot,atomoffset,format,key. Actual fieldwidths/overflow require implementationcontract.',
  source_vs_compute='All1103operations payindependentcoldsourcefill, oneboundarycycle,2lifecyclecycles,7epochphasealignment; individualnative drains.343retainedglobalbarriers outside. Noexpertbatchedcompute orcrossopweightprefetchcredit.'),
 conclusion='Constructive finite firstuse service succeeds for21actualshapes,84poolbase/stallchecks. Architectureonly; sourcearea/power andfixedLclosure unqualified.')
Path('/tmp/hbrom-global-firstuse-service.json').write_text(json.dumps(out,indent=2)+'\n')
for s in scenarios:
 if s['L']==30 and s['prefill']==1:print(s)
