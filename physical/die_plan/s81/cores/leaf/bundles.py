#!/usr/bin/env python3
"""S81-CORES 10-24: GEOM-REVIEW table + render of one plan type's hard cores: every declared core-core / core-bus
bundle (core_conns.json), pin-group centroid -> partner pin-group centroid (Manhattan), the facing faces, the mean best
cosine of the port (G0C core-face rule), and the routing channel the bundle crosses first (gap um, tracks of the
channel's two routing directions on M2..M7 at 0.6 of the pitch).
usage (repo root): python3 bundles.py PLANDIR TYPE OUT_PREFIX   (writes OUT_PREFIX.json / .png if matplotlib)"""
import json, math, re, sys, collections
from pathlib import Path
PITCH = dict(H=dict(M2=0.036, M4=0.048, M6=0.064), V=dict(M3=0.036, M5=0.048, M7=0.064))
NRM = dict(N=(0, 1), S=(0, -1), E=(1, 0), W=(-1, 0))


def tr(o, w, h, x, y):
    if o in ("MY", "R180"): x = w - x
    if o in ("MX", "R180"): y = h - y
    return x, y


def face(x, y, w, h):
    return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]


def main(pd, tn, out):
    pd = Path(pd)
    plan = json.load(open(pd / "die_plan.json"))
    T = plan["partition_types"][tn]
    W, H = T["outline_um"]
    side = json.load(open(pd / "core_conns.json")).get(tn, {})
    C = {}
    for hc in T["hard_cores"]:
        w, h = hc["outline_um"]; o = hc.get("orient", "R0")
        X0 = hc["origin_um"][0] + hc["track_offset_um"][0]; Y0 = hc["origin_um"][1] + hc["track_offset_um"][1]
        pins = json.load(open(pd / hc["pins_file"]))["pins"]
        grp = collections.defaultdict(list)
        for p in pins:
            x, y = tr(o, w, h, p["x"], p["y"])
            grp[re.sub(r"\[\d+\]$", "", p["name"])].append((X0 + x, Y0 + y, face(x, y, w, h)))
        C[hc["inst"]] = dict(box=(X0, Y0, X0 + w, Y0 + h), grp=grp, cen=(X0 + w / 2, Y0 + h / 2), orient=o)
    bus = {b["name"]: b for b in T["buses"]}

    def bus_pt(b):
        m = sum(b["window_um"]) / 2
        return dict(N=(m, H), S=(m, 0), E=(W, m), W=(0, m))[b["face"]]
    rows = []
    for ci, ports in side.items():
        if ci not in C:
            continue
        for p, tg in ports.items():
            g = C[ci]["grp"].get(p)
            if not g:
                continue
            gx = sum(q[0] for q in g) / len(g); gy = sum(q[1] for q in g) / len(g)
            fc = collections.Counter(q[2] for q in g)
            for t in tg:
                k, _, nm = t.partition(":")
                if k == "core" and nm in C:
                    rev = [pp for pp, tt in side.get(nm, {}).items() if "core:" + ci in tt]
                    pg = [q for pp in rev for q in C[nm]["grp"].get(pp, [])]
                    px, py = (sum(q[0] for q in pg) / len(pg), sum(q[1] for q in pg) / len(pg)) if pg else C[nm]["cen"]
                    tgt = C[nm]["cen"]
                elif k == "bus" and nm in bus:
                    px, py = tgt = bus_pt(bus[nm])
                else:
                    continue
                cx, cy = C[ci]["cen"]; dx, dy = tgt[0] - cx, tgt[1] - cy; d = math.hypot(dx, dy) or 1
                cos = sum(n * max(0, 0) for n in [0]) or sum((NRM[f][0] * dx + NRM[f][1] * dy) / d * n for f, n in fc.items()) / len(g)
                rows.append(dict(core=ci.split(".")[-1], port=p, bits=len(g), faces=dict(fc), partner=t,
                                 manhattan_um=round(abs(gx - px) + abs(gy - py)), cos=round(cos, 3),
                                 a=(round(gx), round(gy)), b=(round(px), round(py))))
    # channels: gaps between facing core boxes (H gap: vertical channel uses V layers along it, turns on H)
    ch = []
    names = list(C)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, B = C[a]["box"], C[b]["box"]
            ox = min(A[2], B[2]) - max(A[0], B[0]); oy = min(A[3], B[3]) - max(A[1], B[1])
            if oy > 0 and (0 < B[0] - A[2] < 120 or 0 < A[0] - B[2] < 120):
                gap = max(B[0] - A[2], A[0] - B[2])
                ch.append(dict(between=[a.split(".")[-1], b.split(".")[-1]], kind="vertical", gap_um=round(gap, 2),
                               tracks_V=int(sum(gap / p for p in PITCH["V"].values()) * 0.6), span_um=round(oy)))
            if ox > 0 and (0 < B[1] - A[3] < 120 or 0 < A[1] - B[3] < 120):
                gap = max(B[1] - A[3], A[1] - B[3])
                ch.append(dict(between=[a.split(".")[-1], b.split(".")[-1]], kind="horizontal", gap_um=round(gap, 2),
                               tracks_H=int(sum(gap / p for p in PITCH["H"].values()) * 0.6), span_um=round(ox)))
    res = dict(type=tn, outline=[W, H], bundles=sorted(rows, key=lambda r: -r["bits"]), channels=ch,
               worst_manhattan_core_core=max([r["manhattan_um"] for r in rows if r["partner"].startswith("core:")] or [0]),
               min_cos=min([r["cos"] for r in rows] or [0]))
    json.dump(res, open(out + ".json", "w"), indent=1)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError:
        return res
    fig, ax = plt.subplots(figsize=(14, 12))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for b in T["buses"]:
        f_, m_ = b["face"], sum(b["window_um"]) / 2
        if f_ in "NS":
            y = H if f_ == "N" else 0
            ax.plot(b["window_um"], [y, y], lw=5, color="tab:orange"); ax.text(m_, y + 12, b["name"], fontsize=7, ha="center")
        else:
            x = W if f_ == "E" else 0
            ax.plot([x, x], b["window_um"], lw=5, color="tab:orange"); ax.text(x + 12, m_, b["name"], fontsize=7, rotation=90)
    for ci, c in C.items():
        b = c["box"]
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc="#dde6f0", ec="k"))
        ax.text(c["cen"][0], c["cen"][1], "%s %s" % (ci.split(".")[-1] if "g_ln" not in ci else ci.split(".")[2], c["orient"]),
                ha="center", va="center", fontsize=6)
        for g in c["grp"].values():
            ax.scatter([q[0] for q in g], [q[1] for q in g], s=0.3, color="k")
    for r in rows:
        col = "red" if r["manhattan_um"] > 405 or r["cos"] < -0.1 else ("orange" if r["cos"] < 0 else "green")
        ax.annotate("", xy=r["b"], xytext=r["a"], arrowprops=dict(arrowstyle="->", lw=0.3 + r["bits"] / 300, color=col, alpha=0.6))
        if r["bits"] >= 32:
            ax.text((r["a"][0] + r["b"][0]) / 2, (r["a"][1] + r["b"][1]) / 2, "%s %d b %d um" % (r["port"], r["bits"], r["manhattan_um"]),
                    fontsize=5, color=col)
    # ft-slot station sites (straight in->out line, 16 sampled bits, j/k of the way; face_flops.tcl placement)
    def fpt(face, win, tt):
        q = win[0] + tt * (win[1] - win[0])
        return dict(E=(W, q), W=(0, q), N=(q, H), S=(q, 0))[face]
    for s_ in T.get("ft_slots", []):
        k = s_["stations"]
        for i in range(16):
            tt = (i + 0.5) / 16
            a_ = fpt(s_["in_face"], s_["in_window_um"], tt); b_ = fpt(s_["out_face"], s_["out_window_um"], tt)
            ax.plot([a_[0], b_[0]], [a_[1], b_[1]], lw=0.15, color="purple", alpha=0.3)
            ax.scatter([a_[0] + (b_[0] - a_[0]) * j / k for j in range(1, k)],
                       [a_[1] + (b_[1] - a_[1]) * j / k for j in range(1, k)], s=1.5, color="purple")
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal")
    ax.set_title("%s: hard cores + every declared bundle (pin-group centroid -> partner; red > 405 um or cos < -0.1)" % tn, fontsize=9)
    fig.tight_layout(); fig.savefig(out + ".png", dpi=110)
    return res


if __name__ == "__main__":
    r = main(*sys.argv[1:4])
    print("worst core-core", r["worst_manhattan_core_core"], "min cos", r["min_cos"])
