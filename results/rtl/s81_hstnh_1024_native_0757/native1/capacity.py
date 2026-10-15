import odb,json,hashlib
from pathlib import Path
p=Path('/db/3_2_place_iop.odb');db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=db.getTech().getDbUnitsPerMicron()
area=lambda m:m.getWidth()*m.getHeight()/(u*u)
masters={m.getName():m for lib in db.getLibs() for m in lib.getMasters()}
rows=[]
for row in b.getRows():
 r=row.getBBox();rows.append((r.xMax()-r.xMin())*(r.yMax()-r.yMin())/(u*u))
existing=sum(area(i.getMaster()) for i in b.getInsts())
quantities={'HB2xp67_ASAP7_75t_R':2048,'BUFx4f_ASAP7_75t_R':3072}
additional={k:dict(count=n,unit_area_um2=area(masters[k]),area_um2=n*area(masters[k])) for k,n in quantities.items()}
projected=existing+sum(v['area_um2'] for v in additional.values())
x=dict(scope='ACTUAL_IO_ODB_PLUS_LOGGED_RECIPE2_INSERTIONS',original_odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),existing_std_area_um2=existing,row_site_area_um2=sum(rows),additional_hold_cells=additional,projected_total_std_area_um2=projected,minimum_row_area_ratio=projected/sum(rows),minimum_extra_row_area_um2=max(0,projected-sum(rows)),qualification='Area lower bound only; whitespace, clock/PG/routing and timing add further requirements',no_fit=projected>sum(rows))
Path('/out/capacity.json').write_text(json.dumps(x,indent=1)+'\n');print(json.dumps(x))
