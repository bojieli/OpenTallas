"""Actual-FF, full-body geometry only input for the existing native ring planner."""
import sys,json,math
from pathlib import Path
repo,geo,sites,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(repo/'tools/die_plan'));import core_infra_htree as H
hard=[];fixed=[]
for l in sites.read_text().splitlines():
 f=l.split()
 if f[:1]!=['FIXED']:continue
 x,y,xx,yy=map(float,f[3:7])
 if yy-y>.4:hard.append((x-2.2,y-2.2,xx+2.2,yy+2.2))
 else:fixed.append((x-.918,y-.189,xx+.918,yy+.189))
old=H.Maze.__init__
def occupied(self,core,macros,G=.54,halo=2.2,keepout=()):
 old(self,core,macros,G,halo,keepout)
 for rectangles,body in ((hard,True),(fixed,False)):
  for x,y,xx,yy in rectangles:
   for i in range(max(0,math.ceil((x-core[0])/G)),min(self.NX,math.floor((xx-core[0])/G))+1):
    for j in range(max(0,math.ceil((y-core[1])/G)),min(self.NY,math.floor((yy-core[1])/G))+1):
     self.K[i][j]=True
     if body:self.B[i][j]=True
H.Maze.__init__=occupied
r=H.search_islands(str(geo),rmax=350,pitch=8.64,sample=6,G=1.08,passes=1)
r['actual_hard_bodies_full_wire_obstacles']=len(hard);r['actual_fixed_footprints']=len(fixed);r['scope']='geometry island selection only; all3556sinks must enter full native R7 model before build';out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r),flush=True)
