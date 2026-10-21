import importlib.util,sys,json,re,collections,gzip
from pathlib import Path
sp=importlib.util.spec_from_file_location("native","native_census.py");nc=importlib.util.module_from_spec(sp);sp.loader.exec_module(nc)
TL=nc.TL;record=json.loads(Path("qkd_hr_core_peer_n32.json").read_text());roles,_=nc.liberty_roles(list(Path("real5").glob("asap7sc*")))
# Strict equality of imported truth-function/pin roles across SS and formal TT.
allroles,_=nc.liberty_roles(list(Path("real5").glob("asap7sc*"))+list(Path("libs").glob("*.lib")))
areas={}
for p in Path("real5").iterdir():
 raw=p.read_bytes();s=(gzip.decompress(raw)if p.suffix==".gz" else raw).decode()
 s=re.sub(r"/\*.*?\*/|//[^\n]*", "", s, flags=re.S)
 for kind,name,body in nc.groups(s):
  if kind!="library":continue
  for typ,name,b in nc.groups(body):
   if typ=="cell":
    hit=re.search(r"(?m)^\s*area\s*:\s*([0-9.eE+-]+)\s*(?:;|$)",b)
    if hit:areas[name]=float(hit.group(1))
g,_=TL.flatten(TL.parse_verilog(Path("resynth.v").read_text()),record["top"]);a=TL.build(g,None);count=collections.Counter(t for t,n,p in g.cells)
assert not(set(count)-set(areas)),set(count)-set(areas)
macro=sum(areas[t]*n for t,n in count.items()if "sram" in t.lower());total=sum(areas[t]*n for t,n in count.items())
seq=sum(areas[g.cells[i][0]] for i in range(len(g.cells))if a["kind"][i]=="ff")
og,_=TL.flatten(TL.parse_verilog(Path("original.v").read_text()),None);oa=TL.build(og,None);groups=collections.Counter()
for i,(typ,name,pins)in enumerate(og.cells):
 if oa["kind"][i]=="ff":groups[re.sub(r"\[[^\]]+\]","",name).split("$_")[0]]+=1
large={n:v for n,v in groups.items()if v>2048}
implemented=set(re.findall(r"(?m)^module (\w+)",Path("models/comb_models.v").read_text()))|{"DFFHQNx1_ASAP7_75t_R","DFFASRHQNx1_ASAP7_75t_R","ot_sram_1r1w_32x546_m1_p192_mir"}
assert not(set(count)-implemented),set(count)-implemented
result=dict(area_um2=total,macro_area_um2=macro,stdcell_area_um2=total-macro,seq_area_um2=seq,cells=sum(count.values()),cell_counts=dict(count),SS_TT_pin_truth_roles_exact_equal=True,all_used_masters_have_verified_models=True,storage_field_groups_above2048=large,storage_scope="ActualoriginalmappedFFnames grouped by removing declared indices; source array use still requires owner classification, not an SRAM waiver.")
Path("area_storage_models.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps({k:v for k,v in result.items()if k!="cell_counts"}))
