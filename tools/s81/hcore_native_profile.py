#!/usr/bin/env python3
"""Materialize the qualified CTLA/RSTE sender+core cohort into a new binder manifest.

Never edits an existing manifest or its source worktree. The selected component
qualification must pass before this profile can be emitted. Compiler/runtime must
also honor the published +1 stationary-load and +2 core-reset readiness edges.
"""
import argparse, hashlib, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FILES=["rtl/hdc/v41x/ot_s81c_attn_hcore.sv","rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv"]

def main():
 p=argparse.ArgumentParser();p.add_argument("manifest");p.add_argument("--out",required=True);p.add_argument("--qualification",default=str(ROOT/"results/arch/s81_hcore_native_profile_0719/record.json"));a=p.parse_args()
 q=json.loads(Path(a.qualification).read_text())
 if q.get("miter")!="PASS" or q.get("mutant")!="CAUGHT":raise SystemExit("profile component qualification is not PASS+CAUGHT")
 d=json.loads(Path(a.manifest).read_text());defs=list(d.get("defines",[]))
 if "OT_ATTN_HCORE" not in defs:raise SystemExit("input manifest does not select the native S81 hcore hierarchy")
 defs=[x for x in defs if x!="OT_S81C_HCORE_WPRE"]
 for x in ["OT_S81C_HCORE_CTLA","OT_S81C_HCORE_RSTE"]:
  if x not in defs:defs.append(x)
 d["defines"]=defs;out=Path(a.out).resolve()
 if out.exists():raise SystemExit("refusing to overwrite manifest "+str(out))
 snap=out.parent/(out.stem+"_core_sources");snap.mkdir(parents=True,exist_ok=True);mapping={};hashes={}
 for rel in FILES:
  src=ROOT/rel;data=src.read_bytes();dst=snap/src.name
  expected=q.get("source_sha256",{}).get(rel)
  if expected!=hashlib.sha256(data).hexdigest():raise SystemExit("component qualification source mismatch: "+rel)
  if dst.exists() and dst.read_bytes()!=data:raise SystemExit("snapshot differs: "+str(dst))
  dst.write_bytes(data);mapping[src.name]=str(dst);hashes[src.name]=hashlib.sha256(data).hexdigest()
 if b"ot_s81c_hcore_load_stage u_load_stage" not in (ROOT/FILES[0]).read_bytes():raise SystemExit("missing connected native sender stage")
 for field in ["files","prefer"]:
  arr=d.get(field,[]);seen=set();result=[];n=0
  for f in arr:
   name=Path(f).name
   if name not in mapping:result.append(f);continue
   new=mapping[name];n+=1
   if new not in seen:result.append(new);seen.add(new)
  if len(seen)!=len(FILES):raise SystemExit(field+" does not contain both selected hcore sources")
  d[field]=result
 contract={"kind":"S81_CTLA_RSTE_NATIVE_LOAD_STAGE","core_WPRE":2,"reset_release_cycles_after_core_pin":2,"stationary_load_transport_added_cycles":1,"stationary_load_stage_source_FF_per_16head_tile":1029,"controls":"ld_grp/ld_w2v bypass sender data stage; all load valid/mode/bank/data fields captured once. No prediction.","source_sha256":hashes,"component_qualification":str(Path(a.qualification).resolve()),"compiler_gate":"Actual-program last load -> first IV guard must include +1 sender stage; +2 core readiness must be included in boot/start. Component PASS is not G5."}
 d["defines_note"]="Qualified physical hcore CTLA/WPRE2 + RSTE, connected sender load stage; legacy WPRE1 removed"
 d["core_profile"]=contract
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(d,indent=2)+"\n");out.with_suffix(".core_profile.json").write_text(json.dumps(contract,indent=2)+"\n")
 print(json.dumps({"manifest":str(out),"source_sha256":hashes,"added_load_cycles":1,"added_core_release_cycles":2}))
if __name__=="__main__":main()
