#!/usr/bin/env python3
"""PATH-KV-GRT2 10-25: bit-level channel water-fill of the W hgi column N-S feedthrough buses (KV die GRT0 fix).

Cause (GRT0 9e120c34f3 / GRT1 29bbfd2957): the W hgi column (hub_Wi -> hgi_WN_7..0 -> io_W3) carries 3,390 b of
pass-through N-S buses (L663 1044, L350 552, L751 549, L1524 548, L2048 523, L354 174) in whole-bus windows; c2 (L663)
and c3 (L751+L2048) need 1.10 / 1.13 of the die-share channel capacity (9.11 b/um), while c0/c4 run at 0.25 / 0.70.
With head cores blocking M1-M7 the 4 core-free channels are the only N-S passage, and no whole-bus assignment fits
(GRT1: best 1.13).  Here every bit keeps ONE x through the whole column (no jog), and the bits are water-filled over
the channels' free mouths so every channel carries the same share (column total 3,461 b / 3,779 b = 0.916).
Each port gets subwindows_um [lo, hi, nbits] (schema, PATH-KV-GRT2) -- same buses, lanes, stations and RTL.
usage: post_grt2_wf.py IN_PLAN OUT_PLAN --report R.json"""
import json, sys, collections, argparse
ap = argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("--report")
ap.add_argument("--order", default="L350,L354,L663,L751,L2048,L1524"); ap.add_argument("--margin", type=float, default=1.0)
ap.add_argument("--drop", default="", help="lanes re-pathed out of the column (their windows do not block)")
a = ap.parse_args()
d = json.load(open(a.inp))
ORDER = a.order.split(",")
X0, CAP = 3179.52, 0.25 * (1 / 0.048 + 1 / 0.064)
CH = [(0, 17.28), (233.28, 336.96), (552.96, 656.64), (872.64, 976.32), (1192.32, 1278.72)]
COL = {f"hgi_WN_{r}" for r in range(8)} | {"hub_Wi", "io_W3"}
L = {l["id"]: l for l in d["lanes"]}; P = {p["id"]: p for p in d["ports"]}
lane_of = {p: l["id"] for l in d["lanes"] for p in l["ports"]}
mov = [pid for lid in ORDER for pid in L[lid]["ports"] if P[pid]["face"] in "NS"
       and P[pid]["src"]["part"] in COL and P[pid]["dst"]["part"] in COL]
import schema as _S
npins = _S.port_pins_count
width = {lid: max(npins(P[pid]) for pid in mov if lane_of[pid] == lid) for lid in ORDER}
DROP = set(a.drop.split(",")) if a.drop else set()
# fixed N/S windows of other ports on any boundary of the column (hgi rows, hub_Wi N, io_W3 S), relative x
fixed = [[] for _ in CH]; fixed_bits_row = [0] * len(CH)
for pr in d["ports"]:
    if lane_of.get(pr["id"]) in ORDER or lane_of.get(pr["id"]) in DROP or pr.get("face") not in ("N", "S") or "window_um" not in pr: continue
    ends = {pr["src"]["part"], pr["dst"]["part"]}
    if not ends <= COL or not ends & {f"hgi_WN_{r}" for r in range(8)}: continue
    lo, hi = sorted(pr["window_um"]); lo -= X0; hi -= X0
    for k, (u, v) in enumerate(CH):
        if lo < v and hi > u:
            fixed[k].append((lo, hi))
            if ends == {"hgi_WN_3", "hgi_WN_4"}: fixed_bits_row[k] += pr["width"]
def free(k):
    u, v = CH[k]; cur, out = u + a.margin, []
    for lo, hi in sorted(fixed[k]):
        if lo - 0.3 > cur: out.append((cur, lo - 0.3))
        cur = max(cur, hi + 0.3)
    if v - a.margin > cur: out.append((cur, v - a.margin))
    return [iv for iv in out if iv[1] - iv[0] > 2.0]
tot = sum(width.values())
lo, hi = 0.0, 2.0
for _ in range(60):
    u = (lo + hi) / 2
    room = sum(max(0, (v - w) * CAP * u - f) for (w, v), f in zip(CH, fixed_bits_row))
    lo, hi = (u, hi) if room < tot else (lo, u)
rooms = [max(0, (v - w) * CAP * hi - f) for (w, v), f in zip(CH, fixed_bits_row)]
# integer rooms summing to tot
ri = [int(r) for r in rooms]; ri[max(range(len(ri)), key=lambda k: rooms[k] - ri[k])] += tot - sum(ri)
while sum(ri) != tot:
    k = max(range(len(ri)), key=lambda k: rooms[k] - ri[k]); ri[k] += 1 if sum(ri) < tot else -1
# sequential fill: lane bits -> (channel, count) pieces
pieces = collections.defaultdict(list); k, used = 0, 0
for lid in ORDER:
    left = width[lid]
    while left:
        while ri[k] - used == 0: k, used = k + 1, 0
        n = min(left, ri[k] - used); pieces[lid].append([k, used, n]); used += n; left -= n
# sub-window per piece: the channel's bits spread uniformly over the concatenated free mouth intervals
def piece_windows(k, off, n):
    F = free(k); Lk = sum(b - a_ for a_, b in F); res = []
    cuts = [0.0]
    for a_, b in F: cuts.append(cuts[-1] + (b - a_))
    # bit t of the channel -> centre s=(t+0.5)*Lk/ri; count bits per interval
    cnt = [0] * len(F)
    for t in range(off, off + n):
        s_ = (t + 0.5) * Lk / ri[k]
        j = max(i for i in range(len(F)) if cuts[i] <= s_ + 1e-9) if s_ < Lk else len(F) - 1
        cnt[min(j, len(F) - 1)] += 1
    t = off
    for j, (a_, b) in enumerate(F):
        if not cnt[j]: continue
        s0 = max(cuts[j], t * Lk / ri[k]); s1 = min(cuts[j + 1], (t + cnt[j]) * Lk / ri[k])
        res.append([round(a_ + s0 - cuts[j] + X0, 4), round(a_ + s1 - cuts[j] + X0, 4), cnt[j]]); t += cnt[j]
    return res
sub = {lid: [w for k, off, n in pl for w in piece_windows(k, off, n)] for lid, pl in pieces.items()}
for pid in mov:
    pr = P[pid]; s = [list(x) for x in sub[lane_of[pid]]]
    s[-1][2] -= width[lane_of[pid]] - npins(pr)     # a port without the epoch pin: one bit fewer in the last piece
    if pr.get("order", "lsb_low") != "lsb_low": raise SystemExit(f"{pid}: lsb_high not handled")
    pr["window_um"] = [min(x[0] for x in s), max(x[1] for x in s)]
    if len(s) > 1: pr["subwindows_um"] = s
    else: pr.pop("subwindows_um", None)
d["note"] += (" | v3.9w (PATH-KV-GRT2 10-25): W hgi column N-S ft buses " + ",".join(ORDER) +
              " water-filled at bit level over the core-free channels (subwindows_um), every bit straight through "
              "hub_Wi -> hgi_WN_7..0 -> io_W3; channel share %.3f of the die-share capacity" % hi)
open(a.out, "w").write(json.dumps(d, indent=1) + "\n")
rep = dict(u=round(hi, 3), rooms=ri, fixed_row_bits=fixed_bits_row, free_mouths=[free(k) for k in range(len(CH))], drop=sorted(DROP),
           util=[round((ri[k] + fixed_bits_row[k]) / ((CH[k][1] - CH[k][0]) * CAP), 3) for k in range(len(CH))],
           density_b_per_um={lid: [round(n / (b - a_), 2) for a_, b, n in s] for lid, s in sub.items()},
           subwindows=sub, ports_changed=len(mov))
if a.report: json.dump(rep, open(a.report, "w"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "subwindows"}))
