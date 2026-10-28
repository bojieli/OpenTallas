#!/usr/bin/env python3
"""DIE-S81-5 S81 plan delta (COORD 00:06 ruling 1): SerDes clock taps off the macro.
(a) reconcile die.pg.domains phy_lk_* with the ot_pdie_serdes macro the type places: domain = macro + 63.64 um halo
    clipped to the partition (12 of 14 already are; lk_ES0 = whole partition, lk_ES1 = die-edge side while the macro
    sits on the inner side under MY -> both set to the macro rect + halo; the orient fix stays a PATH-S81 item);
(b) every serdes__t* type with a macro: clock.tap_mode explicit = R4 pitch grid over the CORE STRIP only (outline minus
    the domain in the type frame, inset TAP_CLEAR) + ONE macro clock tap on the strip side of the macro edge (centre x);
    taps must be legal for taps.explicit_taps (outline/halo/spacing + sink radius/capacity), else the type keeps the
    grid and gets clock.keepouts_um = domain (tap_clear moves grid taps off it).
usage: serdes_taps.py WT PLAN_IN PLAN_OUT"""
import copy, json, math, sys
from pathlib import Path
WT, PIN, POUT = sys.argv[1:4]
sys.path.insert(0, WT + "/tools/die_plan")
import schema as S, taps as TP, gen_phys
raw = json.loads(Path(PIN).read_text())
P = S.Plan(S.load(PIN), Path(PIN))
HALO = 63.64
CLR = S.TAP_CLEAR_UM
dom = {d["name"]: d for d in raw["die"]["pg"]["domains"]}
types = raw["partition_types"] if isinstance(raw["partition_types"], dict) else {t["name"]: t for t in raw["partition_types"]}
rep = dict(domains={}, types={})
done = set()
for n in sorted(x for x in P.parts if x.startswith("lk_")):
    tn = P.parts[n]["type"]; t = P.types[tn]; W, H = t["outline_um"]
    c = [c for c in t.get("contents", []) if c.get("module") == "ot_pdie_serdes" and c.get("origin_um")]
    if not c:
        d = dom.get("phy_" + n)
        if d and tn not in done:     # no placed macro (serdes__t12): keep the grid off the declared VDDPHY domain
            done.add(tn)
            a, b = P.to_type(n, d["rect_um"][:2]), P.to_type(n, d["rect_um"][2:])
            ko = [round(min(a[0], b[0]), 3), round(min(a[1], b[1]), 3), round(max(a[0], b[0]), 3), round(max(a[1], b[1]), 3)]
            types[tn]["clock"]["keepouts_um"] = [ko]
            types[tn]["clock"]["tap_note"] = "DIE-S81-5: no placed macro; grid taps kept off the VDDPHY domain (keepouts_um)"
            rep["types"][tn] = dict(mode="keepouts (domain, no macro content)", keepout=[ko])
        continue
    (x, y), (w, h) = c[0]["origin_um"], c[0]["outline_um"]
    a, b = P.to_die(n, (x, y)), P.to_die(n, (x + w, y + h))
    mac = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
    ox, oy = P.parts[n]["origin_um"]
    want = [round(max(ox, mac[0] - HALO), 3), round(max(oy, mac[1] - HALO), 3),
            round(min(ox + W, mac[2] + HALO), 3), round(min(oy + H, mac[3] + HALO), 3)]
    d = dom["phy_" + n]
    if any(abs(u - v) > 0.01 for u, v in zip(d["rect_um"], want)):
        rep["domains"][n] = dict(old=d["rect_um"], new=want)
        d["rect_um"] = want
    if tn in done:
        continue
    done.add(tn)
    # domain in the type frame (= macro + halo, clipped)
    tx0, ty0, tx1, ty1 = max(0, x - HALO), max(0, y - HALO), min(W, x + w + HALO), min(H, y + h + HALO)
    # core strip = the larger side band of the outline outside the domain
    bands = [(0, 0, W, ty0), (0, ty1, W, H), (0, 0, tx0, H), (tx1, 0, W, H)]
    sb = max(bands, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    bw, bh = sb[2] - sb[0], sb[3] - sb[1]
    if sb[1] >= ty1 - 1e-6:   mt = ((x + x + w) / 2, ty1 + CLR)
    elif sb[3] <= ty0 + 1e-6: mt = ((x + x + w) / 2, ty0 - CLR)
    elif sb[2] <= tx0 + 1e-6: mt = (tx0 - CLR, (y + y + h) / 2)
    else:                     mt = (tx1 + CLR, (y + y + h) / 2)
    sinks = TP.sink_sites(P, tn)
    def mk(pitch):
        nx, ny = max(1, math.ceil(bw / pitch - 1e-9)), max(1, math.ceil(bh / pitch - 1e-9))
        pts = [(sb[0] + (i + 0.5) * bw / nx, sb[1] + (j + 0.5) * bh / ny) for j in range(ny) for i in range(nx)]
        pts = [(round(p[0] / 2.16) * 2.16, round(p[1] / 2.16) * 2.16) for p in pts] + [mt]
        pts = [(round(min(max(p[0], CLR), W - CLR), 4), round(min(max(p[1], CLR), H - CLR), 4)) for p in pts]
        # drop taps with no sink within 200 um (explicit taps must be non-empty); the macro tap always stays
        keep = [p for p in pts[:-1] if any(abs(p[0] - q[0]) + abs(p[1] - q[1]) <= 200 for q in sinks)] + [pts[-1]]
        return keep
    cands = [mk(pch) for pch in (400.0, 300.0, 240.0, 200.0)]
    T = types[tn]
    old = copy.deepcopy(T["clock"])
    err = None
    for pts in cands:
        tab = [dict(name="clk" if k == 0 else f"clk_t{k}", xy=list(p)) for k, p in enumerate(pts)]
        T["clock"] = copy.deepcopy(old)
        T["clock"]["tap_mode"] = "explicit"
        T["clock"]["taps"] = [tp for tp in old.get("taps", []) if tp.get("kind") == "core"] + tab
        T["clock"]["tap_note"] = ("DIE-S81-5 (COORD 10-28 00:06 ruling 1): R4 grid over the core strip only + one macro "
                                  "clock tap at the ot_pdie_serdes edge; no tap over the macro / VDDPHY domain")
        P2 = S.Plan(json.loads(json.dumps(raw)), Path(PIN))
        try:
            TP.explicit_taps(P2, tn)
            rep["types"][tn] = dict(mode="explicit", strip=[round(v, 3) for v in sb], taps=len(tab), macro_tap=mt)
            err = None
            break
        except Exception as e:
            err = str(e)[:300]
    if err:
        T["clock"] = old
        T["clock"]["keepouts_um"] = [[round(tx0, 3), round(ty0, 3), round(tx1, 3), round(ty1, 3)]]
        T["clock"]["tap_note"] = "DIE-S81-5: grid taps kept off the macro/VDDPHY domain (keepouts_um); explicit failed: " + err[:200]
        rep["types"][tn] = dict(mode="keepouts", why=err, keepout=T["clock"]["keepouts_um"])
Path(POUT).write_text(json.dumps(raw, indent=1) + "\n")
print(json.dumps(rep, indent=1))
