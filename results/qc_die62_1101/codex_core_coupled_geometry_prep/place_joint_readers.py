"""Place existing macro-adjacent FFs on unique conservative native-row sites.

Only immediate macro endpoints are constrained. FF-to-FF/control/clock/reset
and remaining source gates are not qualified by this finite planning packet.
"""
import gzip,json,math,sys
from pathlib import Path
import numpy as np
d=json.load(gzip.open(sys.argv[1]));r=json.load(open(sys.argv[2]));g=json.load(gzip.open(sys.argv[3]));o=Path(sys.argv[4]);o.mkdir(exist_ok=True)
px,py=2.592,.54;W,H=r['actual_core_box_um'][2:];xs=(np.arange(math.floor(W/px))+.5)*px;ys=(np.arange(math.floor(H/py))+.5)*py
free=np.ones((len(ys),len(xs)),dtype=bool)
for h in r['macros']:
    x,y=h['origin_um'];w,z=h['outline_um'];a=h['halo_um'];xx=(xs+px/2>x-a+1e-8)&(xs-px/2<x+w+a-1e-8);yy=(ys+py/2>y-a+1e-8)&(ys-py/2<y+z+a-1e-8);free[np.ix_(yy,xx)]=False
tasks=[];failed=[];radius=402
bb=json.load(gzip.open(sys.argv[5]))["bounds"] if len(sys.argv)>5 else None
for ff,es in d['FF_macro_constraints'].items():
    u=[e['xy_um'][0]+e['xy_um'][1]for e in es];v=[e['xy_um'][0]-e['xy_um'][1]for e in es];lo,hi=max(u)-radius,min(u)+radius;vl,vh=max(v)-radius,min(v)+radius
    if bb:lo,hi,vl,vh=bb[ff]
    if lo>hi or vl>vh:failed.append(dict(ff=ff,name=g['ff_nodes'][ff]['name'],kind='EMPTY_AT_3UM_PIN_RESERVE',u=[lo,hi],v=[vl,vh]));continue
    tasks.append((max(0,hi-lo)*max(0,vh-vl),ff,es,lo,hi,vl,vh))
adj={k:set()for k in bb}
for a,b in json.load(gzip.open(sys.argv[5]))['edges']:adj[a].add(b);adj[b].add(a)
placed={};rows=[]
for _,ff,es,lo,hi,vl,vh in sorted(tasks,key=lambda t:t[0]/(1+len(adj[t[1]]))):
    for nn in adj[ff]:
        if nn in placed:
            nx,ny=placed[nn];lo=max(lo,nx+ny-399);hi=min(hi,nx+ny+399);vl=max(vl,nx-ny-399);vh=min(vh,nx-ny+399)
    if lo>hi or vl>vh:
        failed.append(dict(ff=ff,name=g['ff_nodes'][ff]['name'],kind='PLACED_NEIGHBOR_DIAMONDS_EMPTY'));continue
    yc=((lo+hi)-(vl+vh))/4;xc=((lo+hi)+(vl+vh))/4;rylo=max(0,math.ceil((((lo-vh)/2)-py/2)/py));ryhi=min(len(ys)-1,math.floor((((hi-vl)/2)-py/2)/py));point=None
    for row in sorted(range(rylo,ryhi+1),key=lambda z:abs(ys[z]-yc)):
        y=ys[row];xl=max(lo-y,vl+y,0);xh=min(hi-y,vh+y,W);cl=max(0,math.ceil((xl-px/2)/px));ch=min(len(xs)-1,math.floor((xh-px/2)/px))
        if cl>ch:continue
        cols=np.flatnonzero(free[row,cl:ch+1])+cl
        if not len(cols):continue
        col=int(cols[np.argmin(np.abs(xs[cols]-xc))]);point=[float(xs[col]),float(y)];free[row,col]=False;break
    if point is None:failed.append(dict(ff=ff,name=g['ff_nodes'][ff]['name'],kind='NO_UNIQUE_FREE_NATIVE_GRID_SITE',u=[lo,hi],v=[vl,vh]));continue
    dist=max(abs(point[0]-e['xy_um'][0])+abs(point[1]-e['xy_um'][1])for e in es);assert dist<=radius+1e-7
    placed[ff]=point
    rows.append(dict(ff=ff,name=g['ff_nodes'][ff]['name'],type=g['ff_nodes'][ff]['type'],center_um=point,max_macro_endpoint_distance_um=round(dist,6),macro_endpoints=len(es)))
summary=dict(tightened_FF_graph_bounds=bb is not None,status='CONDITIONAL_SOURCE_ONLY_MACRO_READER_SITE_PROPOSAL',requested_existing_FFs=len(d['FF_macro_constraints']),placed_existing_FFs=len(rows),failed=len(failed),site_pitch_um=[px,py],macro_endpoint_center_budget_um=radius,extra_pin_offset_reserve_um=3,unique_nonoverlap_sites=True,macros_and_halos_avoided=True,max_macro_endpoint_center_distance_um=max(r['max_macro_endpoint_distance_um']for r in rows),new_FFs=0,new_functional_edges=0,unqualified=['ConditionalonUNQUALIFIEDuniformfoldcontrolpinpolicy','FF-to-FF/control predecessor and successor geometry notclosed','Remaining52663FFs including rederivedclocklanding contract notplaced','NativeinternalR90support absent','Clock/reset/PG/START/boot/model/programme/view/SIGNED notclosed'])
(o/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(o/'READER_SITE_PROPOSAL.json.gz','wt')as f:json.dump(dict(summary=summary,rows=rows,failed=failed),f,separators=(',',':'))
print(json.dumps(summary));print('FAIL',failed[:5])
