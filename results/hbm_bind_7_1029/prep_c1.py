"""HBM-BIND-7 c1 manifest = DIE-HBM-19 d4 manifest + coll parent cuts (compose c1/compose.json, map c1/map.json); netlist
= the spliced d4 netlist (splice_coll.py); as-built sources = d4 + the coll body files of the donor elaboration
(Codex probe_body asbuilt_sources.json full + lib, every one under the manifest base worktree).  usage: prep_c1.py R D4 PROBE_SOURCES"""
import json, os, sys
R, D4, PS = sys.argv[1:4]
d = json.load(open(f"{D4}/asbuilt.json"))
d["compose"] = f"{R}/c1/compose.json"; d["map_file"] = f"{R}/c1/map.json"
d["straps"] = d["straps"] + [r"hb_coll_N[EW]\.__cut_ring_ag\.strap_qid"]
d["strap_note"] += " | HBM-BIND-7 10-29: coll ring_ag quarter id (parent-tied qid NE 2'b11 / NW 2'b10) = plan kit pin strap_qid (ID strap)"
d["note"] = "HBM-BIND-7 c1: d4 + hb_coll_NE/NW bodies spliced (splice_coll.py) + exact coll parent cuts (coll_parent_cutmap.py, keep q0) | " + d["note"]
json.dump(d, open(f"{R}/c1/asbuilt.json", "w"), indent=1)
os.makedirs(f"{R}/c1/out", exist_ok=True)
s = json.load(open(f"{D4}/out/asbuilt_sources.json")); p = json.load(open(PS))
add = [f for f in p["full"] + p["lib"] if f not in s["lib"] and f not in s["full"]]
assert all(f.startswith(d["base"] + "/") for f in add), add
s["lib"] += add
json.dump(s, open(f"{R}/c1/out/asbuilt_sources.json", "w"), indent=1)
if not os.path.exists(f"{R}/c1/out/asbuilt.json"):
    os.link(f"{R}/e1/spliced.json", f"{R}/c1/out/asbuilt.json")
print("lib added", add)
