import json,hashlib,math
from pathlib import Path
base=Path('/home/ubuntu/OpenTallas-hbrom-cluster-20261005')
timing=Path('/tmp/hbrom-global-16-engine-timing.json');layout=Path('/tmp/hbrom-global-compact-layout.json')
x=json.loads(timing.read_text())
def shape(fmt,K,R,G,remap=False):
 la={'fp4':8,'fp8':4,'bf16':64}[fmt];chunk=8 if fmt=='bf16' else 256
 counts=[max(0,min(la,(K+chunk-1)//chunk-g*la)) for g in range(G)]
 lengths=[math.ceil(8*a/la) for a in counts];offsets=[sum(lengths[:g]) for g in range(G)];stride=sum(lengths)
 cache={};last={};clock=0;miss=0;stalls=0;hits=0;first_conflicts=[];issued=0
 for wave in range(0,R*G,8):
  for t in range(8):
   for slot in range(8):
    item=wave+slot
    if item>=R*G:continue
    r,g=divmod(item,G);a=counts[g];p=(t*a)//la
    b=r*stride+offsets[g]
    # Pairwise swap only inside even-length immutable group chunks.
    addr=b+(p^((b&1)^(item&1)) if remap and lengths[g]%2==0 else p)
    key=(item,p)
    if cache.get(slot)!=key:
     cache[slot]=key;miss+=1
     bank=addr&1
     wait=max(0,last.get(bank,-2)+2-clock)
     if wait and len(first_conflicts)<3:first_conflicts.append(dict(item=item,t=t,slot=slot,address=addr,bank=bank,cycle=clock))
     stalls+=wait;clock+=wait;last[bank]=clock
    else:hits+=1
    clock+=1;issued+=1
 issue=math.ceil(R*G/8)*64
 return dict(fmt=fmt,K=K,rows=R,groups=G,native_records=issued,compact_records=miss,compact_row_records=stride,
  source_zero_latency_guard_cycles=clock,source_bank_stalls=stalls,cache_hits=hits,issue_cycles=issue,
  first_conflicts=first_conflicts,within_consumer_issue_at_zero_latency=clock<=issue,
  remap=remap,serial_finite_source_upper_cycles_L30=issue+miss*(30+7),
  serial_finite_source_upper_cycles_L36=issue+miss*(36+7))
scenarios=[];shapes={}
for s in x['scenarios'][:2]:
 summaries=[];records=miss=issue=stall0=stall1=0;surplus=0
 for group in s['groups']:
  details=[]
  for o in group['ops']:
   key=(o['fmt'],o['K'],o['sm_rows'],o['groups'])
   if key not in shapes:shapes[key]={m:shape(*key,remap=bool(m)) for m in [0,1]}
   a,b=shapes[key][0],shapes[key][1]
   records+=a['native_records'];miss+=a['compact_records'];issue+=a['issue_cycles'];stall0+=a['source_bank_stalls'];stall1+=b['source_bank_stalls']
   surplus+=o.get('observed_startup',0)
   details.append(dict(tag=o['tag'],shape=list(key)))
  summaries.append(dict(layer=group['layer'],batch=group['batch'],operations=len(details)))
 scenarios.append(dict(engines_per_rank=s['engines_per_rank'],flush_groups=len(s['groups']),operations=sum(g['operations'] for g in summaries),
  native_records_on_busiest_engine_per_operation=records,compact_reads=miss,sum_individual_issue_cycles=issue,
  zero_latency_bank_stalls_original=stall0,zero_latency_bank_stalls_xor_remap=stall1,
  conditional_startup_per_flush_cycles_30=343*30,conditional_startup_per_flush_cycles_36=343*36,
  conservative_startup_per_operation_cycles_30=1103*30,conservative_startup_per_operation_cycles_36=1103*36,
  serialized_compact_miss_added_bound_cycles_L30=miss*37,
  serialized_compact_miss_added_bound_cycles_L36=miss*43,
  bound_scope='Standalone finite no-lookahead schedule upper bound versus sum individual native issue. Not a delta to current composer lines+drain: baseline issue/startup itself has unpriced terms.'))
paths=[timing,layout,base/'rtl/gpu/ot_gpu_bulk_copy.sv',base/'rtl/gpu/ot_gpu_issue.sv',Path(__file__)]
out=dict(schema='opentallas.hbrom.global_source_service.v1',architecture_only=True,qualified=False,
 source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},scenarios=scenarios,
 shapes=[dict(original=v[0],offline_pair_xor=v[1]) for k,v in sorted(shapes.items())],
 native_ring=dict(lines=1024,bytes=1024*136,scope='post-decode native responses; cannot count as compact predecode context storage'),
 compact_contexts=dict(count=8,scope='one current compact record per wave slot; holds until final reuse accepted; permits simple serial-miss finite schedule',
 latency_hiding='8 contexts alone do not prove >=30-cycle pipelined read lookahead; ring entries and outstanding tags are distinct resources'),
 descriptor_accounting=dict(flush_groups=343,operations=1103,inside_flush_transitions=760,
 rule='Charge one path startup per343flushgroups only with proof of legal prefetch across all760internal operation transitions. Retained bulk queue DQ4 permits descriptors, but does not establish early expert selection/config availability or compact-context epoch turnover.',
 conservative_rule='Without ownership proof charge peroperation startup. Do not multiply observed SM startdone surplus by343 or1103 blindly: component-specific matrix startup/activation/drain must first be separated.'),
 blockers=['Eight-context decoder has no proven finite miss-prefetch schedule through24–30cycle mux plus capture/decode stages. Zero-latency guard trace is diagnostic only.',
 'Offline pairwise XOR fixes selected bursts but not all compact-hit/odd-tail bank conflicts; actual readready guard remains necessary.',
 'Native ring releases responses in order, but compact fetch/retention is upstream; no free conversion of1024ring slots into compactcontexts.',
 '343flush composer merges1103operations; ownership/configuration/expert availability and descriptor boundary timing remain unproven for760internal overlaps.',
 'Existing linecount+drain matrix estimate omits measured start-to-done surplus, so source-only increment cannot establish full TPOT.'],
 finite_safe_bound=dict(policy='At each native output, on cache miss issue only when samebank2cycle recurrence allows, wait full path latency, retain response in its slot, then emit in native order; consumer waits to its slot phase. No more8contexts and at most1new native line resident.',
 formula='sum_individual_issue_cycles + compact_misses*(L+7), excluding explicit SM arithmetic drain/config/activation. L must bound readready+capture+mux+decode;30/36cycle sensitivities are assumptions, not closed timing.',
 implication='Finite and starvation-free analytically if every accepted physical read returns within L; sacrifices overlap and is deliberately conservative, not proposed headline performance.'),
 conclusion='NO_ZERO_STALL_OR343_STARTUP_ADMISSION. Require concrete finite prefetch/context ownership calendar or adopt charged serialized bound; static XOR alone is insufficient.')
Path('/tmp/hbrom-global-source-service.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(scenarios,indent=2));print('shapes',len(shapes))
