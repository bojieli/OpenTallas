"""Small-domain exhaustive equality checks; never a production model run."""
import itertools
from interval_successor import optimum_pair
def brute(A,B,blocked,ax,bx):
 result=[]
 for al,v,ar in A:
  for bl,w,br in B:
   lo,hi=sorted((v,w))
   if any(lo<=d and hi>=c for c,d in blocked):continue
   result.append((abs(ax-v)+abs(v-w)+abs(bx-w),ar,br,al,v,bl,w))
 return min(result,default=None)
points=(-2,0,2);sets=[]
for mask in range(8):
 vals=[x for i,x in enumerate(points) if mask>>i&1]
 sets.append([(l,x,r) for r,(l,x) in enumerate((l,x) for x in vals for l in ('M3','M5'))])
obstacles=[[],[(-2,-2)],[(0,0)],[(-1,1)],[(-3,-1),(1,3)],[(-2,0),(0,2)],[(8,9)]]
count=0
for A,B,blocked,ax,bx in itertools.product(sets,sets,obstacles,points,points):
 expected=brute(A,B,blocked,ax,bx);actual=optimum_pair(A,B,blocked,ax,bx)
 assert actual==expected,(A,B,blocked,ax,bx,actual,expected)
 count+=1
print('PASS exact candidate / cost / tie equality',count,'small-domain cases')
