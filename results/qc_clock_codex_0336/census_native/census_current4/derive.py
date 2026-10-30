import json,gzip,sys,collections,hashlib
from pathlib import Path
q=Path("/srv/opentallas-scratch2/claude");r=q/"codex-qc-clock-0336/census_current4";w=q/"wt/codex-qc-clock-0336";p=w/"physical/die_plan/qwen_compute/plan_of_record"
sys.path.insert(0,str(w/"tools/die_plan"));import schema as S,census_cov as C
mp=json.load(open(p/"census/native_current3_map.json"))
with gzip.open(p/"census/native_current2_bit_witness.json.gz","rt")as f:bc=json.load(f)
forwarded=set(mp["tree_lanes"]); perbit=collections.defaultdict(set)
for src,pn,b,sp,dp,path in bc["planned_bit_routes"]:
 if src+"."+pn in forwarded:perbit[(src,pn,b)].update(lid for lid,k in path)
bundles=collections.defaultdict(lambda:collections.defaultdict(set))
for (src,pn,b),lids in perbit.items():bundles[(src,pn)][tuple(sorted(lids))].add(b)
audit_aliases={}; aliases={}; trees={}
for (src,pn),gr in sorted(bundles.items()):
 for n,(lids,bits)in enumerate(sorted(gr.items())):
  apn=pn+"__native_route_group"+str(n);key=src+"."+apn
  trees[key]=list(lids);audit_aliases[key]=dict(source_inst=src,source_port=pn,source_bits=sorted(bits),actual_lanes=list(lids))
  for b in bits:aliases[(src,pn,b)]=apn
extra=[]
for c in bc["conns"]:
 if c["s"]+"."+c["sp"] not in forwarded:continue
 groups=collections.defaultdict(list)
 for sb,db in c["pairs"]:groups[aliases[(c["s"],c["sp"],sb)]].append([sb,db])
 for apn,pairs in groups.items():extra.append(dict(s=c["s"],sp=apn,d=c["d"],dp=c["dp"],pairs=pairs,original_source_port=c["sp"],audit_alias=True))
assert sum(len(c["pairs"])for c in extra)==sum(len(c["pairs"])for c in bc["conns"]if c["s"]+"."+c["sp"]in forwarded)
bc["conns"]+=extra;bc["audit_source_aliases"]=audit_aliases
wf=p/"census/native_current4_bit_witness.json.gz"
with gzip.open(wf,"wt")as f:json.dump(bc,f,separators=(",",":"))
mp["tree_lanes"]=trees;mp["note"]="Current native CE source inventory; explicit bit-subset trees follow exactly the actual lane-set of each source bit. All native raw source/sink aliases and all790369 bit/destination lane-position routes retained; no capacities/widths/exemptions altered."
mf=p/"census/native_current4_map.json";mf.write_text(json.dumps(mp,indent=1)+"\n")
candidate=json.load(open(q/"codex-qc-clock-0336/census_current3/plan_qc46_current_census.json"))
candidate["census"][1].update(map="census/native_current4_map.json",bitcon="census/native_current4_bit_witness.json.gz")
(r/"plan_qc46_current_census.json").write_text(json.dumps(candidate,indent=1)+"\n")
class Report:
 def __init__(self):self.errors=[];self.warnings=[]
 def err(self,*a,**k):self.errors.append((a,k))
 def warn(self,*a,**k):self.warnings.append((a,k))
rp=Report();su=C.coverage(S.Plan(candidate),p,rp)
rec=dict(verdict="FAIL"if rp.errors else"PASS",forwarded_source_buses=len(forwarded),bit_subset_trees=len(trees),census=su,errors=rp.errors,warnings=rp.warnings,packed_positions=bc["packed_positions"],exact_routes=len(bc["planned_bit_routes"]),source_files={str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in[p/"census/native_current2_rows.tsv.gz",mf,wf]},note=mp["note"])
(r/"receipt.json").write_text(json.dumps(rec,indent=1));print("VERDICT",rec["verdict"],"errors",len(rp.errors),"trees",len(trees),"census",su["dropped_bits"],flush=True)
if rp.errors:print(rp.errors);raise SystemExit(1)
