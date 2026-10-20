from pathlib import Path
import odb,json,gzip,hashlib,collections
p=next(Path('/gate/routes/gate/work/orfs/results/asap7').glob('*/base/5_1_grt.odb'));db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();pg=collections.Counter();bad=[];pgrows=[];outside=[];macros=[];area=0;cells=0
for i in b.getInsts():
 m=i.getMaster()
 for t in i.getITerms():
  if t.getSigType() in ['POWER','GROUND']:
   n=t.getNet();ok=n is not None and n.getSigType()==t.getSigType();pg[(t.getSigType(),str(n.getName()) if n else 'UNBOUND')]+=1
   if not ok:bad.append(dict(cell=i.getName(),master=m.getName(),pin=t.getMTerm().getName(),pin_type=t.getSigType(),net=n.getName() if n else None,net_type=n.getSigType() if n else None))
 if m.isBlock():
  z=i.getBBox();macros.append(dict(cell=i.getName(),master=m.getName(),bbox=[v/u for v in [z.xMin(),z.yMin(),z.xMax(),z.yMax()]],orientation=str(i.getOrient())));continue
 if not any(t.getNet() is not None and t.getSigType() not in ['POWER','GROUND'] for t in i.getITerms()):continue
 z=i.getBBox();x0,y0,x1,y1=[v/u for v in [z.xMin(),z.yMin(),z.xMax(),z.yMax()]];area+=(x1-x0)*(y1-y0);cells+=1
 if x0<2.16-1e-6 or x1>343.44+1e-6 or y0<216-1e-6 or y1>300.24+1e-6:outside.append(dict(cell=i.getName(),master=m.getName(),bbox=[x0,y0,x1,y1]))
rows=[]
for r in b.getRows():
 z=r.getBBox();rows.append([v/u for v in [z.xMin(),z.yMin(),z.xMax(),z.yMax()]])
s=dict(odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pg_counts=[dict(pin_type=k[0],net=k[1],count=v) for k,v in pg.items()],pg_bad=bad,pg_bad_count=len(bad),macros=macros,functional_std_count=cells,functional_std_area_um2=area,functional_std_outside_band_count=len(outside),functional_std_outside_band=outside,rows=rows,row_count=len(rows),scope='Actual5_1GRT PG ITerm net/type binding and functional cell/row occupancy. Read-only measured evidence, not canonical fresh PG receipt/admission.')
Path('/work/pg_rows.json').write_text(json.dumps(s,indent=2));print({k:s[k] for k in ['pg_bad_count','functional_std_count','functional_std_area_um2','functional_std_outside_band_count','row_count']})
