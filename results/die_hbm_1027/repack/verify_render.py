#!/usr/bin/env python3
"""DIE-HBM/REPACK independent check of c20_repack_delta.json on the basis plan: apply in memory, then recount pin6 face
density of every new pins table, overlap/outline/keepout check per touched type, taps moved with cores; render
before/after per touched type. usage: verify_render.py PLANDIR DELTADIR"""
import json, sys, collections, itertools
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pd, dd = Path(sys.argv[1]), Path(sys.argv[2])
raw = json.load(open(pd / "die_plan.json")); T = raw["partition_types"]
D = json.load(open(dd / "c20_repack_delta.json"))
CAP, END, EPS = 5.5, 8.64, 1e-6
def lface(x, y, w, h): return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]
out = dict(tables={}, types={})
for f in sorted({e["new_pins_file"] for e in D["entries"] if e["grown"]}):
    e = next(e for e in D["entries"] if e["new_pins_file"] == f); w, h = e["new_outline"]
    ps = json.load(open(dd / f)); cnt = collections.Counter(lface(p["x"], p["y"], w, h) for p in ps)
    old = json.load(open(pd / e["old_pins_file"])); ow, oh = e["old_outline"]; c0 = collections.Counter(lface(p["x"], p["y"], ow, oh) for p in old)
    pn = lambda p: p.get("name") or (p.get("bus"), p.get("bit"))
    names_ok = sorted(map(str, map(pn, ps))) == sorted(map(str, map(pn, old)))
    out["tables"][f] = dict(before={F: round(c0[F] / ((ow if F in "NS" else oh) - 2 * END), 3) for F in "NSEW"},
                            after={F: round(cnt[F] / ((w if F in "NS" else h) - 2 * END), 3) for F in "NSEW"},
                            same_pin_names=names_ok, inside=all(-EPS <= p["x"] <= w + EPS and -EPS <= p["y"] <= h + EPS for p in ps),
                            face_kept=all(lface(p["x"], p["y"], w, h) == lface(q["x"], q["y"], ow, oh) for p, q in zip(sorted(ps, key=lambda p: str(pn(p))), sorted(old, key=lambda p: str(pn(p))))))
by = collections.defaultdict(list)
for e in D["entries"]: by[e["type"]].append(e)
def rect(o, s): return (o[0], o[1], o[0] + s[0], o[1] + s[1])
def ovl(a, b): return a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS
for tn, es in sorted(by.items()):
    t = T[tn]; W, H = t["outline_um"]
    before = {c["inst"]: rect(c["origin_um"], c["outline_um"]) for c in t["hard_cores"]}
    after = dict(before)
    for e in es:
        c = next(c for c in t["hard_cores"] if c["inst"] == e["inst"])
        assert [round(v, 3) for v in c["origin_um"]] == [round(v, 3) for v in e["old_origin"]]
        after[e["inst"]] = rect(e["new_origin"], e["new_outline"])
    ov0 = {frozenset(p) for p in itertools.combinations(before, 2) if ovl(before[p[0]], before[p[1]])}
    ov1 = {frozenset(p) for p in itertools.combinations(after, 2) if ovl(after[p[0]], after[p[1]])}
    outside = [i for i, r in after.items() if r[0] < -EPS or r[1] < -EPS or r[2] > W + EPS or r[3] > H + EPS]
    ks = [tuple(k) for k in (t.get("clock") or {}).get("keepouts_um") or []]
    kos = [e["inst"] for e in es if any(ovl(after[e["inst"]], k) and not ovl(before[e["inst"]], k) for k in ks)]
    taps = {tp["name"]: tp["xy"] for tp in (t.get("clock") or {}).get("taps") or [] if tp.get("xy")}
    tap_bad = []
    for e in es:
        for tm in e["taps_moved"]:
            r = after[e["inst"]]
            if not (r[0] - EPS <= tm["new_xy"][0] <= r[2] + EPS and r[1] - EPS <= tm["new_xy"][1] <= r[3] + EPS): tap_bad.append(tm["name"])
        n_t = sum(1 for k in taps if k.split(".")[0] == e["inst"])
        if n_t != len(e["taps_moved"]): tap_bad.append(e["inst"] + " count")
    mv = [e["move_um"] for e in es]
    out["types"][tn] = dict(entries=len(es), grown=sum(e["grown"] for e in es), moved=sum(not e["grown"] for e in es),
                            max_move_um=max(mv), moves_over_100=[e["inst"] for e in es if e["move_um"] > 100],
                            new_overlaps=[sorted(p) for p in ov1 - ov0], overlaps_before=len(ov0), outside=outside,
                            new_keepout_hits=kos, taps_bad=tap_bad)
    fig, axs = plt.subplots(1, 2, figsize=(16, 16 * H / W / 2 + 1.5) if W > H else (12, 9))
    for ax, st, ttl in ((axs[0], before, "C19 before"), (axs[1], after, "C20g re-pack after")):
        ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k", lw=1.5))
        for k in ks: ax.add_patch(Rectangle((k[0], k[1]), k[2] - k[0], k[3] - k[1], fc="#f4c0c0", ec="none", alpha=0.6))
        g = {e["inst"] for e in es if e["grown"]}; m = {e["inst"] for e in es if not e["grown"]}
        for i, r in st.items():
            col = "#d9534f" if i in g else ("#f0ad4e" if i in m else "#9fb7d0")
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=col, ec="k", lw=0.4, alpha=0.85))
            if i in g or (ttl.startswith("C20") and i in m): ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, i.replace("u_", "")[:16], fontsize=5, ha="center", va="center")
        if ttl.startswith("C20"):
            for e in es:
                if not e["grown"]:
                    ax.annotate("", xy=(e["new_origin"][0], e["new_origin"][1]), xytext=(e["old_origin"][0], e["old_origin"][1]), arrowprops=dict(arrowstyle="->", lw=0.6))
        ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal"); ax.set_title(f"{tn} {ttl} (red=grown, orange=moved)", fontsize=9)
    fig.tight_layout(); p = dd / f"render_{tn}.png"; fig.savefig(p, dpi=110); plt.close(fig); out["types"][tn]["render"] = str(p)
json.dump(out, open(dd / "verify_report.json", "w"), indent=1)
for f, v in out["tables"].items(): print(Path(f).name[:60], "before", {k: x for k, x in v["before"].items() if x > CAP}, "after max", max(v["after"].values()), v["same_pin_names"], v["inside"], "face_kept", v["face_kept"])
for tn, v in out["types"].items(): print(tn, {k: x for k, x in v.items() if k != "render"})
