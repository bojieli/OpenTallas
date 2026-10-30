import sys, json, re
from pathlib import Path
sys.path.insert(0, sys.argv[1]); import geom_rules as G, numpy as np
geom, kit = sys.argv[2], Path(sys.argv[3])
D = G.Design(geom)
ck = G.clock_metrics(D)
lr = G.land_ring_captures(D, json.loads((kit/"land_slots.json").read_text()), json.loads((kit/"face_guard.json").read_text()))
caps = lr["caps"]
# full distance list (copy of pin_reg_metrics, collecting all)
import collections
m = G.pin_reg_metrics(D, re.compile(G.STRAP_RE_DEFAULT), frozenset(ck["tap_sinks"]) | frozenset(lr["clock_exports"]), caps)
print({k: m[k] for k in ("pins_registered","pin_reg_p50","pin_reg_p90","pin_reg_max","pins_land_ring","pins_unregistered")})
# distances of land ring pins
P = {p["name"]: p for p in D.pins}
dl = sorted(((max(abs(x-P[n]["x"])+abs(y-P[n]["y"]) for x,y in (G.ctr(D.cells[c]) for c in cs)), n) for n, cs in caps.items()), reverse=True)
print("land pins", len(dl), "n>=30:", sum(d>=30 for d,_ in dl), "n>=80:", sum(d>=80 for d,_ in dl), dl[:3], dl[len(dl)//2])
print("slots per ring pin", collections.Counter(len(v) for v in caps.values()).most_common(3))
# sinks
S = np.array([G.ctr(c) for cid, c in D.cells.items() if c[0]=="S" and any(isc for _, isc in D.cell_in.get(cid, []))])
print("sinks", len(S), "bbox", S.min(0).round(1), S.max(0).round(1))
def reach(E):
    E=np.array(E); d=np.abs(S[:,None,0]-E[None,:,0])+np.abs(S[:,None,1]-E[None,:,1]); a=d.argmin(1); b=d.min(1)
    return float(b.max()), np.bincount(a, minlength=len(E))
# equal-count recursive bisection into 2^k groups; entry at L1 median of group
def bisect(idx, k, box):
    if k == 0: return [idx]
    pts = S[idx]; w = np.ptp(pts[:,0]); h = np.ptp(pts[:,1])
    ax = 0 if w >= h else 1
    o = idx[np.argsort(pts[:,ax], kind="stable")]; half = len(o)//2
    return bisect(o[:half], k-1, box) + bisect(o[half:], k-1, box)
for k, label in ((4,"16 equal-count bisection"),):
    G_ = bisect(np.arange(len(S)), k, None)
    E = [tuple(np.median(S[g],0)) for g in G_]
    own = max(float((np.abs(S[g,0]-e[0])+np.abs(S[g,1]-e[1])).max()) for g,e in zip(G_,E))
    r, cnt = reach(E)
    print(label, "own-group max", round(own,1), "nearest-entry max", round(r,1), "loads", cnt.min(), cnt.max())
    print([tuple(round(v,1) for v in e) for e in E])
# 12 = 3x4-ish: bisection to 12 via 4 then 3 splits
def ksplit(idx, n):
    if n == 1: return [idx]
    pts=S[idx]; ax = 0 if np.ptp(pts[:,0]) >= np.ptp(pts[:,1]) else 1
    o = idx[np.argsort(pts[:,ax], kind="stable")]
    a = n//2; cut = len(o)*a//n
    return ksplit(o[:cut], a) + ksplit(o[cut:], n-a)
for n in (12, 14, 16, 20):
    G_ = ksplit(np.arange(len(S)), n); E=[tuple(np.median(S[g],0)) for g in G_]
    own = max(float((np.abs(S[g,0]-e[0])+np.abs(S[g,1]-e[1])).max()) for g,e in zip(G_,E))
    r,cnt=reach(E); print(n, "equal-count split: own max", round(own,1), "nearest max", round(r,1), "loads", cnt.min(), cnt.max())
for n in ("cland_dn_fault_i","cland_dn_ready_i","i[564]"):
    print(n, (P[n]["x"],P[n]["y"]), [(D.cells[c][6], tuple(round(v,1) for v in G.ctr(D.cells[c]))) for c in caps[n]])
