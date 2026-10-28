#!/usr/bin/env python3
"""DIE-KV-4 KV plan event D9c (COORD 22:31 QK-CORES-11 default: kits carry the 4 pv_pair island sites + mirrored fMX
ft_ck pins, the KV plan follows).  Plan-only; one source; base = hm_r26q9b (D9b).

    d9c_event.py PD9B PD9C WT
PD9C must be a hard-link copy of PD9B (cp -al); this script only writes NEW files there (never edits a linked file):
  cores/kv3_pv_pair_pins_r26c.json      = cores/kv3_pv_pair_pins_r25.json + core_tree (R0 slice, QK-CORES-11)
  cores/kv3_pv_pair_pins_fMX_r26c.json  = pins_view_image(R0 r25, fMX r25, MX) (ft_ck_* pins + island_ft rects imaged)
                                          + core_tree (fMX slice = MX image)
  hm_r26q9c.json                        = hm_r26q9b with the pv_pair pins_file refs r25 -> r26c and the plan core-island
                                          record extended with the fMX image rects; nothing else changes.
"""
import copy, hashlib, json, sys
from pathlib import Path

pb, pc, wt = map(Path, sys.argv[1:4])
sys.path.insert(0, str(wt / "physical/die_plan/qwen_kvsys/cores/macro_sites"))
import pins_view_image as PVI  # noqa: E402

Q = wt / "results/qk_cores_11_1027"
r0 = json.load(open(pb / "cores/kv3_pv_pair_pins_r25.json"))
mx = json.load(open(pb / "cores/kv3_pv_pair_pins_fMX_r25.json"))
sl = {v: json.load(open(Q / f"pv_tree_slice_{v}.json")) for v in ("R0", "fMX")}
H = 190.08


def tree_block(s, view):
    return dict(source="QK-CORES-11 ee52329aae results/qk_cores_11_1027/pv_tree_slice_%s.json (GEOM-REVIEW-39 PASS rows "
                       "d64406953e63 / 6454828e359c); plan follows the kit (COORD 22:31)" % view,
                rule="12.8b in-core tree: entry island -> 4 branch BUFx12f -> 4 FIRM quadrant island nodes -> CTS leaves; "
                     "core-internal (no die pin), recorded so the die plan keeps its die-lattice ft cells off these islands",
                view=view, clock_port=s["core_tree"]["clock_port"], entry_island_um=s["islands"][0]["rect_um"],
                nodes=s["core_tree"]["nodes"])


o0 = copy.deepcopy(r0)
o0["core_tree"] = tree_block(sl["R0"], "R0")
o0["source"] += " | DIE-KV-4 D9c 10-27: + core_tree (QK-CORES-11 4 in-core islands)"
o1 = PVI.image(r0, mx, "MX")
o1["core_tree"] = tree_block(sl["fMX"], "fMX")
o1["source"] += " | DIE-KV-4 D9c 10-27: + core_tree (QK-CORES-11 4 in-core islands, MX image)"
# fail-closed: the fMX quadrant islands are the exact MX image (as a set) of the R0 ones; the entry branch buffers stay in
# the (MX-invariant, centred) entry island
isl = {v: sorted((round(n["xy_um"][0], 2), round(n["xy_um"][1], 2)) for n in sl[v]["core_tree"]["nodes"] if "_isl" in n["name"])
       for v in sl}
assert len(isl["R0"]) == 4 and isl["fMX"] == sorted((x, round(H - y, 2)) for x, y in isl["R0"]), isl
assert sl["fMX"]["islands"][0]["rect_um"] == sl["R0"]["islands"][0]["rect_um"]


def ov(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


for o in (o0, o1):
    isl = [n["island_rect_um"] for n in o["core_tree"]["nodes"] if n.get("island_rect_um")]
    for arc in o["island_ft"]["arcs"]:
        bad = [r for r in isl if ov(r, arc["rect_um"])]
        assert not bad, (o["core_tree"]["view"], arc["source"], bad)
(pc / "cores/kv3_pv_pair_pins_r26c.json").write_text(json.dumps(o0, indent=1) + "\n")
(pc / "cores/kv3_pv_pair_pins_fMX_r26c.json").write_text(json.dumps(o1, indent=1) + "\n")
plan = json.load(open(pb / "hm_r26q9b.json"))
n = 0
for t in plan["partition_types"].values():
    for hc in t.get("hard_cores", []):
        pf = hc.get("pins_file")
        if pf in ("cores/kv3_pv_pair_pins_r25.json", "cores/kv3_pv_pair_pins_fMX_r25.json"):
            hc["pins_file"] = pf.replace("_r25.json", "_r26c.json")
            n += 1
# clock.mesh.core_islands.kv3_pv_pair.rects_um = the cell rects G0 (island_ft_rows) accepts for this module's island ft
# cells, in each master's own frame: add the exact MX image of every R0 cell rect for the fMX master (schema keys unchanged)
ci = plan["clock"]["mesh"]["core_islands"]["kv3_pv_pair"]
img = [[r[0], round(H - r[3], 4), r[2], round(H - r[1], 4)] for r in ci["rects_um"]]
ci["rects_um"] = ci["rects_um"] + [r for r in img if r not in ci["rects_um"]]
ci["frame"] = ci.get("frame", "") + " + fMX master (MX image, DIE-KV-4 D9c)"
plan["note"] = plan.get("note", "") + " | D9c (DIE-KV-4 10-27): QK-CORES-11 pv_pair in-core islands + fMX ft_ck MX image (plan follows kit)"
(pc / "hm_r26q9c.json").write_text(json.dumps(plan, indent=1) + "\n")
ft = {p["name"]: (p["x"], p["y"]) for p in o1["pins"] if PVI.FT.fullmatch(p["name"])}
print(json.dumps(dict(pins_file_refs=n, fMX_ft_ck=ft, fMX_island_ft=[a["rect_um"] for a in o1["island_ft"]["arcs"]],
                      r0_nodes=[(x["name"], x["xy_um"]) for x in sl["R0"]["core_tree"]["nodes"]],
                      sha=hashlib.sha256((pc / "hm_r26q9c.json").read_bytes()).hexdigest())))
