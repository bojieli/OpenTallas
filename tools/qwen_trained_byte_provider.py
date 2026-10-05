#!/usr/bin/env python3
"""Immutable checkpoint codec producer and raw r17 byte backend; no operator oracle."""
import argparse,bisect,gzip,hashlib,json,os,re,time
from importlib.metadata import version
from collections import OrderedDict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
ARTIFACT='results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz'
PINS=['tools/qwen_trained_page_continuation.py','tools/qwen_trained_byte_provider.py','tools/qwen_hbm_complete_executor.py','tools/qwen3_deployment_quality.py','tools/h3_qwen_complete_native.py','compiler/models/qwen3-8b/checkpoint_source.json']
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def native():return json.load(gzip.open(ROOT/ARTIFACT,'rt'))
def extents(n):return {e['provider_ref']:e for a in n['provider_binding']['allocation']for e in a['extents']}
def refs(n):return {r['provider_ref']for o in n['operations']for r in o['provider_binding']['external_providers']}
MUTABLE_ROLES={'persistent_FP8_K','persistent_FP8_V','software_KV_publication_and_reader_lease_state'}
def immutable_refs(n):
 """Checkpoint producer owns requested immutable bytes; native memory owns KV/state."""
 ex=extents(n)
 return {r for r in refs(n) if ex[r].get('role')not in MUTABLE_ROLES}
def matrix_inventory(n):
 """Validate every matrix format and consumer projection before producing any bytes."""
 ex=extents(n);wanted=immutable_refs(n);descriptors=n['source_program']['weight_descriptors'];plan={}
 families={}
 for key,d in descriptors.items():
  name=d['name'];die=d['die']
  if name not in {'qkv','o','gu','down','head'}or die not in (0,1)or d['rows']<=0 or d['K']<=0 or not d['checkpoint_sources']:raise ValueError('unsupported matrix descriptor format '+key)
  if (name=='head')!=(d['layer']is None):raise ValueError('matrix layer/format mismatch '+key)
  cr=f"Qwen.rank{die}.extent."+('head'if d['layer']is None else f"L{d['layer']}.{name}")+'.codes';sr=cr[:-5]+'scales'
  for ref,count,codec in [(cr,d['rows']*d['K'],'signed_INT8_row_major'),(sr,d['rows']*2,'BF16_little_endian')]:
   if ref not in ex or ex[ref]['bytes']!=count or ex[ref]['codec'].get('data')!=codec:raise ValueError('unsupported matrix extent format '+ref)
  if cr not in wanted:raise ValueError('missing requested matrix code '+key)
  scale_used=not(name in {'o','down'}and die==1)
  if (sr in wanted)!=scale_used:raise ValueError('matrix scale consumer ownership mismatch '+key)
  plan[key]=dict(code_ref=cr,scale_ref=sr if scale_used else None,declared_scale_ref=sr,rows=d['rows'],K=d['K'])
  families[name]=families.get(name,0)+1
 if n['source_program']['config'].get('num_hidden_layers')==36 and families!={'qkv':72,'o':72,'gu':72,'down':72,'head':2}:raise ValueError('incomplete290 matrix descriptor inventory')
 covered={r for item in plan.values()for r in (item['code_ref'],item['scale_ref'])if r is not None}
 if covered!={r for r in wanted if r.endswith(('.codes','.scales'))}:raise ValueError('matrix consumer inventory has unsupported/orphan extent')
 return plan

def validate_checkpoint_inventory(reader,n):
 """All descriptor source shapes/dtypes checked from headers before the first page."""
 from safetensors import safe_open
 result={}
 for key,d in n['source_program']['weight_descriptors'].items():
  rows=0;headers=[];column=d['name']in ('o','down')
  for source in d['checkpoint_sources']:
   with safe_open(str(reader._verified_file(reader.index[source])),framework='pt',device='cpu')as handle:
    tensor=handle.get_slice(source);shape=tensor.get_shape();dtype=tensor.get_dtype()
   if dtype!='BF16'or len(shape)!=2 or shape[0]<=0 or shape[1]<=0 or (column and shape[1]%2)or (not column and shape[0]%2)or d['K']!=(shape[1]//2 if column else shape[1]):raise ValueError('unsupported checkpoint matrix format '+key+':'+source)
   rows+=shape[0]if column else shape[0]//2;headers.append(dict(source=source,shape=shape,dtype=dtype))
   if d['folded_norm']:
    norm=d['folded_norm']
    with safe_open(str(reader._verified_file(reader.index[norm])),framework='pt',device='cpu')as handle:
     tensor=handle.get_slice(norm)
     if tensor.get_dtype()!='BF16'or tensor.get_shape()!=[shape[1]]:raise ValueError('unsupported checkpoint folded norm '+key)
  if rows!=d['rows']:raise ValueError('checkpoint descriptor row inventory '+key)
  result[key]=headers
 return result

def bfbytes(value):
 import torch
 if value.dtype!=torch.bfloat16:raise ValueError('BF16 producer type')
 return value.contiguous().view(torch.int16).numpy().astype('<i2',copy=False).tobytes()
def matrix_rows(reader,d,batch=128):
 """Exact shipped full-row fold/quantization; column slicing only after quantization."""
 from safetensors import safe_open
 from qwen3_deployment_quality import quantize_w8
 norm=reader.tensor(d['folded_norm']).float()if d['folded_norm']else None
 axis='columns'if d['name']in ('o','down')else 'rows'
 offset=0
 for source in d['checkpoint_sources']:
  path=reader._verified_file(reader.index[source])
  with safe_open(str(path),framework='pt',device='cpu')as f:rows,k=f.get_slice(source).get_shape()
  start,end=(d['die']*(rows//2),(d['die']+1)*(rows//2))if axis=='rows'else(0,rows)
  for r in range(start,end,batch):
   w=reader.read_tensor(source,r,min(r+batch,end)).float()
   if norm is not None:w=w*norm[None,:]
   q,s,_=quantize_w8(w)
   if axis=='columns':q=q[:,d['die']*(k//2):(d['die']+1)*(k//2)]
   if q.shape[1]!=d['K']:raise ValueError('descriptor K/source mismatch')
   yield offset,q.contiguous().numpy().tobytes(),bfbytes(s)
   offset+=len(q)
 if offset!=d['rows']:raise ValueError('descriptor row/source mismatch')

def build(snapshot,out,n=None,admission=None,go_commit=None):
 from qwen_hbm_complete_executor import CheckpointWeights
 import torch
 from qwen3_deployment_quality import quantize_w8,rope_tables_g
 n=native()if n is None else n
 if admission is None:raise ValueError('fresh resource admission required for full checkpoint production')
 inventory=matrix_inventory(n)
 from qwen_trained_native_run import validate_admission,guard
 validate_admission(admission,go_commit);guard(admission,Path(out),sum(extents(n)[r]['bytes']for r in immutable_refs(n)))
 out=Path(out);out.mkdir(parents=True,exist_ok=True);p=n['source_program'];reader=CheckpointWeights(p,snapshot,row_batch=128);ex=extents(n);wanted=immutable_refs(n)
 lock=ROOT/'compiler/models/qwen3-8b/checkpoint_source.json';identity=dict(native_sha256=hashlib.sha256(canonical(n)).hexdigest(),checkpoint_lock_sha256=sha(lock),checkpoint_revision=reader.checkpoint_revision,snapshot=str(Path(snapshot).resolve()),source_sha256={f:sha(ROOT/f)for f in PINS})
 # Source shards are all independently hashed before accepting continuation pages.
 for source in sorted({s for d in p['weight_descriptors'].values()for s in d['checkpoint_sources']}|{'model.embed_tokens.weight','model.norm.weight'}|{f'model.layers.{l}.self_attn.{k}_norm.weight'for l in range(36)for k in ('q','k')}|{d['folded_norm']for d in p['weight_descriptors'].values()if d['folded_norm']}):reader._verified_file(reader.index[source])
 validate_checkpoint_inventory(reader,n)
 identity['runtime_package_versions']={k:version(k)for k in ('numpy','torch','safetensors')};identity['checkpoint_files_sha256']=reader.file_pins.copy();identitypath=out/'producer_identity.json'
 if identitypath.exists():
  if identitypath.read_bytes()!=canonical(identity):raise ValueError('producer continuation identity changed')
 else:identitypath.write_bytes(canonical(identity))
 segments={r:[]for r in wanted};offsets={r:0 for r in wanted};created=0;reused=0;known_output_bytes=sum(f.stat().st_size for f in out.rglob('*')if f.is_file())
 def emit(r,data):
  nonlocal created,reused,known_output_bytes
  guard(admission,out,known_output_bytes=known_output_bytes);e=ex[r];start=offsets[r];size=len(data)
  if size<=0 or start+size>e['bytes']:raise ValueError('producer extent overflow')
  tag=r.replace('.','_')+'_'+str(start);path=out/(tag+'.bin');receipt=out/(tag+'.json');h=hashlib.sha256(data).hexdigest();entry=dict(start=start,bytes=size,file=path.name,sha256=h)
  if receipt.exists():
   if json.loads(receipt.read_text())!=entry or not path.is_file()or path.is_symlink()or sha(path)!=h:raise ValueError('completed incremental page drift')
   reused+=1
  else:
   # Preserve an interrupted orphan; never silently overwrite progress.
   with path.open('xb')as f:f.write(data);f.flush();os.fsync(f.fileno())
   with receipt.open('xb')as f:f.write(canonical(entry))
   created+=1;known_output_bytes+=size+len(canonical(entry))
   guard(admission,out,known_output_bytes=known_output_bytes)
  segments[r].append(entry);offsets[r]+=size
  print(json.dumps(dict(event='CHECKPOINT_PAGE_VISIBLE',provider_ref=r,start=start,bytes=size,created=created,reused=reused)),flush=True)
 def completed_extent(r):
  prefix=r.replace('.','_')+'_';records=[]
  for receipt in out.glob(prefix+'*.json'):
   record=json.loads(receipt.read_text());records.append(record)
  records.sort(key=lambda x:x['start']);end=0
  for record in records:
   if record['start']!=end:return None
   end+=record['bytes']
  if end!=ex[r]['bytes']:return None
  for record in records:
   path=out/record['file']
   if Path(record['file']).name!=record['file']or path.is_symlink()or not path.is_file()or path.stat().st_size!=record['bytes']or sha(path)!=record['sha256']:raise ValueError('completed extent continuation drift')
  return records
 for key,d in p['weight_descriptors'].items():
  cr=inventory[key]['code_ref'];sr=inventory[key]['declared_scale_ref']
  # Column-sharded rank1 scales are declared but unconsumed: post-all-reduce uses rank0 scale.
  prior_codes=completed_extent(cr);prior_scales=completed_extent(sr)if sr in wanted else []
  if prior_codes is not None and prior_scales is not None:
   segments[cr]=prior_codes;offsets[cr]=ex[cr]['bytes'];reused+=len(prior_codes)
   if sr in wanted:segments[sr]=prior_scales;offsets[sr]=ex[sr]['bytes'];reused+=len(prior_scales)
   print(json.dumps(dict(event='SOURCE_QUALIFIED_COMPLETE_DESCRIPTOR_REUSED',descriptor=key)),flush=True);continue
  for row,codes,scales in matrix_rows(reader,d):
   emit(cr,codes)
   if sr in wanted:emit(sr,scales)
 # Embedding row codecs are identical for both rank replicas, but their bytes are distinct extents.
 embedding=[r for r in wanted if r.endswith('.embedding')];scale_parts=[];c=p['config'];h=c['hidden_size']
 for row in range(0,c['vocab_size'],128):
  q,s,_=quantize_w8(reader.read_tensor('model.embed_tokens.weight',row,min(row+128,c['vocab_size'])).float());data=q.contiguous().numpy().tobytes();scale_parts.append(bfbytes(s))
  for r in embedding:emit(r,data)
 for r in embedding:
  for data in scale_parts:emit(r,data)
 for r in sorted(wanted):
  if r.endswith('.qk_norm'):
   layer=int(re.search(r'\.L(\d+)\.',r)[1]);emit(r,bfbytes(reader.tensor(f'model.layers.{layer}.self_attn.q_norm.weight'))+bfbytes(reader.tensor(f'model.layers.{layer}.self_attn.k_norm.weight')))
  elif r.endswith('.final_norm'):emit(r,bfbytes(reader.tensor('model.norm.weight')))
  elif r.endswith('.rope_table'):
   for start in range(0,p['context_capacity'],128):
    co,si=rope_tables_g(list(range(start,min(start+128,p['context_capacity']))),c['head_dim'],c['rope_theta'],'cpu');emit(r,np.concatenate([co.numpy(),si.numpy()],axis=1).astype('<f4').tobytes())
 for r in wanted:
  if offsets[r]!=ex[r]['bytes']:raise ValueError('incomplete immutable extent '+r)
 manifest=dict(schema='opentallas.Qwen.trained-byte-images.v1',identity=identity,provider_binding_pin=n['provider_binding_pin'],images={r:dict(base=ex[r]['base'],bytes=ex[r]['bytes'],codec=ex[r]['codec'],segments=segments[r])for r in sorted(wanted)},reader_provenance=reader.provenance(),complete=True,oracle_callbacks=0,actual_RTL=False)
 target=out/'manifest.json';data=canonical(manifest)
 if target.exists():
  # Read trace counts can differ on an explicitly resumed producer; immutable pages and identity cannot.
  old=json.loads(target.read_text())
  if old['identity']!=identity or old['images']!=manifest['images']:raise ValueError('complete producer manifest changed')
 else:
  with target.open('xb')as f:f.write(data)
 return manifest

class TrainedByteBackend:
 """Addressed immutable bytes only. No tensor/operator method is exported."""
 def __init__(self,directory,n):
  self.directory=Path(directory);self.manifest=json.loads((self.directory/'manifest.json').read_text());m=self.manifest
  if m['schema']!='opentallas.Qwen.trained-byte-images.v1'or not m['complete']or m['identity']['native_sha256']!=hashlib.sha256(canonical(n)).hexdigest():raise ValueError('complete matching native byte images required')
  for name,want in m['identity'].get('runtime_package_versions',{}).items():
   if version(name)!=want:raise ValueError('producer codec library version changed')
  for f,h in m['identity']['source_sha256'].items():
   if sha(ROOT/f)!=h:raise ValueError('immutable producer recipe changed')
  if m['identity']['checkpoint_lock_sha256']!=sha(ROOT/'compiler/models/qwen3-8b/checkpoint_source.json'):raise ValueError('checkpoint lock changed')
  ex=extents(n)
  if set(m['images'])!=immutable_refs(n):raise ValueError('incomplete external provider source coverage')
  self.verified={};self.indices={};self.handles=OrderedDict();self.active=None;self.transactions=0;self.bytes_read=0;self.range_counts=0
  for r,image in m['images'].items():
   if any(image[k]!=ex[r][k]for k in ('base','bytes','codec')):raise ValueError('r17 extent/codec identity changed')
   end=0
   for part in image['segments']:
    if part['start']!=end or part['bytes']<=0 or Path(part['file']).name!=part['file']:raise ValueError('invalid producer page layout')
    end+=part['bytes']
   if end!=image['bytes']:raise ValueError('incomplete producer page layout')
   self.indices[id(image)]=[p['start']for p in image['segments']]
 def _read(self,image,start,count):
  result=bytearray();end=start+count
  starts=self.indices[id(image)];idx=bisect.bisect_right(starts,start)-1
  while start<end:
   p=image['segments'][idx];path=self.directory/p['file'];stat=path.stat();identity=(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
   if path.is_symlink()or stat.st_size!=p['bytes']:raise ValueError('immutable byte page replaced')
   if path.name not in self.verified:
    if sha(path)!=p['sha256']:raise ValueError('immutable byte page hash')
    self.verified[path.name]=identity
   if self.verified[path.name]!=identity:raise ValueError('immutable byte page changed after visibility')
   take=min(end-start,p['start']+p['bytes']-start)
   if path.name not in self.handles:
    if len(self.handles)>=8:os.close(self.handles.popitem(last=False)[1])
    self.handles[path.name]=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
   self.handles.move_to_end(path.name);fd=self.handles[path.name];fs=os.fstat(fd)
   if (fs.st_dev,fs.st_ino,fs.st_size,fs.st_mtime_ns,fs.st_ctime_ns)!=identity:raise ValueError('immutable open page identity')
   data=os.pread(fd,take,start-p['start'])
   if len(data)!=take:raise ValueError('short immutable byte read')
   result.extend(data);start+=take;idx+=1
  return bytes(result)
 def read_tile_bytes(self,request):
  r=request['provider_ref'];image=self.manifest['images'].get(r)
  if image is None or request.get('base')!=image['base']or request.get('bytes')!=image['bytes']or request.get('lease_state')!='visible'or request.get('producer_dependency')!=r+'.codec_backing_visible':raise ValueError('immutable provider ownership/visibility')
  ranges=request['byte_ranges'];lease=request.get('lease')
  if not lease or self.active is not None or not 1<=len(ranges)<=128 or sum(x['bytes']for x in ranges)>4096:raise ValueError('finite provider read acceptance')
  for x in ranges:
   if not 0<x['bytes']<=4096 or x['address']<image['base']or x['address']+x['bytes']>image['base']+image['bytes']:raise ValueError('immutable read byte aperture')
  self.active=lease
  try:
   payload=[self._read(image,x['address']-image['base'],x['bytes'])for x in ranges];self.transactions+=1;self.range_counts+=len(ranges);self.bytes_read+=sum(len(x)for x in payload)
   return dict(provider_ref=r,lease=lease,state='visible',reverse_grant_ACK=True,payloads=payload)
  finally:self.active=None
 def close(self):
  for fd in self.handles.values():os.close(fd)
  self.handles.clear()
 def observations(self):return dict(transactions=self.transactions,bytes=self.bytes_read,byte_ranges=self.range_counts,verified_pages=len(self.verified),read_lease_outstanding=self.active is not None,hardware_timing_credit=False)

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--snapshot',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--admission',type=Path,required=True);ap.add_argument('--go-commit',required=True);a=ap.parse_args();build(a.snapshot,a.out,admission=json.loads(a.admission.read_text()),go_commit=a.go_commit)
