#!/usr/bin/env python3
"""KV-PLAN-DELTA-2 GEOM column census of FT bit hops (per partition type).

Every bit of every sited ft slot is a chain in-pin -> station sites -> out-pin.  Each hop is routed as one L.
Vertical demand of a hop = its vertical leg at x of one endpoint (HV: at the destination x, VH: at the source x).
Modes: HV (KV-PLAN-EVAL screen, pessimistic for corner hops), and BEST = per (slot, hop) one orientation for all its
bits, chosen greedily (widest first) to minimise the peak column it touches (what a router can do with an L).
Gate (GEOM-24): peak vertical bits in any 10-um column <= 0.6 x 32 tracks/um x 10 um = 192 (ratio <= 1.0), same for
horizontal bits per 10-um row; also reported: the max bits in one 15-um column (the 1,648-b spine screen).
    geom_census.py PLAN TYPE[,TYPE..] OUT.json [--png-dir D]
"""
import json, sys, argparse
import numpy as np
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/kv-plan-q3-1027/tools/die_plan")
import schema as S
from gen_phys import type_pins

TR_UM, FILL, DX = 32.0, 0.6, 5.0
CAP10 = TR_UM * FILL * 10


def chains(model, tn):
    t = model.types[tn]
    pins = {(bn, i): (x, y) for bn, i, _, x, y, _ in type_pins(model, tn)}
    out = []
    for s in t.get("ft_slots") or []:
        bs = s.get("bit_sites_um")
        if not bs and int(s.get("stations", 0)) > 1:
            out.append((s["name"], None, None)); continue
        wd = int(s["width"]) + 1
        cell = np.array(s.get("bit_site_cell_um") or [0, 0]) / 2
        a = np.array([pins[(s["name"] + "_i", i)] for i in range(wd)])
        b = np.array([pins[(s["name"] + "_o", i)] for i in range(wd)])
        st = [np.array(x) + cell for x in (bs or [])]
        lane = a[:, 0] if s["in_face"] in "NS" else (b[:, 0] if s["out_face"] in "NS" else None)
        out.append((s["name"], [a, *st, b], lane))
    return out


def census(model, tn):
    t = model.types[tn]
    W, H = t["outline_um"]
    nx, ny = int(W // DX) + 2, int(H // DX) + 2
    hops, unsited = [], []
    for name, ch, lane in chains(model, tn):
        if ch is None:
            unsited.append(name); continue
        for k in range(len(ch) - 1):
            hops.append((name, k, ch[k], ch[k + 1], lane))
    def add(G, h, orient, sgn):
        _, _, A, B, lane = h
        for n_, (a, c) in enumerate(zip(A, B)):
            if G.get("z") or orient == 2:
                # ZSPREAD: each bit-hop is a monotone Z (a 2-pin net as the router sees it); the short leg's jog of bit
                # n_ sits at fraction (n_+.5)/N of the long leg, so a bundle's jogs spread over the hop span
                f = (n_ + .5) / len(A)
                if G["zdir"][h[0], h[1]]:          # mostly horizontal hop: vertical jog at x_b
                    xb = a[0] + (c[0] - a[0]) * f
                    j = min(max(int(xb // DX), 0), nx - 1); i0, i1 = sorted((int(a[1] // DX), int(c[1] // DX)))
                    if i1 > i0: G["V"][i0:i1 + 1, j] += sgn
                    for y_, p0, p1 in ((a[1], a[0], xb), (c[1], xb, c[0])):
                        i = min(int(y_ // DX), ny - 1); j0, j1 = sorted((int(p0 // DX), int(p1 // DX)))
                        if j1 > j0: G["Hh"][i, j0:j1 + 1] += sgn
                else:                               # mostly vertical hop: horizontal jog at y_b
                    yb = a[1] + (c[1] - a[1]) * f
                    i = min(max(int(yb // DX), 0), ny - 1); j0, j1 = sorted((int(a[0] // DX), int(c[0] // DX)))
                    if j1 > j0: G["Hh"][i, j0:j1 + 1] += sgn
                    for x_, p0, p1 in ((a[0], a[1], yb), (c[0], yb, c[1])):
                        j = min(int(x_ // DX), nx - 1); i0, i1 = sorted((int(p0 // DX), int(p1 // DX)))
                        if i1 > i0: G["V"][i0:i1 + 1, j] += sgn
                continue
            if lane is not None and G.get("lane"):
                # LANE: a bundle with an N/S face runs its vertical leg on the bit's own window lane x (ft_corridor
                # keeps window offsets); station sites only add horizontal jogs to/from that lane
                x = lane[n_]
                if abs(a[1] - c[1]) >= 1e-6:
                    j = min(max(int(x // DX), 0), nx - 1); i0, i1 = sorted((int(a[1] // DX), int(c[1] // DX)))
                    G["V"][i0:i1 + 1, j] += sgn
                for (p_, y_) in ((a[0], a[1]), (c[0], c[1])):
                    if abs(p_ - x) >= 1e-6:
                        i = min(int(y_ // DX), ny - 1); j0, j1 = sorted((int(p_ // DX), int(x // DX)))
                        G["Hh"][i, j0:j1 + 1] += sgn
                continue
            if abs(a[1] - c[1]) >= 1e-6:
                x = c[0] if orient == 0 else a[0]
                j = min(int(x // DX), nx - 1); i0, i1 = sorted((int(a[1] // DX), int(c[1] // DX)))
                G["V"][i0:i1 + 1, j] += sgn
            if abs(a[0] - c[0]) >= 1e-6:
                y = a[1] if orient == 0 else c[1]
                i = min(int(y // DX), ny - 1); j0, j1 = sorted((int(a[0] // DX), int(c[0] // DX)))
                G["Hh"][i, j0:j1 + 1] += sgn
    res = dict(type=tn, outline_um=[W, H], slots_unsited=unsited, hops=len(hops),
               bits=int(sum(len(h[2]) for h in hops if h[1] == 0)))
    grids = {}
    zdir = {(h[0], h[1]): bool(np.abs(h[3][:, 0] - h[2][:, 0]).mean() >= np.abs(h[3][:, 1] - h[2][:, 1]).mean()) for h in hops}
    for mode in ("HV", "BEST", "ROUTE"):
        G = dict(V=np.zeros((ny, nx)), Hh=np.zeros((ny, nx)), z=False, zdir=zdir)
        orient = [0] * len(hops)
        for h in hops:
            add(G, h, 0, 1)
        if mode in ("BEST", "ROUTE"):
            # BEST: per (slot, hop) one L orientation for the whole bundle; ROUTE: also the monotone Z whose jogs are
            # spread over the hop span (bit-ordered, no crossings) -- the 2-bend routes a global router uses
            opts = (0, 1) if mode == "BEST" else (0, 1, 2)
            order = sorted(range(len(hops)), key=lambda i: -len(hops[i][2]))
            def peak():
                # overflow energy over the 10-um gate (sum of squared excess) + a small peak term
                v, hh = win(G["V"], 2, 1), win(G["Hh"], 2, 0)
                ov = float((np.maximum(v - CAP10, 0) ** 2).sum() + (np.maximum(hh - CAP10, 0) ** 2).sum())
                return ov + 1e-3 * max(v.max(), hh.max())
            for _ in range(3):
                for i in order:
                    h = hops[i]
                    best_o, best_p = orient[i], peak()
                    for o in opts:
                        if o == orient[i]:
                            continue
                        add(G, h, orient[i], -1); add(G, h, o, 1); p1 = peak()
                        add(G, h, o, -1); add(G, h, orient[i], 1)
                        if p1 < best_p - 1e-9:
                            best_o, best_p = o, p1
                    if best_o != orient[i]:
                        add(G, h, orient[i], -1); add(G, h, best_o, 1); orient[i] = best_o
        grids[mode] = G
        r = {}
        for key, axis, nm in (("V", 1, "col"), ("Hh", 0, "row")):
            for wu in (10, 15):
                S10 = win(G[key], int(wu // DX), axis)
                i, j = np.unravel_index(np.argmax(S10), S10.shape)
                r[f"{nm}{wu}_max_bits"] = int(S10[i, j])
                r[f"{nm}{wu}_at_um"] = [round(float(j) * DX, 1), round(float(i) * DX, 1)]
                r[f"{nm}{wu}_ratio"] = round(float(S10[i, j]) / (TR_UM * FILL * wu), 3)
        r["pass"] = bool(r["col10_ratio"] <= 1.0 and r["row10_ratio"] <= 1.0)
        res[mode] = r
    hl = [float(np.abs(h[3] - h[2]).sum(axis=1).max()) for h in hops]
    res["max_bit_hop_um"] = round(max(hl), 2) if hl else 0
    res["bit_hops_over_405"] = int(sum(int((np.abs(h[3] - h[2]).sum(axis=1) > 405).sum()) for h in hops))
    return res, grids


def win(G, k, axis):
    cs = np.cumsum(np.pad(G, ((0, 0), (1, 0)) if axis == 1 else ((1, 0), (0, 0))), axis=axis)
    return (cs[:, k:] - cs[:, :-k]) if axis == 1 else (cs[k:] - cs[:-k])


def render(model, tn, res, grids, png):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    t = model.types[tn]; W, H = t["outline_um"]
    G = grids["ROUTE"]
    fig, ax = plt.subplots(1, 3, figsize=(22, 10), gridspec_kw=dict(width_ratios=[1.2, 1.2, 1]))
    for a_, key, lab in ((ax[0], "V", "vertical"), (ax[1], "Hh", "horizontal")):
        im = a_.imshow(win(G[key], 2, 1 if key == "V" else 0) if False else G[key], origin="lower",
                       extent=[0, G[key].shape[1] * DX, 0, G[key].shape[0] * DX], cmap="magma")
        plt.colorbar(im, ax=a_, label=f"{lab} FT bits per 5-um cell")
        for c in t.get("hard_cores", []):
            x, y = c["origin_um"]; cw, chh = c["outline_um"]
            a_.add_patch(plt.Rectangle((x, y), cw, chh, fill=False, ec="cyan", lw=0.5))
        for name, ch, _l in chains(model, tn):
            if ch is None: continue
            cs = np.array([c.mean(axis=0) for c in ch])
            a_.plot(cs[:, 0], cs[:, 1], "-", color="lime", lw=0.4, alpha=0.7)
            a_.plot(cs[1:-1, 0], cs[1:-1, 1], ".", color="yellow", ms=2.5)
        a_.add_patch(plt.Rectangle((0, 0), W, H, fill=False, ec="white", lw=1)); a_.set_xlim(-5, W + 5); a_.set_ylim(-5, H + 5)
        a_.set_title(f"{tn}: {lab} demand (ROUTE) + station centroids")
    pv = win(G["V"], 2, 1).max(axis=0); ph = win(G["Hh"], 2, 0).max(axis=1)
    ax[2].plot(np.arange(len(pv)) * DX, pv, "k-", lw=1, label="max vertical bits / 10-um column (over y)")
    ax[2].plot(np.arange(len(ph)) * DX, ph, "b-", lw=0.8, alpha=0.7, label="max horizontal bits / 10-um row (over x), axis=y")
    ax[2].axhline(CAP10, color="r", ls="--", label=f"gate 0.6 x 32 tr/um x 10 um = {CAP10:.0f}")
    b = res["ROUTE"]
    ax[2].set_title(f"ROUTE col10 {b['col10_max_bits']} ({b['col10_ratio']}), row10 {b['row10_max_bits']} ({b['row10_ratio']}); HV col10 {res['HV']['col10_max_bits']}, BEST {res['BEST']['col10_max_bits']}")
    ax[2].legend(fontsize=8); ax[2].set_xlabel("um")
    plt.tight_layout(); plt.savefig(png, dpi=100); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("types"); ap.add_argument("out")
    ap.add_argument("--png-dir")
    a = ap.parse_args()
    model = S.Plan(json.load(open(a.plan)))
    out = []
    for tn in a.types.split(","):
        r, g = census(model, tn)
        out.append(r)
        print(json.dumps({k: r[k] for k in ("type", "bits", "hops", "max_bit_hop_um", "bit_hops_over_405")}), "HV", r["HV"], "BEST", r["BEST"], "ROUTE", r["ROUTE"], "unsited", len(r["slots_unsited"]), flush=True)
        if a.png_dir:
            render(model, tn, r, g, f"{a.png_dir}/{tn}.png")
    json.dump(out, open(a.out, "w"), indent=1)
