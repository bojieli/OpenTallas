#!/usr/bin/env python3
"""HBM-R16/C17 (b): pin6 face capacity (5.5 pins/um over L - 2*8.64, pincap.py) per core pin table, and the minimal
structural fix per over face: (i) RE-SPREAD whole port groups to another face where EVERY instance of the master has
cos > 0 toward that port's partners (type frame, orient applied) and the destination stays <= cap; (ii) else GROW the
side carrying the face to n/5.5 + 17.28 um, with a lot check (grown rect, both growth directions, vs the type outline
and every other hard core / placed content of each instance's type).
usage: respread.py PLANDIR REPORT.json [--apply OUTPLANDIR]   (apply = (i) only, into a copy; never the basis)"""
import sys, json, re, math, collections, shutil
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan")
import check as C, schema as S
pd = Path(sys.argv[1]).resolve(); outp = sys.argv[2]
apply_to = Path(sys.argv[sys.argv.index("--apply") + 1]).resolve() if "--apply" in sys.argv else None
CAP, END, PITCH, OFF, INSET = 5.5, 8.64, 0.048, 0.024, 0.019
LAYER = dict(W="M4", E="M4", N="M5", S="M5")
raw = json.loads((pd / "die_plan.json").read_text()); T = raw["partition_types"]
P = S.Plan(raw, pd / "die_plan.json")
last = {}; o_bf = C.best_face
def bf(d): last["d"] = list(d); return o_bf(d)
class Rep(C.Report):
    def err(self, check, msg, **kw):
        super().err(check, msg, **kw); self.items[-1]["dirs"] = last.get("d")
C.best_face = bf; C.FACE_WARN_COS = C.FACE_AWAY_COS = 1e9
R = Rep(True); C.check_core_faces(P, R, str(pd), None, max_msgs=10**9)
MSG = re.compile(r"type (\S+) core (\S+) port (\S+): (\d+) pins on face")
D = {}
for i in R.errors():
    m = MSG.match(i["msg"])
    if m and i.get("dirs"): D[(m.group(1), m.group(2), m.group(3))] = [(d[1], d[2]) for d in i["dirs"]]
OPP = dict(N="S", S="N", E="W", W="E")
def tface(o, f):
    if o in ("MX", "R180") and f in "NS": f = OPP[f]
    if o in ("MY", "R180") and f in "EW": f = OPP[f]
    return f
def sc(o, F, dirs):
    nx, ny = C._NORMAL[tface(o, F)]; return max(nx * x + ny * y for x, y in dirs)
def pname(p): return p.get("name") or (p["bus"] + ("" if p.get("bit") is None else f"[{p['bit']}]"))
def gbase(n): return re.sub(r"\[\d+\]$", "", n)
def lface(x, y, w, h): return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]
def place(ps, w, hh, lf, src, exclude):
    L = hh if lf in "WE" else w
    onf = [p for p in ps if lface(p["x"], p["y"], w, hh) == lf and gbase(pname(p)) not in exclude]
    used = {round(((p["y"] if lf in "WE" else p["x"]) - OFF) / PITCH) for p in onf}
    lo = int(math.ceil((END - OFF) / PITCH - 1e-9)); hi = int(math.floor((L - END - OFF) / PITCH + 1e-9))
    free = sorted((k for k in range(lo, hi + 1) if k not in used), key=lambda k: (abs(k - (lo + hi) / 2), k))
    taken = set(used); pick = []
    for k in free:
        if len(pick) == len(src): break
        if k - 1 not in taken and k + 1 not in taken: pick.append(k); taken.add(k)
    for k in free:
        if len(pick) == len(src): break
        if k not in taken: pick.append(k); taken.add(k)
    if len(pick) < len(src): return None
    pick.sort(); res = []
    for p, k in zip(sorted(src, key=lambda p: (len(pname(p)), pname(p))), pick):
        pos = round(OFF + k * PITCH, 6)
        x, y = {"W": (INSET, pos), "E": (w - INSET, pos), "S": (pos, INSET), "N": (pos, hh - INSET)}[lf]
        res.append(dict(name=pname(p), layer=LAYER[lf], x=round(x, 6), y=round(y, 6)))
    return res
users = collections.defaultdict(list)
for tn, t in T.items():
    for h in t.get("hard_cores", []):
        if h.get("pins_file"): users[h["pins_file"]].append((tn, h))
def rects(tn, skip):
    t = T[tn]; out = []
    for h in t.get("hard_cores", []):
        if h["inst"] == skip: continue
        x, y = h["origin_um"]; w, hh = h["outline_um"]; out.append((h["inst"], x, y, x + w, y + hh))
    return out
def lot(tn, h, face_core, grow):
    """grown rect fits? try both growth directions along the side carrying the face (type frame)."""
    x, y = h["origin_um"]; w, hh = h["outline_um"]; tw, th = T[tn]["outline_um"]
    horiz = face_core in "NS"     # N/S face length = core width -> grows in x (orient keeps axes)
    opts = []
    for d in (+1, -1):
        r = (x - (grow if d < 0 else 0), y, x + w + (grow if d > 0 else 0), y + hh) if horiz else \
            (x, y - (grow if d < 0 else 0), x + w, y + hh + (grow if d > 0 else 0))
        if r[0] < -1e-6 or r[1] < -1e-6 or r[2] > tw + 1e-6 or r[3] > th + 1e-6:
            opts.append((d, "outside type")); continue
        hit = [n for n, a, b, c, e in rects(tn, h["inst"]) if a < r[2] - 1e-6 and c > r[0] + 1e-6 and b < r[3] - 1e-6 and e > r[1] + 1e-6]
        opts.append((d, "ok" if not hit else "overlaps " + ",".join(hit[:3])))
    return opts
rep = {}
for f, us in sorted(users.items()):
    w, hh = us[0][1]["outline_um"]
    try: ps = json.loads((pd / f).read_text())
    except Exception: continue
    if isinstance(ps, dict): ps = ps.get("pins", [])
    cnt = collections.Counter(lface(p["x"], p["y"], w, hh) for p in ps)
    capf = {F: int(CAP * ((hh if F in "WE" else w) - 2 * END)) for F in "NSEW"}
    over = [F for F in "NSEW" if cnt[F] > capf[F]]
    if not over: continue
    groups = collections.defaultdict(list)
    for p in ps: groups[gbase(pname(p))].append(p)
    moves = []; ps2 = list(ps)
    for F in over:
        cand = []
        for g, gp in groups.items():
            if collections.Counter(lface(p["x"], p["y"], w, hh) for p in gp).most_common(1)[0][0] != F: continue
            judged = [(tn, h) for tn, h in us if D.get((tn, h["inst"], g))]
            if not judged: continue
            for F2 in "NSEW":
                if F2 == F: continue
                if all(sc(h.get("orient", "R0"), F2, D[(tn, h["inst"], g)]) > 1e-9 for tn, h in judged):
                    cand.append((len(gp), g, F2)); break
        for n, g, F2 in sorted(cand, reverse=True):
            c2 = collections.Counter(lface(p["x"], p["y"], w, hh) for p in ps2)
            if c2[F] <= capf[F]: break
            if c2[F2] + n > capf[F2]: continue
            new = place(ps2, w, hh, F2, groups[g], {g})
            if new is None: continue
            ps2 = [p for p in ps2 if gbase(pname(p)) != g] + new; moves.append((g, F, F2, n))
    cnt2 = collections.Counter(lface(p["x"], p["y"], w, hh) for p in ps2)
    faces = {}
    for F in over:
        L = (hh if F in "WE" else w); need = cnt2[F] / CAP + 2 * END
        grow = max(0.0, math.ceil((need - L) / 4.32) * 4.32)
        faces[F] = dict(pins=cnt[F], L=round(L - 2 * END, 2), dens=round(cnt[F] / (L - 2 * END), 2),
                        after_respread=cnt2[F], dens_after=round(cnt2[F] / (L - 2 * END), 2),
                        grow_um=round(grow, 2),
                        lots={f"{tn}.{h['inst']}": lot(tn, h, F, grow) for tn, h in us} if grow else {})
    rep[f] = dict(module=Path(f).name, instances=len(us), outline=[w, hh], faces=faces,
                  moves=[dict(group=g, frm=a, to=b, pins=n) for g, a, b, n in moves])
    if apply_to and moves:
        assert "hbm-r15-1027" not in str(apply_to)
        (apply_to / f).write_text(json.dumps(ps2) + "\n")
    print(Path(f).name[:58], len(us), {F: (v["dens"], v["dens_after"], v["grow_um"]) for F, v in faces.items()}, "moves", len(moves), flush=True)
json.dump(rep, open(outp, "w"), indent=1)
