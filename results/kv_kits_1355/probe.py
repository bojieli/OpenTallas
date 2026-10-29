import odb,json
from pathlib import Path
OUT=Path("/work");reports=[]
for tn in ["kv3_io_ft","kv3_io_ft_v1"]:
 root=Path("/input")/tn/"run/results/asap7"/("dp_"+tn)/"base"
 cells={}
 for stage in ["3_3_place_gp","3_4_place_resized","3_5_place_dp-failed"]:
  p=root/(stage+".odb")
  if not p.exists():continue
  db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();cl={};taps={}
  for i in b.getInsts():
   n=i.getName();m=i.getMaster();q=i.getBBox();r=[q.xMin(),q.yMin(),q.xMax(),q.yMax()]
   if n.startswith("TAP_"):taps.setdefault(r[1],[]).append((n,r))
   if "u_cland_" in n:cl[n]=[m.getName(),str(i.getPlacementStatus()),r]
  hits=[]
  for n,(m,s,r) in cl.items():
   if s not in ["FIRM","LOCKED"]:continue
   for nm,t in taps.get(r[1],[]):
    if min(r[2],t[2])>max(r[0],t[0]) and min(r[3],t[3])>max(r[1],t[1]):hits.append(dict(cell=n,master=m,status=s,rect=[v/u for v in r],tap=nm,taprect=[v/u for v in t]))
  row=dict(type=tn,stage=stage,cland_cells=len(cl),cland_fixed=sum(s in ["FIRM","LOCKED"] for m,s,r in cl.values()),fixed_tap_overlap=len(hits),examples=hits[:8])
  if cells:
   changed=[(n,cells[n],v) for n,v in cl.items() if n in cells and cells[n][0]!=v[0]]
   row["cland_resized_since_prior"]=len(changed);row["resize_examples"]=changed[:8];row["cland_new_since_prior"]=sum(n not in cells for n in cl)
  reports.append(row);cells=cl;odb.dbDatabase.destroy(db)
(OUT/"report.json").write_text(json.dumps(reports,indent=2)+"\n");print(json.dumps(reports))
