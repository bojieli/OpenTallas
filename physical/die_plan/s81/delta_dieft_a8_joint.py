"""PATH-S81 2026-10-25 a8 FT fix, step 1 of 2 (joint column-aligned seam re-lay). Base plan = main die_plan.json 80d089d7.
Run: python3 physical/die_plan/s81/delta_dieft_a8_joint.py <main plan> <out plan>; then delta_dieft_a8_repack.py; then gen.py latency --inplace."""
import json, sys, re, collections
from pathlib import Path
S = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(S / "physical/die_plan/s81"), str(S), str(S / "tools/die_plan")]
import delta_dieft_1713 as D, compact_plan
raw = json.loads(Path(sys.argv[1]).read_text())
import os
SCOPE = os.environ.get("A8_SCOPE", "L1")      # L1 = Codex seams (an L1 side); SLICE = every seam between two s_* partitions
if SCOPE == "SLICE":
    def _seams(raw):
        PA = {p["name"]: p for p in raw["partitions"]}
        Sx = collections.defaultdict(list)
        for pr in raw["ports"]:
            a, b = pr["src"]["part"], pr["dst"]["part"]
            if a not in PA or b not in PA or "window_um" not in pr: continue
            if not (a.startswith("s_") and b.startswith("s_")): continue
            if PA[a].get("orient", "R0") not in ("R0", "MY") or PA[b].get("orient", "R0") not in ("R0", "MY"): continue
            Sx[(a, b, pr["face"]) if a < b else (b, a, D.OPP[pr["face"]])].append(pr)
        return PA, Sx
    D.seams = _seams
T = raw["partition_types"]
PA, Sm = D.seams(raw)
GAP = 3.072
# --- Codex skip logic (type consistency) ---
inst = collections.defaultdict(list)
for p in raw["partitions"]: inst[p["type"]].append(p["name"])
seam_parts = set()
for (a, b, f) in Sm: seam_parts |= {(a, f), (b, D.OPP[f])}
for key in list(Sm):
    a, b, f = key; ok = True
    for part, df in ((a, f), (b, D.OPP[f])):
        tf = D.tface(PA[part], df)
        for other in inst[PA[part]["type"]]:
            if other == part: continue
            odf = {"E": "W", "W": "E"}.get(tf, tf) if PA[other].get("orient", "R0") == "MY" else tf
            if (other, odf) not in seam_parts: ok = False
    if not ok: del Sm[key]
P = {pr["id"]: pr for pr in raw["ports"]}
seam_of, seam_info = {}, {}
for key, prs in Sm.items():
    a, b, f = key
    ra, rb = D.rect(T, PA[a]), D.rect(T, PA[b])
    s0, s1 = (max(ra[0], rb[0]), min(ra[2], rb[2])) if f in "NS" else (max(ra[1], rb[1]), min(ra[3], rb[3]))
    fixed = {}
    for pr in prs:
        seam_of[pr["id"]] = key
        for side in ("src", "dst"):
            ep = pr[side]
            if re.search(r"_L[0-4]$", ep["part"]) and any(bb["name"] == ep["bus"] for bb in T[PA[ep["part"]]["type"]].get("buses", [])):
                fixed[pr["id"]] = sorted(pr["window_um"])
    nb = {pr["id"]: -(-(int(pr["width"]) + 1) // len(pr["layers"])) for pr in prs}
    holes = [[s0 + D.MARGIN, s1 - D.MARGIN]]
    for lo, hi in sorted(fixed.values()):
        rest = []
        for x, y in holes:
            if lo - GAP / 2 > x: rest.append([x, min(y, lo - GAP / 2)])
            if hi + GAP / 2 < y: rest.append([max(x, hi + GAP / 2), y])
        holes = [h for h in rest if h[1] - h[0] > 1e-6]
    moving = [pr["id"] for pr in prs if pr["id"] not in fixed]
    tot = sum(nb[i] for i in moving) or 1
    upper = D.FILL * sum(y - x for x, y in holes) / tot
    lower = max([len(P[i]["layers"]) for i in moving] or [1]) / 5.8
    seam_info[key] = dict(holes=holes, fixed=fixed, nb=nb, upper=upper, lower=lower, ori="NS" if f in "NS" else "EW")
# --- chains ---
by_src = {(pr["src"]["part"], pr["src"]["bus"]): pr for pr in raw["ports"]}
nxt = {}
for pr in raw["ports"]:
    p, b = pr["dst"]["part"], pr["dst"]["bus"]
    if b.endswith("_i"):
        q = by_src.get((p, b[:-2] + "_o"))
        if q: nxt[pr["id"]] = q["id"]
prev = {v: k for k, v in nxt.items()}
groups = []
for pid in P:
    if pid in prev: continue
    c = [pid]
    while c[-1] in nxt and nxt[c[-1]] not in c: c.append(nxt[c[-1]])
    for ori in ("NS", "EW"):
        g = [x for x in c if x in seam_of and seam_info[seam_of[x]]["ori"] == ori and x not in seam_info[seam_of[x]]["fixed"]]
        if g: groups.append(g)
# --- coupling: (type, bus) shared by several instances -> type-frame equality ---
tb_ports = collections.defaultdict(list)     # (type,bus) -> [(port id, part, die face)]
for pid in seam_of:
    pr = P[pid]
    for side in ("src", "dst"):
        part = pr[side]["part"]; df = pr["face"] if side == "src" else D.OPP[pr["face"]]
        ref, _ = D.type_win_ref(T[PA[part]["type"]], pr[side]["bus"])
        if ref is not None: tb_ports[(PA[part]["type"], pr[side]["bus"])].append((pid, part, df))
coupled = {k: v for k, v in tb_ports.items() if len({x[0] for x in v}) > 1}

FAIL, SPLIT, NEAR, LAST = [], [], [], [None]
def attempt(f):
    FAIL.clear(); SPLIT.clear(); NEAR.clear()
    free = {k: [list(h) for h in v["holes"]] for k, v in seam_info.items()}
    win = {}
    def nearest(key, lo, hi):
        L_ = hi - lo; c0 = (lo + hi) / 2
        ch = [min(max(c0, a + L_ / 2), b - L_ / 2) for a, b in free[key] if b - a >= L_ - 1e-9]
        if not ch: return None
        c = min(ch, key=lambda v: abs(v - c0)); NEAR.append(abs(c - c0))
        return round(c - L_ / 2, 3), round(c + L_ / 2, 3)
    def take(key, lo, hi, retry=True):
        fl = free[key]
        for j, (x, y) in enumerate(fl):
            if x - 1e-6 <= lo and hi <= y + 1e-6:
                fl.pop(j)
                if lo - GAP / 2 > x: fl.append([x, lo - GAP / 2])
                if hi + GAP / 2 < y: fl.append([hi + GAP / 2, y])
                return True
        if retry:
            nw = nearest(key, lo, hi)
            if nw and take(key, *nw, retry=False):
                LAST[0] = nw; return True
        return False
    order = sorted(groups, key=lambda g: (-len(g), -int(P[g[0]]["width"])))
    for g in order:
        pre = [win[x] for x in g if x in win]
        L = {x: max(2.0, seam_info[seam_of[x]]["nb"][x] * max(seam_info[seam_of[x]]["lower"], seam_info[seam_of[x]]["upper"] * f)) for x in g}
        todo = [x for x in g if x not in win]
        if not todo: continue
        if pre:
            c = sum(pre[0]) / 2
        else:
            target = sum(sum(P[x]["window_um"]) / 2 for x in g) / len(g)
            # feasible centres = intersection over the group's seams of [x+L/2, y-L/2]
            feas = None
            for x in todo:
                iv = [(a + L[x] / 2, b - L[x] / 2) for a, b in free[seam_of[x]] if b - a >= L[x] - 1e-9]
                if feas is None: feas = iv
                else:
                    feas = [(max(a, c_), min(b, d)) for a, b in feas for c_, d in iv if max(a, c_) <= min(b, d)]
            if not feas:
                # no common hole across the whole column: split the group into maximal runs with a common hole
                runs, cur, cf = [], [], None
                for x in todo:
                    iv = [(a + L[x] / 2, b - L[x] / 2) for a, b in free[seam_of[x]] if b - a >= L[x] - 1e-9]
                    nf = iv if cf is None else [(max(a, c_), min(b, d)) for a, b in cf for c_, d in iv if max(a, c_) <= min(b, d)]
                    if nf: cur.append(x); cf = nf
                    else:
                        if not cur: FAIL.append(("nohole", x)); return None
                        runs.append((cur, cf)); cur, cf = [x], iv
                        if not iv: FAIL.append(("nohole", x)); return None
                runs.append((cur, cf)); SPLIT.append(len(runs))
                for run, rf in runs:
                    t2 = sum(sum(P[x]["window_um"]) / 2 for x in run) / len(run)
                    c2 = min((min(max(t2, a), b) for a, b in rf), key=lambda v: abs(v - t2))
                    for x in run:
                        lo, hi = round(c2 - L[x] / 2, 3), round(c2 + L[x] / 2, 3)
                        LAST[0] = (lo, hi)
                        if not take(seam_of[x], lo, hi): FAIL.append(("take", x)); return None
                        lo, hi = LAST[0]; win[x] = [lo, hi]
                        if not prop(x, lo, hi, take, win): return None
                continue
            c = min((min(max(target, a), b) for a, b in feas), key=lambda v: abs(v - target))
        for x in todo:
            lo, hi = round(c - L[x] / 2, 3), round(c + L[x] / 2, 3)
            LAST[0] = (lo, hi)
            if not take(seam_of[x], lo, hi): FAIL.append(("take", x)); return None
            lo, hi = LAST[0]; win[x] = [lo, hi]
            if not prop(x, lo, hi, take, win): return None
    return win

def prop(x, lo, hi, take, win):
    pr = P[x]
    for side in ("src", "dst"):
        part = pr[side]["part"]; df = pr["face"] if side == "src" else D.OPP[pr["face"]]
        k = (PA[part]["type"], pr[side]["bus"])
        if k not in coupled: continue
        tw = D.to_type(T, PA[part], df, lo, hi)
        for (y, opart, odf) in coupled[k]:
            if y == x or y in win: continue
            dw = sorted(D.from_type(T, PA[opart], odf, *tw))
            if not take(seam_of[y], *dw, retry=False): FAIL.append(("couple", y)); return False
            win[y] = dw
    return True

best = None
for step in range(0, 101):
    f = 1.0 - step * 0.01
    w = attempt(f)
    if w is not None:
        best = (f, w); break
if best is None: sys.exit(f"A8 no packing; last fail {FAIL[-3:]}")
f, win = best
for pid, w in win.items():
    lo, hi = sorted(P[pid]["window_um"])
    P[pid]["window_um"] = w if P[pid]["window_um"][0] <= P[pid]["window_um"][1] else w[::-1]
# write type windows through Codex relay() with anchored_layout returning the precomputed (now current) windows
D.anchored_layout = lambda items, span, fixed, preferred: [preferred[pr["id"]] for pr, n in items]
rep, changed = D.relay(raw)
Path(sys.argv[2]).write_text(compact_plan.dumps(raw))
lat = 0
for g in groups:
    xs = [sum(win[x]) / 2 for x in g if x in win]
    lat += sum(abs(a - b) for a, b in zip(xs, xs[1:])) * int(P[g[0]]["width"])
print(f"A8 relocated {len(NEAR)} (max {max(NEAR or [0]):.0f} um) split groups {len(SPLIT)} f={f:.2f} groups {len(groups)} placed ports {len(win)} changed types {len(changed)} residual chain lateral {lat/1e6:.2f} M bit-um")
json.dump(dict(f=f, rep=rep, changed=sorted(changed)), open(sys.argv[2] + ".report.json", "w"), indent=1)
