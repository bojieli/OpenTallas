"""DIE-QC-34: full mixed PG access materialization (185,698 contacts) on the reach-fixed provider ODB with Codex mixed_apply_access (unchanged) under OpenROAD Python 3.10 deps."""
import json,sys,hashlib,time
from pathlib import Path
import odb
R=Path("/srv/opentallas-scratch2/claude/nc-qc-2");F=Path("/srv/opentallas-scratch2/claude/codex-qc-import-0824/reachfix");o=R/"mat";sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/codex-qc-import-0824/tools/die_plan");sys.path.insert(0,str(R/"src"))
from mixed_apply_access import apply_access
src=F/"provider/provider.odb";sha=hashlib.sha256(open(src,"rb").read()).hexdigest()
assert sha==json.load(open(F/"pg_candidate/summary.json"))["source_odb_sha256"],sha
t=time.time();d=odb.dbDatabase.create();odb.read_db(d,str(src));b=d.getChip().getBlock()
grid=json.load(open(F/"readback/pg_rects.json"));tech=d.getTech();ng=0
for n in ["VDD","VSS"]:
 net=b.findNet(n);net.setSpecial();sw=odb.dbSWire.create(net,"FIXED")
 for nn,ly,*xy in grid:
  if nn==n:odb.dbSBox.create(sw,tech.findLayer(ly),*[round(v*1000) for v in xy],"STRIPE");ng+=1
print("CANONICAL_GRID_STRIPES",ng,flush=True)
res=apply_access(b,F/"pg_candidate",F/"readback/pg_rects.json",185698,json.load(open(F/"provider/all_cells.json")))
odb.write_db(d,str(o/"provider_pg.odb"));res["source_odb_sha256"]=sha;res["out_odb_sha256"]=hashlib.sha256(open(o/"provider_pg.odb","rb").read()).hexdigest();res["canonical_grid_stripes"]=ng;res["seconds"]=round(time.time()-t)
res["scope"]="Full mixed clock/provider PG access materialization. Canonical M8/M9 grid materialized from readback/pg_rects.json (dbu-rounded). Native-cell PG bridges, connectivity census, DRC, IR NOT in this step."
json.dump(res,open(o/"summary.json","w"),indent=2);print(json.dumps(res,indent=2),flush=True)
