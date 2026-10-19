"""UNEXECUTED SOURCE successor kernel. Exact integer interval / pair minimizer.

For fixed H ray, the previous candidate pair has cost
  |ax-v| + |v-w| + |bx-w| + vertical_constant.
H occupancy partitions columns into connected free integer intervals; v,w
must inhabit the same interval. Endpoint V and local-jog feasibility depend
only on that endpoint column. For sorted feasible B columns, prefix minima
of (|bx-w|-w) and suffix minima of (|bx-w|+w) give the exact minimum for each
A column. This removes the Cartesian pair enumeration without changing any
candidate, occupied interval, objective, or original (A-rank,B-rank) tiebreak.
Outer H-ray order and strict improvement test must remain unchanged.
"""
import bisect,collections
def optimum_pair(a_candidates,b_candidates,blocked,ax,bx):
 """Inputs (layer,x,original_rank); blocked are inclusive H forbidden spans.
 Returns (cost,a_rank,b_rank,a_layer,a_x,b_layer,b_x), or None.
 """
 merged=[]
 for lo,hi in sorted(blocked):
  if merged and lo<=merged[-1][1]+1:merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
  else:merged.append((lo,hi))
 ends=[b for a,b in merged]
 def component(x):
  k=bisect.bisect_left(ends,x)
  return None if k<len(merged) and merged[k][0]<=x else k
 aa=collections.defaultdict(list);bb=collections.defaultdict(list)
 for l,x,r in a_candidates:
  k=component(x)
  if k is not None:aa[k].append((x,r,l))
 for l,x,r in b_candidates:
  k=component(x)
  if k is not None:bb[k].append((x,r,l))
 result=None
 for k,aas in aa.items():
  bs=sorted(bb[k]);xs=[x for x,r,l in bs]
  if not bs:continue
  pref=[];best=None
  for x,r,l in bs:
   z=(abs(bx-x)-x,r,l,x);best=z if best is None else min(best,z);pref.append(best)
  suff=[None]*len(bs);best=None
  for j in range(len(bs)-1,-1,-1):
   x,r,l=bs[j];z=(abs(bx-x)+x,r,l,x);best=z if best is None else min(best,z);suff[j]=best
  for x,r,l in aas:
   j=bisect.bisect_right(xs,x);choices=[]
   if j:
    q,br,bl,bv=pref[j-1];choices.append((q+x,br,bl,bv))
   if j<len(bs):
    q,br,bl,bv=suff[j];choices.append((q-x,br,bl,bv))
   q,br,bl,bv=min(choices);z=(abs(ax-x)+q,r,br,l,x,bl,bv)
   result=z if result is None else min(result,z)
 return result
