#!/usr/bin/env python3
"""KV-CORE-SLICE-1 (2026-10-27): ONE per-type KV hard-core slice for the CLOCK-KV-R15 plan event (METHODOLOGY 12.2a1,
12.7c, 12.8a-c).  Plan-only geometry; no build, no measurement input.

    kv_core_slice.py PLAN_DIR --census R15_census.json --mesh R15_mesh.json --out OUT [--hr-price hr_price.json]

Per hard-core module of the plan (every instance of a module uses one slice, core frame = R0 master):
  entry       12.8a centre clock entry = master_plan.core_entry rule (outline centre on the 4.32 PG lattice), island
              8.64 x 8.64 (master_plan.entry_island), via stack M9->M8->M7->M6->M5 (VIA89/78/67/56), M5 interior pins:
              every die-clock pin of the core (ck / clk / <sub>__clk) and the core's die reset pin (rst_n) sit inside
              the entry island on M5 tracks (same track phase as the native pin).  PHY-domain clocks (ck_phy) are NOT die
              clock: they stay at their PHY face pin (separate clocks only inside PHY macros, AGENTS clock domains).
  core_tree   12.8b: entry -> farthest corner Manhattan > 200 um -> internal H-tree with in-core islands at the leaf
              centres of master_plan.restructure_islands(w, h, 200) (power-of-two leaf grid, leaf reach <= 200 um).
  die_islands the CLOCK-KV-R15 die-lattice pushdown points inside this core (R15 census top pattern, 12.2a1: one
              pattern on every instance) -> 8.64 islands with ft ports; the slice refuses any overlap with core islands.
  m7_pins     every plan pin on M6/M7 with its face (after the clock/reset move); M7 = top core layer (12.1a).
  trunk       12.8c designed fixed trunk for shallow cores: N x BUFx4 from the plan insertion model
              (master_plan.core_insertion: TT = A + B x L_max) -> N = round((target - pred) / stage), frozen.
Outputs OUT/kv_core_slice.json (+ per-type OUT/slices/<module>.json) and OUT/pd_slice/cores/*.json = the plan pin views
with the slice applied (only clock/reset pins move; data pins byte-for-byte the same values).
"""
import argparse
import copy
import hashlib
import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import master_plan as MP  # noqa: E402

SCHEMA = "opentallas.kv_core_slice.v1"
ISL = 8.64
STACK = ["VIA89", "VIA78", "VIA67", "VIA56"]
CLK_RE = re.compile(r"^(?:\w+__)?(ck|clk)(\[0\]|\[None\])?$")
PHY_RE = re.compile(r"^ck_phy(\[0\])?$")
RST_RE = re.compile(r"^rst_n(\[0\]|\[None\])?$")
TRUNK_PS_PER_UM = 0.20   # centre -> island trunk, repeated BUFx12f/x24 (PATH-KV R2: 2 stages ~30-45 ps over 190 um), MODEL
BUF_STAGE_PS = dict(TT=23.9, FF=17.6)   # BUFx4_ASAP7_75t_R steady chain (PATH-KV R4 analytic, NLDM 220122); re-derived below
M5_PITCH = 0.048   # plan M5 track pitch (check.py hard_cores: pitch 0.048); pins keep the native pin track phase


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def face(p, w, h, tol=0.5):
    x, y = p["x"], p["y"]
    d = dict(W=x, E=w - x, S=y, N=h - y)
    f = min(d, key=d.get)
    return f if d[f] <= tol else "interior"


def rect_ov(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def track(x, phase):
    return round(round((x - phase) / M5_PITCH) * M5_PITCH + phase, 4)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_dir")
    ap.add_argument("--plan", default="hm_r12.json")
    ap.add_argument("--census", required=True)
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hr-price")
    ap.add_argument("--outline", action="append", default=[], help="MODULE=W,H,anchor (anchor SE|SW|NE|NW) outline delta")
    a = ap.parse_args(argv)
    pd = Path(a.plan_dir)
    plan_path = pd / a.plan
    plan = json.loads(plan_path.read_text())
    cen = json.loads(Path(a.census).read_text())["modules"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    common = float(plan["clock"]["insertion_ps"])
    outlines = {}
    for s in a.outline:
        m, v = s.split("=")
        w, h, anc = v.split(",")
        outlines[m] = (float(w), float(h), anc)

    # module -> instances (part type, inst, orient, pins_file, outline)
    mods = defaultdict(lambda: dict(uses=[], views=Counter(), parts=set()))
    nparts = Counter(p["type"] for p in plan["partitions"])
    for tn, t in plan["partition_types"].items():
        for hc in t.get("hard_cores", []):
            m = mods[hc["module"]]
            m["outline"] = hc["outline_um"]
            m["uses"].append(dict(type=tn, inst=hc["inst"], orient=hc.get("orient", "R0"), n=nparts[tn]))
            m["views"][hc["pins_file"]] += nparts[tn]
            m["parts"].add(tn)

    # die-lattice strap geometry (R15 mesh) for the entry->strap check, die frame
    M = json.loads(Path(a.mesh).read_text())
    xs, ys = M["xs"], M["ys"]
    hr = json.loads(Path(a.hr_price).read_text()) if a.hr_price else {}

    # ---- pv_join fixed trunk from the plan insertion model (12.8c, 12.9d)
    slices, blocked = {}, {}
    new_views = {}
    for mod in sorted(mods):
        m = mods[mod]
        if mod.startswith("kv3_head_eighth_"):
            # heads: out of this slice (PATH-KV R5 centre entry measured 239-245 TT; e1/e5 signed views are the only
            # KV real views for R15 die STA) -> listed, pins untouched
            slices[mod] = dict(module=mod, outline_um=m["outline"], instances=sum(u["n"] for u in m["uses"]),
                               out_of_slice="heads: R5 centre entry (108,108) known OK; signed e1/e5 kept; rebuilt only if die STA names them")
            continue
        w, h = m["outline"]
        delta_outline = None
        if mod in outlines:
            W2, H2, anc = outlines[mod]
            delta_outline = dict(old_um=[w, h], new_um=[W2, H2], anchor=anc)
            w, h = W2, H2
        hrow = dict(outline_um=[w, h])
        ex, ey = MP.snap(w / 2), MP.snap(h / 2)
        isl = MP.entry_island((ex, ey))
        far = max(abs(cx - ex) + abs(cy - ey) for cx in (0, w) for cy in (0, h))
        tree = None
        grid_choice = None
        if far > 200.0:
            # 12.8b + 12.9d: smallest island grid whose plan-model insertion is in band (250 +-20); else the lowest
            cands = []
            for reach in (200.0, 150.0, 110.0):
                t_ = MP.restructure_islands(w, h, reach)
                ltt, _ = MP.core_insertion(t_["leaf_reach_um"])
                tr = max(abs(q["centre_um"][0] - ex) + abs(q["centre_um"][1] - ey) for q in t_["islands"])
                cands.append((round(ltt + tr * TRUNK_PS_PER_UM, 1), reach, t_))
            inband = [c for c in cands if abs(c[0] - common) <= 20.0]
            pick = (min(inband, key=lambda c: len(c[2]["islands"])) if inband
                    else min(cands, key=lambda c: (abs(c[0] - common), len(c[2]["islands"]))))  # LOW -> 12.8c trunk
            tree = pick[2]
            grid_choice = [dict(leaf_reach_limit_um=r, grid=t_["grid"], islands=len(t_["islands"]), pred_TT_ps=p) for p, r, t_ in cands]
        # die pushdown islands (R15 census, one pattern per module)
        c = cen.get(mod)
        die_pts = []
        if c:
            if c["patterns"] != 1:
                blocked.setdefault(mod, []).append(f"R15 census {c['patterns']} patterns (12.2a1)")
            die_pts = [dict(xy=[p[0], p[1]], role={"n": "tree_node", "d": "mesh_driver"}[p[2]],
                            rect_um=MP.entry_island((p[0], p[1]))) for p in (c["top"][0][0] if c["top"] else [])]
        # conflicts: entry/core islands vs die islands (no overlap, 12.2a1 islands are distinct sites)
        core_isl = [dict(name="clock_entry", rect_um=isl, centre_um=[ex, ey])]
        if tree:
            core_isl += [dict(name=f"core_tree_{k}", rect_um=q["rect_um"], centre_um=q["centre_um"])
                         for k, q in enumerate(tree["islands"])]
        conflicts = [(ci["name"], dp["xy"]) for ci in core_isl for dp in die_pts if rect_ov(ci["rect_um"], dp["rect_um"])]
        # ---- pins: move die clock + die reset pins into the entry island
        views_out = {}
        moved = []
        m7 = Counter()
        clocks, phy_clocks, other_rst = [], [], []
        for view in sorted(m["views"]):
            J = json.loads((pd / view).read_text())
            J2 = copy.deepcopy(J)
            ow, oh = m["outline"]
            if delta_outline:
                for p in J2["pins"]:
                    f = face(p, ow, oh)
                    sx, sy = w / ow, h / oh
                    if f == "E":
                        p["x"], p["y"] = round(w - (ow - p["x"]), 4), round(p["y"] * sy, 4)
                    elif f == "W":
                        p["y"] = round(p["y"] * sy, 4)
                    elif f == "N":
                        p["x"], p["y"] = round(p["x"] * sx, 4), round(h - (oh - p["y"]), 4)
                    elif f == "S":
                        p["x"] = round(p["x"] * sx, 4)
                    else:
                        p["x"], p["y"] = round(p["x"] * sx, 4), round(p["y"] * sy, 4)
                # re-snap the rescaled coordinate to the native track phase (pitch 0.048) and keep pins unique per
                # (layer, face coordinate); the moved axis is the along-face axis only
                used = set()
                for p, q in zip(J2["pins"], J["pins"]):
                    ax_ = "x" if p["layer"] in ("M5", "M7") else "y"
                    ph_ = round(q[ax_] % M5_PITCH, 4)
                    v = round(round((p[ax_] - ph_) / M5_PITCH) * M5_PITCH + ph_, 4)
                    other = "y" if ax_ == "x" else "x"
                    step = 0
                    while (p["layer"], ax_, v, round(p[other], 3)) in used:
                        step += 1
                        v = round(v + (step if step % 2 else -step) * M5_PITCH, 4)
                    used.add((p["layer"], ax_, v, round(p[other], 3)))
                    p[ax_] = v
                J2["frame"] = f"core R0, origin (0,0), outline {w} x {h}"
            mv = [p for p in J2["pins"] if CLK_RE.match(p["name"])]
            mv += [p for p in J2["pins"] if RST_RE.match(p["name"])] if mv else []
            slot = {id(p): i for i, p in enumerate(mv)}
            # M5 track phase from the native M5 data pins of this view (they pass the plan track check on every instance)
            ph = Counter(round(q["x"] % M5_PITCH, 4) for q in J2["pins"] if q["layer"] == "M5" and id(q) not in slot)
            m5_phase = ph.most_common(1)[0][0] if ph else 0.024
            for p in J2["pins"]:
                nm = p["name"]
                if id(p) in slot:
                    k = slot[id(p)]
                    phase = m5_phase
                    old = (p["layer"], p["x"], p["y"])
                    # M5 tracks inside the island, 8 tracks (0.384 um) apart, centred on the entry; clocks first, then reset;
                    # the first clock pin sits ON the entry (12.8a, clock_entry gate tol 0.5 um)
                    off = (k + 1) // 2 * (1 if k % 2 else -1) * 8 * M5_PITCH   # 0.384 um pin spacing
                    p["layer"], p["x"], p["y"] = "M5", track(ex + off, phase), round(ey, 4)
                    assert isl[0] < p["x"] < isl[2], (mod, nm, p["x"], isl)
                    if view == sorted(m["views"])[0]:
                        (clocks if CLK_RE.match(nm) else other_rst).append(dict(pin=nm, from_=list(old), to=[p["layer"], p["x"], p["y"]]))
                    moved.append(nm)
                elif PHY_RE.match(nm) and view == sorted(m["views"])[0]:
                    phy_clocks.append(dict(pin=nm, layer=p["layer"], xy=[p["x"], p["y"]], face=face(p, w, h)))
            J2["source"] = J2.get("source", "") + " | KV-CORE-SLICE-1 10-27: die clock/reset pins -> 12.8a centre entry island (M5 under the M9->M5 stack)" + (f"; outline {delta_outline}" if delta_outline else "")
            views_out[view] = J2
            if view == sorted(m["views"])[0]:
                for p in J2["pins"]:
                    if p["layer"] in ("M6", "M7"):
                        m7[(p["layer"], face(p, w, h))] += 1
        new_views.update(views_out)
        die_clocked = bool(clocks)
        # ---- insertion model + trunk
        tt, ff = MP.core_insertion(far)
        htree_pred = None
        if tree:
            ltt, lff = MP.core_insertion(tree["leaf_reach_um"])
            tr = max(abs(q["centre_um"][0] - ex) + abs(q["centre_um"][1] - ey) for q in tree["islands"])
            htree_pred = dict(leaf_TT_ps=ltt, leaf_FF_ps=lff, trunk_um=MP.r3(tr), trunk_TT_ps=round(tr * TRUNK_PS_PER_UM, 1),
                              pred_TT_ps=round(ltt + tr * TRUNK_PS_PER_UM, 1), pred_FF_ps=round(lff + tr * TRUNK_PS_PER_UM * MP.FF_RATIO, 1),
                              form="leaf = core_insertion(leaf reach) + trunk 0.20 ps/um x centre->island Manhattan (MODEL UNCHECKED)")
            tt, ff = htree_pred["pred_TT_ps"], htree_pred["pred_FF_ps"]
        trunk = None
        if die_clocked and tt < common - 20.0:
            n = max(0, round((common - tt) / BUF_STAGE_PS["TT"]))
            trunk = dict(cell="BUFx4_ASAP7_75t_R", n=n, delay_ps=dict(TT=round(n * BUF_STAGE_PS["TT"], 1), FF=round(n * BUF_STAGE_PS["FF"], 1)),
                         pred_after_ps=dict(TT=round(tt + n * BUF_STAGE_PS["TT"], 1), FF=round(ff + n * BUF_STAGE_PS["FF"], 1)),
                         place="in the entry island ahead of the CTS root, dont_touch, identical in every instance",
                         frozen="with the plan; a miss -> plan model fix + PLAN-DELTA (12.8e), never a post-measurement change")
        # ---- partition-level feed: worst die instance entry -> nearest mesh strap (M9 x / M8 y) distance (info)
        row = dict(module=mod, outline_um=[w, h], instances=sum(u["n"] for u in m["uses"]),
                   partition_types=sorted(m["parts"]), pin_views=dict(m["views"]),
                   die_clocked=die_clocked,
                   entry=dict(xy_um=[ex, ey], island_um=isl, layer="M5", via_stack=STACK, stack_from="M9",
                              pins=clocks + other_rst, rule="12.8a centre (outline centre on the 4.32 PG lattice)")
                   if die_clocked else None,
                   phy_clocks=phy_clocks,
                   far_corner_um=MP.r3(far),
                   core_tree=dict(form="internal H-tree from the entry (12.8b)", grid=tree["grid"], grid_candidates=grid_choice,
                                  leaf_reach_um=tree["leaf_reach_um"],
                                  islands=[dict(centre_um=q["centre_um"], rect_um=q["rect_um"]) for q in tree["islands"]],
                                  trunk_um=[MP.r3(abs(q["centre_um"][0] - ex) + abs(q["centre_um"][1] - ey)) for q in tree["islands"]])
                   if (tree and die_clocked) else (dict(form="single CTS tree from the centre entry", grid=[1, 1]) if die_clocked else None),
                   die_islands=dict(source="CLOCK-KV-R15 census (die pushdown, 12.2a1)", points=die_pts,
                                    ports="dedicated ck_ft_in/ck_ft_out per island, M5 interior, no core logic") if die_pts else None,
                   island_conflicts=conflicts,
                   insertion_model=dict(L_max_um=MP.r3(far), pred_TT_ps=tt, pred_FF_ps=ff, target_TT_ps=common, htree=htree_pred,
                                        in_cal_range=MP.CAL_RANGE_UM[0] - 1e-6 <= (tree["leaf_reach_um"] if tree else far) <= MP.CAL_RANGE_UM[1] + 1e-6,
                                        band="IN" if abs(tt - common) <= 20 else ("LOW (trunk)" if tt < common else "HIGH"),
                                        form="master_plan.core_insertion (CTS-grown centre-entry fit, MODEL UNCHECKED)",
                                        note="H-tree cores: plan-built tree, predicted by core_infra_htree at kit time" if tree else None)
                   if die_clocked else None,
                   trunk=trunk,
                   m6_m7_pins={f"{k[0]}:{k[1]}": v for k, v in sorted(m7.items())},
                   outline_delta=delta_outline)
        if hr.get(mod):
            row["face_recut_price"] = hr[mod]
        slices[mod] = row
        if conflicts:
            blocked.setdefault(mod, []).append(f"core island overlaps die island {conflicts}")

    # ---- write applied pin views + slices
    pdo = out / "pd_slice"
    if pdo.exists():
        shutil.rmtree(pdo)
    shutil.copytree(pd, pdo, symlinks=True, ignore=shutil.ignore_patterns("*.png"))
    for view, J2 in new_views.items():
        (pdo / view).write_text(json.dumps(J2, indent=1) + "\n")
    if outlines:
        P2 = json.loads((pdo / a.plan).read_text())
        for tn, t in P2["partition_types"].items():
            for hc in t.get("hard_cores", []):
                if hc["module"] in outlines:
                    W2, H2, anc = outlines[hc["module"]]
                    ow, oh = hc["outline_um"]
                    ox, oy = hc["origin_um"]
                    # anchor corner fixed in the TYPE frame for R0 (only R0/MX instances of phy cores exist)
                    o = hc.get("orient", "R0")
                    e_side = ("E" in anc) != (o in ("MY", "R180"))
                    n_side = ("N" in anc) != (o in ("MX", "R180"))
                    hc["origin_um"] = [MP.r3(ox + (ow - W2) if e_side else ox), MP.r3(oy + (oh - H2) if n_side else oy)]
                    hc["outline_um"] = [W2, H2]
                    hc["note"] = hc.get("note", "") + f" | KV-CORE-SLICE-1 outline {ow}x{oh} -> {W2}x{H2} anchored {anc}"
        (pdo / a.plan).write_text(json.dumps(P2) + "\n")
    meta = dict(schema=SCHEMA, lane="KV-CORE-SLICE-1", plan=str(plan_path), plan_sha256=sha(plan_path),
                census=str(a.census), census_sha256=sha(a.census), mesh=str(a.mesh), mesh_sha256=sha(a.mesh),
                applied_plan_sha256=sha(pdo / a.plan),
                common_latency_ps=common, model=dict(A=round(MP.CAL_A, 2), B=round(MP.CAL_B, 4), FF_RATIO=round(MP.FF_RATIO, 4),
                                                     rms_ps=MP.CAL_RMS_PS, loo_max_ps=MP.CAL_LOO_MAX_PS))
    (out / "slices").mkdir(exist_ok=True)
    for mod, row in slices.items():
        (out / "slices" / f"{mod}.json").write_text(json.dumps(dict(meta, slice=row), indent=1) + "\n")
    (out / "kv_core_slice.json").write_text(json.dumps(dict(meta, types=slices, blocked=blocked), indent=1) + "\n")
    for mod, r in slices.items():
        if "out_of_slice" in r:
            print(mod.ljust(26), "OUT", r["out_of_slice"][:40]); continue
        e = r["entry"]
        print(mod.ljust(26), r["outline_um"], "n", r["instances"], "entry", e and e["xy_um"],
              "tree", r["core_tree"] and r["core_tree"]["grid"], "die_isl", len((r["die_islands"] or {}).get("points", [])),
              "pred", r["insertion_model"] and r["insertion_model"]["pred_TT_ps"], "trunk", r["trunk"] and r["trunk"]["n"],
              "m67", r["m6_m7_pins"], "conf", r["island_conflicts"])
    print("blocked", blocked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
