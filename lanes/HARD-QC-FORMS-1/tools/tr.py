#!/usr/bin/env python3
"""HARD-QC-FORMS-1 type plan render: outline, cores (hard_cores + LEF content macros), face windows, ft chains,
internal stations, taps, landing bands. usage: tr.py PLAN TYPE OUT.png [--title T] [--street J.json] [--labels]"""
import json, sys, argparse
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("type"); ap.add_argument("out")
ap.add_argument("--title", default=""); ap.add_argument("--zoom", default=""); a = ap.parse_args()
P = json.load(open(a.plan)); T = P["partition_types"][a.type]; W, H = T["outline_um"]
def core_wh(h):
    w, hh = h["outline_um"]
    return (hh, w) if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90") else (w, hh)
fig, ax = plt.subplots(figsize=(max(7, 14 * W / max(W, H)) + 2, max(7, 14 * H / max(W, H))), dpi=110)
ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k", lw=1.5))
for h in T.get("hard_cores", []):
    x, y = h["origin_um"]; w, hh = core_wh(h)
    lefc = "ot_rom" in h["module"] or "ot_sram" in h["module"]
    ax.add_patch(Rectangle((x, y), w, hh, fc="#f4c7a0" if lefc else "#c9d6ea", ec="#7a4a1a" if lefc else "#34507a", lw=0.8, alpha=0.85))
    nm = h["inst"].split(".")[-1] if lefc else h["inst"]
    nm = h["inst"].replace("u_bound.", "")[-28:]
    ax.text(x + w / 2, y + hh / 2, f"{nm}\n{h.get('orient','R0')} obs {h.get('obs_max','?')}", ha="center", va="center", fontsize=5.5)
cols = {"in": "#1a7f37", "out": "#b3261e"}
def face_seg(face, lo, hi, off=0.0):
    if face == "N": return (lo, H + off), (hi, H + off)
    if face == "S": return (lo, -off), (hi, -off)
    if face == "E": return (W + off, lo), (W + off, hi)
    return (-off, lo), (-off, hi)
for b in T.get("buses", []):
    if not b.get("window_um") or not b.get("face"): continue
    lo, hi = b["window_um"]; p, q = face_seg(b["face"], lo, hi, 6)
    ax.plot([p[0], q[0]], [p[1], q[1]], color=cols[b["dir"]], lw=4, solid_capstyle="butt")
    if b["width"] >= 30:
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        dx = {"E": 14, "W": -14}.get(b["face"], 0); dy = {"N": 14, "S": -14}.get(b["face"], 0)
        ax.text(mx + dx, my + dy, f"{b['name']} {b['width']}", fontsize=5.5, color=cols[b["dir"]], ha={"E": "left", "W": "right"}.get(b["face"], "center"),
                va={"N": "bottom", "S": "top"}.get(b["face"], "center"), rotation=90 if b["face"] in "NS" else 0)
for f in T.get("ft_slots", []):
    r = f.get("regs_um")
    if f.get("out_window_um"):
        p, q = face_seg(f["out_face"], *f["out_window_um"], 2); ax.plot([p[0], q[0]], [p[1], q[1]], color="#7b3fb5", lw=2.5, solid_capstyle="butt")
    if r:
        xs = [p[0] for p in r]; ys = [p[1] for p in r]
        ow = f.get("out_window_um")
        if ow:
            p, q = face_seg(f["out_face"], *ow, 0); xs.append((p[0] + q[0]) / 2); ys.append((p[1] + q[1]) / 2)
        ax.plot(xs, ys, "-", color="#7b3fb5", lw=0.7 + f["width"] / 400, alpha=0.6); ax.plot(xs[:len(r)], ys[:len(r)], "s", color="#7b3fb5", ms=3)
        ax.text(xs[len(r) // 2], ys[len(r) // 2], f"ft {f['name']} {f['width']}", fontsize=5, color="#5a2a90")
for s in T.get("internal_stations", []):
    pts = [s.get("from_um")] + list(s.get("regs_um") or []) + [s.get("to_um")]
    pts = [p for p in pts if p]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color="#c77700", lw=0.6, alpha=0.7)
    for p in (s.get("regs_um") or []): ax.plot(p[0], p[1], "o", color="#c77700", ms=2.5)
for t in T.get("clock", {}).get("taps", []):
    ax.plot(*t["xy"], marker="^" if t["kind"] != "core" else "v", color="#0057b8", ms=6 if t["kind"] != "core" else 4)
lc = T.get("clock", {}).get("landing_contract", {})
for n, b in (lc.get("bands") or {}).items():
    r = b.get("rect_um")
    if r: ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#ffe066", ec="#b38f00", lw=0.5, alpha=0.6))
ax.set_xlim(-60, W + 60); ax.set_ylim(-60, H + 60)
if a.zoom:
    z = [float(v) for v in a.zoom.split(",")]; ax.set_xlim(z[0], z[2]); ax.set_ylim(z[1], z[3])
ax.set_aspect("equal"); ax.grid(True, lw=0.2, alpha=0.5)
ax.set_title(f"{a.title or a.type}  {W} x {H} um   green=in red=out purple=ft orange=internal stations yellow=landing bands blue=taps", fontsize=8)
fig.savefig(a.out, bbox_inches="tight"); print("wrote", a.out)
