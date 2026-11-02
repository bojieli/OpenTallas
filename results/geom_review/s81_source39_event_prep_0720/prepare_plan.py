#!/usr/bin/env python3
"""Prepare only the approved SOURCE39 plan delta; never activate a recipe."""
import argparse,hashlib,json
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
args.output.write_text(json.dumps(d,indent=1)+"\n")
print(json.dumps({"candidate_plan":str(args.output),"clock_deltas":changes,"dead_declarations":proofs,"physical_release":False,"recipe_activation":False},indent=2))
