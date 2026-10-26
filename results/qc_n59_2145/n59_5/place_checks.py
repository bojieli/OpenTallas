"""PATH-QC-N59-5 post-DPL checks for GEOM-REVIEW-11 conditions (b) and (f), read-only OpenDB.
(b) std-cell utilisation per 10-um bin (cell area / free bin area, macros + halo removed), max and bins > 0.8, overall
    and in bins holding N59 anchors; anchor displacement vs their n59_reach405 sites.
(f) planned FIRM sites (face/FT pin registers from ot_face_flops.txt, ft stations u_bound.u_ft*, reset relays/taps
    u_rrl_/u_srl_/u_rst_in/u_run_in, macro-pin flops): displacement from the GPL (FIRM) database to the final 3_place,
    and whether any sits inside an anchor-dense bin.
Usage: openroad -python place_checks.py 3_3_place_gp.odb 3_place.odb n59_reach405.tcl ot_face_flops.txt out.json"""
import json,re,sys
from collections import defaultdict
import odb
gp,fin,anch,ff,out=sys.argv[1:6]
def load(p):
    db=odb.dbDatabase.create();odb.read_db(db,p);return db,db.getChip().getBlock()
def ctr(i,u):
    z=i.getBBox();return ((z.xMin()+z.xMax())/(2*u),(z.yMin()+z.yMax())/(2*u))
dbg,bg=load(gp);u=bg.getDbUnitsPerMicron()
FIRMRE=re.compile(r'u_bound\.u_ft|u_bound\.u_rrl_|u_bound\.u_srl_|u_bound\.u_rst_in|u_bound\.u_run_in')
face=set(l.split('\t')[0] for l in open(ff) if l.strip())
A={}
for l in open(anch):
    m=re.match(r'\s*\{\{(.*)\} ([\d.]+) ([\d.]+)\}',l)
    if m:A[m[1]]=(float(m[2]),float(m[3]))
pre={}
for i in bg.getInsts():
    n=i.getName()
    if n in face or FIRMRE.search(n.replace('\\','')) or i.getPlacementStatus()=='FIRM':pre[n]=(ctr(i,u),i.getPlacementStatus())
dbf,bf=load(fin);uf=bf.getDbUnitsPerMicron()
area=defaultdict(float);mac=[];anb=defaultdict(int);adisp=[];firm=[];firm_bins={}
core=bf.getCoreArea()
for i in bf.getInsts():
    m=i.getMaster();z=i.getBBox()
    if m.isBlock():mac.append((z.xMin()/uf-5.4,z.yMin()/uf-5.4,z.xMax()/uf+5.4,z.yMax()/uf+5.4));continue
    if m.getType() in ('CORE_SPACER','CORE_WELLTAP','ENDCAP') or 'TAPCELL' in m.getName() or 'FILLER' in m.getName():continue
    x,y=ctr(i,uf)
    # Charge the exact overlap of each cell, rather than its whole area to its centre bin.
    x0,y0,x1,y1=z.xMin()/uf,z.yMin()/uf,z.xMax()/uf,z.yMax()/uf
    for bx in range(int(x0//10),int(x1//10)+1):
        for by in range(int(y0//10),int(y1//10)+1):
            area[(bx,by)]+=max(0,min(x1,(bx+1)*10)-max(x0,bx*10))*max(0,min(y1,(by+1)*10)-max(y0,by*10))
    n=i.getName()
    if n in A:
        anb[(int(x//10),int(y//10))]+=1;adisp.append(abs(x-A[n][0])+abs(y-A[n][1]))
    if n in pre:
        (x0,y0),st=pre[n];firm.append((abs(x-x0)+abs(y-y0),n,st));firm_bins[n]=(int(x//10),int(y//10))
def free(bx,by):
    x0,y0=bx*10.0,by*10.0;x1,y1=x0+10,y0+10
    x0=max(x0,core.xMin()/uf);y0=max(y0,core.yMin()/uf);x1=min(x1,core.xMax()/uf);y1=min(y1,core.yMax()/uf)
    if x1<=x0 or y1<=y0:return 0.0
    a=(x1-x0)*(y1-y0)
    for mx0,my0,mx1,my1 in mac:
        ox=max(0,min(x1,mx1)-max(x0,mx0));oy=max(0,min(y1,my1)-max(y0,my0));a-=ox*oy
    return max(a,0.0)
util={}
for k,a in area.items():
    f=free(*k)
    if f>=20:util[k]=a/f   # bins with < 20 um2 free area (macro halo slivers) are not utilisation bins
firm.sort(reverse=True)
r=dict(bins=len(util),util_max=round(max(util.values()),3),bins_over_0p8=sum(v>0.8 for v in util.values()),
  anchor_bins=len(anb),anchor_bin_util_max=round(max(util.get(k,0) for k in anb),3),anchor_bins_over_0p8=sum(util.get(k,0)>0.8 for k in anb),
  max_anchors_per_10um_bin=max(anb.values()),anchors_found=len(adisp),anchors_listed=len(A),
  anchor_disp_max_um=round(max(adisp),2),anchor_disp_mean_um=round(sum(adisp)/len(adisp),3),
  firm_sites=len(firm),firm_disp_max_um=round(firm[0][0],3) if firm else None,firm_disp_over_1um=sum(d>1 for d,_,_ in firm),
  firm_worst=[(round(d,3),n,s) for d,n,s in firm[:8]],
  firm_in_anchor_bins_over_0p8=sum(1 for d,n,s in firm if firm_bins[n] in anb and util.get(firm_bins[n],0)>0.8))
top=sorted(util.items(),key=lambda kv:-kv[1])[:10];r['top_bins']=[[k[0]*10,k[1]*10,round(v,3),anb.get(k,0)] for k,v in top]
json.dump(r,open(out,'w'),indent=1);print(json.dumps(r)[:2500])
