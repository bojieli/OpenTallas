#!/usr/bin/env python3
"""COORD ruling 10-25 (fold-gather duty, option B): the svc fold rung keeps the gather word FULL WIDTH.

TOK-DS 04:32: the attention engine scores one gather beat per cycle into the exchange leaf, so the 2-beat F2B
serialisation (1068 b x 2 beats, <= 1/2 duty) faults by construction.  Main RTL (dsdv_svc_rs gi_d/go_d) is already
full width (2132 b + valid = 2133 b per face), so B is a PLAN-only delta that makes the plan match the RTL:

  lanes  attnh__svc_*__svc_*     beats 2 -> 1 (word_bits 2133 unchanged; 0 cycles)
  ports  attnh__svc_*__svc_*__0  width 1068 -> 2133, pin layers M7/M5 -> M7/M5/M3
  types  each hi/lo svc pair's abutting fold face (hi S / lo N) gets face_layers [M7, M5, M3] (budget 9 pins/um on
         that face only) and its bus windows are re-laid in the free face span (ft slot windows and buses to other partitions stay fixed): same
         order, window length per bus = pins / layers at one common density, 2.136-um gaps; both ends of every
         port keep identical type-frame windows (hi/lo are stacked at the same x and orient).
Fallback A (KV row beats every 2 cycles, F2B kept, ~+0.4 % AR) is NOT applied.

    python3 physical/die_plan/s81/delta_gatherB_1025.py PLAN [OUT]
"""
import json
import sys

FOLD_LAYERS = ["M7", "M5", "M3"]
GAP = 2.136
EDGE_LO, EDGE_HI = 6.144, 8.868          # face margins as the current plan (first window 6.144, last ends W - 8.868)


def _pairs(raw):
    PA = {x["name"]: x for x in raw["partitions"]}
    return [(PA[f"svc_{2 * i + 1}"], PA[f"svc_{2 * i}"]) for i in range(64)
            if f"svc_{2 * i + 1}" in PA and f"svc_{2 * i}" in PA]


def apply(raw):
    rep = []
    T = raw["partition_types"]
    nl = 0
    for ln in raw["lanes"]:
        if ln["id"].startswith("attnh__svc_"):
            assert ln.get("word_bits") == 2133, ln
            if ln.get("beats", 1) != 1:
                ln["beats"] = 1
                nl += 1
    na = 0
    for pr in raw["ports"]:
        if pr["id"].startswith("attnh__svc_"):
            pr["width"] = 2133
            pr["layers"] = list(FOLD_LAYERS)
            na += 1
    for th in {x["type"] for x in raw["partitions"] if x["name"].startswith("svc_")}:
        for b in T[th]["buses"]:
            if b["name"].startswith("attnh_"):
                b["width"] = 2133
                b["layers"] = list(FOLD_LAYERS)
    rep.append(f"gatherB: {nl} attnh lanes beats 2 -> 1, {na} ports 1068 -> 2133 b on {FOLD_LAYERS}")
    for H, L in _pairs(raw):
        assert H["orient"] == L["orient"] and abs(H["origin_um"][0] - L["origin_um"][0]) < 1e-3, (H, L)
        th, tl = T[H["type"]], T[L["type"]]
        W = th["outline_um"][0]
        assert abs(W - tl["outline_um"][0]) < 1e-3
        ps = [x for x in raw["ports"] if {x["src"]["part"], x["dst"]["part"]} == {H["name"], L["name"]}]
        if not any(x["id"].startswith("attnh") for x in ps):
            continue
        hb = {b["name"]: b for b in th["buses"] if b["face"] == "S"}
        lb = {b["name"]: b for b in tl["buses"] if b["face"] == "N"}
        obst = []
        for t, f in ((th, "S"), (tl, "N")):
            for s in t.get("ft_slots", []):
                for k in ("in", "out"):
                    if s[f"{k}_face"] == f:
                        obst.append(sorted(s[f"{k}_window_um"]))
        items = []
        for x in ps:
            e = {x["src"]["part"]: x["src"], x["dst"]["part"]: x["dst"]}
            if "bus" not in e[H["name"]] or "bus" not in e[L["name"]]:
                continue
            bh, bl = hb.get(e[H["name"]]["bus"]), lb.get(e[L["name"]]["bus"])
            if bh is None or bl is None:
                continue
            assert all(abs(u - v) < 1e-3 for u, v in zip(sorted(bh["window_um"]), sorted(bl["window_um"]))), (x["id"], bh, bl)
            items.append((min(bh["window_um"]), x, bh, bl))
        items.sort(key=lambda z: z[0])
        used = {id(z[2]) for z in items} | {id(z[3]) for z in items}
        fixed = [b["name"] for b in list(hb.values()) + list(lb.values()) if id(b) not in used]
        obst += [sorted(b["window_um"]) for b in list(hb.values()) + list(lb.values()) if id(b) not in used]
        free, c = [], EDGE_LO
        for o in sorted(obst):
            if o[0] - GAP > c:
                free.append([c, o[0] - GAP])
            c = max(c, o[1] + GAP)
        free.append([c, W - EDGE_HI])
        need = [x["width"] / len(x["layers"]) for _, x, _, _ in items]

        def pack(um_per_pin):
            out, fi, c = [], 0, free[0][0]
            for n in need:
                ln = n * um_per_pin
                while fi < len(free) and c + ln > free[fi][1] + 1e-9:
                    fi += 1
                    if fi < len(free):
                        c = free[fi][0]
                if fi >= len(free):
                    return None
                out.append([round(c, 3), round(c + ln, 3)])
                c += ln + GAP
            return out
        lo_, hi_ = 0.0, 10.0
        for _ in range(60):
            m = (lo_ + hi_) / 2
            if pack(m):
                lo_ = m
            else:
                hi_ = m
        wins = pack(lo_)
        assert wins, H["name"]
        mir = H["orient"] in ("MY", "R180")
        X0 = H["origin_um"][0]
        dens = []
        for (x0, x, bh, bl), w in zip(items, wins):
            a0 = min(x["window_um"])
            b0, b1 = sorted(bh["window_um"])
            assert abs(a0 - (X0 + (W - b1 if mir else b0))) < 0.05, (x["id"], a0, b0, b1, mir)
            x["window_um"] = ([round(X0 + W - w[1], 3), round(X0 + W - w[0], 3)] if mir else
                              [round(X0 + w[0], 3), round(X0 + w[1], 3)])
            bh["window_um"] = list(w)
            bl["window_um"] = list(w)
            dens.append(f"{x['id'].split('__')[0]}:{x['width'] / (w[1] - w[0]):.2f}/um@{len(x['layers'])}L")
        for t, f in ((th, "S"), (tl, "N")):
            t.setdefault("face_layers", {})[f] = list(FOLD_LAYERS)
        rep.append(f"{H['name']}/{L['name']} ({H['type']}/{L['type']}): {len(items)} bus windows re-laid, "
                   f"{len(obst)} ft/other windows fixed {fixed}, {1 / lo_:.2f} pins/um/layer; " + ", ".join(dens))
    return rep


def main():
    pf = sys.argv[1]
    raw = json.load(open(pf))
    print("\n".join(apply(raw)))
    try:
        sys.path.insert(0, "/srv/opentallas-scratch2/claude/s81-plan2")
        import pdump
        txt = pdump.dumps(raw)
    except ImportError:
        txt = json.dumps(raw, indent=1) + "\n"
    open(sys.argv[2] if len(sys.argv) > 2 else pf, "w").write(txt)


if __name__ == "__main__":
    main()
