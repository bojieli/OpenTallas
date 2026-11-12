#!/usr/bin/env python3
"""CPL-S81-SLICE-5: approved +1 pin cycles (S81-ARCH-RTL-2 a754fcbe5bd7f2b5d) as plan stations on t73:
  vs -> vq (u, u_i, u_v, um_b, um_i, um_q, um_v): one new FIRM station each (CS_U_D 1);
  leafdn_i0 -> vs (g_c, g_d, g_v, s_d, s_v): 1 -> 2 regs.
Regs on free lattice sites at equal Manhattan hops along the L path.  usage: pc.py PLAN_IN DIE_DIR PLAN_OUT"""
import json, sys
T = "ot_s81sl_leaf__t73"
pin, die, pout = sys.argv[1:4]
P = json.load(open(pin)); t = P["partition_types"][T]; hc = {h["inst"]: h for h in t["hard_cores"]}
boxes = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in t["hard_cores"]]
free = lambda p: not any(a - 4.32 < p[0] < c + 4.32 and b - 4.32 < p[1] < d + 4.32 for a, b, c, d in boxes)
def snap(p):
    for r in range(0, 200):
        for i in range(-r, r + 1):
            for j in (-r + abs(i), r - abs(i)):
                q = (round(p[0] + i * 4.32, 3), round(p[1] + j * 4.32, 3))
                if free(q) and 0 <= q[0] <= t["outline_um"][0] and 0 <= q[1] <= t["outline_um"][1]: return list(q)
    raise SystemExit(f"no site near {p}")
def centroid(inst, bus):
    h = hc[inst]; W, H = h["outline_um"]; x0, y0 = h["origin_um"]
    pins = [p for p in json.load(open(f"{die}/{h['pins_file']}"))["pins"] if p["name"].split("[")[0] == bus]
    assert h["orient"] == "R180", inst
    return [round(x0 + W - sum(p["x"] for p in pins) / len(pins), 3), round(y0 + H - sum(p["y"] for p in pins) / len(pins), 3)], len(pins)
def lpath(a, b, k, xfirst=True):
    """k regs at equal shares of the Manhattan L path a -> b"""
    L1 = abs(b[0] - a[0]) if xfirst else abs(b[1] - a[1]); tot = abs(b[0] - a[0]) + abs(b[1] - a[1]); out = []
    for m in range(1, k + 1):
        s = tot * m / (k + 1)
        if xfirst:
            p = (a[0] + (b[0] - a[0]) * min(s, L1) / max(L1, 1e-9), a[1] + (b[1] - a[1]) * max(s - L1, 0) / max(tot - L1, 1e-9))
        else:
            p = (a[0] + (b[0] - a[0]) * max(s - L1, 0) / max(tot - L1, 1e-9), a[1] + (b[1] - a[1]) * min(s, L1) / max(L1, 1e-9))
        out.append(snap(p))
    return out
NOTE = "S81-ARCH-RTL-2 a754fcbe5bd7f2b5d 11-11: approved +1 pin cycle (COORD 08:43 (2)); CPL-S81-SLICE-5 site"
st = t["internal_stations"]; add = 0; ext = 0
for bus in ("u", "u_i", "u_v", "um_b", "um_i", "um_q", "um_v"):
    assert not any(e["conn"] == f"core:u_lf.u_vs.{bus}|core:u_lf.u_vq" for e in st)
    a, n = centroid("u_lf.u_vs", bus); b, _ = centroid("u_lf.u_vq", bus)
    st.append(dict(conn=f"core:u_lf.u_vs.{bus}|core:u_lf.u_vq", from_um=a, to_um=b, regs_um=lpath(a, b, 1, xfirst=False), bits=n,
                   launch=f"core:u_lf.u_vs.{bus}", capture=f"u_lf.u_vq.{bus}", note=NOTE + " (CS_U_D 1)")); add += 1
for e in st:
    if e["conn"] == "bus:leafdn_i0" and e["capture"].startswith("u_lf.u_vs."):
        e["regs_um"] = lpath(e["from_um"], e["to_um"], 2, xfirst=True); e["note"] += " | " + NOTE + ": 1 -> 2 FIRM stations"; ext += 1
hop = lambda e: max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip([e["from_um"]] + e["regs_um"], e["regs_um"] + [e["to_um"]]))
print("vs->vq entries added", add, "leafdn->vs entries extended", ext, "max hop",
      round(max(hop(e) for e in st if NOTE in e["note"]), 1))
json.dump(P, open(pout, "w"))
