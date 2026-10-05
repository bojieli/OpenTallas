import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import numpy as np
import pytest
from dshbm_expert_workgroup_interleave import chunks,compact_stream,expand_stream,sector_addresses,paired_rows
from dshbm_expert_workgroup import weight_lines

@pytest.mark.parametrize('ids',[(41,65,158,164,259,266),(128,129,142,159,160,228),(0,7,14,21,28,35),(0,6,7,377,382,383)])
def test_classes_and_all_sectors_once(ids):
 p=chunks(ids);assert len(p)==42
 for k,e in enumerate(ids):
  c=[x for x in p if x.slot==k];assert [x.j0 for x in c]==[0,8,16,24,32,40,48]
  assert [x.keep for x in c]==[True,True,True,False,True,True,False]
  for pc in range(32):
   a=[v for x in c for v in sector_addresses(x,pc)]
   assert len(a)==len(set(a))==49
   assert [v[3]*4+v[4] for v in a]==[j*32+pc for j in range(49)]
 for c in p: assert 1<=c.sectors<=8
 for k in range(6):
  same=[r for r in range(k) if ids[r]%7==ids[k]%7]
  if same:
   assert max(i for i,x in enumerate(p[:24]) if x.slot==max(same)) < min(i for i,x in enumerate(p[:24]) if x.slot==k)
   assert max(i for i,x in enumerate(p[24:]) if x.slot==max(same)) < min(i for i,x in enumerate(p[24:]) if x.slot==k)

@pytest.mark.parametrize('ids',[(1,1,2,3,4,5),(0,1,2,3,4,384)])
def test_no_router_repair(ids):
 with pytest.raises(ValueError):chunks(ids)


def test_byte_gearbox_tail_and_corruption():
 p=np.arange(12*2560,dtype=np.uint32).astype(np.uint8).reshape(12,2560)
 s=np.arange(12*160,dtype=np.uint32).astype(np.uint8).reshape(12,160)
 raw=compact_stream(p,s);assert len(raw)==32768
 assert expand_stream(raw)==weight_lines(p,s)
 broken=bytearray(raw);broken[7]^=1
 assert expand_stream(broken)!=weight_lines(p,s)
 broken[-1]=1
 with pytest.raises(ValueError):expand_stream(broken)


def test_actual_row_pair_assignment_all_dies_no_alias():
 def read(e,m,a,b):
  return np.broadcast_to(np.arange(a,b,dtype=np.uint32).astype(np.uint8)[:,None],(b-a,2560)).copy(),np.full((b-a,160),1 if m=='w1' else 3,np.uint8)
 for die in (0,95):
  for q in range(4):
   p,s=paired_rows(read,383,die,q)
   assert p[::2,0].tolist()==[v%256 for v in range(die*24+q*6,die*24+q*6+6)]
   assert np.array_equal(p[::2],p[1::2]) and np.all(s[::2]==1) and np.all(s[1::2]==3)


def test_a8_descriptors_preserve_default_and_actual_row_views():
 from dshbm_expert_interleave_descriptor import compile_descriptors_a8
 from dshbm_expert_workgroup_descriptor import compile_descriptors
 ids=(41,65,158,164,259,266);kw=dict(layer=20,die=95,input_job='actual-retained-L20')
 assert compile_descriptors_a8(ids,**kw)==compile_descriptors(ids,**kw)
 a=compile_descriptors_a8(ids,**kw,interleave8=True)
 assert [d['sm'] for d in a['descriptors']]==list(range(24))
 for k,e in enumerate(ids):
  for parity,w in enumerate(('w1','w3')):
   covered=[]
   for q in range(4):
    d=a['descriptors'][4*k+q];v=d['source_views'][parity]
    assert v['tensor']==f'layers.20.ffn.experts.{e}.{w}.weight'
    assert v['native_rows']==list(range(parity,12,2))
    covered.extend(range(v['row_start'],v['row_stop']))
   assert covered==list(range(2280,2304))


def test_w2_real_source_rows_tail_and_prefix_are_not_uniform():
 from dshbm_expert_workgroup_interleave import w2_source_rows,w2_legacy_tail,w2_compact_stream,w2_stream
 from dshbm_matched_sm_seq import gen_op
 def read(e,m,a,b):
  assert m=='w2'
  p=np.broadcast_to(np.arange(1152,dtype=np.uint32).astype(np.uint8),(b-a,1152)).copy()
  p[:,0]=np.uint8(a%256)
  return p,np.full((b-a,72),127,np.uint8)
 views=w2_source_rows(read,383,2,0)  # actual54 rows106..159, not die0's53
 assert [v['suffix_capacity_lines'] for v in views]==[10,10,0,0,28,28,28,28]
 assert [len(v['rows']) for v in views]==[1,1,0,0,3,3,3,3]
 raw,lut,prefix,native=w2_legacy_tail(views)
 assert len(raw)==136*128 and lut[-4:]==((255,255),)*4
 assert len(prefix[0])==64 and len(prefix[4])==96
 full,full_lut,counts,full_native=w2_stream(views)
 assert counts==(10,10,0,0,29,29,29,29) and len(full)==len(raw)==136*128
 assert len(full_lut)==136 and all(m<8 for m,l in full_lut)
 offset=0
 for i,v in enumerate(views):
  source,_=w2_compact_stream(v['packed'],v['scale'])
  assert full[offset:offset+len(source)]==source
  assert all(x==0 for x in full[offset+len(source):offset+counts[i]*128])
  offset+=counts[i]*128
 assert full_native==native

 off=0
 for i,v in enumerate(views):
  compact,words=w2_compact_stream(v['packed'],v['scale']);n=v['suffix_capacity_lines']*128
  assert prefix[i]+raw[off:off+len(compact)-len(prefix[i])]==compact
  assert all(x==0 for x in raw[off+len(compact)-len(prefix[i]):off+n]);off+=n
  if v['rows']:
   g=gen_op('v41_fp4',len(v['rows']),2304,8,None,
        X=[np.zeros(2304,np.float32) for _ in range(8)],released_fp4=(v['packed'],v['scale']))
   assert tuple(g['lines'])==words==native[i]
 assert sum(len(v['rows']) for q in range(4) for v in w2_source_rows(read,383,0,q))==53
 assert sum(len(v['rows']) for q in range(4) for v in w2_source_rows(read,383,2,q))==54
