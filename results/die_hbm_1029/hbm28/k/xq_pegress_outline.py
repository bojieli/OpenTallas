#!/usr/bin/env python3
"""DIE-HBM-28-K: xq_pegress outline delta (fill vs pin budget) + slot checks; opstore_a q_b113 slot search.

    python3 xq_pegress_outline.py PLANDIR PLACED_CSV OUTDIR

Reads only.  Fill = std-cell area (placed.csv, taps excluded, as geom_rules area_metrics kinds S/B) / outline area
(geom_rules.py fill_of_free, no macros).  Gates (unchanged): geom_rules fill >= 0.20 (layout_review FILL_FREE_FAIL),
GEOM-AUTO-2 FILL_LO 0.15; outline aspect <= 2.0; pin budget 6 pins/um per 10-um window per layer and face
(geom_rules PIN_WIN_MAX, METHODOLOGY 5.2, plan budgets face_pins_per_um 6 / face_pin_layers 2).
"""
import collections
import csv
import json
import os
import re
import sys

PLAN, PLACED, OUT = sys.argv[1:4]
CORE = "ot_hgi_sm_xload_xq_pegress"
PINF = "ot_hgi_sm_xload_xq_pegress__362.88x276.48__pin6_trial__codex_g21.json"
END = 8.712            # first/last pin offset from the corner in the current pin files
LAT = 8.64


def faces(pins, W, H):
    c = collections.defaultdict(collections.Counter)
    for p in pins:
        x, y = p["x"], p["y"]
        f = "S" if y < .1 else "N" if y > H - .1 else "W" if x < .1 else "E" if x > W - .1 else "I"
        c[f][re.sub(r"\[\d+\]$", "", p["name"])] += 1
    return c


def overlap(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def main():
    os.makedirs(OUT, exist_ok=True)
    dp = json.load(open(os.path.join(PLAN, "die_plan.json")))
    cm = json.load(open(os.path.join(PLAN, "core_macros.json")))["cores"]
    area = collections.Counter()
    for r in csv.DictReader(open(PLACED)):
        area[r["kind"]] += float(r["w"]) * float(r["h"])
    std = area["std"] + area["buf"] + area["ff"]
    pins = json.load(open(os.path.join(PLAN, "cores", PINF)))
    fc = faces(pins, 362.88, 276.48)
    now = {f: sum(v.values()) for f, v in fc.items()}
    buses = {f: dict(v.most_common()) for f, v in fc.items()}
    nface = sum(n for f, n in now.items() if f != "I")

    def fill(W, H):
        return std / (W * H)

    def dens(n, side):
        return n / (side - 2 * END)

    # (A) one pin layer per face (every HBM hard core today: N/S M5, E/W M4), <= 6 pins/um
    # minimum perimeter: sum(side - 2*END) * 6 >= face pins
    need = nface / 6.0
    sq = need / 4 + 2 * END
    a_side = LAT * -(-sq // LAT)
    asp2_h = (need / 2 + 4 * END) / 3          # W = 2H
    optA = dict(rule="1 layer/face, 6 pins/um", min_span_um=round(need, 1),
                square_min=round(sq, 2), outline=[a_side, a_side], fill=round(fill(a_side, a_side), 4),
                aspect2_best=dict(outline=[round(2 * asp2_h, 1), round(asp2_h, 1)],
                                  fill=round(fill(2 * asp2_h, asp2_h), 4)),
                verdict="fill gate 0.20 (and 0.15) unreachable at aspect <= 2 with 1 pin layer/face")
    # (B) two pin layers per face (METHODOLOGY 5.2 <= 2 layers: N/S M5+M7, E/W M4+M6), 6 pins/um per layer
    W, H = 190.08, 146.88
    asg = dict(N=now["N"], S=now["S"], W=now["W"], E=now["E"])
    optB = dict(rule="2 layers/face (N/S M5+M7, E/W M4+M6), 6 pins/um per layer", outline=[W, H],
                fill=round(fill(W, H), 4), aspect=round(W / H, 3),
                faces={f: dict(pins=n, per_um=round(dens(n, W if f in "NS" else H), 2),
                               per_um_per_layer=round(dens(n, W if f in "NS" else H) / 2, 2)) for f, n in asg.items()},
                note="face assignment unchanged (N bq_d 2048, S xw_data 752, W xw_data 1296+2, E rwq 1024+57)")
    cur = dict(outline=[362.88, 276.48], fill=round(fill(362.88, 276.48), 4),
               faces={f: dict(pins=n, per_um=round(dens(n, 362.88 if f in "NS" else 276.48), 2))
                      for f, n in now.items() if f != "I"})
    old = dict(outline=[369.36, 369.36], fill=round(fill(369.36, 369.36), 4))

    # slots: every type holding the core; a new outline anchored at the old origin stays inside the old bbox
    slots = []
    for tn, t in dp["partition_types"].items():
        for h in t.get("hard_cores", []):
            if h["module"] != CORE:
                continue
            ox, oy = h["origin_um"]
            ow, oh = h["outline_um"]
            new = (ox, oy, ox + W, oy + H)
            hits = [o["inst"] for o in t["hard_cores"] if o is not h and overlap(new, (
                o["origin_um"][0], o["origin_um"][1], o["origin_um"][0] + o["outline_um"][0],
                o["origin_um"][1] + o["outline_um"][1]))]
            oldhits = [o["inst"] for o in t["hard_cores"] if o is not h and overlap((ox, oy, ox + ow, oy + oh), (
                o["origin_um"][0], o["origin_um"][1], o["origin_um"][0] + o["outline_um"][0],
                o["origin_um"][1] + o["outline_um"][1]))]
            slots.append(dict(type=tn, inst=h["inst"], orient=h.get("orient"), origin=h["origin_um"],
                              old=[round(ow, 3), round(oh, 3)], new=[W, H], inside_old=W <= ow + 1e-6 and H <= oh + 1e-6,
                              overlaps_new=hits, overlaps_old=oldhits))
    parts = collections.Counter(p["type"] for p in dp["partitions"])
    for s in slots:
        s["partitions_of_type"] = parts.get(s["type"], 0)

    # opstore_a: any 760.32 x 483.84 (either orientation) free spot in q_b113 avoiding hard cores + die ft bands?
    t = dp["partition_types"]["q_b113"]
    PW, PH = t["outline_um"]
    obst = [(o["origin_um"][0], o["origin_um"][1], o["origin_um"][0] + o["outline_um"][0],
             o["origin_um"][1] + o["outline_um"][1]) for o in t["hard_cores"] if "opstore_a" not in o["inst"]]
    for b in t.get("die_ft_bands") or []:
        lo, hi = b["span_um"]
        obst.append((0, lo, PW, hi) if b["dir"] == "EW" else (lo, 0, hi, PH))
    found = []
    for (w, h) in ((760.32, 483.84), (483.84, 760.32)):
        y = 0.0
        while y + h <= PH + 1e-6:
            x = 0.0
            while x + w <= PW + 1e-6:
                if not any(overlap((x, y, x + w, y + h), o) for o in obst):
                    found.append((w, h, x, y))
                x += LAT
            y += LAT
    opa_slot = dict(type="q_b113", outline=[PW, PH], free_slots_for_760x484=len(found), first=found[:3],
                    right_column_width=round(PW - 1434.24, 2),
                    note="obstacles = other hard cores + die_ft_bands (EW y 8.64-207.36, NS x 310-656)")

    cmx = cm[CORE]
    delta = dict(schema="opentallas.hbm.plan_delta.v1", lane="DIE-HBM-28-K", item="xq_pegress outline",
                 status="PROPOSED, NOT APPLIED; option B needs a COORD/owner ruling on 2 pin layers per hard-core face",
                 std_area_um2=dict(std=round(area["std"], 1), buf=round(area["buf"], 1), ff=round(area["ff"], 1),
                                   tap=round(area["tap"], 1), fill_basis=round(std, 1)),
                 pins_total=len(pins), face_pins=nface, pins_now=cur, buses_now=buses, old_kit_outline=old,
                 core_macros_now=dict(outline_um=cmx.get("outline_um"), status=cmx.get("status")),
                 option_A=optA, option_B=optB,
                 core_macros={CORE: dict(cmx, outline_um=[W, H], basis="DIE-HBM-28-K outline proposal (option B); "
                                         "no macros; kit rebuild required", sources=[])},
                 die_plan_hard_cores=[dict(type=s["type"], inst=s["inst"], outline_um_old=s["old"],
                                           outline_um_new=[W, H], origin_um=s["origin"]) for s in slots],
                 slots=slots, opstore_a_q_b113_slot=opa_slot)
    json.dump(delta, open(os.path.join(OUT, "xq_pegress_delta.json"), "w"), indent=1)
    print(json.dumps({k: delta[k] for k in ("std_area_um2", "pins_total", "face_pins", "pins_now", "old_kit_outline",
                                            "option_A", "option_B", "slots", "opstore_a_q_b113_slot")}, indent=1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    tt = sorted({s["type"] for s in slots})
    fig, axs = plt.subplots(1, len(tt) + 1, figsize=(7 * (len(tt) + 1), 5))
    for ax, tn in zip(axs, tt):
        t = dp["partition_types"][tn]
        for o in t["hard_cores"]:
            ax.add_patch(Rectangle(o["origin_um"], *o["outline_um"], fc="#ddd", ec="k", lw=.3))
        for s in [s for s in slots if s["type"] == tn]:
            ax.add_patch(Rectangle(s["origin"], *s["old"], fill=False, ec="red", lw=1))
            ax.add_patch(Rectangle(s["origin"], *s["new"], fc="#31a354", ec="g", lw=1))
        ax.set_xlim(0, t["outline_um"][0]); ax.set_ylim(0, t["outline_um"][1]); ax.set_aspect("equal")
        ax.set_title(f"{tn}: xq_pegress old (red) vs new {W}x{H} (green)")
    ax = axs[-1]
    t = dp["partition_types"]["q_b113"]
    for o in t["hard_cores"]:
        c = "#fdae6b" if "opstore_a" in o["inst"] else "#ddd"
        ax.add_patch(Rectangle(o["origin_um"], *o["outline_um"], fc=c, ec="k", lw=.5))
        ax.text(o["origin_um"][0] + 5, o["origin_um"][1] + 20, o["inst"].replace("u_sfucore_Q_", ""), fontsize=7)
    for b in t.get("die_ft_bands") or []:
        lo, hi = b["span_um"]
        r = (0, lo, PW, hi - lo) if b["dir"] == "EW" else (lo, 0, hi - lo, PH)
        ax.add_patch(Rectangle(r[:2], r[2], r[3], fc="blue", alpha=.15))
    ax.add_patch(Rectangle((1434.24 - 760.32 + 423.36, 941.76), 760.32, 483.84, fill=False, ec="red", ls="--"))
    ax.set_xlim(0, PW); ax.set_ylim(0, PH); ax.set_aspect("equal")
    ax.set_title("q_b113: opstore_a (orange) + 760x484 need (red dash, right-aligned)")
    fig.savefig(os.path.join(OUT, "slots.png"), dpi=90, bbox_inches="tight")


if __name__ == "__main__":
    main()
