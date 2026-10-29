import json,math,sys,collections as C
from pathlib import Path
import fixed_tree as F
diag,cw,pg,power,out=sys.argv[1:6]
fails=json.load(open(diag))['failures'];holes=json.load(open(cw))['cells']
pgr=json.load(open(pg));pw=json.load(open(power))
nd=dict(width=.08,space=.32,rf=.5,cf=1.15)
rp=F.C128.TrackRouter(nd,'VSS',F.DCM.DEFAULT_TRACKS,8.64);rp.reserve(F.C128.pg_shapes(pgr))
ra=F.C128.TrackRouter(nd,'VSS',F.DCM.DEFAULT_TRACKS,8.64);ra.reserve(F.C128.pg_shapes(pgr));ra.reserve(F.C128.pg_shapes(pw))
r0=F.C128.TrackRouter(nd,'VSS',F.DCM.DEFAULT_TRACKS,8.64)
print('M8 tracks',F.DCM.DEFAULT_TRACKS['M8'],flush=True)
m8pg=[r for r in pgr if r[1]=='M8']
res=C.Counter();rows=[]
for i,f in enumerate(fails):
    x,y=f['base_xy_um'];hs=[q['rect_die_um'] for q in holes[f['cell'].removeprefix('ck_')]]
    ylo=min(h[1] for h in hs);yhi=max(h[3] for h in hs);xlo=min(h[0] for h in hs);xhi=max(h[2] for h in hs)
    ys=sorted({round(.04+k*.08,6) for k in range(math.ceil((ylo+.027-.04)/.08),math.floor((yhi-.027-.04)/.08)+1)})
    cols=[d['bx'] for d in f['diag'] if d['stage']=='riser_m8']
    def anyok(r):
        return sum(1 for bx in cols for ty in ys if r.place('M8',ty,bx-.08,bx+.08,f['net'],keep=(ty,ty),dry=True)[0] is not None)
    a0=anyok(r0);ap=anyok(rp);aa=anyok(ra)
    npg=[(r[0],round(r[3],3),round(r[5],3)) for r in m8pg if r[3]<yhi and r[5]>ylo and r[2]<xhi and r[4]>xlo]
    k='empty_ok=%d pgonly_ok=%d'%(a0>0,ap>0);res[k]+=1
    rows.append(dict(cell=f['cell'],pin=f['pin'],island=[xlo,ylo,xhi,yhi],n_ys=len(ys),ok_empty=a0,ok_pg=ap,ok_all=aa,m8pg_over_island=npg))
    if i%50==0:print(i,dict(res),flush=True)
json.dump(dict(summary=dict(res),rows=rows),open(out,'w'),indent=0)
print(dict(res))
