#!/usr/bin/env python3
"""Minimum producer gate against independent golden address/image functions."""
import copy,json
from pathlib import Path
import numpy as np
import kv_ingest_ref as R
from s81_native_install import produce

cfg=dict(stacks=[dict(id=i,name=['SW','SE','NW','NE'][i],physical_capacity_sectors=65536,usable_sectors=58982) for i in range(4)],
 engram_home_stack_ids=[0,1],host_stack_stride_sectors=32768,users=2,positions_per_user=64,rope_positions=64,
 engram_pc_local_atom_count=36,window_ring_rows=128,window_stack_id=0,
 mutable_regions=[dict(kind='KEY',global_base_sector=0),dict(kind='CKV',global_base_sector=8192),dict(kind='WINDOW',global_base_sector=16384)])
out=produce(cfg);checked=0
for d in out['descriptors']:
 w=int(d['descriptor_hex'],16);base=(w>>16)&0xffffffff;stride=(w>>48)&0xffffffff
 first=(w>>144)&0xffffff;n=(w>>184)&0xffffffff;rb=(w>>168)&0xffff;ring=(w>>112)&0xffffffff
 if d['kind']=='KEY':
  image=R.ikey_image(4*32768,[b'\x5a'*68]*n,first,base,stride,1,0,4)
 else:
  pitch=(w>>80)&0xffffffff
  image=R.rows_image(4*32768,[b'\x5a'*rb]*n,first,rb,pitch,base,stride,1,0,4,ring=ring)
 touched=np.flatnonzero(image.reshape(-1,32).any(axis=1))
 for a in touched:
  s=int(a)//32768;local=int(a)%32768
  if not any(r['kind']==d['kind'] and r['base']<=local<r['end'] for r in out['stacks'][s]['mutable_regions']):
   raise AssertionError('golden touched outside installed descriptor region')
 checked+=len(touched)
 if ((w>>240)&65535)!=d['payload_beats']:raise AssertionError('descriptor beats mismatch')
for mutate in ['capacity','overlap','missing','homes','span','window']:
 bad=copy.deepcopy(cfg)
 if mutate=='capacity':bad['stacks'][0]['usable_sectors']=1
 if mutate=='overlap':bad['mutable_regions'][1]['global_base_sector']=0
 if mutate=='missing':bad['mutable_regions'].pop()
 if mutate=='homes':bad['engram_home_stack_ids']=[0,0]
 if mutate=='span':bad['engram_pc_local_atom_count']=1<<29
 if mutate=='window':bad['host_stack_stride_sectors']=16
 try:produce(bad)
 except ValueError:pass
 else:raise AssertionError('negative escaped '+mutate)
print('S81_INSTALL PASS golden_touched_sectors=%d descriptors=%d negatives=6 ND1NS4'%(checked,len(out['descriptors'])))
if len(__import__('sys').argv)>1:
 cfg=json.loads(Path(__import__('sys').argv[1]).read_text());out=produce(cfg)
 print('S81_INSTALL CANDIDATE home_mutable_end=%s home_final_end=%s capacity=%s'%(
  [out['stacks'][s]['mutable_reserved_end'] for s in out['engram_home_stack_ids']],
  [out['stacks'][s]['installed_end'] for s in out['engram_home_stack_ids']],
  [out['stacks'][s]['usable_sectors'] for s in out['engram_home_stack_ids']]))
