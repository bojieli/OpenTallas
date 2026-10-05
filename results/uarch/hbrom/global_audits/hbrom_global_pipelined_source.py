import json,hashlib
from collections import deque
from pathlib import Path
src=Path('/tmp/hbrom-global-16-engine-timing.json');data=json.loads(src.read_text())
def simulate(R,G,L,prefill,period=2):
 n=R*G*8; target=min(prefill,n);sent=consumed=returned=0;flight=deque();q=0;cycle=0;started=False
 wave=t=slot=0;phasewait=0;issuefinish=None;start=None;maxused=maxflight=maxq=0;waitmiss=0
 while issuefinish is None:
  while flight and flight[0]<=cycle:flight.popleft();returned+=1;q+=1
  if sent<n and cycle%period==0 and sent-consumed<1024 and len(flight)<512:
   flight.append(cycle+L);sent+=1
  if not started and q>=target:
   # Sequential start latch; phase counter remains free-running.
   started=True;start=cycle;first_allowed=cycle+1
  if started and cycle>=first_allowed and cycle%8==slot:
   item=wave+slot;valid=item<R*G
   if valid and q==0:waitmiss+=8
   else:
    if valid:q-=1;consumed+=1
    if slot==7:
     slot=0
     if t==7:wave+=8;t=0
     else:t+=1
    else:slot+=1
    # Last valid native issue, excluding following unused bubble slots.
    if consumed==n:issuefinish=cycle
  maxused=max(maxused,sent-consumed);maxflight=max(maxflight,len(flight));maxq=max(maxq,q)
  cycle+=1
  if cycle>10000000:raise RuntimeError('analytical noncompletion')
 assert sent==consumed==returned==n
 return dict(cycles_to_last_issue=issuefinish+1,source_to_start_cycles=start,consumer_phase_wait_cycles=waitmiss,
  native_reads=n,peak_allocated_ring_lines=maxused,peak_native_ready_lines=maxq,peak_outstanding_reads=maxflight)
shapes={}
for sc in data['scenarios'][:2]:
 for g in sc['groups']:
  for o in g['ops']:
   key=(o['fmt'],o['K'],o['sm_rows'],o['groups'])
   if key not in shapes:shapes[key]={(L,p):simulate(key[2],key[3],L,p) for L in [24,30,36] for p in [1,4,8,16,32,64]}
scenarios=[]
for sc in data['scenarios'][:2]:
 for L in [24,30,36]:
  for prefill in [1,4,8,16,32,64]:
   cycles=0;intrinsic=0;drains=0;reads=0;peak=0;waits=0
   for g in sc['groups']:
    for o in g['ops']:
     key=(o['fmt'],o['K'],o['sm_rows'],o['groups']);r=shapes[key][(L,prefill)]
     cycles+=r['cycles_to_last_issue']+o['drain']+2+7
     items=key[2]*key[3]
     intrinsic+=( (items+7)//8-1)*64+56+1+(items-1)%8
     drains+=o['drain'];reads+=r['native_reads'];peak=max(peak,r['peak_allocated_ring_lines']);waits+=r['consumer_phase_wait_cycles']
   base=intrinsic+drains
   scenarios.append(dict(engines_per_rank=sc['engines_per_rank'],L=L,prefill=prefill,operations=1103,
    issue_and_drain_native_cycles=base,with_source_two_protocol_and_seven_epoch_phase_cycles_per_op=cycles,
    added_source_and_protocol_cycles=cycles-base,added_us_at_1p2GHz=(cycles-base)/1200,
    standalone_matrix_us_at_1p2GHz=cycles/1200,native_physical_reads=reads,peak_ring_allocated=peak,
    consumer_missing_slot_penalty_cycles=waits))
paths=[src,Path('/tmp/hbrom-global-compact-layout.json'),Path('/tmp/hbrom-global-issue-span.json'),Path(__file__)]
out=dict(schema='opentallas.hbrom.global_source_service.pipelined.v1',architecture_only=True,qualified=False,
 source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},scenarios=scenarios,
 shapes=[dict(fmt=k[0],K=k[1],rows=k[2],groups=k[3],calendars=[dict(L=l,prefill=p,**v) for (l,p),v in s.items()]) for k,s in sorted(shapes.items())],
 design=dict(physical_read_period=2,bank_recurrence_guaranteed=True,reuse_compact_cache=False,
  source_rule='One four-word physical read for EVERY requested native response, rereading compact record on repeated subrecord use. No8context retention dependency; mapped partial widths divide record lanes, so each native response needs only one physical record.',
  native_ring_lines=1024,maximum_outstanding_reads=512,response_latency_sensitivity_cycles=[24,30,36],
  source_prefill_choices=[1,4,8,16,32,64],source_acceptance='Clockcycles modulo2; ring allocation credit before launch; fixed bounded return L; responseexpansionone record/cycle maximum; read rate0.5record/cycle.',
  issue='Native group-slot wave,t,slot; free-runningphase slot modulo8; invalidtail slots bubble; missingvalid record waits complete8cycle revolution.',
  transitions='No weightprefetch acrossoperations; all1103 independently start with emptyring and pay fullsourceprefill. Add2cycles peroperation for start/retire protocol plus7cycles conservative alignment of each sourceepoch to globalphase0; consumerphasewait is explicitly simulated. Retain343globalbarriers, not1103globalbarriers.',
  drain='Existing per-operation last-input-to-last-output drain; never mockHBM60/JIT40 coldstartup.',
  incremental_metadata='Price peroutstandingnative-request format,compactatomoffset,epoch/descriptoridentity andreturntag. Conservative512x64protectedmetadata bits=32768data bits beforeprotection; existingtags cannot silently be reused withoutcontractaudit.',
  power='Rereads eliminate compaction readenergy savings but retain storagecapacity reduction; four274-bit reads pernative response. No saved responsebytes or computeoperations.'),
 caveats=['L must bound complete acceptedROMread to ringready including capture,mux,decode,writevisibility;24/30/36 are architectural assumptions.',
 'Return latency fixed in this calendar; a deterministic upperboundL can be enforced by holding earlierreturns until scheduledready, with priced boundedpipeline buffering.',
 'Start/retire2cycle allowance is an explicit assumption pending interfacecycleaudit; phasealignment is simulated, not assumedzero.',
 'No RTL/simulation/synthesis undertaken. Pipelined schedule requires newcompactaddress/expansionmetadata service; capacityalone doesnotprove implementation.'])
Path('/tmp/hbrom-global-source-service-pipelined.json').write_text(json.dumps(out,indent=2)+'\n')
for s in scenarios:
 if s['L']==30:print(s)
