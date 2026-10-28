#!/usr/bin/env python3
"""HBM-R16/C17 joint what-if: per pin table (core master), choose an orient per instance and ONE core face per port
group so that no (instance, port) is G0C-away (mean cos < -0.1). Coordinate descent + restarts. Report only.
usage: joint.py PLANDIR OUT.json [--fixed-orient]"""
import sys, json, re, math, random, collections
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan")
import check as C, schema as S
pd = Path(sys.argv[1]).resolve(); outp = sys.argv[2]; fixed = "--fixed-orient" in sys.argv
raw = json.loads((pd / "die_plan.json").read_text()); T = raw["partition_types"]
P = S.Plan(raw, pd / "die_plan.json")
last = {}
o_bf = C.best_face
def bf(d):
    last["d"] = list(d); return o_bf(d)
class Rep(C.Report):
    def err(self, check, msg, **kw):
        super().err(check, msg, **kw); self.items[-1]["dirs"] = last.get("d")
C.best_face = bf; C.FACE_WARN_COS = C.FACE_AWAY_COS = 1e9
R = Rep(True); C.check_core_faces(P, R, str(pd), None, max_msgs=10**9)
MSG = re.compile(r"type (\S+) core (\S+) port (\S+): (\d+) pins on face (\S+) face away")
D = {}
for i in R.errors():
    m = MSG.match(i["msg"])
    if m and i.get("dirs"):
        D[(m.group(1), m.group(2), m.group(3))] = [(d[1], d[2]) for d in i["dirs"]]
OPP = dict(N="S", S="N", E="W", W="E")
def tface(o, f):
    if o in ("MX", "R180") and f in "NS": f = OPP[f]
    if o in ("MY", "R180") and f in "EW": f = OPP[f]
    return f
def sc(o, F, dirs):
    nx, ny = C._NORMAL[tface(o, F)]
    return max(nx * x + ny * y for x, y in dirs)
def lface(x, y, w, h): return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]
# tables touched by away groups
away = [k for k, d in D.items()]
bad0 = set()
users = collections.defaultdict(list)
for tn, t in T.items():
    for h in t.get("hard_cores", []):
        users[h.get("pins_file")].append((tn, h))
res = {}
for tn, ci, lp in list(D):
    pass
cur_bad = collections.Counter()
for (tn, ci, lp), dirs in D.items():
    h = next(x for x in T[tn]["hard_cores"] if x["inst"] == ci)
    w, hh = h["outline_um"]
tables = set()
# away now
for (tn, ci, lp), dirs in D.items():
    h = next(x for x in T[tn]["hard_cores"] if x["inst"] == ci)
    pins = C.core_pins(h, str(pd)); g = h.get("pin_select", {}).get(lp, lp)
    fs = [lface(x, y, *h["outline_um"]) for n, _l, x, y in pins if re.sub(r"\[\d+\]$", "", n) == g]
    if fs and sum(sc(h.get("orient", "R0"), F, dirs) for F in fs) / len(fs) < -0.1:
        tables.add(h["pins_file"])
for f in sorted(tables):
    us = users[f]; w, hh = us[0][1]["outline_um"]
    pins = C.core_pins(us[0][1], str(pd))
    gf = collections.defaultdict(collections.Counter)
    for n, _l, x, y in pins:
        gf[re.sub(r"\[\d+\]$", "", n)][lface(x, y, w, hh)] += 1
    ports = sorted({lp for tn, h in us for (t2, c2, lp) in D if (t2, c2) == (tn, h["inst"]) and lp in gf})
    inst = [(tn, h["inst"], h.get("orient", "R0")) for tn, h in us]
    fcnt0 = collections.Counter(lface(x, y, w, hh) for n, _l, x, y in pins)
    capf = {F: int(5.5 * ((hh if F in "WE" else w) - 2 * 8.64)) for F in "NSEW"}
    def feas(faces):
        c = collections.Counter(fcnt0)
        for p, F in faces.items():
            if F is None: continue
            for F0, n in gf[p].items(): c[F0] -= n
            c[F] += sum(gf[p].values())
        return all(c[F] <= max(capf[F], fcnt0[F]) for F in "NSEW") and all(
            c[F] <= capf[F] for F in "NSEW" if any(faces[p] == F for p in faces))
    def cost(orients, faces):
        if not feas(faces):
            return (10**9, 10**9)
        e = wv = 0
        for (tn, ci, _o), o in zip(inst, orients):
            for p in ports:
                d = D.get((tn, ci, p))
                if not d: continue
                if faces[p] is None:   # unchanged group: exact mean over its pins
                    m = sum(sc(o, F, d) * n for F, n in gf[p].items()) / sum(gf[p].values())
                else:
                    m = sc(o, faces[p], d)
                e += m < -0.1; wv += m < 0
        return e, wv
    o0 = [o for _, _, o in inst]; f0 = {p: None for p in ports}
    base = cost(o0, f0)
    best = (base, o0, f0)
    rnd = random.Random(1)
    for rs in range(30):
        orients = list(o0) if rs == 0 or fixed else [rnd.choice(["R0", "MX", "MY", "R180"]) for _ in inst]
        faces = dict(f0)
        for it in range(8):
            ch = False
            for p in ports:
                bestf = min([None, "N", "S", "E", "W"], key=lambda F: (cost(orients, {**faces, p: F}), F is not None))
                if bestf != faces[p]: faces[p] = bestf; ch = True
            if not fixed:
                for i in range(len(inst)):
                    bo = min(["R0", "MX", "MY", "R180"], key=lambda o: (cost(orients[:i] + [o] + orients[i+1:], faces), o != o0[i]))
                    if bo != orients[i]: orients[i] = bo; ch = True
            if not ch: break
        c = cost(orients, faces)
        nchg = sum(a != b for a, b in zip(orients, o0)) + sum(v is not None for v in faces.values())
        if (c, nchg) < (best[0], sum(a != b for a, b in zip(best[1], o0)) + sum(v is not None for v in best[2].values())):
            best = (c, list(orients), dict(faces))
    c, ors, fs = best
    res[f] = dict(users=len(inst), ports=len(ports), before=base, after=c,
                  orient_changes={f"{tn}.{ci}": f"{o}->{n}" for (tn, ci, o), n in zip(inst, ors) if o != n},
                  face_moves={p: f"{'/'.join(gf[p])}->{F}" for p, F in fs.items() if F is not None})
    print(Path(f).name[:60], "users", len(inst), "ports", len(ports), "away/warn", base, "->", c,
          "orients", len(res[f]["orient_changes"]), "moves", len(res[f]["face_moves"]), flush=True)
json.dump(res, open(outp, "w"), indent=1)
