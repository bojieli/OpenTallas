#!/usr/bin/env python3
"""Prepare only the approved SOURCE39 plan delta; never activate a recipe."""
import argparse,hashlib,json,re
from pathlib import Path
BASE_SHA="19a70bb3b1beaf2dcdef84bac779e55c01a331e3b796c4d179bf08c58ccc9963"
PROOF="results/token_pass/s81_dead_inputs_2148/proof_closing_source39_1101.json"
a=argparse.ArgumentParser();a.add_argument("base",type=Path);a.add_argument("output",type=Path);args=a.parse_args()
raw=args.base.read_bytes()
if hashlib.sha256(raw).hexdigest()!=BASE_SHA:raise SystemExit("EXACT_SOURCE39_BASE_PLAN_REQUIRED")
if args.output.exists():raise SystemExit("FRESH_OUTPUT_REQUIRED")
d=json.loads(raw); changes=[]
for typ,field,index,old,new in [
 ("col_h10_r0_p1__t1__cl574cc59d","added_taps",12,[1126.44,980.6],[1126.432,958.496]),
 ("col_h10_r0_p1__t1__cl911743eb","added_taps",12,[1126.44,980.6],[1126.432,958.496]),
 ("slice_station__t18","taps",16,[196.6712,294.8172],[197.088,294.112]),
 ("slice_station__t49","taps",25,[400.1757,307.2182],[400.656,307.712])]:
 tap=d["partition_types"][typ]["clock"][field][index]
 if tap["xy"]!=old:raise SystemExit("ORIGINAL_TAP_REQUIRED "+typ)
 tap["xy"]=new;changes.append({"type":typ,"old_xy":old,"new_xy":new})
proofs=0
for typ in d["partition_types"].values():
 for dead in typ.get("dead_inputs",[]):
  if dead.get("proof")!="results/token_pass/s81_dead_inputs_2148/proof_closing_s13obs_1029.json":raise SystemExit("ORIGINAL_DEAD_PROOF_REQUIRED")
  dead["proof"]=PROOF;proofs+=1
  if dead.get("module_sha256")=="3374673bb4b82772f584205e081e3ada736de9730236209fc447e9f2c445e8b6":dead["module_sha256"]="53d9ec1280afdf8729956324b509cdf0c32d1b61b2aa04d8160cfa26a60781d5"
if proofs!=36:raise SystemExit("EXACT_36_DECLARATIONS_REQUIRED")
# Preserve compact geometry records; only change the approved scalar tokens.
text=raw.decode()
for c in changes:
 typ=c["type"]; name="clk_t28" if "col_h10" in typ else ("clk_t16" if typ.endswith("t18") else "clk_t25")
 start=text.index('  "'+typ+'": {');end=text.find('\n  "',start+6)
 chunk=text[start:end]
 pat=r'("name": "'+re.escape(name)+r'",\s*"xy": \[\s*)'+re.escape(str(c["old_xy"][0]))+r'(,\s*)'+re.escape(str(c["old_xy"][1]))+r'(\s*\])'
 chunk,n=re.subn(pat,lambda m:m[1]+str(c["new_xy"][0])+m[2]+str(c["new_xy"][1])+m[3],chunk)
 if n!=1:raise SystemExit("EXACT_TAP_TOKEN_REQUIRED "+typ)
 text=text[:start]+chunk+text[end:]
text=text.replace("results/token_pass/s81_dead_inputs_2148/proof_closing_s13obs_1029.json",PROOF)
text=text.replace("3374673bb4b82772f584205e081e3ada736de9730236209fc447e9f2c445e8b6","53d9ec1280afdf8729956324b509cdf0c32d1b61b2aa04d8160cfa26a60781d5")
if json.loads(text)!=d:raise SystemExit("TOKEN_PATCH_SEMANTICS_DIFFER")
args.output.write_text(text)
print(json.dumps({"candidate_plan":str(args.output),"clock_deltas":changes,"dead_declarations":proofs,"physical_release":False,"recipe_activation":False},indent=2))
