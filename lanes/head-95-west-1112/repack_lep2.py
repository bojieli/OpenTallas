#!/usr/bin/env python3
"""repack_lep2.py BASE OUT : HEAD-95 hd_lep0N re-pack v2 (no growth, no die move), GEOM-VIS-5 06:49 C1-C4 applied.
Every moved macro sits ON the plan lattice: origin on 8.64, track_offset = base [0.108, 0.012] (+4.32 when the
4.32-um half step is used), so pins stay on the 0.048 track phase of the base plan and no snap pass is needed later.
Rows: tx N row abuts g_pp[1]/g_pp[0] (gap 1.07), S row abuts g_pp[2]/g_pp[3] (gap 0.01); pitch 172.8 (abut 3.4);
each row split 5+5 with an 81-um gap on the vertical street (C2), 43-um W/E outline streets (W/E face bus windows).
Bank groups face their own pair: N row W = g_tx[1] (g_pp[1] NW), N row E = g_tx[0] (NE), S row W = g_tx[2] (SW),
S row E = g_tx[3] (SE).  rx: two stacks of 10 abutting the W pair column (top = g_rx[0..1], bottom = g_rx[2..3]),
pitch 21.6.  Landing srams: E strip, abutting the pairs, pitch 43.2."""
import copy, json, sys
B = json.load(open(sys.argv[1])); P = copy.deepcopy(B)
t = P["partition_types"]["hd_lep0N"]; hc = t["hard_cores"]
g = lambda pat: sorted([h for h in hc if pat in h["inst"]], key=lambda h: h["inst"])
tx = {i: g(f".g_tx[{i}].") for i in range(4)}; rx = {i: g(f".g_rx[{i}].") for i in range(4)}; sr = g("g_sram")
LAT, HALF = 8.64, 4.32; BASE = (0.108, 0.012); log = []
def put(h, X, Y):
    """X, Y = lattice-equivalent origin on the 4.32 grid; actual box at X+0.108, Y+0.012"""
    assert abs(X / HALF - round(X / HALF)) < 1e-6 and abs(Y / HALF - round(Y / HALF)) < 1e-6, (X, Y)
    # written FLAT (origin = placed box, offset 0) because street_rule / core_place read origin_um only; the
    # geometry-identical lattice encoding (origin on 8.64 + offset) is applied after the reset fix by encode_lat.py
    old = h["origin_um"]; h["origin_um"] = [round(X + BASE[0], 3), round(Y + BASE[1], 3)]
    h["track_offset_um"] = [0.0, 0.0]
    log.append(f"{h['inst']} {old} -> {h['origin_um']} +{h['track_offset_um']}")
P_TX = 172.8; XW, XE = 43.2, 984.96; YN, YS = 635.04, 509.76
for row, (Y, w, e) in {"N": (YN, 1, 0), "S": (YS, 2, 3)}.items():
    for k in range(5):
        put(tx[w][k], XW + k * P_TX, Y); put(tx[e][k], XE + k * P_TX, Y)
P_RX = 21.6
for k, h in enumerate(rx[0] + rx[1]): put(h, 846.72, 665.28 + k * P_RX)
for k, h in enumerate(rx[2] + rx[3]): put(h, 846.72, 77.76 + k * P_RX)
for i in range(2): put(sr[i], 1745.28, 4.32 + i * 43.2)   # kit core area is the outline inset by 4.32 (MPL-0034)
for i in range(3): put(sr[2 + i], 1745.28, 950.4 + i * 43.2)
def rect(h):
    x, y = h["origin_um"]; dx, dy = h.get("track_offset_um", [0, 0]); w, hh = h["outline_um"]
    return x + dx, y + dy, x + dx + w, y + dy + hh
R = [rect(h) for h in hc]; RM = [rect(h) for h in hc if "g_pp" not in h["inst"]]
def blocked(x, y, halo=8.65, rs=None):
    return [r for r in (RM if rs is None else rs) if r[0] - halo < x < r[2] + halo and r[1] - halo < y < r[3] + halo]
CORE = (4.32, 4.32, t["outline_um"][0] - 4.32, t["outline_um"][1] - 4.32)
for r in R:
    if r[0] < CORE[0] - 1e-6 or r[1] < CORE[1] - 1e-6 or r[2] > CORE[2] + 1e-6 or r[3] > CORE[3] + 1e-6:
        log.append(f"OUTSIDE-CORE {r}")
for a, b in [(a, b) for i, a in enumerate(R) for b in R[i + 1:]]:
    if a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
        log.append(f"OVERLAP {a} {b}")
lt = t["reset"]["local_taps_um"]
for i, (x, y) in enumerate(list(lt)):
    b = blocked(x, y)
    if not b: continue
    cands = sorted([(abs(c - y), c) for r in b for c in (r[1] - 8.64, r[3] + 8.64)])
    for _, ny in cands:
        ny = round(round(ny / HALF) * HALF, 3)
        if not blocked(x, ny) and not blocked(x, ny, 2.16, R) and 8.64 < ny < t["outline_um"][1] - 8.64:
            lt[i] = [x, ny]; log.append(f"reset local tap {[x, y]} -> {lt[i]}"); break
    else:
        log.append(f"UNRESOLVED reset local tap {[x, y]}")
# C3 (GEOM-VIS-5 06:49): a pair-core clock tap (kind core, the early CTS tap of the pair's M5 clk pin on its K face)
# that a tx row covers moves straight across the row into the centre logic street, 8.64 um clear of the row
# (x kept; the M5 run to the pin passes over the SRAM, whose OBS stops at M4)
import os
for tp in ([] if os.environ.get("NO_C3") else t["clock"].get("taps", [])):
    x, y = tp["xy"]; b = blocked(x, y, halo=0.0, rs=R)
    if not b: continue
    r = b[0]; ny = r[1] - 8.64 if y > 587.52 else r[3] + 8.64
    ny = round(round(ny / 0.048) * 0.048 + 0.0, 3)
    if blocked(x, ny, 8.64): log.append(f"UNRESOLVED clock core tap {tp['name']} {tp['xy']}"); continue
    tp["xy"] = [x, ny]
    log.append(f"clock core tap {tp['name']} {[x, y]} -> {tp['xy']}")
# GEOM-VIS-6 07:44: landing bands (cland flop regions) must be macro-free.  A band that a moved tx row overlaps is
# trimmed on the row side (y edge) to 8.64 um clear of the row; the band keeps its bus-window side and must keep
# area >= its area_reserve_um2, else it is reported (no silent loss)
for k, b in t["clock"]["landing_contract"]["bands"].items():
    x0, y0, x1, y1 = b["rect_um"]
    for r in RM:
        if r[0] - 8.64 < x1 and x0 < r[2] + 8.64 and r[1] - 8.64 < y1 and y0 < r[3] + 8.64:
            up, dn = (r[3] + 8.64) - y0, y1 - (r[1] - 8.64)     # trim from below / from above
            if up <= dn: y0 = round(r[3] + 8.64, 4)
            else: y1 = round(r[1] - 8.64, 4)
    if [x0, y0, x1, y1] != b["rect_um"]:
        a = (x1 - x0) * (y1 - y0)
        ok = y1 > y0 and a >= b.get("area_reserve_um2", 0)
        log.append(f"{'' if ok else 'UNRESOLVED '}landing band {k} {b['rect_um']} -> {[x0, y0, x1, y1]} area {a:.0f} >= reserve {b.get('area_reserve_um2')}")
        if ok: b["rect_um"] = [x0, y0, x1, y1]
import os
if os.environ.get("RESET_CANON"):
    # the type is re-placed, so the frozen-plan 'lef_origin' reset obstacle model (origin only, no track offset) no
    # longer reproduces anything; the canonical model (placement_boxes, offsets applied) matches clock / G0 / gen
    if t["reset"].pop("obstacle_model", None): log.append("reset.obstacle_model lef_origin -> canonical")
json.dump(P, open(sys.argv[2], "w"), indent=1)
print("\n".join(l for l in log if not l.startswith("u_core"))); print("moved", sum(l.startswith("u_core") for l in log))
