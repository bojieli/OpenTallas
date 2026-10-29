"""Restore exact per-station register counts after the approved ring move.
Signal wires may pass over M5 hard cores on M6/M7, but FF homes exclude bodies+halos.
Use complete Manhattan distance reachability on the native 4.32um lattice; never
silently shorten a chain. Reports every unavoidable cycle increase.
"""
import json,sys,math,hashlib,shutil
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_cdt
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import hub_repack as HR
G=4.32

def route(R,a,b,n):
    # Restrict to a bounding box with one full reach of detour slack; expand only on failure.
    for slack in (405,810):
        i0=max(0,int((min(a[0],b[0])-slack)//G));j0=max(0,int((min(a[1],b[1])-slack)//G))
        i1=min(R.nx,int(math.ceil((max(a[0],b[0])+slack)/G))+1);j1=min(R.ny,int(math.ceil((max(a[1],b[1])+slack)/G))+1)
        f=R.f[i0:i1,j0:j1];xx=np.arange(i0,i1)[:,None]*G;yy=np.arange(j0,j1)[None,:]*G
        da=abs(xx-a[0])+abs(yy-a[1]);db=abs(xx-b[0])+abs(yy-b[1])
        reached=f&(da<=405+1e-6);layers=[reached]
        if not reached.any():continue
        end=None
        for k in range(1,n+1):
            if k==n:
                cand=reached&(db<=405+1e-6)
                if cand.any():
                    qi,qj=np.unravel_index(np.where(cand,db,1e20).argmin(),f.shape);end=(int(qi),int(qj));break
            dist=distance_transform_cdt(~reached,metric='taxicab');reached=f&(dist<=int(405//G));layers.append(reached)
        if end is None:continue
        rev=[end];cur=end
        for k in range(n-2,-1,-1):
            cx,cy=(cur[0]+i0)*G,(cur[1]+j0)*G
            dd=abs(xx-cx)+abs(yy-cy)
            good=layers[k]&(dd<=405+1e-6)
            # Select a distinct legal predecessor closest to the ideal remaining straight-line fraction.
            tx=a[0]+(b[0]-a[0])*(k+1)/(n+1);ty=a[1]+(b[1]-a[1])*(k+1)/(n+1)
            cost=abs(xx-tx)+abs(yy-ty)
            for q in rev:good[q]=False
            if not good.any():break
            qi,qj=np.unravel_index(np.where(good,cost,1e20).argmin(),f.shape);cur=(int(qi),int(qj));rev.append(cur)
        if len(rev)!=n:continue
        regs=[[round((i+i0)*G,3),round((j+j0)*G,3)] for i,j in rev[::-1]]
        pts=[a]+regs+[b];assert max(abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(pts,pts[1:]))<=405+1e-5
        return regs
    return None

def main():
    base,moved,out=map(Path,sys.argv[1:4]);p=json.loads((moved/'die_plan.json').read_text());old=json.loads((base/'die_plan.json').read_text());rep={'schema':'hbm-ring-fixed-count.v1','types':{}}
    for tn in ['q_hub_nw','q_hub_ne']:
        t=p['partition_types'][tn];R=HR.Raster(*t['outline_um'],[(h['origin_um'][0],h['origin_um'][1],h['origin_um'][0]+h['outline_um'][0],h['origin_um'][1]+h['outline_um'][1]) for h in t['hard_cores']]);rows=[]
        for i,(s,o) in enumerate(zip(t['internal_stations'],old['partition_types'][tn]['internal_stations'])):
            n=len(o.get('regs_um',[]));nn=len(s.get('regs_um',[]))
            if n==nn:continue
            r=route(R,s['from_um'],s['to_um'],n)
            actual=n
            if r is None:
                for actual in range(n+1,max(n+2,nn+1)):
                    r=route(R,s['from_um'],s['to_um'],actual)
                    if r is not None:break
            assert r is not None,(tn,i,s['conn'])
            s['regs_um']=r;s['note']=s.get('note','')+' | exact-count Manhattan FF-home solve'
            rows.append({'index':i,'conn':s['conn'],'old':n,'draft':nn,'final':actual,'added_cycles':actual-n})
            print(tn,i,s['conn'],n,nn,'->',actual,flush=True)
        rep['types'][tn]=rows
    shutil.copytree(moved,out);(out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');rep['plan_sha256']=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest();(out/'fixed_count_report.json').write_text(json.dumps(rep,indent=1)+'\n')
if __name__=='__main__':main()
