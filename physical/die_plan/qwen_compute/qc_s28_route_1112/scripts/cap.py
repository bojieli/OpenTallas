"""Seam capacity for the R1/R2 lanes: per column, per candidate seam into the ctl row, the length left when MY
lanes' ports are removed (corner margin = the base's own first-window offset, 0.96 guard between windows), vs the
window_for() lengths of my buses (M7/M5 on N/S seams, M6/M4 on E/W)."""
import sys, json
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/qc-s28-route/tools/die_plan")
import schema as S
raw = json.load(open(sys.argv[1])); P = S.Plan(raw)
OPP = {"E":"W","W":"E","N":"S","S":"N"}
MINE = ("__x_fw_ctl__", "__x_fw_ctl_p1__", "__x_fw_ctl_p2__", "__x_su_l1_ctl__")
G = 0.96; M = 4.32
def L(pins, lay=("M7","M5")):
    return S.window_for(0.0, pins, list(lay), P.layers, per_um=P.budgets["face_pins_per_um"], track_max=P.budgets["pin_track_max"])
need = {536: L(536), 456: L(456)}
print("window_for M7/M5: 536 ->", need[536], " 456 ->", need[456], " M6/M4 536 ->", L(536,("M6","M4")))
def ends(pr):
    f = pr["face"]; out = []
    if pr["src"]["part"] != "@die": out.append((pr["src"]["part"], f))
    if pr["dst"]["part"] != "@die": out.append((pr["dst"]["part"], OPP[f] if pr["src"]["part"] != "@die" else f))
    return out
idx = {}
for pid, pr in P.ports.items():
    for part, df in ends(pr): idx.setdefault((part, df), []).append(pid)
cols = [f"{s}{i}" for s in "EW" for i in range(6)]
seams = [("fw","st_a"),("stm","ctl"),("sc","ctl"),("fe","st_b"),("su_c","stm"),("su_l1","fw")]
rows = []
for c in cols:
    out = [c]
    for a, b in seams:
        pa, pb = f"sl_{c}_{a}", f"sl_{c}_{b}"
        ax0,ay0,ax1,ay1 = P.rect(pa); bx0,by0,bx1,by1 = P.rect(pb)
        if abs(ay1-by0) < .5: df = "N"; lo, hi = max(ax0,bx0), min(ax1,bx1)
        elif abs(ax1-bx0) < .5: df = "E"; lo, hi = max(ay0,by0), min(ay1,by1)
        else: out.append(f"{a}|{b} n/a"); continue
        allp = [pid for pid in idx.get((pa, df), []) if P.ports[pid]["dst"]["part"] == pb or P.ports[pid]["src"]["part"] == pb]
        allf = idx.get((pa, df), [])
        oth = [pid for pid in allf if not any(m in pid for m in MINE)]
        mine = [pid for pid in allf if any(m in pid for m in MINE)]
        # windows on the seam interval [lo,hi] only
        wl = sorted(tuple(sorted(P.ports[p]["window_um"])) for p in oth)
        wl = [w for w in wl if w[1] > lo and w[0] < hi]
        used = sum(w[1]-w[0] for w in wl) + G*len(wl)
        free = (hi - lo) - 2*M - used + G   # n windows + k mine need (n+k-1) guards
        pins_oth = sum(P.ports[p]["width"] for p in oth if lo <= sum(P.ports[p]["window_um"])/2 <= hi)
        out.append(f"{a}|{b}.{df} seam {hi-lo:.1f} oth {pins_oth}b used {used:.1f} free {free:.1f} mine[{','.join(p.split('__')[1]+'('+str(P.ports[p]['width'])+')' for p in mine)}]")
    rows.append(out)
for r in rows: print(" | ".join(r))
