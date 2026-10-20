import odb,json
from pathlib import Path
p=next(Path('/gate/routes/gate/work/orfs/results/asap7').glob('*/base/4_1_cts.odb'))
d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();u=b.getDbUnitsPerMicron();site=b.getRows()[0].getSite();sites=dict(name=site.getName(),w=site.getWidth()/u,h=site.getHeight()/u)
layer=d.getTech().findLayer('M4');tg=b.findTrackGrid(layer);patterns=[tg.getGridPatternY(i) for i in range(tg.getNumGridPatternsY())]
ms=[];bad=[]
for i in b.getInsts():
 if 'grp_rsp' not in i.getMaster().getName():continue
 z=i.getBBox();pins=[]
 for t in i.getITerms():
  if t.getSigType() in ('POWER','GROUND'):continue
  ok,x,y=t.getAvgXY()
  if not ok:raise RuntimeError('pinmissing')
  dist=min(abs(y-(o+min(max(round((y-o)/p),0),n-1)*p))/u for o,n,p in patterns)
  pins.append(dict(pin=t.getMTerm().getName(),x=x/u,y=y/u,track_distance_um=round(dist,9)))
  if dist>1e-6:bad.append(dict(inst=i.getName(),**pins[-1]))
 ms.append(dict(inst=i.getName(),master=i.getMaster().getName(),orient=str(i.getOrient()),bbox=[z.xMin()/u,z.yMin()/u,z.xMax()/u,z.yMax()/u],pins=pins))
out=dict(site=sites,M4_Y_grid_patterns_dbu=patterns,dbu_per_um=u,macro_count=len(ms),signal_clock_contacts=sum(len(m['pins']) for m in ms),offtrack_contacts=bad,macros=ms)
Path('/out/grid.json').write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items() if k!='macros'})
