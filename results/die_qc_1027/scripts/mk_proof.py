#!/usr/bin/env python3
"""DIE-QC: proof dir for main die_sta_related from the combo GRT (routed clock) of a die_trial slice-spine tree.
tap_arrivals_<C>.json via LAND-KV-1 trial_tap_arrivals.py (copied verbatim), mesh.json = tap table only (no mesh, as
LAND-KV-1), droop_regions.json = {tap port: clock region} (regions.json part_region: one PDN/droop region per slice).
usage: mk_proof.py RUN_DIR REGIONS_JSON PROOF_DIR"""
import json, subprocess, sys, os
run, regj, pd = sys.argv[1:4]
os.makedirs(pd, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
for c in ("TT", "FF"):
    subprocess.check_call([sys.executable, "-I", here + "/trial_tap_arrivals.py", run + "/clk/tree.json",
                           f"{run}/out_{c}/arr_{c}.txt", c, f"{pd}/tap_arrivals_{c}.json"])
T = json.load(open(run + "/clk/tree.json"))
pr = json.load(open(regj))["part_region"]
json.dump(dict(note="DIE-QC: tap table only (no mesh); die_trial slice-spine region trees",
               taps=[dict(port=t["port"], part=t["part"], xy=t["xy"]) for t in T["taps"]]), open(pd + "/mesh.json", "w"))
json.dump({t["port"]: "reg:" + pr.get(t["part"], "none") for t in T["taps"]}, open(pd + "/droop_regions.json", "w"))
print("taps", len(T["taps"]), "regions", len({pr.get(t["part"]) for t in T["taps"]}))
