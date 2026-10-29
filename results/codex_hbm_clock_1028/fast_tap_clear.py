"""HBM planner adapter: vectorize the existing exact candidate legality filter.
Candidate construction and Python tie-break are byte-for-byte the shared policy.
"""
import math
import numpy as np

def install(S):
 original=S.tap_clear
 def tap_clear(t,x,y,taken=(),clear=S.TAP_CLEAR_UM,strict=False):
  w,h=t['outline_um'];boxes=list(S.placed_macro_boxes(t,halo=clear).values())
  boxes.extend((a-clear,b-clear,c+clear,d+clear) for a,b,c,d in t.get('clock',{}).get('keepouts_um',[]))
  def free(px,py):
   return (clear<=px<=w-clear and clear<=py<=h-clear and not any(abs(px-a)<clear and abs(py-b)<clear for a,b in taken) and not any(x0<px<x1 and y0<py<y1 for x0,y0,x1,y1 in boxes))
  if (not boxes and not strict) or free(x,y):return x,y
  def candidates(origin,extent,edges):
   values={origin}
   for edge in [clear,extent-clear]+list(edges):
    q=(edge-origin)/S.TAP_STEP_UM
    for k in (math.floor(q),math.ceil(q)):
     v=round(origin+k*S.TAP_STEP_UM,8)
     if clear-1e-7<=v<=extent-clear+1e-7:values.add(v)
   return values
  obs=boxes+[(a-clear,b-clear,a+clear,b+clear) for a,b in taken]
  xs=list(candidates(x,w,[v for a,b,c,d in obs for v in (a,c)]));ys=list(candidates(y,h,[v for a,b,c,d in obs for v in (b,d)]))
  X=np.asarray(xs)[:,None];Y=np.asarray(ys)[None,:]
  ok=(X>=clear)&(X<=w-clear)&(Y>=clear)&(Y<=h-clear)
  for a,b in taken:ok &= ~((np.abs(X-a)<clear)&(np.abs(Y-b)<clear))
  for a,b,c,d in boxes:ok &= ~((a<X)&(X<c)&(b<Y)&(Y<d))
  ii,jj=np.nonzero(ok)
  if len(ii):
   px,py=min(((xs[i],ys[j]) for i,j in zip(ii,jj)),key=lambda p:(round(max(abs(p[0]-x),abs(p[1]-y)),7),(p[0]-x)**2+(p[1]-y)**2,p))
   return round(px,4),round(py,4)
  # Preserve the shared implementation's error text and fallback behavior.
  return original(t,x,y,taken,clear,strict)
 S.tap_clear=tap_clear
 return original
