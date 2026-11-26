#!/usr/bin/env python3
"""v3 on top of v2: move the coll_ftn E-face reset/monitor block (landing pins, collector tree, reset anchor relays,
reset.in_sites, sink bins) by DX2 = -354.24 um (old E face 786.24 -> new E face 432.00), y unchanged."""
import json, sys, hashlib, os
v2, out, sb_src, sb_dst, sb_rel = sys.argv[1:6]
DX2 = -354.24; W = 432.0
p = json.load(open(v2)); T = p["partition_types"]["coll_ftn"]; c = T["clock"]; lc = c["landing_contract"]
moved = []
def mv(xy, tag):
    if xy[0] > W - 1e-6:
        old = list(xy); xy[0] = round(xy[0] + DX2, 4); moved.append((tag, old, list(xy)))
for pin in lc["pins"]:
    mv(pin["xy_um"], "pin:" + pin["name"])
ct = lc["collector_tree"]
mv(ct["root"], "tree.root"); mv(ct["start_in"], "tree.start_in")
for r in ct["relays"]:
    mv(r["xy"], "relay:" + r["name"])
for k, r in c["reset_tree_anchor"].get("relays", {}).items():
    mv(r["xy"], "anchor:" + k)
mv(p["reset"]["in_sites"]["coll_ftn"], "reset.in_sites")
# sink bins
sb = json.load(open(sb_src)); nb = 0
for b in sb["bins"]:
    if b[0] > W:
        b[0] = round(b[0] + DX2 if b[0] > 700 else b[0] - 194.4, 4); nb += 1   # E-face bins with the block; x588 bins onto the START nodes (394.2)
sb["source"] = str(sb.get("source", "")) + " | QC-COLLFTN-REFLOOR C1q: %d bins x>432 moved inside the 432-wide outline" % nb
os.makedirs(os.path.dirname(sb_dst), exist_ok=True)
open(sb_dst, "w").write(json.dumps(sb, indent=1))
c["sink_bins_file"] = sb_rel
T["note"] += (" | QC-COLLFTN-REFLOOR v3: E-face reset/monitor block (reset entry, cland_up pins, collector tree, anchor relays) "
              "moved -354.24 to the new E face, y kept (sl_W5_fw W-face pins / reset sender unchanged); sink bins file "
              + sb_rel + " (6 bins moved inside)")
# guard: nothing of the type left outside the outline
bad = []
def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, path + [k])
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(x, (int, float)) for x in o) and o[0] > W and path[-1] != "outline_um":
            bad.append((path, o)); return
        for i, v in enumerate(o): walk(v, path + [i])
walk(T, [])
assert not bad, bad[:5]
json.dump(p, open(out, "w"), separators=(",", ":"))
for m in moved: print("MOVED", m)
print("BINS", nb, "ROW", hashlib.sha256(open(out, "rb").read()).hexdigest())
