#!/usr/bin/env python3
"""Apply the existing planned clock_body_bays body-site overlay to a new kit."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--kit", type=Path, required=True)
parser.add_argument("--bays", type=Path, required=True)
args = parser.parse_args()
tree_file = args.kit/"clock/tree.json"
clock_tcl = args.kit/"clock/ctree.tcl"
tree = json.loads(tree_file.read_text())
sites = json.loads((args.bays/"base_body_sites.json").read_text())["sites"]
if set(sites) != set(tree["sites"]):
    raise ValueError("body inventory differs from generated clock")
for path in (tree_file, clock_tcl):
    backup = path.with_name(path.stem+"_GENERATED"+path.suffix)
    if backup.exists():
        raise ValueError(f"body overlay already applied: {backup}")
    shutil.copyfile(path, backup)
for name, point in sites.items():
    tree["sites"][name] = point
for node, name in tree["node_buf"].items():
    if name in sites:
        tree["nodes"][str(node)]["x"],tree["nodes"][str(node)]["y"] = sites[name]
seen = set()
pattern = re.compile(r"^(place_inst -name (\S+) -location \{)[^}]+(\} -status[^\n]*)$", re.M)
def replace(match):
    name = match[2]
    if name not in sites:
        return match[0]
    seen.add(name)
    x,y = sites[name]
    return match[1]+f"{x:.6f} {y:.6f}"+match[3]
text = pattern.sub(replace, clock_tcl.read_text())
if seen != set(sites):
    raise ValueError("clock placement TCL does not cover body inventory")
tree["meta"]["body_overlay"] = dict(source="clock_body_bays.py", scope="prebuild legal body sites; no timing compensation",
    report=json.loads((args.bays/"bay_report.json").read_text()),explicit_pad_sites_matched=0)
clock_tcl.write_text(text)
tree_file.write_text(json.dumps(tree,indent=1)+"\n")
receipt = dict(clock_cells=len(seen),base_cells=len(sites),explicit_pads=0,
    tree_sha256=hashlib.sha256(tree_file.read_bytes()).hexdigest(),
    ctree_tcl_sha256=hashlib.sha256(clock_tcl.read_bytes()).hexdigest())
(args.kit/"body_overlay.json").write_text(json.dumps(receipt,indent=2)+"\n")
print("QC_BODY_OVERLAY",len(seen),"clock cells")
