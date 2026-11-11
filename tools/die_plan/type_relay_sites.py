#!/usr/bin/env python3
"""RELAY-SITES (TYPE-SAFE-5 2026-11-09): die-agnostic FIRM relay sites for one bound type, from a placed geometry dump.

The DIE-QC-97 STRUCT-CTL-1 idea (qc_struct_ctl.py) without its per-type content boxes.  Existing transport relays
(u_lpad_ packed pads, u_pd<D>_ chains, u_ist_ stations) become plan relay_sites (DIE-KV-59: FIRM, 0 added cycles), one
site per bit, evenly spaced on the line between the chain's fixed endpoints:
  launch end  = L1 minimax of the flops, macros and pins that feed the first stage,
  capture end = L1 minimax of what the last stage drives.
Reset relays are not launches here: the reset tree places them itself.
A chain whose even hop is still above --reach cannot close at its present depth; it is listed in report.pin_cycles
(cycles to add), and nothing is added to the plan by this tool.

A site that falls inside a hard macro (grown by --macro-halo) moves to the macro's free boundary point with the smaller
worst hop (relay_site_clear.py, TYPE-SAFE-5 11-10: leaf__t35 p3 legalised such a site 68 um off, 15 bits over 405).

  type_relay_sites.py SRC GEOM BASE_PLAN TYPE OUT_PLAN REPORT_JSON [--reach 380] [--firm FACE_FLOPS] [--extra BUS=N]
                      [--macro-halo 6 (negative: off)]
"""
import argparse, collections, json, math, re, sys
from pathlib import Path

ap = argparse.ArgumentParser()
for a in "src geom base type out report".split():
    ap.add_argument(a)
ap.add_argument("--reach", type=float, default=380.0)
ap.add_argument("--firm", help="ot_face_flops.txt of the placed kit: with it, u_bin_ flops not listed there (ring-fed buses) are movable too")
ap.add_argument("--extra", action="append", default=[], metavar="BUS=N", help="station bus BUS gets N more u_ist_ stages (pin cycles planned elsewhere); their bits are sited here")
ap.add_argument("--macro-halo", type=float, default=6.0, help="sites inside a macro grown by this many um move to its boundary; negative = off")
A = ap.parse_args()
sys.path.insert(0, A.src + "/tools/autopilot")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom_rules as G  # noqa: E402
from relay_site_clear import clear_sites  # noqa: E402

RELAY = re.compile(r"^(?:u_bound\.)?((?P<lpad>u_lpad_\w+?)\.(?:q\[\d+\]|r\[\d+\]\[\d+\])"
                   r"|(?P<pd>u_pd\d+_\w+?_\d+)\.(?:r\[\d+\]|q)"
                   r"|(?P<ist>u_ist_\w+?_\d+)[./](?:q\[\d+\]|eq)"
                   r"|(?P<bin>u_bin_\w+?)[./](?:q\[\d+\]|eq))\$")
RESET = re.compile(r"u_rrl_|u_cland_(?:rst|reset|collect)|rst_rl_|rst_n_t\d")
EXTRA = {k: int(v) for k, v in (x.split("=") for x in A.extra)}
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])

D = G.Design(A.geom)
name = {c: v[6].replace("\\", "") for c, v in D.cells.items()}
kind = {c: v[0] for c, v in D.cells.items()}
firm = {ln.split("\t")[0].replace("\\", "") for ln in open(A.firm)} if A.firm else None
relay = {}
for c, nm in name.items():
    if kind[c] == "S":
        m = RELAY.match(nm)
        if m:
            k = next(k for k in ("lpad", "pd", "ist", "bin") if m.group(k))
            if k != "bin" or (firm is not None and nm not in firm):
                relay[c] = k


def key(c):
    return re.sub(r"^u_bound[./]", "", re.sub(r"\$_[A-Za-z0-9_]*$", "", name[c]))


def pin_xy(k):
    p = D.pin_by_k[k]
    return (float(p["x"]), float(p["y"]))


def launches(c):
    """the sequential cells, macros and pins feeding the data pins of c, through combinational cells"""
    out, seen, front = set(), set(), [c]
    while front:
        nf = []
        for u in front:
            for n, is_clk in D.cell_in.get(u, []):
                if is_clk:
                    continue
                d = D.nets[n][1]
                if d is None:
                    continue
                if d[0] == "p":
                    out.add(("p", d[1]))
                elif kind.get(d[1]) in ("S", "M"):
                    if not RESET.search(name[d[1]]):
                        out.add(("i", d[1]))
                elif d[1] not in seen:
                    seen.add(d[1])
                    nf.append(d[1])
        front = nf
    return out


def captures(c):
    """data capture flops, macros and pins driven by c, through combinational cells"""
    out, seen, front = set(), set(), [c]
    while front:
        nf = []
        for u in front:
            for n in D.drives.get(u, []):
                for s in D.nets[n][2]:
                    if s[0] == "p":
                        out.add(("p", s[1]))
                    elif not s[2]:
                        if kind.get(s[1]) in ("S", "M"):
                            out.add(("i", s[1]))
                        elif s[1] not in seen:
                            seen.add(s[1])
                            nf.append(s[1])
        front = nf
    return out


def minimax(pts):
    us = [p[0] + p[1] for p in pts]
    vs = [p[0] - p[1] for p in pts]
    u, v = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
    return ((u + v) / 2, (u - v) / 2)


def point(r, toward):
    """an anchor's position: a macro counts at its rectangle point nearest `toward`"""
    if r[0] == "p":
        return pin_xy(r[1])
    v = D.cells[r[1]]
    if v[0] == "M":
        return (min(max(toward[0], v[2]), v[4]), min(max(toward[1], v[3]), v[5]))
    return G.ctr(v)


L = {c: launches(c) for c in relay}
C = {c: captures(c) for c in relay}
pred = {c: {r[1] for r in L[c] if r[0] == "i" and r[1] in relay} for c in relay}
succ = {c: {r[1] for r in C[c] if r[0] == "i" and r[1] in relay} for c in relay}
nxt = {c: next(iter(succ[c])) for c in relay if len(succ[c]) == 1 and len(C[c]) == 1
       and pred[next(iter(succ[c]))] == {c}}
inner = set(nxt.values())
sites, rep = {}, dict(reach_um=A.reach, skipped=collections.Counter(), hop=collections.defaultdict(float), chains=0,
                      over405=0, over_reach=0, pin_cycles=collections.Counter(), macro_halo_um=A.macro_halo,
                      sites_moved_off_macro=0)
die = D.die
rects = [tuple(v[2:6]) for v in D.cells.values() if v[0] == "M"] if A.macro_halo >= 0 else []
for head in sorted(c for c in relay if c not in inner):
    ch = [head]
    while ch[-1] in nxt:
        ch.append(nxt[ch[-1]])
    ends_a = [r for r in L[head] if not (r[0] == "i" and r[1] in relay)]
    ends_b = [r for r in C[ch[-1]] if not (r[0] == "i" and r[1] in relay)]
    if not ends_a or not ends_b:
        rep["skipped"][relay[head] + (":no_launch" if not ends_a else ":no_capture")] += 1
        continue
    here = G.ctr(D.cells[head])
    b0 = minimax([point(r, here) for r in ends_b])
    pa = [point(r, b0) for r in ends_a]
    a = minimax(pa)
    pb = [point(r, a) for r in ends_b]
    b = minimax(pb)
    keys = [key(c) for c in ch]
    m_ist = re.match(r"(u_ist_(\w+?))_0([./].*)$", keys[0]) if len(ch) == 1 else None
    if m_ist and m_ist.group(2) in EXTRA:
        keys = [f"{m_ist.group(1)}_{j}{m_ist.group(3)}" for j in range(1 + EXTRA[m_ist.group(2)])]
    n = len(keys)
    # equal hops including the end fans: ra / rb are the far launch / capture around the two minimax ends
    span, ra, rb = L1(a, b), max(L1(a, p) for p in pa), max(L1(b, p) for p in pb)
    d = (ra + span + rb) / (n + 1)
    first = min(max(d - ra, 0.0), span)
    step = (span - first - max(d - rb, 0.0)) / (n - 1) if n > 1 else 0.0
    step = max(step, 0.0)
    fr = [(first + step * j) / span if span else 0.5 for j in range(n)]
    path = [(round(min(max(a[0] + (b[0] - a[0]) * f, die[0]), die[2]), 3),
             round(min(max(a[1] + (b[1] - a[1]) * f, die[1]), die[3]), 3)) for f in fr]
    if rects:
        path, mv = clear_sites(path, pa, pb, rects, die, halo=A.macro_halo)
        rep["sites_moved_off_macro"] += mv
    hops = [max(L1(path[0], p) for p in pa)] + [L1(path[j], path[j + 1]) for j in range(n - 1)] + \
           [max(L1(path[-1], p) for p in pb)]
    worst = max(hops)
    k0 = relay[head]
    rep["chains"] += 1
    rep["hop"][k0] = max(rep["hop"][k0], worst)
    rep["over405"] += worst > 405
    rep["over_reach"] += worst > A.reach
    if worst > A.reach and A.reach and len(rep.setdefault("examples", [])) < 400:
        nm = lambda r: (name[r[1]] if r[0] == "i" else "pin:" + str(D.pin_by_k[r[1]].get("name", r[1])))
        rep["examples"].append(dict(head=key(head), n=n, worst=round(worst, 1), a=[round(v, 1) for v in a], b=[round(v, 1) for v in b],
                                    la=[(nm(r), kind.get(r[1]) if r[0] == "i" else "p", [round(v, 1) for v in point(r, b)]) for r in ends_a][:4],
                                    lb=[(nm(r), kind.get(r[1]) if r[0] == "i" else "p", [round(v, 1) for v in point(r, a)]) for r in ends_b][:4]))
    if worst > A.reach:
        bus = re.sub(r"[./](q\[\d+\]|eq|r\[\d+\](\[\d+\])?)$", "", key(head))
        rep["pin_cycles"][bus] = max(rep["pin_cycles"][bus], max(1, math.ceil((ra + span + rb) / A.reach) - (n + 1)))
    for k, s in zip(keys, path):
        sites[k] = [s[0], s[1]]
raw_b = Path(A.base).read_bytes()
raw = json.loads(raw_b)
t = raw["partition_types"][A.type]
merged = dict(t.get("relay_sites") or {})
kept = sum(1 for k in sites if k in merged)
merged.update(sites)
t["relay_sites"] = dict(sorted(merged.items()))
style = None
for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
          lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
          lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
    if f(json.loads(raw_b)).encode() == raw_b:
        style = f
        break
if style is None:                         # byte style unknown (hand-edited plan): the JSON value is what the compiler reads
    style = lambda p: json.dumps(p, indent=1, ensure_ascii=False) + "\n"
Path(A.out).write_text(style(raw))
rep.update(relay_flops=len(relay), by_kind=collections.Counter(relay.values()), sites=len(sites), replaced_plan_sites=kept)
rep["hop"] = {k: round(v, 1) for k, v in rep["hop"].items()}
Path(A.report).write_text(json.dumps(rep, indent=1, default=dict) + "\n")
print(json.dumps({k: v for k, v in rep.items() if k != "pin_cycles"}, default=dict), "pin_cycles", dict(rep["pin_cycles"]))
