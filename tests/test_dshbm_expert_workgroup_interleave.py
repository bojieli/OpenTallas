import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import numpy as np
import pytest
from dshbm_expert_workgroup_interleave import chunks,compact_stream,expand_stream,sector_addresses,paired_rows
from dshbm_expert_workgroup import weight_lines

@pytest.mark.parametrize('ids',[(41,65,158,164,259,266),(128,129,142,159,160,228),(0,7,14,21,28,35),(0,6,7,377,382,383)])
def test_classes_and_all_sectors_once(ids):
 p=chunks(ids);assert len(p)==30
 for k,e in enumerate(ids):
  c=[x for x in p if x.slot==k];assert [x.j0 for x in c]==[0,8,16,24,32]
  assert [x.keep for x in c]==[True,True,True,False,False]
  for pc in range(32):
   a=[v for x in c for v in sector_addresses(x,pc)]
   assert len(a)==len(set(a))==49
   assert [v[3]*4+v[4] for v in a]==[j*32+pc for j in range(49)]
 for k in range(6):
  same=[r for r in range(k) if ids[r]%7==ids[k]%7]
  if same:
   assert max(i for i,x in enumerate(p[:24]) if x.slot==max(same)) < min(i for i,x in enumerate(p[:24]) if x.slot==k)

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
