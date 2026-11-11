#!/usr/bin/env python3
"""CPL-S81-SLICE-3 slice-C S-ring form: move u_cap/u_xr (hand-chosen) + legalise contents around them.
usage: legal.py BASE TYPES CAP=x,y XR=x,y OUT_DELTA [BANDS_JSON]
Contents that now conflict (gap<34.56 to a hard core, under a site point, in a landing band) move to the nearest
4.32-lattice site (Manhattan from the old origin) with gap>=34.56 to every hard core and every other content,
outside landing bands and site halos, inside [34.56, W-34.56] x [34.56, H-69.12]. Bottom-up, tallest first."""
import json, sys
base, types, capxy, xrxy, outp = sys.argv[1:6]
bands_new = json.load(open(sys.argv[6])) if len(sys.argv) > 6 else {}
P = json.load(open(base))["partition_types"]
G, L, E = 34.56, 4.32, 1e-6
import os
XMIN = float(os.environ.get("XMIN", "120.96"))  # movers stay out of the W-ring strip
FLOOR = float(os.environ.get("FLOOR", "371.52"))   # movers stay out of the S-ring strip and the cap|xr street
cap = [float(v) for v in capxy.split(",")]; xr = [float(v) for v in xrxy.split(",")]
def gapok(a, b, g=G):
    gx = max(b[0] - a[2], a[0] - b[2]); gy = max(b[1] - a[3], a[1] - b[3])
    return max(gx, gy) >= g - E
def box(o, s): return (o[0], o[1], o[0] + s[0], o[1] + s[1])
out, rep = {}, {}
for tn in types.split(","):
    t = P[tn]; W, H = t["outline_um"]
    newo = {"u_c.u_cap": cap, "u_c.u_xr": xr}
    hcb = [box(newo.get(h["inst"], h["origin_um"]), h["outline_um"]) for h in t["hard_cores"]]
    pts = []
    ck = t.get("clock") or {}
    if ck.get("tap_um"): pts.append(ck["tap_um"])
    pts += [tp["xy"] for tp in ck.get("taps", []) or [] if tp.get("kind") != "core"]
    for s in t.get("ft_slots") or []: pts += list(s.get("regs_um") or []) + [q for row in s.get("bit_sites_um") or [] for q in row]
    for s in t.get("internal_stations") or []: pts += list(s.get("regs_um") or [])
    bands = {k: v.get("rect_um") for k, v in ((ck.get("landing_contract") or {}).get("bands") or {}).items() if v.get("rect_um")}
    bands.update((bands_new.get(tn) or {}))
    keep = [tuple(r) for r in bands.values()] + [(p[0] - L, p[1] - L, p[0] + L, p[1] + L) for p in pts]
    KO = [tuple(map(float, k.split(','))) for k in os.environ.get('KEEPOUT', '').split(';') if k]   # mover-only keep-outs
    C = [e for e in t["contents"] if "origin_um" in e and "outline_um" in e and e.get("lef")]
    def bad(b, others):
        if b[0] < 34.56 - E or b[1] < 34.56 - E or b[2] > W - 34.56 + E or b[3] > H - 69.12 + E: return "edge"
        if any(not gapok(b, h, G + 0.2) for h in hcb): return "hard"
        if any(b[0] < k[2] and b[2] > k[0] and b[1] < k[3] and b[3] > k[1] for k in keep): return "site/band"
        return None
    # base-only edge findings are inherited: judge 'edge' only for movers
    mov = []
    for e in C:
        b = box(e["origin_um"], e["outline_um"])
        r = bad(b, None)
        if not r and any(b[0] < k[2] and b[2] > k[0] and b[1] < k[3] and b[3] > k[1] for k in KO): r = 'xr_street'
        if r and r != "edge": mov.append((e, r))
    stay = [box(e["origin_um"], e["outline_um"]) for e in C if e not in [m[0] for m in mov]]
    placed, failed = {}, []
    for e, why in sorted(mov, key=lambda m: (-m[0]["outline_um"][1], m[0]["origin_um"][1])):
        w, h = e["outline_um"]; ox, oy = e["origin_um"]
        best = None
        fy = round(oy - round(oy / L) * L, 3)   # keep the content's y phase
        x = XMIN
        while x + w <= W - 34.56 + E:
            y = FLOOR + fy
            while y + h <= H - 69.12 + E:
                d = abs(x - ox) + abs(y - oy)
                if best is None or d < best[0]:
                    b = (x, y, x + w, y + h)
                    if not bad(b, None) and all(gapok(b, s) for s in stay) and not any(b[0] < k[2] and b[2] > k[0] and b[1] < k[3] and b[3] > k[1] for k in KO):
                        best = (d, x, y)
                y = round(y + L, 3)
            x = round(x + L, 3)
        if best is None: failed.append(e["inst"]); continue
        d, x, y = best
        stay.append((x, y, x + w, y + h)); placed[e["inst"]] = [round(x, 3), round(y, 3), e.get("orient", "R0"), why, round(d, 1)]
    out[tn] = {"u_c.u_cap": [cap[0], cap[1], "R0"], "u_c.u_xr": [xr[0], xr[1], "R0"]}
    out[tn].update({i: v[:3] for i, v in placed.items()})
    rep[tn] = dict(moved=len(placed), failed=failed, max_d=max([v[4] for v in placed.values()] or [0]),
                   moves={i.split(".u_s.")[-1]: v[3:] for i, v in placed.items()})
    print(tn, "contents moved", len(placed), "failed", len(failed), "max_d", rep[tn]["max_d"], "sum_d", round(sum(v[4] for v in placed.values())))
json.dump(out, open(outp, "w"), indent=1)
json.dump(rep, open(outp.replace(".json", "_rep.json"), "w"), indent=1)
