from pathlib import Path
from collections import defaultdict
from bisect import bisect_left
import json
import census as C
D=C.D;g=C.g;P=C.P;groups=defaultdict(list);shared=[];unknown=[]
for cid in C.comb:
 mask=C.mask[cid];chunks=set()
 while mask:
  b=(mask&-mask).bit_length()-1;chunks.add(b//64);mask&=mask-1
 if len(chunks)==1:groups[next(iter(chunks))].append(cid)
 elif chunks:shared.append(cid)
 else:unknown.append(cid)
rows=[];allnames=sorted(c[6].replace(chr(92),'') for c in D.cells.values());seen=set();spec=['# STATIC PREP only; no native source or dispatch.','set ::ot_mrg_spec {']
for chunk,cs in sorted(groups.items()):
 ff=[cid for cid,bit in C.semantic.items()if bit//64==chunk];xs=[g.ctr(D.cells[k])[0]for k in ff];x0,x1=min(xs)-.54,max(xs)+.54;y0,y1=17.28,82.08;area=sum((D.cells[k][4]-D.cells[k][2])*(D.cells[k][5]-D.cells[k][3])for k in cs);other=0;members=set(cs)
 for cid,c in D.cells.items():
  if cid in members:continue
  other+=max(0,min(x1,c[4])-max(x0,c[2]))*max(0,min(y1,c[5])-max(y0,c[3]))
 names=sorted(D.cells[k][6].replace(chr(92),'') for k in cs);expanded=set()
 for n in names:
  k=bisect_left(allnames,n)
  while k<len(allnames) and allnames[k].startswith(n):expanded.add(allnames[k]);k+=1
 assert expanded==set(names);assert not seen&expanded;seen|=expanded
 rows.append(dict(chunk=chunk,cells=len(cs),box=[x0,y0,x1,y1],movable_area_um2=area,current_other_body_intersection_um2=other,conservative_fill=(area+other)/((x1-x0)*(y1-y0)),names=names))
 spec.append(' hroot_native_chunk%d {'%chunk);spec.extend('  {'+n+'}'for n in names);spec.append(' } '+' '.join(str(round(v,6))for v in [x0,y0,x1,y1]))
spec.append('}')
res=dict(scope='STATIC exact native64-bit chunk ownership; no CAD/source/plan edit or legal-site/PG claim',groups=rows,owned=len(seen),crosschunk_shared=len(shared),unowned_output=len(unknown),unselected_clock_cone_in_target=sum(C.prefix in D.cells[c][6]for c in C.clock),finding='Five full-height native chunk guides own4609 cells versus ten role guides3409; preserves1200 shared write/read combinational cells within real native chunk affinity. Actual postDPL capacity/PG/TAP and all19/clock gates remain held.')
(P/'chunk_guides.json').write_text(json.dumps(res,indent=1)+'\n');(P/'chunk_guide_spec_PREP.tcl').write_text('\n'.join(spec)+'\n');print([(r['chunk'],r['cells'],round(r['conservative_fill'],3))for r in rows]);print(res['owned'],len(shared),len(unknown))
