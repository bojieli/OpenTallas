"""KV-PLAN-DELTA-5 (COORD 16:2x FT ruling): hub_Wi ft4/ft5/ft6 seam pin windows widened on BOTH abutting sides
(hub_C W face == Wi E face, hub_Wo E face == Wi W face); each 1118-b bundle gets <= 8 b/um (0.25 x 32 tr/um at the
0.75 derate).  Root cause (coupon CHECKED): ~97-106-um windows = 10.5-11.5 b/um > 9.1 tr/um free M4+M6.
 E face (core-free): ft5_i 117.0-349.5, ft6_i 358.9-600.0, ft4_i 1188.4-1240.0 (all previously free spans).
 W face (core-free spans only, Wi macros + KEEPOFF within 40 um): ft4_o -> top band 1557.5-1653.5; the small
 Wi-W/Wo-E ports at local 31.1-116.4 shift -25.92 um (PG phase kept) into the vacated ft4_o slot (window only); ft5_o 92.7-254.0;
 ft6_o 615.7-831.1 (whole mid channel face).
Only window_um changes (width/layers/order/face/src/dst identical).  Then hub_Wi FT slots re-sited (Codex wi_split
recipe: ft30/ft31 kept; lane 0.125 um/bit; jogs ft4 x1180, ft6 x1205 in the core-free E margin).
usage: wi_bands2.py RUNTIME_ROOT IN.json OUT.json LEDGER.json"""
import json, sys, copy
from pathlib import Path
import numpy as np
R = Path(sys.argv[1]); inp, out, ledp = sys.argv[2:5]
sys.path.insert(0, str(R / "tools/die_plan")); sys.path.insert(0, str(R))
import schema as S, ft_corridor as F

raw = json.load(open(inp)); ref = copy.deepcopy(raw); P = S.Plan(raw, Path(inp))
Y0 = P.rect("hub_Wi")[1]
NEW = {"L1429_0": (1188.4, 1240.0), "L1429_1": (1557.5, 1653.5), "L1449_0": (117.0, 349.5), "L1449_1": (92.7, 254.0),
       "L1450_0": (358.9, 600.0), "L1450_1": (615.7, 831.1)}
SHIFT_LO, SHIFT_HI, SHIFT = 31.0, 116.5, -25.92   # 3 x 8.64 keeps PG-stripe phase
ports = {p["id"]: p for p in raw["ports"]}


def face_of(pr, side):
    return pr["face"] if (side == "src" or pr["src"]["part"] == S.DIE_PART) else S.OPP[pr["face"]]


boxes = list(S.placed_macro_boxes(P.types["kv3_hub_Wi"], halo=F.KEEPOFF).values())
led = []
for pid, pr in P.ports.items():
    if pid in NEW:
        continue
    for side in ("src", "dst"):
        if pr[side]["part"] == "hub_Wi" and face_of(pr, side) == "W":
            cs = [c for _, _, c in P.port_pins(pid)]
            if SHIFT_LO < min(cs) - Y0 < SHIFT_HI:
                old = ports[pid]["window_um"]
                ports[pid]["window_um"] = [round(old[0] + SHIFT, 6), round(old[1] + SHIFT, 6)]
                led.append(dict(port=pid, width=pr["width"], old=old, new=ports[pid]["window_um"], kind="shift"))
for pid, (lo, hi) in NEW.items():
    pr = P.ports[pid]
    assert pr["width"] / (hi - lo) <= 8.0, (pid, pr["width"] / (hi - lo))
    old = ports[pid]["window_um"]
    ports[pid]["window_um"] = [round(Y0 + lo, 6), round(Y0 + hi, 6)]
    led.append(dict(port=pid, width=pr["width"], src=pr["src"]["part"], dst=pr["dst"]["part"], old=old,
                    new=ports[pid]["window_um"], b_per_um=round(pr["width"] / (hi - lo), 2), kind="widen"))
# checks on the re-pinned plan: no overlaps on the 4 face sides, NEW W windows core-free, only window_um changed
P2 = S.Plan(raw, Path(inp))
for part, f in (("hub_Wi", "E"), ("hub_C", "W"), ("hub_Wi", "W"), ("hub_Wo", "E")):
    iv = []
    for pid, pr in P2.ports.items():
        for side in ("src", "dst"):
            if pr[side]["part"] == part and face_of(pr, side) == f:
                cs = [c for _, _, c in P2.port_pins(pid)]
                iv.append((min(cs), max(cs), pid))
    iv.sort()
    for (a0, a1, p), (b0, b1, q) in zip(iv, iv[1:]):
        assert a1 < b0, ("overlap", part, f, p, q, a1, b0)
    if (part, f) == ("hub_Wi", "W"):
        for a0, a1, p in iv:
            if p in NEW:
                for bx in boxes:
                    assert not (bx[0] < 40 and bx[1] < a1 - Y0 and bx[3] > a0 - Y0), (p, bx)
rp = {p["id"]: p for p in ref["ports"]}
for p in raw["ports"]:
    q = rp[p["id"]]
    assert {k: v for k, v in p.items() if k != "window_um"} == {k: v for k, v in q.items() if k != "window_um"}, p["id"]
# re-site hub_Wi FT slots
P = S.Plan(raw, Path(inp)); tn = "kv3_hub_Wi"; ty = P.types[tn]
keep = {s["name"]: copy.deepcopy(s) for s in ty["ft_slots"] if s["name"] in ("ft30", "ft31")}
fixed = []
for s in keep.values():
    w, h = s["bit_site_cell_um"]
    for stage in s["bit_sites_um"]:
        for x, y in stage:
            fixed.append((x, y, x + w, y + h))
alloc = F.RowAllocator
F.RowAllocator = lambda *a, **kw: alloc(*a, **dict(kw, blocked=list(kw.get("blocked", [])) + fixed))
place = F.place_slot


def kept(slot, a, b, *args, **kw):
    if slot["name"] not in keep:
        return place(slot, a, b, *args, **kw)
    s = keep[slot["name"]]
    sites = [np.array(q) + np.array(s["bit_site_cell_um"]) / 2 for q in s["bit_sites_um"]]
    chain = [a] + sites + [b]
    hops = [float(np.abs(y - x).sum(axis=1).max()) for x, y in zip(chain, chain[1:])]
    assert max(hops) <= 405
    return sites, [p.mean(axis=0) for p in sites], [q.mean(axis=0) for q in chain], dict(
        stations=s["stations"], len_um=round(sum(hops), 2), hops_um=hops, retained_legal_chain=True,
        max_alloc_disp_um=0, proj_mean_um=[])


F.place_slot = kept; F.LANE_UM_PER_BIT = .125; F.LANE_PACK = "bin"
sl = F._place_type(P, tn, 405., 1., {f"{tn}/ft4": 1180., f"{tn}/ft6": 1205.}, {})
raw["note"] = ref.get("note", "") + " | KV-PLAN-DELTA-5 D-KV-WI-SEAM: hub_Wi ft4/5/6 seam windows <=8 b/um both sides + small W ports -25.92, hub_Wi FT re-site"
Path(out).write_text(json.dumps(raw, indent=1) + "\n")
json.dump(dict(windows=led, slots=sl), open(ledp, "w"), indent=1)
print("WI_BANDS_DONE", len(led), len(sl))
