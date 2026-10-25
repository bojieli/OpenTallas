#!/usr/bin/env python3
"""KV-FT 10-24 (owner decision 12 follow-up): feedthrough-crossing audit of a KV die plan + render.

Per lane (check.py lane_geometry = the G0 route model): ft crossings, route length (Manhattan, um), bits, bit-mm,
stations / cycles (Plan.lane_natural), and the cycles the lane needs under decision 12 (ft on <= M7, a registered
station every <= 405 um: hops = ceil(route / 405) + boundary flops, the reach405 model).  Per partition pair: bits,
crossings, bit-crossings, bit-mm.  Per crossed partition: ft lanes / bits (the corridor load).  Fix classes tag every
crossing lane with the structural cause (see CLASSES).

    python3 ft_audit_v39.py PLAN.json --out DIR [--png before.png] [--title T] [--model-lanes lanes.json]

--model-lanes: lanes JSON written by post_v39_ft.py --model (modelled crossings for moves that change RTL), so the
same report/render shows the modelled after-state next to the plan-level candidate.
"""
import argparse
import collections
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("OT_DIE_PLAN_TOOLS", os.path.join(HERE, "..", "..", "..", "tools", "die_plan")))
import schema as S  # noqa: E402
import check  # noqa: E402

REACH = 405.0
IO_ROW = ("sys_c", "sys_SW", "sys_SE", "io_W2", "io_W3", "io_E5", "io_E6")


def grp(p):
    return re.sub(r"_\d+$", "", p)


def fix_class(r):
    """structural cause of a crossing lane (owner principles: neighbour-only hops, no star hubs, tree collectives)."""
    s, d, sb, db = r["src"], r["dst"], r["sbus"], r["dbus"]
    if s in IO_ROW or d in IO_ROW:
        return "T:io-row<->hub trunk"
    if "pvw" in sb and ("fault" in sb or "y_valid" in sb or "_rN_b" in db or re.search(r"_r\d+_b", sb)):
        return "R:pv flag star (pv rows -> hub_C pv ctl)"
    if "fch" in sb or "efault" in sb or "fault" in sb:
        return "R:fault-chain star / far chain tail"
    if s.startswith("pc") and d.startswith("pv") or s.startswith("pv") and d.startswith("pc"):
        return "D:pc<->pv (shared PV column)" if r["nx"] <= 2 else "D:pc<->pv diagonal (row pair)"
    if s == "hub_C" and d.startswith("hroot"):
        return "B:kvs_ctl->hroot per-quadrant copies"
    if s.startswith("hroot") or d.startswith("hroot"):
        return "C:hroot far chain ends"
    if "hsl" in sb:
        return "C:hslice chain tails -> host"
    if s.startswith("hub") and d.startswith("hub"):
        return "H:hub-row internal"
    if s.startswith("hub") or d.startswith("hub"):
        return "H:hub<->rows"
    return "O:other"


def lanes_of(P):
    rows = []
    for lid, ln in P.lanes.items():
        a, b = P.ports[ln["ports"][0]], P.ports[ln["ports"][-1]]
        pts, regs, xs = check.lane_geometry(P, lid)
        L = check.plen(pts)
        lat = P.lane_latency(lid)
        bnd = lat["boundary"]
        r = dict(lid=lid, src=a["src"]["part"], sbus=a["src"]["bus"], dst=b["dst"]["part"], dbus=b["dst"]["bus"],
                 w=int(a["width"]), nx=len(xs), xp=[x["part"] for x in xs], L=round(L, 1), cyc=lat["cycles"],
                 natural=lat["natural"], pad=lat["pad"], st=lat["stations"], fixed=lat["fixed"],
                 cyc405=bnd + max(0, math.ceil(L / REACH) - 1) + lat["fixed"] if xs else lat["cycles"])
        r["cls"] = fix_class(r) if xs else ""
        rows.append(r)
    return rows


def summarise(rows):
    ft = [r for r in rows if r["nx"]]
    out = dict(lanes=len(rows), ft_lanes=len(ft), crossings=sum(r["nx"] for r in rows),
               mean_crossings=round(sum(r["nx"] for r in ft) / max(1, len(ft)), 3),
               max_crossings=max([r["nx"] for r in rows] + [0]),
               bits=sum(r["w"] for r in rows), bit_mm=round(sum(r["w"] * r["L"] for r in rows) / 1e3),
               ft_bit_mm=round(sum(r["w"] * r["L"] for r in ft) / 1e3),
               bit_crossings=sum(r["w"] * r["nx"] for r in rows),
               hist=dict(sorted(collections.Counter(r["nx"] for r in rows).items())))
    cls = collections.defaultdict(lambda: dict(lanes=0, crossings=0, bits=0, bit_crossings=0, bit_mm=0.0))
    for r in ft:
        c = cls[r["cls"]]
        c["lanes"] += 1
        c["crossings"] += r["nx"]
        c["bits"] += r["w"]
        c["bit_crossings"] += r["w"] * r["nx"]
        c["bit_mm"] += r["w"] * r["L"] / 1e3
    out["classes"] = {k: dict(v, bit_mm=round(v["bit_mm"])) for k, v in sorted(cls.items())}
    pair = collections.defaultdict(lambda: [0, 0, 0, 0, 0.0])
    for r in rows:
        k = f"{grp(r['src'])}->{grp(r['dst'])}"
        p = pair[k]
        p[0] += 1
        p[1] += r["w"]
        p[2] += r["nx"]
        p[3] += r["w"] * r["nx"]
        p[4] += r["w"] * r["L"] / 1e3
    out["pairs_top_bit_crossings"] = [dict(pair=k, lanes=v[0], bits=v[1], crossings=v[2], bit_crossings=v[3],
                                           bit_mm=round(v[4])) for k, v in
                                      sorted(pair.items(), key=lambda kv: -kv[1][3])[:30] if v[3]]
    out["pairs_top_crossings"] = [dict(pair=k, lanes=v[0], bits=v[1], crossings=v[2], bit_crossings=v[3],
                                       bit_mm=round(v[4])) for k, v in
                                  sorted(pair.items(), key=lambda kv: -kv[1][2])[:30] if v[2]]
    thru = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        for p in r["xp"]:
            thru[p][0] += 1
            thru[p][1] += r["w"]
    out["corridors"] = [dict(part=k, ft_lanes=v[0], ft_bits=v[1]) for k, v in
                        sorted(thru.items(), key=lambda kv: -kv[1][1])[:30]]
    hub = [r for r in ft if any(x.startswith("hub") for x in [r["src"], r["dst"]] + r["xp"])]
    out["hub_star"] = dict(lanes=len(hub), crossings=sum(r["nx"] for r in hub),
                           ending_at_hub=sum(1 for r in ft if r["src"].startswith("hub") or r["dst"].startswith("hub")),
                           through_hub_row=sum(1 for r in ft if any(x.startswith("hub") for x in r["xp"])))
    out["worst_lanes"] = [dict(lane=r["lid"], src=f"{r['src']}.{r['sbus']}", dst=f"{r['dst']}.{r['dbus']}", bits=r["w"],
                               crossings=r["nx"], route_um=r["L"], cycles=r["cyc"], cycles_405=r["cyc405"],
                               cls=r["cls"]) for r in sorted(ft, key=lambda r: (-r["nx"], -r["w"]))[:25]]
    return out


def render(P, rows, png, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle
    W, H = P.W, P.H
    fig, ax = plt.subplots(figsize=(9.5, 20), dpi=130)
    fam = {"pc": "#9ecae1", "phy": "#c6dbef", "hg": "#a1d99b", "hgi": "#c7e9c0", "pv": "#fdd0a2", "hub": "#fcbba1",
           "hroot": "#fc9272", "io": "#dadaeb", "sys": "#bcbddc"}
    slots = collections.Counter()
    for r in rows:
        for p in r["xp"]:
            slots[p] += 1
    for n in P.parts:
        x0, y0, x1, y1 = P.rect(n)
        f = re.match(r"[a-z]+", n).group(0)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fam.get(f, "#eeeeee"), ec="black", lw=0.4))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"{n}\nft {slots[n]}" if slots[n] else n, ha="center", va="center",
                fontsize=5.5, color="darkred" if slots[n] >= 20 else "black")
    segs = {k: [] for k in ("1-2", "3-6", "7+")}
    lws = {k: [] for k in segs}
    for r in rows:
        if not r["nx"]:
            continue
        k = "1-2" if r["nx"] <= 2 else "3-6" if r["nx"] <= 6 else "7+"
        pts, _, _ = check.lane_geometry(P, r["lid"])
        segs[k].append(pts)
        lws[k].append(0.25 + 2.2 * (r["w"] / 1118.0) ** 0.5)
    for k, col in (("1-2", "#3182bd"), ("3-6", "#e6550d"), ("7+", "#cb181d")):
        ax.add_collection(LineCollection(segs[k], linewidths=lws[k], colors=col, alpha=0.55, zorder=3,
                                         label=f"ft lanes, {k} crossings ({len(segs[k])})"))
    s = summarise(rows)
    ax.set_xlim(-100, W + 100)
    ax.set_ylim(-100, H + 100)
    ax.set_aspect("equal")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=3, fontsize=7, frameon=False)
    ax.set_title(f"{title}\n{s['ft_lanes']} ft lanes / {s['lanes']}, {s['crossings']} crossings (mean "
                 f"{s['mean_crossings']}, max {s['max_crossings']}), {s['bit_crossings']:,} bit-crossings, "
                 f"{s['bit_mm']:,} bit-mm", fontsize=8)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--png")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    P = S.Plan(S.load(a.plan))
    rows = lanes_of(P)
    os.makedirs(a.out, exist_ok=True)
    json.dump(rows, open(os.path.join(a.out, "ft_lanes.json"), "w"))
    s = summarise(rows)
    json.dump(s, open(os.path.join(a.out, "ft_audit.json"), "w"), indent=1)
    print(json.dumps({k: s[k] for k in ("lanes", "ft_lanes", "crossings", "mean_crossings", "max_crossings",
                                        "bit_crossings", "bit_mm", "ft_bit_mm", "hub_star")}))
    for k, v in s["classes"].items():
        print(f"  {k:45s} {v}")
    if a.png:
        render(P, rows, a.png, a.title or a.plan)


if __name__ == "__main__":
    main()
