#!/usr/bin/env python3
"""Minimum placement gate, run remotely under measured admission."""
import json
import hbm_accel_die_fp as f
for variant in (f.R25I, f.R25IC2):
 m=f.build(variant,geometry_only=True)
 idx=[i for i in m['insts'] if i.name.startswith('idx_')]
 overlaps=[(a.name,b.name) for a in idx for b in m['insts'] if a is not b and
  min(a.x+a.w,b.x+b.w)>max(a.x,b.x)+1e-6 and
  min(a.y+a.h,b.y+b.h)>max(a.y,b.y)+1e-6]
 print(json.dumps(dict(variant='r25ic2' if variant.get('indexer_large_slot') else 'r25i',
  geo=m['geo'], native=[dict(name=i.name,x=i.x,y=i.y,w=i.w,h=i.h) for i in idx],overlaps=overlaps)))
 assert not overlaps,overlaps
 print('INDEXER_GEOMETRY_PASS')
