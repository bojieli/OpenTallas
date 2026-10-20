import odb,json,collections
from pathlib import Path
p=next(Path('/gate/routes/gate/work/orfs/results/asap7').glob('*/base/5_1_grt.odb'));d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();groups=collections.Counter();rows=[];physical=[]
for i in b.getInsts():
 sig=any(t.getNet() is not None and t.getSigType() not in ['POWER','GROUND'] for t in i.getITerms())
 if not sig:physical.append(dict(cell=i.getName(),master=i.getMaster().getName(),status=str(i.getPlacementStatus()),signal_connected=False))
 bad=[t for t in i.getITerms() if t.getSigType() in ['POWER','GROUND'] and (t.getNet() is None or t.getNet().getSigType()!=t.getSigType())]
 if not bad:continue
 protected=i.isDoNotTouch() if hasattr(i,'isDoNotTouch') else None
 status=str(i.getPlacementStatus());g=(i.getMaster().getName(),status,protected,sig);groups[g]+=1
 rows.append(dict(cell=i.getName(),master=g[0],placement_status=status,do_not_touch=protected,signal_connected=sig,unbound_pins=[dict(pin=t.getMTerm().getName(),kind=t.getSigType(),net=t.getNet().getName() if t.getNet() else None) for t in bad]))
r=dict(unbound_cell_classes=[dict(master=k[0],status=k[1],do_not_touch=k[2],signal_connected=k[3],cells=v) for k,v in groups.items()],unbound_cells=rows,physical_only_instances=physical)
Path('/work/pg_classification.json').write_text(json.dumps(r,indent=2));print('PG_UNBOUND_CLASSES',r['unbound_cell_classes']);print('PHYSICAL_ONLY',len(physical),collections.Counter(x['master'] for x in physical))
