"""Current QC native census, before plan-bus matching; no resynthesis or exemptions."""
import csv,gzip,hashlib,json,sys,collections
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude"); R=Q/"codex-qc-clock-0336/census_current"; W=Q/"wt/codex-qc-clock-0336"
sys.path.insert(0,str(W/"tools/die_plan"))
import bind as B,schema as S,census_cov as C
plan=Q/"wt/codex-qc-0336/physical/die_plan/qwen_compute/plan_of_record/plan_qc46.json"
manifest=Q/"wt/die-qc-46/results/qc_die33_1029/bind/final_asbuilt.json"
asbuilt=Q/"codex-qc-0336/gates/bind46/asbuilt.json"
B._AB_OVERRIDE["path"]=str(manifest); raw=B.load_plan(plan); base=B.plan_base(plan,raw)
print("NATIVE_LOAD",asbuilt,flush=True)
yjs=json.loads(asbuilt.read_text()); bb=B.Binder(raw,yjs,plan.parent,base)
if bb.ab.get("clock_landing_table"):
 import clock_landings as CL
 lp=Path(base)/bb.ab["clock_landing_table"]; table=json.loads(lp.read_text()); bb._clock_landing_table=table
 CL.expand_station_types(bb,table); bb.clock_landings=CL.Landings(raw,table)
bb.map_cells();bb.analyse()
if bb.errors: raise SystemExit("NATIVE_SOURCE_ERROR "+repr(bb.errors[:15]))
if bb.tied_pins: raise SystemExit("Native census refuses tied named leaf inputs")
print("ANALYSED",len(bb.F.cells),len(bb.cross),bb.counts,flush=True)
# Union is exact source-pin-bit identity per destination partition. No width caps or max-row broadcast approximation.
rows=[]; mapping={p:p for p in bb.parts}; groups=[]; allbits=set()
for (sp,dp),buses in sorted(bb.cross.items()):
 for (ci,pn),bits in sorted(buses.items()):
  cell=bb.F.cells[ci]; old=mapping.setdefault(cell.path,sp)
  if old!=sp: raise SystemExit("Ambiguous physical owner "+cell.path)
  bs=sorted(bits); rows.append((cell.path,pn,dp,"__native_partition_union__","data",len(bs)))
  groups.append(dict(src=cell.path,module=cell.module,src_part=sp,src_bus=pn,dst_part=dp,bits=bs,global_nets=[cell.ports[pn][b]for b in bs]))
  allbits.update((sp,dp,ci,pn,b)for b in bs)
# Exact sink-bit witnesses retain multicast aliases and collapsed transport stage counts.
conns=collections.defaultdict(list)
def source_x(desc):
 if desc[0]=="x":yield desc
 elif desc[0]in("or","and"):
  for sub in desc[1]:yield from source_x(sub)
seen=set()
for (dci,dpn,db),desc in bb.sinks.items():
 for x in source_x(desc):
  _,sp,sci,spn,sb,st,dp=x
  if (sp,dp,sci,spn,sb)not in allbits:raise SystemExit("Witness not in exact source union")
  conns[(sci,spn,dci,dpn)].append((sb,db,st));seen.add((sp,dp,sci,spn,sb))
if seen!=allbits:raise SystemExit("Missing native source-bit witnesses "+str(len(allbits-seen)))
physical=W/"physical/die_plan/qwen_compute/plan_of_record"; out=physical/"census";out.mkdir(parents=True,exist_ok=True)
rf=out/"native_current_rows.tsv.gz"; mf=out/"native_current_map.json"; wf=out/"native_current_bit_witness.json.gz"
with gzip.open(rf,"wt")as f:
 wr=csv.writer(f,delimiter="\t",lineterminator="\n");wr.writerow(["src","src_bus","dst","dst_bus","kind","bits"]);wr.writerows(rows)
mf.write_text(json.dumps(dict(note="Current native elaboration after explicit CE substitutions and declared ownership/transport rules. Rows are exact source-bit unions per destination partition; no caps, exemptions, forwarded credit, or multi-part groups.",parts=mapping),indent=1)+"\n")
connections=[]
for (sci,spn,dci,dpn),pairs in sorted(conns.items()):
 sc,dc=bb.F.cells[sci],bb.F.cells[dci]
 connections.append(dict(s=sc.path,sp=spn,d=dc.path,dp=dpn,src_part=bb.cpart[sci],dst_part=bb.cpart[dci],pairs=[[a,b]for a,b,_ in pairs],transport_stages=[s for _,_,s in pairs],source_global_nets=[sc.ports[spn][a]for a,_,_ in pairs],sink_global_nets=[dc.ports[dpn][b]for _,b,_ in pairs]))
with gzip.open(wf,"wt")as f:json.dump(dict(schema="opentallas.native_census_bit_witness.v1",source_groups=groups,conns=connections),f,separators=(",",":"))
# The outer die and CB censuses remain. This full native source census replaces both stale slice and manual collective sources.
old=raw["census"]; candidate=json.loads(plan.read_text());candidate["census"]=[old[0],dict(rows="census/native_current_rows.tsv.gz",map="census/native_current_map.json",note="Native leaf/glue source graph before plan lane/bus matching; exact bit unions and bit witness archive."),old[3]]
cp=R/"plan_qc46_current_census.json";cp.write_text(json.dumps(candidate,indent=1)+"\n")
class Report:
 def __init__(self):self.errors=[];self.warnings=[]
 def err(self,*a,**k):self.errors.append((a,k))
 def warn(self,*a,**k):self.warnings.append((a,k))
r=Report();summary=C.coverage(S.Plan(candidate),physical,r)
record=dict(schema="opentallas.qc.current_census.v1",plan=str(plan),plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),native_json=str(asbuilt),native_sha256=hashlib.sha256(asbuilt.read_bytes()).hexdigest(),manifest=str(manifest),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),bind_py_sha256=hashlib.sha256((W/"tools/die_plan/bind.py").read_bytes()).hexdigest(),source_counts=bb.counts,source_cells=len(bb.F.cells),partition_pairs=len(bb.cross),source_groups=len(groups),unique_crossing_bits=len(allbits),sink_witness_bits=sum(len(x["pairs"])for x in connections),parent_variants=bb.F.parent_variants,census=summary,errors=r.errors,warnings=r.warnings,verdict="PASS"if not r.errors else"FAIL",files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in[rf,mf,wf]},note="B.Binder mapping/analyse only: B.build_buses/emit/check_types never called. Actual source graph is inventoried before any planned lane matching; all source-bit unions have sink-bit aliases. Historical failures preserved.")
(R/"receipt.json").write_text(json.dumps(record,indent=1)+"\n");print("RESULT",record["verdict"],"errors",len(r.errors),"bits",len(allbits),"sinkwitness",record["sink_witness_bits"],flush=True)
if r.errors:print(r.errors[:20]);raise SystemExit(1)
