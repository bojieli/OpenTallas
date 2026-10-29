#!/usr/bin/env python3
"""Actual-metal connectivity through read-back physical via layer enclosures."""
import argparse,json,collections
from shapely.geometry import box
from shapely.strtree import STRtree
p=argparse.ArgumentParser();p.add_argument('--actual',required=True);p.add_argument('--grid',required=True);p.add_argument('--out',required=True);a=p.parse_args();d=json.load(open(a.actual));rr=d['records'];pg=json.load(open(a.grid));grid={(n,ly,*[round(v*1000) for v in r]) for n,ly,*r in pg};parent=list(range(len(rr)))
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def union(i,j):
 i,j=root(i),root(j)
 if i!=j:parent[j]=i
layers=collections.defaultdict(list);top=[]
for i,r in enumerate(rr):
 for ly,*xy in r['rects']:
  layers[r['net'],ly].append((i,xy))
  if (r['net'],ly,*xy) in grid and ly=='M8':top.append(i)
for key,items in layers.items():
 bb=[box(*q) for i,q in items];tree=STRtree(bb)
 for j,geom in enumerate(bb):
  for k in tree.query(geom,predicate='intersects'):union(items[j][0],items[k][0])
toproots={root(i) for i in top};bad=[q for q in d['contacts'] if root(q['record']) not in toproots];counts=collections.Counter(root(q['record']) for q in d['contacts']);s=dict(actual_contacts=len(d['contacts']),physically_connected_to_actual_canonical_M8_grid=len(d['contacts'])-len(bad),unconnected=bad,actual_vias=d['via_count'],actual_wires=d['wire_count'],source=d['source'],scope='Scoped physical coupon, not whole die PG/DRC/IR',verdict='PASS_SCOPED_PHYSICAL_CONNECTIVITY' if not bad else 'FAIL');json.dump(s,open(a.out,'w'),indent=2);print(s)
if bad:raise SystemExit(1)
