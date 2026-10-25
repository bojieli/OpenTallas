"""Die IO planning (PLAN-TOOL5, COORD DIE-PLAN VISUAL REVIEW 10-23 item (a)).

Every die's external interfaces (SerDes, UCIe, HBM PHY) and its host link must be planned as die IO: a `die.io`
window over the PHY footprint, on the die shoreline, with enough bump sites for the off-die signals. Until 10-23 the
plans had none (die_io windows 0 / ports 0 on all four dies), so the die boundary was unchecked.

The PHY macros are licensed-IP abstracts whose off-die side is modelled (owner 10-14: only PHY / off-chip signals are
modelled). Their off-die signals therefore exist only as bump counts, not as RTL ports. A window says so with
`iface` + `signals`, and lists `ports` only when the plan has real @die ports (S81-P5 form, check_die_io).

    die.io[] = {name, kind: phy_macro, iface: serdes|ucie|hbm_phy|host, part, rect_um, sites, pitch_um, signals,
                host: true (this window also carries the die's host link)
                    | "in_band" (S81-XDIE 10-24: the die has NO host link; host traffic rides this die link in-band,
                                 e.g. S81 stage dies: stage-in WN2/3 -> s_0N_LP -> seqhost, RELEASE_RACK 2.1 S81.HOST),
                host_route (in_band: the declared on-die route to the host logic), basis, note}

Catalog (CLASSES): content module regex -> interface class, off-die signals per instance, bump pitch.
  serdes   4 per lane (TX+/-, RX+/-) + 2 refclk. Lanes from the module name (_x12 / _x6); ot_pdie_serdes = 6
           (half of the 112G strip, 512-b flit per 833-ps cycle = 614 Gb/s -> 6 x 112G PAM4). C4 pitch 150 um.
  ucie     one x64 advanced module: 2 x (64 data + valid + track + 2 clock) + 2 x 4 redundant = 144. Pitch 45 um
           (UCIe-A 25-55 um).
  hbm_phy  ~1,900 per HBM3/3E stack (16 ch x ~117: 64 DQ, ECC / DBI / SEV, strobes, row/col CA, CK, plus globals);
           a 4-PC slice (qkd_hbm3e_phy_pc) is 1/8 stack, the v41x _s4 view 1/4. Micro-bump pitch 55 um.
  All counts are ASSUMED interface-class values (the PHY views carry no bump map); a plan may override `signals`.

G0C (`check.py --completeness`, check name 'die_io_plan'):
  - every placed instance of an IO-class content has a window of its class over it (inside its partition);
  - each window is on the shoreline: its rect within budgets.io_edge_max_um (200) of a die edge;
  - signals <= sites;
  - the die names its host link: one window with iface 'host' or host: true, OR (in-band-host die) one or more
    windows host: "in_band" from which the port graph reaches the host logic (host_rt / seq_host / ...);
    a die may not mix a dedicated host window with in-band ones;
  - die.io empty -> one die-level ERROR.

Host link: no die has a host PHY macro; the host rides a die link PHY (serdes / ucie). `plan` marks the link PHY
nearest (port-graph hops) to the host logic (host_rt / seq_host / host_cp / sys_face) host: true -- CONFIRM it.
`plan --in-band-host PART[=LANE+LANE...][,...]` instead marks the windows on those partitions host: "in_band" (no BFS
guess) and records the ingress lane route to the host logic in host_route (declared lane chain, checked; else the
shortest functional lane path).  G0C re-checks a declared host_route against the plan's lanes.

Die-corner windows (S81-XDIE 10-24): `plan --corner-keepout-um C` gives every PHY window that overlaps a C x C square
at a die-outline corner a `bump_exclude_um` rect (= that overlap): no bumps there (package corner stress zone: C4 / micro-
bump depopulation at the die corners), and `sites` counts only the pitch sites whose centre lies outside the exclusions.
So a PHY may take a die-corner slot (the S81 reserve pair lk_WS2 / lk_EN3, like lk_WN2) without a whole keep-out cell.
G0C: an exclusion must lie inside its window, and `sites` must not exceed the sites left outside the exclusions.
pg_domains (S81) copy the exclusions into the VDDPHY domain's bumps.exclude_um and use them as the domain's rail-clamp
ESD / decap area (esd_um); check_pg_domains: exclude_um / esd_um inside the bump / domain rect, and a window's
exclusions present in its domain's bumps.exclude_um.

The plan's die.io wins; without it check.py reads PLANDIR/die_io.json (written by `plan --out`), so the windows
survive the die generators' regeneration of die_plan.json.

    python3 tools/die_plan/die_io.py plan PLAN.json [--inplace] [--out PLANDIR/die_io.json] [--in-band-host P1,P2]
"""
import argparse
import json
import math
import re
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
from schema import DIE_PART  # noqa: E402

HBM_STACK_SIGNALS = 1900
UCIE_X64_SIGNALS = 2 * (64 + 1 + 1 + 2) + 2 * 4
# (class, module regex, signals(module) -> int, bump pitch um, basis)
CLASSES = [
    ("hbm_phy", re.compile(r"hbm3e?_phy", re.I),
     lambda m: HBM_STACK_SIGNALS // 8 if re.search(r"_pc$", m) else
     HBM_STACK_SIGNALS // 4 if re.search(r"_s4$", m) else HBM_STACK_SIGNALS, 55.0,
     "HBM3/3E stack ~1,900 signals (16 ch x ~117 + globals; ASSUMED class value), 55-um micro-bumps"),
    ("ucie", re.compile(r"ucie_x\d+_phy|pdie_ucie", re.I), lambda m: UCIE_X64_SIGNALS, 45.0,
     "UCIe-A x64 module: 2 x (64 data + valid + track + 2 clk) + 2 x 4 redundant = 144, 45-um bumps (ASSUMED)"),
    ("serdes", re.compile(r"serdes.*phy|pdie_serdes", re.I),
     lambda m: 4 * int((re.search(r"_x(\d+)", m) or [None, 6])[1]) + 2, 150.0,
     "112G PAM4 SerDes: 4 per lane (TX/RX pairs) + 2 refclk; lanes from _xN, ot_pdie_serdes 6 (614 Gb/s); C4 150 um"),
]
HOST_RE = re.compile(r"host_rt|seq_host|host_cp|sys_face|host_static_ingress", re.I)
HOST_CARRIERS = ("serdes", "ucie")      # the host link rides a die link PHY (no host PHY macro on any die)
EDGE_MAX_UM = 200.0
EPS = 1e-6


def classify(module):
    for cls, rx, sig, pitch, basis in CLASSES:
        if rx.search(module or ""):
            return cls, sig(module), pitch, basis
    return None


def io_instances(P):
    """[(part, content inst, class, signals, pitch, basis, die rect of the content footprint)] for every placed
    instance of an IO-class content (footprint = contents[].origin/outline, else the whole partition)."""
    out = []
    for pn in P.parts:
        t = P.ptype(pn)
        cs = t.get("contents") or [dict(inst=pn, module=t.get("module", ""))]
        for c in cs:
            k = classify(c.get("module", ""))
            if not k:
                continue
            if "origin_um" in c and "outline_um" in c:
                (x0, y0), (w, h) = c["origin_um"], c["outline_um"]
                a, b = P.to_die(pn, (x0, y0)), P.to_die(pn, (x0 + w, y0 + h))
                r = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
                pr = P.rect(pn)            # clip to the partition (a macro outline may overhang its slot)
                r = (max(r[0], pr[0]), max(r[1], pr[1]), min(r[2], pr[2]), min(r[3], pr[3]))
            else:
                r = P.rect(pn)
            out.append((pn, c.get("inst", pn), k[0], k[1], k[2], k[3], r))
    return out


def edge_dist(P, r):
    return min(r[0], r[1], P.W - r[2], P.H - r[3])


def corner_excl(W, H, r, c):
    """S81-XDIE: overlaps of window r with the c x c squares at the four die-outline corners (bump depopulation)."""
    out = []
    if not c:
        return out
    for q in ((0.0, 0.0, c, c), (W - c, 0.0, W, c), (0.0, H - c, c, H), (W - c, H - c, W, H)):
        x0, y0, x1, y1 = max(r[0], q[0]), max(r[1], q[1]), min(r[2], q[2]), min(r[3], q[3])
        if x1 > x0 + EPS and y1 > y0 + EPS:
            out.append([round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)])
    return out


PHY_STRIP_UM = 150.0      # boundary-flop strip depth behind a SerDes partition's bus face window (phy_zone)


def phy_zone(P, pn, guard, edge_max=EDGE_MAX_UM, strip=PHY_STRIP_UM):
    """S81-XDIE 10-24 (GEOM condition: PHY fit beside the partition strip): the PHY footprint of a serdes partition whose
    content has no origin / outline = the largest free rectangle of its rect that touches the shoreline (edge distance
    <= edge_max) after blocking, each grown by `guard` (the VDDPHY ring): every bus face window's boundary-flop strip
    (`strip` deep behind the window), every straight ft slot's band (E-W: full width at the window's y, N-S: full
    height at its x) and every L-route ft slot's two legs (from its N/S window down / up to its E/W window's y, and from
    the E/W face across to the N/S window's x).  So the strip, its ft stations and their core-VDD straps stay outside
    the PHY / VDDPHY area.  If no free rectangle touches the shoreline the largest free one is returned (G0C then
    reports the window off-shore).  Returns (rect, note)."""
    r = P.rect(pn)
    t = P.ptype(pn)
    w, h = t["outline_um"]

    def seg(face, a0, a1):
        """die rect of a face window: degenerate across the face (x0 == x1 for E/W)."""
        if face in "EW":
            x = 0.0 if face == "W" else w
            (xa, ya), (xb, yb) = P.to_die(pn, (x, a0)), P.to_die(pn, (x, a1))
        else:
            y = 0.0 if face == "S" else h
            (xa, ya), (xb, yb) = P.to_die(pn, (a0, y)), P.to_die(pn, (a1, y))
        return min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)

    def grow(b):
        return (b[0] - guard, b[1] - guard, b[2] + guard, b[3] + guard)
    blk = []
    for b in t.get("buses", []):
        x0, y0, x1, y1 = seg(b["face"], *b["window_um"])
        if b["face"] in "EW":
            blk.append(grow((x0 - strip, y0, x1 + strip, y1)))
        else:
            blk.append(grow((x0, y0 - strip, x1, y1 + strip)))
    for f in t.get("ft_slots", []):
        A, B = seg(f["in_face"], *f["in_window_um"]), seg(f["out_face"], *f["out_window_um"])
        ew = [z for z, fc in ((A, f["in_face"]), (B, f["out_face"])) if fc in "EW"]
        ns = [z for z, fc in ((A, f["in_face"]), (B, f["out_face"])) if fc in "NS"]
        if len(ew) == 2:
            blk.append(grow((r[0], min(z[1] for z in ew), r[2], max(z[3] for z in ew))))
        elif len(ns) == 2:
            blk.append(grow((min(z[0] for z in ns), r[1], max(z[2] for z in ns), r[3])))
        else:                                        # L route: vertical leg at the N/S window's x, horizontal leg at the E/W y
            e, n = ew[0], ns[0]
            blk.append(grow((n[0], min(n[1], e[1]), n[2], max(n[3], e[3]))))
            blk.append(grow((min(e[0], n[0]), e[1], max(e[2], n[2]), e[3])))
    xs = sorted({r[0], r[2]} | {min(max(v, r[0]), r[2]) for b in blk for v in (b[0], b[2])})
    ys = sorted({r[1], r[3]} | {min(max(v, r[1]), r[3]) for b in blk for v in (b[1], b[3])})
    free = [[not any(b[0] < xs[i + 1] - EPS and b[2] > xs[i] + EPS and b[1] < ys[j + 1] - EPS and b[3] > ys[j] + EPS
                     for b in blk) for j in range(len(ys) - 1)] for i in range(len(xs) - 1)]
    best = bshore = None
    for i0 in range(len(xs) - 1):
        for j0 in range(len(ys) - 1):
            if not free[i0][j0]:
                continue
            jmax = len(ys) - 1
            for i1 in range(i0, len(xs) - 1):
                j = j0
                while j < jmax and free[i1][j]:
                    j += 1
                jmax = min(jmax, j)
                if jmax <= j0:
                    break
                c = (xs[i0], ys[j0], xs[i1 + 1], ys[jmax])
                a = (c[2] - c[0]) * (c[3] - c[1])
                if best is None or a > best[0]:
                    best = (a, c)
                if edge_dist(P, c) <= edge_max + EPS and (bshore is None or a > bshore[0]):
                    bshore = (a, c)
    pick = bshore or best
    if pick is None:
        return tuple(r), "no free PHY area beside the strip (whole partition kept)"
    c = pick[1]
    return c, ("PHY zone %.0f x %.0f um beside the strip (%d blocked strip / ft rects, %g-um guard)%s"
               % (c[2] - c[0], c[3] - c[1], len(blk), guard, "" if bshore else "; NO shoreline area: PHY OFF-SHORE"))


def count_sites(r, pitch, excl=()):
    """pitch sites of window r (floor(w/p) x floor(h/p), the grid from the window's lower-left corner) whose centre lies
    outside every exclusion rect."""
    nx, ny = int(math.floor((r[2] - r[0]) / pitch + EPS)), int(math.floor((r[3] - r[1]) / pitch + EPS))
    if not excl:
        return max(1, nx * ny)
    n = 0
    for i in range(nx):
        for j in range(ny):
            cx, cy = r[0] + (i + 0.5) * pitch, r[1] + (j + 0.5) * pitch
            if not any(e[0] <= cx <= e[2] and e[1] <= cy <= e[3] for e in excl):
                n += 1
    return max(1, n)


def host_parts(P):
    hp = []
    for pn in P.parts:
        t = P.ptype(pn)
        if any(HOST_RE.search(c.get("module", "") + " " + c.get("inst", "")) for c in t.get("contents", [])):
            hp.append(pn)
    return hp


def port_graph(P):
    g = {}
    for pr in P.ports.values():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if DIE_PART in (a, b):
            continue
        g.setdefault(a, set()).add(b)
        g.setdefault(b, set()).add(a)
    return g


def lane_graph(P):
    """functional graph: lane source partition -> lane sink partition (ft pass-throughs skipped), edge label = lane."""
    g = {}
    for lid, ln in P.lanes.items():
        ps = ln.get("ports") or []
        if not ps or ps[0] not in P.ports or ps[-1] not in P.ports:
            continue
        a, b = P.ports[ps[0]]["src"]["part"], P.ports[ps[-1]]["dst"]["part"]
        if DIE_PART in (a, b) or a == b:
            continue
        g.setdefault(a, {}).setdefault(b, lid)
    return g


def lane_ends(P, lid):
    ps = P.lanes[lid].get("ports") or []
    return P.ports[ps[0]]["src"]["part"], P.ports[ps[-1]]["dst"]["part"]


def route_path(P, start, lanes, targets):
    """declared in-band route: the lane chain from start must be continuous and end at host logic.
    Returns ([part, lane, part, ...], error or None)."""
    path, cur = [start], start
    for lid in lanes:
        if lid not in P.lanes:
            return path, f"lane {lid} not in the plan"
        a, b = lane_ends(P, lid)
        if a != cur:
            return path, f"lane {lid} starts at {a}, not {cur}"
        path += [lid, b]
        cur = b
    if cur not in targets:
        return path, f"route ends at {cur}, not at host logic ({', '.join(sorted(targets)) or 'none'})"
    return path, None


def fmt_path(path):
    return " -> ".join(("[%s]" % x) if k % 2 else x for k, x in enumerate(path))


def parse_route(txt):
    """'a -> [l1] -> b -> [l2] -> c' -> (start, [l1, l2])"""
    toks = [t.strip() for t in txt.split("->")]
    return toks[0], [t[1:-1] for t in toks[1:] if t.startswith("[")]


def host_path(P, start, targets):
    """BFS path start -> nearest of targets over the functional lane graph (directed, source -> sink):
    [part, lane, part, lane, ..., part], or None."""
    g = lane_graph(P)
    prev = {start: None}
    q = deque([start])
    while q:
        u = q.popleft()
        if u in targets:
            path = [u]
            while prev[u] is not None:
                u, lid = prev[u]
                path[:0] = [u, lid]
            return path
        for v, lid in sorted(g.get(u, {}).items()):
            if v not in prev:
                prev[v] = (u, lid)
                q.append(v)
    return None


def nearest_io(P, starts, io_parts):
    """BFS over the port graph from the host-logic partitions to the nearest IO partition: (part, hops)."""
    g = port_graph(P)
    seen = {s: 0 for s in starts}
    q = deque(starts)
    while q:
        u = q.popleft()
        if u in io_parts:
            return u, seen[u]
        for v in sorted(g.get(u, ())):
            if v not in seen:
                seen[v] = seen[u] + 1
                q.append(v)
    return None, None


def plan(P, in_band=None, corner_um=0.0, phy_zone_guard=None):
    """proposed die.io list from the catalog (one window per IO-class content instance).  in_band: partitions whose
    link windows carry the host traffic in-band (host: "in_band"; replaces the BFS host guess).  corner_um: die-corner
    bump depopulation square (bump_exclude_um on the windows that overlap it).  phy_zone_guard: serdes windows of a
    partition without a placed PHY footprint shrink to phy_zone() (the strip stays core VDD)."""
    io = []
    names = set()
    inst = io_instances(P)
    for pn, ci, cls, sig, pitch, basis, r in inst:
        nm = re.sub(r"[^A-Za-z0-9_]", "_", f"io_{pn}_{ci}")
        while nm in names:
            nm += "_"
        names.add(nm)
        zn = None
        if phy_zone_guard is not None and cls == "serdes" and tuple(r) == tuple(P.rect(pn)):
            z, zn = phy_zone(P, pn, phy_zone_guard)
            if edge_dist(P, z) <= float(P.budgets.get("io_edge_max_um", EDGE_MAX_UM)) + EPS:
                r = z
            else:      # keep the whole slot as the window (pre-zone form) and say so: the strip sits on the die-edge side
                zn = ("PHY ZONE OFF-SHORE: free area %s is %.0f um from the die edge (the partition's ft / bus strip is "
                      "on the die-edge side; orient fix owed) -> window = whole slot" % ([round(v, 2) for v in z],
                                                                                         edge_dist(P, z)))
                print(f"die_io plan: WARNING {pn}: {zn}", file=sys.stderr)
        w, h = r[2] - r[0], r[3] - r[1]
        ex = corner_excl(P.W, P.H, r, corner_um)
        sites = count_sites(r, pitch, ex) if ex else max(1, int(math.floor(w / pitch)) * int(math.floor(h / pitch)))
        io.append(dict(name=nm, kind="phy_macro", iface=cls, part=pn, rect_um=[round(v, 4) for v in r],
                       sites=sites, pitch_um=pitch, signals=sig,
                       basis=basis + f"; shoreline {edge_dist(P, r):.0f} um", note=f"die_io.py plan: {ci}"))
        if zn:
            io[-1]["note"] += "; " + zn
        if ex:
            io[-1]["bump_exclude_um"] = ex
            io[-1]["note"] += (f"; die-corner window: no bumps in the {corner_um:g}-um corner stress square "
                               f"(bump_exclude_um), {count_sites(r, pitch)} -> {sites} sites")
    hp = host_parts(P)
    if in_band:
        in_band = dict(x if isinstance(x, tuple) else (x, None) for x in in_band)    # part -> declared lanes | None
        miss = sorted(set(in_band) - {w["part"] for w in io if w["iface"] in HOST_CARRIERS})
        if miss:
            raise SystemExit(f"die_io plan: --in-band-host {miss}: no serdes / ucie window on those partitions")
        for w in io:
            if w["part"] in in_band and w["iface"] in HOST_CARRIERS:
                w["host"] = "in_band"
                lanes = in_band[w["part"]]
                if lanes:
                    path, err = route_path(P, w["part"], lanes, set(hp))
                    if err:
                        raise SystemExit(f"die_io plan: --in-band-host {w['part']}: {err}")
                else:
                    path = host_path(P, w["part"], set(hp))
                w["host_route"] = fmt_path(path) if path else ""
                w["note"] += ("; in-band host (no host link on this die), %s route: " % (
                    "declared" if lanes else "shortest lane")) + (w["host_route"] or "NO ROUTE")
        return io
    if io and hp:
        via, hops = nearest_io(P, hp, {w["part"] for w in io if w["iface"] in HOST_CARRIERS})
        if via:
            w = next(x for x in io if x["part"] == via and x["iface"] in HOST_CARRIERS)
            w["host"] = True
            w["note"] += f"; host link (BFS {hops} port hop(s) from {', '.join(sorted(hp)[:3])}): CONFIRM"
    return io


def check(P, R, edge_max=None):
    """G0C die IO plan rules (see the module docstring). Returns the summary dict."""
    io = P.die.get("io") or []
    edge_max = float(P.budgets.get("io_edge_max_um", EDGE_MAX_UM) if edge_max is None else edge_max)
    inst = io_instances(P)
    summ = dict(windows=len(io), iface_windows=sum(1 for w in io if w.get("iface")), io_instances=len(inst),
                by_class={}, host=None, uncovered=0, off_shore=0, over_sites=0)
    for _, _, cls, sig, *_ in inst:
        d = summ["by_class"].setdefault(cls, dict(instances=0, signals=0))
        d["instances"] += 1
        d["signals"] += sig
    if not io:
        cls_txt = ", ".join(f"{k} {v['instances']}" for k, v in sorted(summ["by_class"].items()))
        R.err("die_io_plan", f"no die IO planned (die.io empty): {len(inst)} IO-class instances "
              f"({cls_txt or 'none'}) and the "
              "host link have no bump / pad window (generate: python3 tools/die_plan/die_io.py plan PLAN --inplace)")
        summ["uncovered"] = len(inst)
        return summ
    for pn, ci, cls, sig, pitch, basis, r in inst:
        ok = [w for w in io if w.get("iface") == cls and w.get("part") == pn]
        if not ok:
            summ["uncovered"] += 1
            R.err("die_io_plan", f"{cls} {pn}.{ci}: no die.io window (iface {cls}) over it", type=P.parts[pn]["type"],
                  part=pn)
    for w in io:
        r = w["rect_um"]
        d = edge_dist(P, r)
        tn = P.parts[w["part"]]["type"] if w.get("part") in P.parts else None
        if w.get("iface") in ("serdes", "ucie", "hbm_phy") and d > edge_max + EPS:
            summ["off_shore"] += 1
            R.err("die_io_plan", f"io window {w['name']} ({w['iface']}): {d:.0f} um from the die edge > io_edge_max_um "
                  f"{edge_max:g} (the bump field / PHY must sit on the shoreline)", type=tn, part=w.get("part"))
        ex = w.get("bump_exclude_um") or []
        for e in ex:
            if not (e[0] >= r[0] - EPS and e[1] >= r[1] - EPS and e[2] <= r[2] + EPS and e[3] <= r[3] + EPS):
                R.err("die_io_plan", f"io window {w['name']}: bump_exclude_um {e} outside the window {r}", type=tn,
                      part=w.get("part"))
        if ex and w.get("pitch_um"):
            left = count_sites(r, w["pitch_um"], ex)
            if w["sites"] > left:
                R.err("die_io_plan", f"io window {w['name']}: sites {w['sites']} > {left} pitch sites outside "
                      f"bump_exclude_um", type=tn, part=w.get("part"))
        sig = w.get("signals")
        if sig is not None and sig > w["sites"]:
            summ["over_sites"] += 1
            R.err("die_io_plan", f"io window {w['name']}: {sig} off-die signals > {w['sites']} sites", type=tn,
                  part=w.get("part"))
    hw = [w["name"] for w in io if w.get("iface") == "host" or w.get("host") is True]
    ib = [w for w in io if w.get("host") == "in_band"]
    summ["host"] = hw + [w["name"] for w in ib]
    summ["host_mode"] = "in_band" if ib and not hw else ("dedicated" if hw and not ib else ("mixed" if hw else None))
    bad = [w["name"] for w in io if w.get("host") not in (None, False, True, "in_band")]
    if bad:
        R.err("die_io_plan", f"io windows {bad}: host must be true or \"in_band\"")
    if hw and ib:
        R.err("die_io_plan", f"host link windows {hw} AND in-band host windows {[w['name'] for w in ib]}: a die has "
              "either a host link or in-band host traffic")
    elif ib:
        hp = set(host_parts(P))
        for w in ib:
            if w.get("iface") not in HOST_CARRIERS:
                R.err("die_io_plan", f"io window {w['name']}: in-band host on iface {w.get('iface')} (serdes / ucie only)")
            elif w.get("host_route"):
                st, lanes = parse_route(w["host_route"])
                _, err = route_path(P, st, lanes, hp) if st == w["part"] else (None, f"starts at {st}, not {w['part']}")
                if err:
                    R.err("die_io_plan", f"io window {w['name']}: in-band host route {w['host_route']!r}: {err}")
            elif not hp or not host_path(P, w["part"], hp):
                R.err("die_io_plan", f"io window {w['name']}: in-band host, but no lane route from {w['part']} to the "
                      f"host logic ({', '.join(sorted(hp)) or 'none on this die'})")
    elif not hw:
        R.err("die_io_plan", "no host link window (a die.io entry with iface 'host' or host: true, or in-band host "
              "windows host: \"in_band\")")
    return summ


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["plan"])
    ap.add_argument("plan_json")
    ap.add_argument("--inplace", action="store_true", help="write die.io into the plan (keeps existing port windows)")
    ap.add_argument("--out", help="write the proposed die.io list to this JSON file")
    ap.add_argument("--in-band-host", help="comma-separated PART[=LANE+LANE...]: partitions whose link windows carry "
                    "the host traffic in-band (the die has no host link): host: \"in_band\" instead of the BFS host "
                    "guess; the optional lane chain declares the on-die ingress route to the host logic (checked)")
    ap.add_argument("--corner-keepout-um", type=float, default=0.0,
                    help="die-corner bump depopulation square (S81-XDIE): windows overlapping it get bump_exclude_um")
    ap.add_argument("--phy-zone-guard-um", type=float, default=None,
                    help="S81-XDIE: shrink each serdes window (no placed PHY footprint) to the free cell beside its "
                         "partition strip, this guard from the face-window bands (phy_zone)")
    a = ap.parse_args(argv)
    raw = S.load(a.plan_json)
    P = S.Plan(raw)
    ib = []
    for x in (a.in_band_host or "").split(","):
        if x:
            pn, _, lanes = x.partition("=")
            ib.append((pn, [l for l in lanes.split("+") if l] or None))
    io = plan(P, in_band=ib, corner_um=a.corner_keepout_um, phy_zone_guard=a.phy_zone_guard_um)
    keep = [w for w in (raw["die"].get("io") or []) if not w.get("iface")]
    new = keep + io
    if a.out:
        Path(a.out).write_text(json.dumps(new, indent=1) + "\n")
    if a.inplace:
        raw["die"]["io"] = new
        Path(a.plan_json).write_text(json.dumps(raw, indent=1) + "\n")
    for w in io:
        print(f"{w['name']:40s} {w['iface']:8s} sites {w['sites']:6d} signals {w['signals']:5d} "
              f"{'HOST-IN-BAND ' if w.get('host') == 'in_band' else 'HOST ' if w.get('host') else ''}"
              f"{w['basis'].split('; ')[-1]}")
    print(f"{len(io)} io windows ({len(keep)} port windows kept)")
    return 0


if __name__ == "__main__":
    sys.exit(main())


def check_pg_domains(P, R):
    """OWNER DECISION 7 (2026-10-24): IR over SerDes windows -> a separate PHY supply + dedicated bump rows per window.
    ERROR: a domain names an unknown io window, does not cover its windows, has bumps outside its rect or not over
    the window, or straps on a non-die layer.  WARN: a serdes window without a domain (not yet adopted)."""
    pg = P.die.get("pg", {}) or {}
    doms = pg.get("domains", []) or []
    io = {w["name"]: w for w in P.die.get("io", []) or []}
    die_layers = set(P.layer_budget.get("die_layers", []))

    def inside(a, b, e=0.01):
        return a[0] >= b[0] - e and a[1] >= b[1] - e and a[2] <= b[2] + e and a[3] <= b[3] + e
    covered = set()
    for d in doms:
        r = d["rect_um"]
        for n in d["io"]:
            w = io.get(n)
            if w is None:
                R.err("pg_domain", f"pg domain {d['name']}: io window {n} not in die.io")
                continue
            covered.add(n)
            if not inside(w["rect_um"], r):
                R.err("pg_domain", f"pg domain {d['name']}: rect {r} does not cover io window {n} {w['rect_um']}")
            b = d["bumps"]["rect_um"]
            if not (b[0] < w["rect_um"][2] and b[2] > w["rect_um"][0] and b[1] < w["rect_um"][3] and b[3] > w["rect_um"][1]):
                R.err("pg_domain", f"pg domain {d['name']}: bump rows {b} not over io window {n}")
        if not inside(d["bumps"]["rect_um"], r):
            R.err("pg_domain", f"pg domain {d['name']}: bump rect outside the domain rect")
        bx = d["bumps"].get("exclude_um") or []
        for e in bx:
            if not inside(e, d["bumps"]["rect_um"]):
                R.err("pg_domain", f"pg domain {d['name']}: bumps.exclude_um {e} outside the bump rect")
        for e in d.get("esd_um") or []:
            if not inside(e, r):
                R.err("pg_domain", f"pg domain {d['name']}: esd_um {e} outside the domain rect")
        for n in d["io"]:
            for e in (io.get(n) or {}).get("bump_exclude_um") or []:
                if not any(inside(e, x) for x in bx):
                    R.err("pg_domain", f"pg domain {d['name']}: io window {n} bump_exclude_um {e} not in the domain's "
                          f"bumps.exclude_um (power bumps in the die-corner stress zone)")
        for g in d["grid"]:
            if die_layers and g["layer"] not in die_layers:
                R.err("pg_domain", f"pg domain {d['name']}: strap layer {g['layer']} not a die layer {sorted(die_layers)}")
            if g["width_um"] >= g["pitch_um"] / 2:
                R.err("pg_domain", f"pg domain {d['name']}: {g['layer']} width {g['width_um']} >= half pitch (two nets)")
    for n, w in io.items():
        if w.get("iface") == "serdes" and n not in covered:
            R.warn("pg_domain", f"serdes window {n}: no separate PHY supply / bump rows (OWNER decision 7)")
    return dict(domains=len(doms), serdes_windows=sum(1 for w in io.values() if w.get("iface") == "serdes"),
                covered=len(covered))
