"""Read immutable released metadata only. No tensor payload or replacement RTL."""
import collections,gzip,hashlib,importlib.util,json,math,sys
from pathlib import Path
R=Path.cwd();O=R/'out/census_r2';O.mkdir(parents=True,exist_ok=False)
B=R/'results/quality/w16_w17_checkpoint_header_catalogue_20261001';c=json.loads((B/'catalogue.json').read_text())
s=importlib.util.spec_from_file_location('hc',R/'tools/dsrom_checkpoint_header_catalogue.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
verify=m.verify_output(B)
T=c['tensors'];pairs=c['weight_scale_pairs'];exp=[];shapes=collections.Counter()
for L in range(40):
 for e in range(384):
  mats=[]
  for n in ['w1','w3','w2']:
   key=f'layers.{L}.ffn.experts.{e}.{n}.weight';sk=pairs[key];w,sc=T[key],T[sk];rows,cols=w['stored_shape'];logicalK=2*cols
   assert w['dtype'] in ('I8','U8') and sc['stored_shape']==[rows,logicalK//32]
   assert rows%4==0 and logicalK%32==0
   shapes[(n,rows,logicalK,w['dtype'],sc['dtype'])]+=1
   mats.append(dict(tensor=key,scale=sk,logical_shape=[rows,logicalK],rank_shape=[rows//4,logicalK],shard=w['shard'],absolute_offsets=w['absolute_file_offsets'],stored_bytes=w['stored_bytes']))
  assert mats[0]['logical_shape']==mats[1]['logical_shape']==[2304,5120]
  assert mats[2]['logical_shape']==[5120,2304]
  exp.append(dict(layer=L,expert=e,matrices=mats))
(O/'all_expert_metadata.json').write_text(json.dumps(exp,separators=(',',':'))+'\n')
plan=json.loads((R/'results/arch/s81_dv_1016/p4l/plan.json').read_text());frames=collections.defaultdict(list)
for b in plan['blocks']:
 if b['kind']=='frame':frames[b['group']].append(b['name'])
counts=collections.Counter(map(len,frames.values()));assert dict(counts)=={8:12,7:2,6:2}
missing={k:dict(physical_frames=len(v),phantom_owners=8-len(v),names=v) for k,v in frames.items() if len(v)!=8}
# Source op_groups deals each slice independently across eight owners.
# Count missing indices; the actual Die.frames_of enumerates only existing frames.
profiles={}
for n,rows in [('wq_b_head',512),('gu_merged_per_expert_slice',72),('down_per_expert_slice',80)]:
 lost=0;detail=[]
 for group,names in sorted(frames.items()):
  b,x=divmod(rows,8);sizes=[b+(i<x) for i in range(8)]
  l=sum(sizes[len(names):]);lost+=l
  if l:detail.append(dict(group=group,missing_rows=l))
 profiles[n]=dict(rows_per_slice=rows,missing_rank_rows=lost,detail=detail)
# Legacy canonical map remains explicitly incompatible with this topology.
by_stage=collections.defaultdict(set);nmat=0;oldN=set();expert_ids=set();sample=None
with gzip.open(R/'results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz','rt') as f:
 for line in f:
  r=json.loads(line);nmat+=1;oldN.add(r['compiled_NP'])
  if r.get('expert') is not None:
   identity=(r['layer'],r['expert']);by_stage[r['stage']].add(identity);expert_ids.add(identity)
   if sample is None:sample={k:v for k,v in r.items() if k not in ('plans','rank_slices')}
summary=dict(header_verify=verify,checkpoint_revision=c['checkpoint_revision'],index_sha256=c['index_sha256'],weight_scale_pairs=len(pairs),actual_experts=len(exp),expert_shapes=[dict(kind=k[0],rows=k[1],K=k[2],stored_dtype=k[3],scale_dtype=k[4],count=v) for k,v in shapes.items()],physical_frames=sum(map(len,frames.values())),frame_count_histogram=dict(counts),missing_owners=missing,old_compiler_row_loss=profiles,legacy_map=dict(matrix_records=nmat,compiled_NP=sorted(oldN),stage_expert_counts={str(k):len(v) for k,v in by_stage.items()},unique_expert_identities=len(expert_ids),first_expert=sample,compatible_with_p4l=False),payload_read=False,admission=False)
(O/'summary.json').write_text(json.dumps(summary,indent=1)+'\n')
(O/'input_sources.json').write_text(json.dumps({str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [B/'catalogue.json',B/'config.json',B/'model.safetensors.index.json',R/'tools/dsrom_checkpoint_header_catalogue.py',R/'results/arch/s81_dv_1016/p4l/plan.json',R/'results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz']},indent=1)+'\n')
print('HEADER_CENSUS',verify,'experts',len(exp),'frames',summary['frame_count_histogram'],'missing',profiles,'legacyNP',oldN,'uniqueExperts',len(expert_ids),flush=True)
