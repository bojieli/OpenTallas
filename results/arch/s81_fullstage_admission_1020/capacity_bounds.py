"""Necessary ROM-capacity bounds, never an admission PASS. No tensor payload access.
Run from immutable source root; takes header metadata/census and actual field pickles.
"""
import collections, hashlib, json, math, pickle, sys
from pathlib import Path
R=Path.cwd(); sys.path.insert(0,str(R/'tools'));sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import v41_rom_ksplit_bankmap as S
import xs_place as X
O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False)
M=Path(sys.argv[2]); experts=json.loads((M/'all_expert_metadata.json').read_text());summary=json.loads((M/'summary.json').read_text())
assert len(experts)==15360
# Derive storage per segment from the actual production image writer's segment ordering.
shapes={}
for fmt,K in [('fp4',5120),('fp4',2304)]:
 segs=S.segments(K,5);words=[len(S.segment_order(fmt,a,n)) for a,n in segs]
 shapes[str((fmt,K))]=dict(segments=segs,paired_address_increments=words,total_per_superrow=sum(words))
gu=shapes[str(('fp4',5120))]['total_per_superrow'];down=shapes[str(('fp4',2304))]['total_per_superrow']
assert gu==80 and down==40
# Fixed semantic ownership retains 72 GU rows and 80 down rows on EVERY slice per expert.
# Even perfectly packed row pairs consume these minimum addresses. Odd rows, idle phases,
# actual pair rotations and all dense weights can only increase the required physical depth.
minimum_per_slice=math.ceil(72/2)*gu+math.ceil(80/2)*down
bounds=[]
for nframes in [6,7,8]:
 capacity=nframes*12*8192
 bounds.append(dict(physical_frames=nframes,q_pairs=nframes*12,paired_depth=8192,
  minimum_paired_addresses_per_expert=minimum_per_slice,
  max_experts_necessary_bound_ignoring_dense=capacity//minimum_per_slice,
  minimum_mean_depth_at_140_experts=140*minimum_per_slice/(nframes*12),
  qualification='NECESSARY_BOUND_ONLY; no per-pair admission'))
actual={}
for op,fn in [('ffn.experts_gu','experts_gu'),('ffn.down','down')]:
 f=Path('/srv/opentallas-scratch/codex/s81-stage-admission-1020/out/compact_fseq')/(fn+'.pickle')
 rec,field=pickle.loads(f.read_bytes());v=[0]*len(rec['pairs']);ps=[]
 for p in rec['phases']:
  if p['op']!=op:continue
  n=0
  for slot,row,sg in p['plan']['assign_slots']:
   a,b=S.segments(p['K'],p['nseg'])[sg];w=len(S.segment_order(p['fmt'],a,b));v[slot]+=w;n+=w
  ps.append(dict(phase=p['phase'],rows=p['rows'],slots=len(p['plan']['assign_slots']),paired_addresses=n,
   ret_words=p['ret_words']))
 actual[op]=dict(input_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),per_pair_increments=v,
  total=sum(v),phases=ps,scope='real six-activated-expert fixture, first eight-frame slice; NOT full-stage')
max_hot=next(x for x in bounds if x['physical_frames']==6)['max_experts_necessary_bound_ignoring_dense']
cases=[]
for stages in [97,110,130]:
 capacity=stages*max_hot
 cases.append(dict(stages=stages,max_expert_identities_necessary_bound=capacity,required=15360,
  status='FAIL_NECESSARY_BOUND' if capacity<15360 else 'NOT_ADMITTED_NO_SELECTED_MAP',
  excludes=['all dense weights','per-pair imbalance','odd-row/idle-phase padding','cfg phase admission','stage ownership selection','consumer contract']))
r=dict(scope='SOURCE_PINNED_NECESSARY_CAPACITY_BOUND; NEVER_FULL_STAGE_PASS',
 existing_ownership='72 mergedGU and80 down rank rows per expert per slice',
 segment_shapes=shapes,minimum_per_slice=minimum_per_slice,physical_slice_bounds=bounds,
 stage_count_cases=cases,minimum_stage_count_ignoring_dense=math.ceil(15360/max_hot),
 actual_compact_fixture=actual,
 inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [M/'all_expert_metadata.json',M/'summary.json',Path(S.__file__),Path(X.__file__),R/'tools/v41_die_images_w17w10.py']})
(O/'capacity_bounds.json').write_text(json.dumps(r,indent=1)+'\n')
print('CAPACITY_BOUND',json.dumps(dict(hot_six_frame_max=max_hot,minimum_stages=r['minimum_stage_count_ignoring_dense'],cases=cases,actual={k:v['per_pair_increments'] for k,v in actual.items()})),flush=True)
