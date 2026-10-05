"""Codec/transport tests use small explicit source tensors; not a trained token claim."""
import copy,hashlib,json,sys,tempfile
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_trained_byte_provider as B
# Original ABI class is extracted from immutable41eef, so main's restored source
# is never imported or rewritten. The relocated implementation gets its own join.
import ast,subprocess
archived=subprocess.check_output(['git','show','41eef76fa:tools/h3_qwen_complete_native.py'],cwd=B.ROOT,text=True)
node=next(n for n in ast.parse(archived).body if isinstance(n,ast.ClassDef)and n.name=='HBMByteTileProvider')
namespace={'np':np,'F':np.float32};exec(compile(ast.Module(body=[node],type_ignores=[]),'archived41eef-HBMByteTileProvider','exec'),namespace)
HBMByteTileProvider=namespace['HBMByteTileProvider']

def test_full_source_coverage():
 n=B.native();assert len(n['operations'])==1737;assert len(n['source_program']['weight_descriptors'])==290;assert len(B.refs(n))==732;assert not B.refs(n)-B.extents(n).keys()
 for d in n['source_program']['weight_descriptors'].values():
  r=f"Qwen.rank{d['die']}.extent."+('head'if d['layer']is None else f"L{d['layer']}.{d['name']}")
  assert B.extents(n)[r+'.codes']['bytes']==d['rows']*d['K'];assert B.extents(n)[r+'.scales']['bytes']==d['rows']*2

def test_bf16_codec():
 import torch
 from qwen_hbm_complete_executor import bf16
 x=torch.tensor([0.,-0.,1.,-2.,1.0078125],dtype=torch.bfloat16);got=(np.frombuffer(B.bfbytes(x),'<u2').astype(np.uint32)<<16).view(np.float32);assert np.array_equal(got.view(np.uint32),x.float().numpy().view(np.uint32))

def test_full_row_quantize_before_tp_slice(tmp_path):
 import torch
 from safetensors.torch import save_file
 from qwen3_deployment_quality import quantize_w8
 torch.set_num_threads(1)
 w=torch.tensor([[.125, .5, 8.,16.],[1.,2.,3.,4.],[4.,3.,2.,1.],[9.,8.,.125,.25]],dtype=torch.bfloat16);gamma=torch.tensor([1.,2.,.5,1.],dtype=torch.bfloat16);path=tmp_path/'source.safetensors';save_file({'w':w},str(path))
 class Reader:
  index={'w':'source.safetensors'}
  def _verified_file(self,name):return path
  def tensor(self,name):return gamma
  def read_tensor(self,name,a,b):return w[a:b]
 d=dict(name='down',die=1,K=2,rows=4,folded_norm='gamma',checkpoint_sources=['w']);pages=list(B.matrix_rows(Reader(),d,batch=2));q,s,_=quantize_w8(w.float()*gamma.float()[None,:]);assert b''.join(x[1]for x in pages)==q[:,2:].contiguous().numpy().tobytes();assert b''.join(x[2]for x in pages)==B.bfbytes(s)
 d.update(name='qkv',die=0,K=4,rows=2);pages=list(B.matrix_rows(Reader(),d,batch=1));assert b''.join(x[1]for x in pages)==q[:2].numpy().tobytes()

def backend(tmp_path):
 r='Qwen.rank0.extent.test.codes';e=dict(provider_ref=r,base=64,bytes=6,codec={'data':'signed_INT8_row_major'});n=dict(source_program={},provider_binding=dict(allocation=[dict(extents=[e])]),operations=[dict(provider_binding=dict(external_providers=[dict(provider_ref=r)]))]);parts=[]
 for i,data in enumerate([b'\x01\x02\x03',b'\x04\x05\x06']):
  p=tmp_path/f'p{i}.bin';p.write_bytes(data);parts.append(dict(file=p.name,start=i*3,bytes=3,sha256=B.sha(p)))
 m=dict(schema='opentallas.Qwen.trained-byte-images.v1',complete=True,identity=dict(native_sha256=hashlib.sha256(B.canonical(n)).hexdigest(),source_sha256={},checkpoint_lock_sha256=B.sha(B.ROOT/'compiler/models/qwen3-8b/checkpoint_source.json')),images={r:dict(base=64,bytes=6,codec=e['codec'],segments=parts)});(tmp_path/'manifest.json').write_bytes(B.canonical(m));b=B.TrainedByteBackend(tmp_path,n);req=dict(provider_ref=r,base=64,bytes=6,lease_state='visible',lease='PC1.'+r,producer_dependency=r+'.codec_backing_visible',byte_ranges=[dict(address=66,bytes=3)]);return b,req,n

def test_cross_page_addressed_bytes(tmp_path):
 b,r,_=backend(tmp_path);reply=b.read_tile_bytes(r);assert reply['payloads']==[b'\x03\x04\x05'];assert reply['reverse_grant_ACK'];assert b.active is None

def test_existing_adapter_reads_only_bytes(tmp_path):
 b,r,_=backend(tmp_path);x=HBMByteTileProvider(b).read_tile(r,'matrix_tile');assert x.dtype==np.int8;assert x.tolist()==[[3,4,5]]

@pytest.mark.parametrize('change',[{'base':0},{'lease_state':'pending'},{'producer_dependency':'unpublished'},{'byte_ranges':[dict(address=63,bytes=1)]},{'byte_ranges':[dict(address=68,bytes=3)]},{'byte_ranges':[dict(address=64,bytes=0)]}])
def test_bad_provider_requests_rejected(tmp_path,change):
 b,r,_=backend(tmp_path);r.update(change)
 with pytest.raises(ValueError):b.read_tile_bytes(r)

def test_page_tamper_after_visibility(tmp_path):
 b,r,_=backend(tmp_path);b.read_tile_bytes(r);(tmp_path/'p0.bin').write_bytes(b'xxx');import os
 # Deliberate mutation test changes the declared immutable inode identity explicitly.
 file=tmp_path/'p0.bin';before=file.stat();os.utime(file,ns=(before.st_atime_ns,before.st_mtime_ns+1000000000))
 with pytest.raises(ValueError):b.read_tile_bytes(r)

def test_finite_read_acceptance(tmp_path):
 b,r,_=backend(tmp_path);b.active='held'
 with pytest.raises(ValueError):b.read_tile_bytes(r)

def test_incomplete_native_images_rejected(tmp_path):
 b,r,n=backend(tmp_path);m=json.loads((tmp_path/'manifest.json').read_text());m['images'][r['provider_ref']]['segments'][1]['start']=4;(tmp_path/'manifest.json').write_bytes(B.canonical(m))
 with pytest.raises(ValueError):B.TrainedByteBackend(tmp_path,n)

def test_model_precedes_implementation():
 m=json.loads((B.ROOT/'results/uarch/qwen_trained_byte_provider_20261002/model.json').read_text());assert m['model_before_implementation'];assert m['image_bytes']==9428966912;assert m['admission']['wall_limit']is None

def test_real_production_preparation_is_full_and_data_fail_closed():
 import prepare_qwen_trained_native as P
 p=P.prepare();assert p['scope']['layers']==36;assert p['scope']['tokens']==1;assert not p['scope']['fixture_weights'];assert p['policy']['FSIZE']=='unlimited';assert p['policy']['wall_limit']is None
 if p['missing_checkpoint_files']:assert p['readiness']=='BLOCKED_CHECKPOINT_DATA_AND_FRESH_FLEET_ADMISSION'

def test_missing_admission_rejected_before_production(tmp_path):
 import qwen_trained_native_run as R
 with pytest.raises(ValueError,match='fresh trained-native resource GO'):R.validate_admission({'admitted':False},'unused')

def test_actual_inventory_guards(tmp_path):
 import qwen_trained_native_run as R
 file=tmp_path/'page';file.write_bytes(b'1234');a=dict(disk_headroom_bytes=0,aggregate_output_bytes=3)
 with pytest.raises(ValueError,match='aggregate'):R.guard(a,tmp_path)
 a['aggregate_output_bytes']=4;R.guard(a,tmp_path)
 a['disk_headroom_bytes']=10**30
 with pytest.raises(ValueError,match='headroom'):R.guard(a,tmp_path)


def test_requested_images_exclude_runtime_mutable_KV_state():
 n=B.native();ex=B.extents(n);wanted=B.immutable_refs(n)
 runtime_refs={r['provider_ref']for o in n['operations']if o['opcode']in ('KV_WRITE','KV_READ','KV_FENCE')for r in o['provider_binding']['external_providers']}
 assert wanted==B.refs(n)-runtime_refs
 assert len(wanted)==586 and len(runtime_refs)==146
 assert sum(ex[r]['bytes']for r in wanted)==8824912128
 assert 'Qwen.rank1.extent.L0.down.scales'not in wanted
 assert 'Qwen.rank0.extent.L0.down.scales'in wanted
 assert 'Qwen.rank1.extent.L0.down.codes'in wanted

def test_build_column_shards_without_unrequested_scale_or_mutable_images(tmp_path,monkeypatch):
 # Tiny explicit codec fixture tests real build/manifest/backend lifecycle, not trained numerics.
 import collections,qwen_hbm_complete_executor as E,qwen_trained_native_run as R
 base='Qwen.rank';rows=[]
 for die in (0,1):
  for suffix in ('codes','scales'):
   rows.append(dict(provider_ref=f'{base}{die}.extent.L0.down.{suffix}',base=64+len(rows)*64,bytes=4,codec={'data':'signed_INT8_row_major'if suffix=='codes'else 'BF16_little_endian'},role='immutable_checkpoint_W8'if suffix=='codes'else 'immutable_checkpoint_BF16_scales'))
 rows.append(dict(provider_ref='Qwen.rank0.extent.KV_provider_state',base=512,bytes=4,codec={'data':'state'},role='software_KV_publication_and_reader_lease_state'))
 consumed=[rows[0],rows[1],rows[2],rows[4]]
 n=dict(provider_binding={'allocation':[{'extents':rows}]},provider_binding_pin='explicit-fixture',operations=[{'provider_binding':{'external_providers':[{'provider_ref':x['provider_ref']}for x in consumed]}}],source_program=dict(weight_descriptors={f'd{d}':dict(die=d,layer=0,name='down',checkpoint_sources=['w'],folded_norm=None,rows=2,K=2)for d in (0,1)},config={'vocab_size':0,'hidden_size':2}))
 class Reader:
  checkpoint_revision='fixture';file_pins={};index=collections.defaultdict(lambda:'fixture')
  def __init__(self,*args,**kwargs):pass
  def _verified_file(self,name):pass
  def provenance(self):return {'explicit_fixture':True}
 monkeypatch.setattr(E,'CheckpointWeights',Reader)
 monkeypatch.setattr(B,'validate_checkpoint_inventory',lambda *args:{})
 monkeypatch.setattr(R,'validate_admission',lambda *args:None)
 monkeypatch.setattr(R,'guard',lambda *args,**kwargs:None)
 monkeypatch.setattr(B,'matrix_rows',lambda *args:iter([(0,b'abcd',b'efgh')]))
 out=tmp_path/'images';manifest=B.build(tmp_path,out,n,admission={})
 assert set(manifest['images'])=={x['provider_ref']for x in consumed[:-1]}
 assert not list(out.glob('Qwen_rank1_extent_L0_down_scales*'))
 backend=B.TrainedByteBackend(out,n)
 assert backend.active is None
 # Explicit resumed lifecycle must also skip an unconsumed scale without a KeyError.
 again=B.build(tmp_path,out,n,admission={});assert again['images']==manifest['images']


def test_all290_matrix_inventory_is_validated():
 plan=B.matrix_inventory(B.native());assert len(plan)==290
 assert sum(p['scale_ref']is None for p in plan.values())==72
 assert all(p['code_ref']for p in plan.values())
 assert plan['L0.down.d0']['scale_ref']=='Qwen.rank0.extent.L0.down.scales'
 assert plan['L0.down.d1']['scale_ref']is None

@pytest.mark.parametrize('mutation',['codec','family','missing_descriptor','scale_owner'])
def test_unsupported_matrix_inventory_rejected_before_pages(tmp_path,mutation):
 n=B.native()
 if mutation=='codec':B.extents(n)['Qwen.rank1.extent.L0.down.codes']['codec']['data']='packed_INT4_unsupported'
 elif mutation=='family':n['source_program']['weight_descriptors']['L0.down.d1']['name']='unsupported_projection'
 elif mutation=='missing_descriptor':del n['source_program']['weight_descriptors']['L0.down.d1']
 else:
  for op in n['operations']:
   if op['opcode']=='ALL_REDUCE'and any(x['provider_ref']=='Qwen.rank0.extent.L0.down.scales'for x in op['provider_binding']['external_providers']):
    op['provider_binding']['external_providers'][0]['provider_ref']='Qwen.rank1.extent.L0.down.scales';break
 with pytest.raises(ValueError):B.build(tmp_path,tmp_path/'images',n,admission={})
 assert not(tmp_path/'images').exists()


@pytest.mark.parametrize('dtype',['bfloat16','float16'])
def test_actual_checkpoint_header_format_gate(tmp_path,dtype):
 import torch
 from safetensors.torch import save_file
 path=tmp_path/'source.safetensors';save_file({'w':torch.ones((2,4),dtype=getattr(torch,dtype))},str(path))
 class Reader:
  index={'w':'source.safetensors'}
  def _verified_file(self,name):return path
 descriptor=dict(name='down',die=1,K=2,rows=2,folded_norm=None,checkpoint_sources=['w'])
 n={'source_program':{'weight_descriptors':{'actual-header':descriptor}}}
 if dtype=='bfloat16':assert B.validate_checkpoint_inventory(Reader(),n)['actual-header'][0]['shape']==[2,4]
 else:
  with pytest.raises(ValueError,match='unsupported checkpoint matrix format'):B.validate_checkpoint_inventory(Reader(),n)
