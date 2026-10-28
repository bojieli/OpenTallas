"""DIE-HBM-9 C21 = ONE HBM plan event on C20j (COORD 08:51 rulings + REBAL-5/6 ASKs + CLK-LOCAL 12.16e).
usage: apply_c21.py SRC_DIR OUT_DIR REBAL6_DIR RETREE_JSON HUBTREE_JSON HNX_VIEW_JSON
(a) idx SW/SE native quarters get plan homes (RTL = functional truth, COORD 08:51 (a)): the 64 hcol pieces + 2 tails of
    the 2nd native quarter per side are placed in the free strips of the HC-bank partitions q_b010 (40) and q_b001
    (26) (same canon views as the planned quarter: 0 new core types, 0 new partition types; NW/NE share the types
    via MY, so each side gets one quarter).  Pieces on the 2.16-um lattice, >= 17.28 um from edges, no overlap.
(b) half-local VM banks (COORD 08:51 (6)): the streaming crossing-read link is a PLANNED link of each hub
    (4096 b/cycle each direction, bank row Q1 <-> Q5, 3 pipeline registers, Lx 4 cycles).  The far bank<->client
    stations stay until the RTL owner declares them dead-by-schedule (tie rule COORD 10-25); listed, not removed.
(c) REBAL-6: lanes_plain / programme_store plan-fixed SRAM arrays + island driver_rect_um (dr_lp/dr_ps.json).
(d) clock (12.16e local form, inverter tree, DIE-QC-11 / COORD 08:4x): clock.local_form = cell inv, hub comb
    trees (DIE-HBM-9 hub_retree, D8, spine-tap start sync), die region re-tree (PHY_N split W/C/E by connectivity,
    centre column vsN4-6 from root T010) from die_retree_split.json.
(e) hnx_lane_x hard-child view (REBAL-5 ASK): clock.local_form is untouched by it; the view lives in
    core_views.hnx_rp3lp3h_{n,s} (outline, children per half, centre clock entry)."""
import json, sys, shutil, os, hashlib, copy, re
from pathlib import Path
SRC, OUT, R6, RT, HT, HV = map(Path, sys.argv[1:7])
P = json.load(open(SRC / "die_plan.json")); T = P["partition_types"]
SIDE = {}
rep = dict(event="C21 (DIE-HBM-9)", source=str(SRC / "die_plan.json"),
           source_sha=hashlib.sha256((SRC / "die_plan.json").read_bytes()).hexdigest()[:12])
OUT.mkdir(parents=True, exist_ok=True)
if not (OUT / "cores").exists(): shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")
def r4(v): return round(v, 4)
G = 2.16
def snap(v): return r4(round(v / G) * G)

# ---------------- (a) idx 2nd quarter homes
src_pieces = []
for tn in ("q_b100", "q_b101_nw", "q_b102", "q_b103"):
    for h in T[tn]["hard_cores"]:
        if h["module"].startswith("ot_hbm_idx_score_"): src_pieces.append(h)
assert len(src_pieces) == 66, len(src_pieces)
W, H = 218.592, 187.488
def free_slots(t, xs, y0=25.92, pitch=198.72):
    Wt, Ht = t["outline_um"]; occ = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
                                     h["origin_um"][1] + h["outline_um"][1]) for h in t["hard_cores"]]
    occ += [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
            for c in t["contents"] if c.get("origin_um") and c.get("outline_um")]
    halo = 8.64; out = []
    for x in xs:
        y = y0
        while y + H <= Ht - 17.28:
            r = (x, y, x + W, y + H)
            if r[2] <= Wt - 17.28 and not any(r[0] < o[2] + halo and o[0] < r[2] + halo and r[1] < o[3] + halo and o[1] < r[3] + halo for o in occ):
                out.append((snap(x), snap(y)))
            y += pitch
    return out
homes = {"q_b010": free_slots(T["q_b010"], [345.6, 587.52, 25.92]), "q_b001": free_slots(T["q_b001"], [345.6, 25.92])}
need = {"q_b010": 40, "q_b001": 26}
rep["idx_homes"] = {}
k = 0
for tn in ("q_b010", "q_b001"):
    sl = homes[tn]; assert len(sl) >= need[tn], (tn, len(sl))
    t = T[tn]; added = []
    for (x, y) in sl[:need[tn]]:
        s = src_pieces[k]; k += 1
        h = copy.deepcopy(s); h["inst"] = s["inst"].replace("u_hb_idx__s_Q", "u_hb_idx__s_Q2", 1)
        h["origin_um"] = [x, y]; h.pop("orient", None)
        h["note"] = f"C21 (a) 2nd native idx quarter home (SW/SE, COORD 08:51): replica of {s['inst']} (same canon view)"
        t["hard_cores"].append(h); added.append(h["inst"])
    ha = sum(h["outline_um"][0] * h["outline_um"][1] for h in t["hard_cores"])
    rep["idx_homes"][tn] = dict(added=len(added), slots_free=len(sl), hard_fill=round(ha / (t["outline_um"][0] * t["outline_um"][1]), 3),
                                first=added[:2])
T["q_b010"]["contents"].append(dict(inst="u_hb_idx__s_Q2", module="ot_hnx_idxn_quarter_with_keybuf", status="new",
                                    cells=32810 // 4, note="C21 (a): scorer glue (tails/fault/meta/delay) of the 2nd native quarter of this side "
                                    "(hb_idx__s_SW on NW, hb_idx__s_SE on NE); keybuf stays in the hub (u_mu_keybuf_*)",
                                    origin_um=list(homes["q_b010"][need["q_b010"]]), outline_um=[60.48, 25.92]))
assert k == 66
rep["idx_homes"]["lanes_owed"] = [
    dict(lane="L6q2", src="NW_su30", dst="NW_b010", width=2484, via=["NW_b000"], note="key half stream (as L6 for b100)"),
    dict(lane="L7q2", src="NW_hub", dst="NW_b010", width=2484, via=["NW_b000"], note="keybuf stream (as L7), hub W face"),
    dict(lane="L91q2", src="NW_hub", dst="NW_b010", width=54, via=["NW_b000"], note="query"),
    dict(lane="L137q2", src="NW_b010", dst="NW_hub", width=2, via=["NW_b000"], note="score out"),
    dict(lane="Lq2_int", src="NW_b010", dst="NW_b001", width="as b100<->b101..b103 internal", note="piece chain")]
rep["idx_homes"]["note"] = ("lanes are NOT yet ports in die_plan (windows/ft bit sites owed by the next event pass); "
                            "face load estimate: +~5.0k b on b000 W/E (14.3k -> 19.3k of 25.9k = 0.75) and the hub W face")

# ---------------- (b) planned VM crossing link
rep["vm_link"] = {}
for tn in ("q_hub_nw", "q_hub_ne"):
    t = T[tn]; hc = {h["inst"]: h for h in t["hard_cores"]}
    a, b = hc["u_vmb_Q1"], hc["u_vmb_Q5"]
    ya = r4(a["origin_um"][1] + a["outline_um"][1] / 2)
    xa = r4(a["origin_um"][0] + a["outline_um"][0]); xb = r4(b["origin_um"][0])
    regs = [[snap(xa + (xb - xa) * i / 4), snap(ya)] for i in (1, 2, 3)]
    links = []
    for d, (l, c, f, to) in {"W2E": ("u_vmb_Q1", "u_vmb_Q5", xa, xb), "E2W": ("u_vmb_Q5", "u_vmb_Q1", xb, xa)}.items():
        links.append(dict(name=f"vmx_{d}", launch=l, capture=c, bits=4096, from_um=[f, ya], to_um=[to, ya],
                          regs_um=regs if d == "W2E" else regs[::-1], latency_cycles=4, status="planned",
                          rule="COORD 08:51 (6): streaming one-owner crossing read, >= 4096 b/cycle, read issued with the record"))
    for l in links:
        t["internal_stations"].append(dict(conn=l["launch"] + "|" + l["capture"], from_um=l["from_um"], to_um=l["to_um"],
                                           regs_um=l["regs_um"], bits=l["bits"], launch=l["launch"], capture=l["capture"],
                                           note="C21 (b) PLANNED VM crossing link " + l["name"] + " (COORD 08:51 (6)): 4096 b/cycle streaming "
                                                "one-owner crossing read, Lx 4 cycles; RTL port owed (hb_vms crossing-read pair)"))
    SIDE.setdefault("planned_links", {})[tn] = links
    rep["vm_link"][tn] = dict(links=2, bits_each=4096, span_um=r4(xb - xa), regs=3,
                              rtl_owed="crossing-read port pair on hb_vms banks Q1/Q5 (+ Q0/Q4.. groups by static schedule); "
                                       "far bank<->client ports dead-by-schedule -> declared ties")
# ---------------- (c) REBAL-6 arrays + driver rects
ci = P["clock"]["mesh"]["core_islands"]; rep["rebal6"] = {}
for f, mod in (("dr_lp.json", "ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526"), ("dr_ps.json", "ot_hgi_sfu_programme_store_r10")):
    d = json.load(open(R6 / f)); e = ci[mod]
    rects = [list(map(float, q["rect_um"])) for q in d["islands"]]
    assert all(abs(a_ - b_) < 0.01 for r1, r2 in zip(rects, e["rects_um"]) for a_, b_ in zip(r1, r2)) and len(rects) == len(e["rects_um"]), mod
    SIDE.setdefault("core_arrays", {})[mod] = dict(rects_um=rects, driver_rects_um=[q["driver_rect_um"] for q in d["islands"]],
        macro_placement=d["macro_placement"], source="REBAL-6 bd8c7c1b54 " + f)
    SIDE["core_arrays"][mod]["macro_rules"] = dict(halo_um=d["halo"], min_channel_um=d["min_channel"], interior_channel_um=d["interior_channel_um"], basis=d["basis"])
    rep["rebal6"][mod] = dict(islands=len(rects), driver_rects=sum(1 for q in d["islands"] if q["driver_rect_um"]),
                              macros=len(d["macro_placement"]), max_detour_um=d["max_detour_um"], max_move_um=d["max_move_um"])
# ---------------- (d) clock local form
rt = json.load(open(RT)); ht = json.load(open(HT))
SIDE["clock_local_form"] = dict(
    rule="12.16e local form; inverter clock tree (die_trial --clock-cell inv, COORD 08:4x); tap parity INV by plan",
    cell="inv", ca_depth="D8", start_sync="on the spine at the fork tap",
    hub_trees={tn: dict(grid="4x3", root=v["chosen"]["root"], parent=v["chosen"]["parent"], off_tree=v["chosen"]["off_tree"])
               for tn, v in ht["types"].items()},
    die_regions=dict(split={"T060": {"T060W": "T059", "T060C": "T057", "T060E": "T061",
                                     "by": "PHY_N face entries: W (L8/L21/L22 from NW_mcb), centre (L9/L63/L114 from vsN6), E (mirror)"}},
                     reparent={"T054": "T010", "T057": "T054"},
                     estimate=dict(before=rt["base"] if "base" in rt else None)),
    duty=dict(target="45-55 % every tap, both edges; lib MPW both phases", estimate="hbm9 README (9)"))
rep["clock"] = dict(hub_trees=list(SIDE["clock_local_form"]["hub_trees"]), die_split="T060 -> W/C/E", reparent={"T054": "T010", "T057": "T054"})
# ---------------- (e) hnx_lane_x view
SIDE["core_views"] = json.load(open(HV))
rep["hnx_view"] = list(json.load(open(HV)))
P["note"] = (P.get("note") or "") + " | C21 (DIE-HBM-9 10-28): idx 2nd quarter homes, planned VM crossing link, REBAL-6 arrays, local clock form, hnx_lane_x view"
txt = json.dumps(P, indent=1); (OUT / "die_plan.json").write_text(txt)
(OUT / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
for f in os.listdir(SRC):
    if f.endswith(".json") and not (OUT / f).exists() and f not in ("die_plan.json",): shutil.copy(SRC / f, OUT / f)
json.dump(SIDE, open(OUT / "c21_side.json", "w"), indent=1); json.dump(rep, open(OUT / "c21_event_report.json", "w"), indent=1); print(json.dumps(rep, indent=1)[:3500])
