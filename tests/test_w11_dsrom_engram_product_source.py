"""Actual parameter product, immutable provenance and runtime fences; no DUT run."""
import copy,sys,struct
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w11_dsrom_engram_product_source as E


def test_integer_product_all_finite_bf16_against_binary32_rounding():
 q=np.arange(65536,dtype=np.uint16);q=q[((q>>7)&255)!=255]
 for k in [0,0x8000,0x3f80,0xbf80,0x3700,0x7f7f,1,0x8080]:
  a=(q.astype(np.uint32)<<16).view(np.float32);b=np.array([k<<16],dtype=np.uint32).view(np.float32)[0]
  with np.errstate(over='ignore',under='ignore',invalid='ignore'):expected=(a*b).astype(np.float32)
  expected=np.where(expected==0,np.float32(0),expected).astype(np.float32).view(np.uint32)
  actual=np.array([E.mul_bf16_bits(int(v),k) for v in q],dtype=np.uint32)
  assert np.array_equal(actual,expected)
 assert E.mul_bf16_bits(1,0x3700)==0
 assert E.mul_bf16_bits(3,0x3700)==2
 assert E.mul_bf16_bits(5,0x3700)==2
 assert E.mul_bf16_bits(0x8001,0x3700)==0
 with pytest.raises(ValueError,match='nonfinite'):E.mul_bf16_bits(0x7f80,0x3f80)


@pytest.fixture(scope='module')
def retained():
 b=E.retained_source_binding(14)
 q=Path(b['inputs']['q_weight']['path']).read_bytes();k=Path(b['inputs']['k_weight']['path']).read_bytes()
 p,c=E.produce(b,14,q,k)
 return b,q,k,p,c


def test_actual_L14_parameter_product_hash_and_perlane_layout(retained):
 b,q,k,p,c=retained
 assert E.sha(p)=='ab43ae81a7cc77c56b063a7ba730f5f1535c76d04d1dd8507cb6ad3bca22e9fe'
 assert E.sha(c)=='f2297940486c2604a7a4baf8887ed319c264f77cb10ccc3f164c16e01182f377'
 assert len(p)==81920 and len(c)==163840
 words=np.frombuffer(c,dtype='<u4').reshape(-1,2)
 assert not words[:,1].any() and np.array_equal(words[:,0],np.frombuffer(p,dtype='<u4'))
 qbits=struct.unpack('<20480H',q);kbits=struct.unpack('<20480H',k);product=struct.unpack('<20480I',p)
 for head in range(4):
  for lane in range(1024):
   for slot in range(5):
    i=head*5120+slot*1024+lane
    assert product[i]==E.mul_bf16_bits(qbits[i],kbits[i])


def test_missing_L1_and_L14_substitution_rejected(retained):
 b,q,k,_,_=retained
 assert E.retained_source_binding(1) is None
 with pytest.raises(ValueError,match='unbound'):E.produce(None,1,q,k)
 bad=copy.deepcopy(b);bad['layer']=1
 for family in ('q_weight','k_weight'):bad['inputs'][family]['tensor']=f'layers.1.engram.{family}'
 with pytest.raises(ValueError,match='immutable source manifest'):E.produce(bad,1,q,k)
 with pytest.raises(ValueError,match='L1'):E.require_full40_source_pairs(E.contract())
 fake=E.contract();fake['inputs']['L1']=copy.deepcopy(fake['inputs']['L14']);fake['inputs']['L1']['layer']=1
 with pytest.raises(ValueError,match='immutable'):E.require_full40_source_pairs(fake)


@pytest.mark.parametrize('mutation',['SHA','manifestSHA','dtype','shape','revision'])
def test_provenance_mutants_rejected(retained,mutation):
 b,q,k,_,_=retained;b=copy.deepcopy(b)
 if mutation=='SHA':b['inputs']['q_weight']['sha256']='0'*64
 elif mutation=='manifestSHA':b['inputs']['q_weight']['source_manifest_sha256']='0'*64
 elif mutation=='dtype':b['inputs']['q_weight']['dtype']='F32'
 elif mutation=='shape':b['inputs']['q_weight']['shape']=[20480]
 else:b['checkpoint_revision']='other'
 with pytest.raises(ValueError):E.produce(b,14,q,k)


def test_existing_SU_producer_descriptor_only_no_BF16_round():
 with pytest.raises(ValueError,match='opt_in'):E.lower_vm_product(0,20480,40960)
 op=E.lower_vm_product(0,20480,40960,opt_in=True)
 assert op['m1']==E.I.M1_AB and op['rnd']==0 and op['su_nout']==4 and op['su_nin']==5120
 import w11_dsrom_crom_demand as D
 f=E.I.decode(E.I.encode(full_shape=True,**op),full_shape=True)
 assert len(list(D.batches(f)))==20
 import v41_su_legality as L
 assert not L.check_op(f,1024,256,7)
 with pytest.raises(ValueError,match='overlap'):E.lower_vm_product(0,100,40960,opt_in=True)


def test_runtime_exactbits_publication_and_final_lifetime(retained):
 b,q,k,p,_=retained;a,_=E.object_json(E.PROGRAM_PIN,E.PROGRAM_PATH)
 tag=E.runtime_product_tag(b,0,12,a['ranks'][0]['encoded_template_sha256'],E.sha(p))
 args=dict(producer_done=True,output_quiet=True,consumer_drain=False)
 v=E.accept_runtime_product(b,14,q,k,p,tag,tag,**args)
 assert v['product_visible'] and v['consumer_read_allowed'] and not v['credit_release_allowed']
 assert v['physical_CROM_base'] is None
 for flag in ['producer_done','output_quiet']:
  bad=dict(args);bad[flag]=False
  with pytest.raises(ValueError,match='not yet visible'):E.accept_runtime_product(b,14,q,k,p,tag,tag,**bad)
 for value in ['X',None,1]:
  bad=dict(args);bad['producer_done']=value
  with pytest.raises(ValueError,match='not yet visible'):E.accept_runtime_product(b,14,q,k,p,tag,tag,**bad)
 bad=dict(args);bad['consumer_drain']='X'
 with pytest.raises(ValueError,match='unknown'):E.accept_runtime_product(b,14,q,k,p,tag,tag,**bad)
 wrong=bytearray(p);wrong[0]^=1
 with pytest.raises(ValueError):E.accept_runtime_product(b,14,q,k,bytes(wrong),tag,tag,**args)
 bad=copy.deepcopy(tag);bad['program_sha256']='0'*64
 with pytest.raises(ValueError,match='program'):E.accept_runtime_product(b,14,q,k,p,bad,bad,**args)
 bad=copy.deepcopy(tag);bad['epoch']+=1
 with pytest.raises(ValueError,match='epoch'):E.accept_runtime_product(b,14,q,k,p,bad,tag,**args)
 bad=copy.deepcopy(tag);bad['CROM_image_sha256']='0'*64
 with pytest.raises(ValueError,match='identity'):E.accept_runtime_product(b,14,q,k,p,bad,bad,**args)
