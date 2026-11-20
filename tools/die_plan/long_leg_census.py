#!/usr/bin/env python3
"""long_leg_census.py -- LONG-LEG-0040: every single-cycle leg longer than the placed-hop cap (300 um; 200 um on half-cycle legs) on every placed kit.

PRECHECK-1119 kit_scan.py reports "legs>405" per kit from a sample and drops strap/core legs; the owner asked for ALL of them,
with their endpoints, so a station / pin / placement fix can be assigned per class.  This tool reuses that scan's OpenROAD
programme (long-wire DP over the combinational DAG, launch -> capture straight Manhattan distance; derived copy
long_leg_census_or.py also records the capture net and the endpoint kinds / masters).

  long_leg_census.py scan   --roots R[,R..] --out DIR [--jobs 4] [--mem-gb 14] [--max-age-h 72]   (on a gen host, under ot-run)
  long_leg_census.py census --in DIR [DIR ..] --tsv OUT.tsv --md OUT.md [--legs-tsv OUT.legs.tsv]  (aggregate, no OpenROAD)
  long_leg_census.py fleet  --out DIR [--hosts epyc2,...] [--tsv .. --md ..]                       (hub: ot-run scan on every gen host in parallel, pull, census)

Kit selection: per (die, type) the NEWEST kit (by directory epoch) that has a placed DB (3_place.odb, else a later stage ODB).
Read-only on kits.  One row per leg: die, type, family, bus, length, launch / capture name + kind, FIXED / MOVABLE per end,
station row (a plan slot / internal-station pattern of the kit names the endpoint), class a / b / c.

FIXED = a port pin, a macro / hard-core pin, or a plan station site (register named by a plan slot: u_bin_/u_bout_/u_lpad_ cells, or
matched by a kit istations.tcl pattern).  MOVABLE = any other std-cell logic.
Half-cycle: launch and capture edges differ (negedge register: DFFL* / DLL* master or an inverted clock pin): limit 200 um, class h.
rank1 = firm-site: one end is a face / station register and the other a movable register, i.e. the first rank behind (or ahead of) a face register, to be given a firm site.
Class: a both ends fixed (station / relay row, +1 cycle); b one end fixed (pin or macro site move, or a station); c both movable
(placement / region problem).
"""
import argparse
import collections
import concurrent.futures as cf
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REACH_UM = 300.0         # owner-approved placed-hop cap 11-20 (was the CBC 405 um reach); scan --reach overrides
HALF_UM = 200.0          # COORD 11-19: a leg launched or captured on a negedge face has half a cycle (~200-250 um)
IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
OR_SCRIPT = HERE / "long_leg_census_or.py"
OT_HEAVY = "/srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-heavy"
OT_RUN = "/srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-run"
ODB_STAGES = ["3_place.odb", "3_5_place_dp.odb", "4_1_cts.odb", "5_1_grt.odb", "5_2_route.odb", "5_route.odb", "6_final.odb"]
KIT_RE = re.compile(r"^(?P<type>.+?)-(route|place|cts|grt|kit|sign|signoff|flow|full)-(?P<host>[^-]+)-(?P<pid>\d+)-(?P<epoch>\d+)$")
STATION_RE = re.compile(r"(^|[./\\])u_(bin|bout|lpad|cland)_|(^|[._])(pinreg|ftst|ft_st)")
STRAP_RE = re.compile(r"(^|[._/:])(strap|tie|TIEHI|TIELO|count_strap)", re.I)      # as cbc_rules.STRAP_TIE
RESET_RE = re.compile(r"(^|[._/:\\])(rst|reset|raw_reset|arst|rstn|rst_n)(?![a-z])|u_cland_rst|u_rstr|rst_ft|reset_ring|rstring", re.I)     # reset-ring / reset-tree legs: their own class r
VARIANT_RE = re.compile(r"__(cl|pv)[0-9a-f]{8}")
GEN_HOSTS = ["epyc2", "intel1", "epyc7", "epyc8", "epyc9", "epyc10"]
CLEAN_IDX = re.compile(r"\\?\[\d+\\?\]|(?<=[a-zA-Z_])\d+$|_\d+(?=[./]|$)")


# ---------------------------------------------------------------- pin geometry (pure)
def orient_point(x, y, orient, w, h):
    """master-frame point (x, y) of a w x h master -> offset from the lower-left of the PLACED bounding box, for the 8 LEF/DEF orients"""
    o = orient.upper().replace("MXR90", "MXR90")
    return {"R0": (x, y), "MY": (w - x, y), "MX": (x, h - y), "R180": (w - x, h - y),
            "R90": (h - y, x), "R270": (y, w - x), "MXR90": (y, x), "MYR90": (h - y, w - x)}[o]


def longest_launches_by_edge(sources, sink_xy):
    """Retain the longest-wire launch independently on each clock edge.

    Each source supplies its pin location and paths of the form
    (wire length, launch name, launch location, launched on falling edge).
    """
    best = {}
    for (x, y), paths in sources:
        distance = abs(x - sink_xy[0]) + abs(y - sink_xy[1])
        for length, launch, launch_xy, falling in paths:
            accumulated = length + distance
            previous = best.get(falling)
            if previous is None or accumulated > previous[0]:
                best[falling] = (accumulated, launch, launch_xy, falling)
    return tuple(best.values())


def pin_centroid(rects, orient, ll, size):
    """area-weighted centroid (um) of master-frame pin rects (x0, y0, x1, y1) of a macro placed with `orient` whose placed bbox lower-left
    is `ll`; `size` = (master width, height).  The leg end of a macro / hard-core pin sits HERE, not at the macro centre."""
    sx = sy = sa = 0.0
    for x0, y0, x1, y1 in rects:
        a = max(1e-9, (x1 - x0) * (y1 - y0))
        cx, cy = orient_point((x0 + x1) / 2.0, (y0 + y1) / 2.0, orient, size[0], size[1])
        sx, sy, sa = sx + a * cx, sy + a * cy, sa + a
    return ll[0] + sx / sa, ll[1] + sy / sa


# ---------------------------------------------------------------- kit selection
def kit_parts(name):
    m = KIT_RE.match(name)
    return (m.group("type"), int(m.group("epoch"))) if m else (name, 0)


def base_type(tn):
    """plan-variant hashes (__cl<hex>, __pv<hex>) stripped: the newest attempt of a type, whichever variant it was"""
    return VARIANT_RE.sub("", tn)


def placed_odb(kit):
    res = Path(kit, "work/run/results")
    for st in ODB_STAGES:
        c = sorted(res.glob(f"*/*/base/{st}"))
        if c:
            return c[0]
    return None


def kit_budget(kit):
    try:
        return json.loads(Path(kit, "work/budget.json").read_text())
    except (OSError, ValueError):
        return {}


def select_kits(roots, max_age_h=72.0, now=None, dies=()):
    """{(die, type): kit} newest placed attempt per type"""
    now = now or time.time()
    best = {}
    for root in roots:
        for cfg in Path(root).glob("*/work/config.mk"):
            kit = cfg.parent.parent
            tn, epoch = kit_parts(kit.name)
            odb = placed_odb(kit)
            if not odb or now - odb.stat().st_mtime < 60 or (max_age_h and now - odb.stat().st_mtime > max_age_h * 3600):
                continue
            b = kit_budget(kit)
            if dies and (b.get("die") or "?") not in dies:
                continue
            key = (b.get("die") or "?", base_type(b.get("type") or tn))
            rank = (epoch, odb.stat().st_mtime)
            if key not in best or rank > best[key][0]:
                best[key] = (rank, kit, odb)
    return {k: (v[1], v[2]) for k, v in best.items()}


# ---------------------------------------------------------------- station rows of a kit
def station_patterns(kit):
    """plan station rows of the kit: slot names of ft_stations.txt, land_slots.json buses, istations.tcl is_place patterns"""
    slots, pats = set(), []
    w = Path(kit, "work")
    try:
        for ln in (w / "ft_stations.txt").read_text().splitlines():
            if ln.strip() and not ln.startswith("#"):
                slots.add(ln.split()[0])
    except OSError:
        pass
    try:
        for b in (json.loads((w / "land_slots.json").read_text()).get("buses") or {}):
            if not b.startswith("cland_"):
                slots.add(re.sub(r"_[io]$", "", b))
    except (OSError, ValueError):
        pass
    try:
        for m in re.finditer(r"is_place\s+(\{[^}]*\}|\S+)", (w / "istations.tcl").read_text()):
            pats.append(m.group(1).strip("{}").replace("\\", ""))
    except OSError:
        pass
    return sorted(slots), pats


# ---------------------------------------------------------------- scan (host side)
def run_or(kit, odb, out_json, mem_gb, reach=REACH_UM, netlen=False):
    o = out_json.parent
    cmd = ["docker", "run", "--rm", "--name", f"llc-{os.getpid()}-{out_json.stem[-12:]}", "--cpus=1", f"--memory={mem_gb}g", f"--memory-swap={mem_gb}g",
           "-e", "OT_ODB=/k/" + odb.name, "-e", "OT_OUT=/o/" + out_json.name, "-e", f"OT_REACH_UM={reach}", "-e", f"OT_NETLEN={int(netlen)}",
           "-v", f"{odb.parent}:/k:ro", "-v", f"{o}:/o", "-v", f"{HERE}:/s:ro", IMAGE, "bash", "-lc",
           "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /s/long_leg_census_or.py > /o/%s.log 2>&1; "
           "rc=$?; chown %d:%d /o/%s /o/%s.log 2>/dev/null; exit $rc" % (out_json.stem, os.getuid(), os.getgid(), out_json.name, out_json.stem)]
    if not os.access("/var/run/docker.sock", os.W_OK):
        cmd = ["sg", "docker", "-c", shlex.join(cmd)]
    if os.path.exists(OT_HEAVY):
        cmd = [OT_HEAVY, "--mem", str(mem_gb), "--tag", "llcensus", "--max-wait", "3600", "--"] + cmd
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10800).returncode


# ---------------------------------------------------------------- routed slack vs placed hop length (300 um cap check)
BINS = [(lo, lo + 50) for lo in range(100, 600, 50)]


def routed_kits(roots, per_type=2):
    """kits that reached sign-off STA (signoff/tt/ep_tt.tsv) and hold 6_final.odb: newest `per_type` per (die, base type)"""
    got = collections.defaultdict(list)
    for root in roots:
        for ep in Path(root).glob("*/work/signoff/tt/ep_tt.tsv"):
            kit = ep.parent.parent.parent.parent
            res = sorted(Path(kit, "work/run/results").glob("*/*/base/6_final.odb"))
            if not res:
                continue
            b = kit_budget(kit)
            tn = base_type(b.get("type") or kit_parts(kit.name)[0])
            got[(b.get("die") or "?", tn)].append((kit_parts(kit.name)[1], kit, res[0], ep))
    return [x[1:] for v in got.values() for x in sorted(v, reverse=True)[:per_type]]


def read_ep(path):
    d = {}
    for ln in Path(path).read_text().splitlines()[1:]:
        f = ln.split("\t")
        if len(f) >= 2:
            try:
                d[f[0]] = float(f[-1])
            except ValueError:
                pass
    return d


def inst_of(endpoint, insts):
    if endpoint in insts:
        return endpoint
    h = endpoint.rsplit("/", 1)[0]
    return h if h in insts else None


def slack_rows(legs, eps):
    """compact rows [um, slack_ps, launch_edge, capture_edge, station 0/1, direct 0/1, routed/pin-to-pin ratio or -1, die-class key] for the
    legs whose capture endpoint has a TT setup slack in the sign-off endpoint table (the endpoint's worst path, an approximation of the leg)"""
    byinst = {}
    for e, sl in eps.items():
        byinst.setdefault(e.rsplit("/", 1)[0] if e.rsplit("/", 1)[0] else e, sl)
        byinst[e] = sl
    rows = []
    for leg in legs:
        um, acc, la, lb = leg[0], leg[1], leg[2], leg[3]
        if um < BINS[0][0] or um >= BINS[-1][1] or la.startswith("port:") or lb.startswith("port:") or len(leg) < 15:
            continue
        sl = byinst.get(lb.replace("\\", ""))
        if sl is None:
            sl = byinst.get(lb)
        if sl is None:
            continue
        station = bool(STATION_RE.search(la.replace("\\", "")) or STATION_RE.search(lb.replace("\\", "")))
        direct = leg[13] == 0.0
        nl = leg[14]
        rows.append([um, sl, leg[11], leg[12], int(station), int(direct), round(nl / acc, 3) if (direct and nl > 0 and acc > 0) else -1])
    return rows


def cmd_slack_scan(a):
    import socket
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = []
    for kit, odb, ep in routed_kits([r for r in a.roots.split(",") if r], a.per_type)[: a.max_kits]:
        raw = out / "raw" / f"{kit.name}.slack_pin3.json"
        raw.parent.mkdir(parents=True, exist_ok=True)
        if not raw.exists():
            rc = run_or(kit, odb, raw, a.mem_gb, reach=100.0, netlen=True)
            if rc or not raw.exists():
                res.append(dict(kit=kit.name, status=f"FAILED rc {rc}"))
                continue
        legs = json.loads(raw.read_text()).get("legs") or []
        eps = read_ep(ep)
        rows = slack_rows(legs, eps)
        res.append(dict(kit=kit.name, die=kit_budget(kit).get("die"), type=base_type(kit_budget(kit).get("type") or ""), status="OK",
                        legs=len(legs), endpoints=len(eps), rows=rows))
    dst = out / f"{socket.gethostname()}.slack.jsonl"
    dst.write_text("".join(json.dumps(r) + "\n" for r in res))
    print(f"slack scan: {len(res)} kits, {sum(len(r.get('rows', [])) for r in res)} joined legs -> {dst}")
    return 0


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]


def crossing(xs, ys, level, below=True):
    """first bin centre (um) where the series y crosses `level` going down (y <= level), linear interpolation between bin centres, else None"""
    for i, y in enumerate(ys):
        if y is not None and y <= level:
            if i and ys[i - 1] is not None and ys[i - 1] > level:
                x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], y
                return round(x0 + (x1 - x0) * (y0 - level) / (y0 - y1), 0)
            return xs[i]
    return None


def slack_report(rows, minn=30):
    """-> markdown: median / p10 TT slack per 50 um bin for full vs half cycle and station vs logic, crossings, routed/placed ratio"""
    groups = {"full-cycle logic": [], "full-cycle station": [], "half-cycle logic": [], "half-cycle station": []}
    for um, sl, ea, eb, st, direct, ratio in rows:
        groups[("half" if ea != eb else "full") + "-cycle " + ("station" if st else "logic")].append((um, sl, ratio))
    o = ["## 300 um cap check: routed TT setup slack vs placed hop length", "",
         "Single-cycle register-to-register legs (pin to pin, placed distance on the routed 6_final.odb), endpoint TT setup slack from the kit sign-off "
         "endpoint table (signoff/tt/ep_tt.tsv = the endpoint's worst path, an approximation of the leg). Bins of 50 um, 100-600 um; bins with fewer than "
         f"{minn} legs are shown as n/a. Median slack crossing 0 and p10 slack crossing -42 ps are linearly interpolated between bin centres.", ""]
    for name, g in groups.items():
        xs, med, p10, cnt = [], [], [], []
        for lo, hi in BINS:
            v = [sl for um, sl, _ in g if lo <= um < hi]
            xs.append((lo + hi) / 2)
            cnt.append(len(v))
            med.append(round(pct(v, 0.5), 1) if len(v) >= minn else None)
            p10.append(round(pct(v, 0.1), 1) if len(v) >= minn else None)
        o += [f"### {name} ({len(g)} legs)", "", "| bin um | legs | median slack ps | p10 slack ps |", "|---|---|---|---|"]
        for (lo, hi), n, m, p in zip(BINS, cnt, med, p10):
            o.append(f"| {lo}-{hi} | {n} | {m if m is not None else 'n/a'} | {p if p is not None else 'n/a'} |")
        o += ["", f"median slack crosses 0 ps at: {crossing(xs, med, 0.0)} um; p10 slack crosses -42 ps at: {crossing(xs, p10, -42.0)} um", ""]
    ratios = [r for g in groups.values() for _, _, r in g if r > 0]
    if ratios:
        o.append(f"Routed / placed wire length (direct single-net legs, routed net length over placed pin-to-pin Manhattan): median {pct(ratios, 0.5):.2f}, "
                 f"p10 {pct(ratios, 0.1):.2f}, p90 {pct(ratios, 0.9):.2f} over {len(ratios)} legs.")
    else:
        o.append("Routed / placed wire length: not measured (routed net length unavailable from the DB).")
    return "\n".join(o) + "\n"


def cmd_slack_report(a):
    rows, kits = [], []
    for d in a.inp:
        for f in sorted(Path(d).glob("*.slack.jsonl")):
            for x in f.read_text().splitlines():
                if x.strip():
                    r = json.loads(x)
                    kits.append(f"{r.get('die')}/{r.get('type')} ({r.get('status')}, {len(r.get('rows', []))} legs)")
                    rows += r.get("rows", [])
    md = slack_report(rows) + "\nKits: " + "; ".join(kits) + "\n"
    Path(a.md).write_text(md)
    print(f"slack report: {len(rows)} legs from {len(kits)} kits -> {a.md}")
    return 0


def scan_one(key, kit, odb, out, mem_gb):
    die, tn = key
    raw = out / "raw" / f"{kit.name}.pin3.json"      # precise macro terminals plus independent launch edges
    raw.parent.mkdir(parents=True, exist_ok=True)
    if not raw.exists() or raw.stat().st_mtime < odb.stat().st_mtime:
        rc = run_or(kit, odb, raw, mem_gb)
        if rc or not raw.exists():
            return dict(die=die, type=tn, kit=kit.name, status=f"FAILED rc {rc}")
    r = json.loads(raw.read_text())
    slots, pats = station_patterns(kit)
    return dict(die=die, type=tn, kit=kit.name, odb=odb.name, status="OK", n_regs=r.get("n_regs"), macros=r.get("macros") or [],
                legs=r.get("legs") or [], slots=slots, patterns=pats)


def cmd_scan(a):
    import socket
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    kits = select_kits([r for r in a.roots.split(",") if r], a.max_age_h, dies=tuple(x for x in a.dies.split(",") if x))
    rows = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = [ex.submit(scan_one, k, v[0], v[1], out, a.mem_gb) for k, v in sorted(kits.items())]
        for f in futs:
            try:
                rows.append(f.result())
            except Exception as e:  # noqa: BLE001 -- one kit never stops the pass
                rows.append(dict(status=f"ERROR {type(e).__name__}: {e}"))
    dst = out / f"{socket.gethostname()}.scan.jsonl"
    dst.write_text("".join(json.dumps(r) + "\n" for r in rows))
    ok = sum(1 for r in rows if r.get("status") == "OK")
    print(f"long_leg_census scan: {len(rows)} kits, {ok} OK, {sum(len(r.get('legs', [])) for r in rows)} legs > {REACH_UM:.0f} um -> {dst}")
    return 0


# ---------------------------------------------------------------- classification (pure)
def family_of(tn):
    return re.sub(r"__.*$", "", base_type(tn))


def norm_bus(s):
    s = (s or "").lstrip("\\")
    s = s.split("/")[0] if "/" in s else s
    s = re.sub(r"\$_\w+$", "", s)
    s = re.sub(r"^u_bound\.", "", s)
    s = re.sub(r"\\?\[\d+\\?\]", "", s)
    s = re.sub(r"src_[0-9a-f]{8,}", "src_H", s)
    s = re.sub(r"(_\d+)+(?=\.|$|_[a-z])", "", s)
    s = re.sub(r"\d+$", "", s)
    return s.rstrip("_.")


def slot_token(name):
    m = re.search(r"u_(?:bin|bout|lpad|cland)_(.+?)(?:[./]|$)", name.lstrip("\\"))
    return norm_bus(m.group(1)) if m else None


def bus_of(launch, capture):
    """class bus name: the port bus, else the station slot, else the normalised capture register (hierarchy kept to the last 2 levels)"""
    for n in (capture, launch):
        if n.startswith("port:"):
            return norm_bus(n[5:])
    for n in (capture, launch):
        t = slot_token(n)
        if t:
            return t
    parts = norm_bus(capture).split(".")
    return ".".join(parts[-2:])[-60:]


def compile_rows(slots, pats):
    """one regex for the glob patterns and one for the slot names of a kit (a kit has thousands: per-name loops were too slow)"""
    pr = re.compile("|".join("(?:%s)" % fnmatch.translate(p) for p in pats)) if pats else None
    sr = re.compile(r"(^|[._/])(?:" + "|".join(re.escape(x) for x in slots if x) + r")(?=[._/\d]|$)") if any(slots) else None
    return pr, sr


def kind_of(name, master, macros_hit, slots, pats, compiled=None):
    """-> (kind label, FIXED?, station-row?)"""
    clean = name.replace("\\", "")
    if name.startswith("port:"):
        return "port", True, False
    if master.startswith("macro:") or macros_hit:
        return "macro", True, False
    in_row = bool(STATION_RE.search(clean))
    pr, sr = compiled if compiled else compile_rows(slots, pats)
    row = bool((pr and pr.match(clean)) or (sr and sr.search(clean)))
    return ("station" if (in_row or row) else "logic"), (in_row or row), row or in_row


def in_macro(loc, macros, tol=1.0):
    x, y = loc
    return any(r[0] - tol <= x <= r[2] + tol and r[1] - tol <= y <= r[3] + tol for r in macros)


def classify_rows(scan_rows):
    """legs of the scan rows -> list of dicts (one per leg, strap / tie legs kept but marked)"""
    out = []
    for r in scan_rows:
        if r.get("status") != "OK":
            continue
        memo = {}
        comp = compile_rows(r["slots"], r["patterns"])

        def kof(n, m, r=r, memo=memo, comp=comp):
            k = (n, m)
            if k not in memo:
                memo[k] = kind_of(n, m, False, r["slots"], r["patterns"], comp)
            return memo[k]
        for leg in r["legs"]:
            straight, acc, la, lb, pin, pa, pb, net = leg[:8]
            ma, mb = (leg[8], leg[9]) if len(leg) > 9 else ("?", "?")
            legacy = leg[10] if len(leg) > 10 else straight
            ea, eb = (leg[11], leg[12]) if len(leg) > 12 else ("p", "p")
            half = ea != eb
            lim = HALF_UM if half else REACH_UM
            ka, fa, ra = kof(la, ma)
            kb, fb, rb = kof(lb, mb)
            isrst = bool(RESET_RE.search(la) or RESET_RE.search(lb) or RESET_RE.search(net))
            cls = "h" if half else ("r" if isrst else ("a" if (fa and fb) else ("b" if (fa or fb) else "c")))
            out.append(dict(limit=lim, launch_edge=ea, capture_edge=eb, fcls=("a" if (fa and fb) else ("b" if (fa or fb) else "c")), legacy_um=legacy, die=r["die"], type=r["type"], family=family_of(r["type"]), kit=r["kit"], um=straight, bus=bus_of(la, lb), net=net,
                            launch=la, launch_kind=ka, launch_fixed="FIXED" if fa else "MOVABLE", capture=lb, capture_kind=kb,
                            capture_fixed="FIXED" if fb else "MOVABLE", station_row="yes" if (ra or rb) else "no", cls=cls,
                            rank1=("firm-site" if ((ka == "station") != (kb == "station") and "port" not in (ka, kb) and "macro" not in (ka, kb)) else ""),
                            strap=bool(STRAP_RE.search(la) or STRAP_RE.search(lb)),
                            changed=("new" if (legacy <= lim < straight) else ("dropped" if (straight <= lim < legacy) else ""))))
    return out


FIX = {"r": "reset-ring / reset-tree leg (own class): relay rank per <= 300 um hop in the reset tree (plan reset row), not a data station; fixed/movable split in fcls",
       "h": "half-cycle face (negedge end, limit 200 um): retime to a posedge / full-cycle phase, or station row so each half-cycle hop is <= 200 um; fixed/movable ends in the leg rows",
       "a": "plan station / relay row (+1 cycle, pre-approved) on the leg",
       "b": "pin or macro-site move toward the fixed end, else a station row (+1 cycle)",
       "c": "placement / region fix: pull both registers into one region (or add a plan station row)"}


def owner_of(die, family, bus):
    f = family
    if die == "s81":
        if f.startswith("col"):
            return "S81-GEOM-OPUS"
        if "leaf" in f:
            return "FABLE-FIX-S81-LEAF-2140"
        if "serdes" in f:
            return "FABLE-FIX-S81-SERDES-0000"
        if f.startswith("dsdv_slice_c") or "slice_c" in f:
            return "FABLE-FIX-S81-SLICEC-0045"
        if "svc" in f or "dsdv" in f:
            return "S81-SVC-DSDV-0005"
        return "S81-DIE-R3"
    if die in ("s81_head", "head"):
        return "HEAD-CROSSING-1119"
    if die in ("qwen_compute", "qc"):
        return "QC-PLAN-R3"
    if die in ("qwen_kvsys", "kv"):
        if f.startswith(("hg", "kv_hg")) or "hg" in f.split("_"):
            return "FABLE-FIX-KV-HG-0000"
        if "pv" in f.split("_"):
            return "FABLE-FIX-KV-PV-2140"
        return "KV-D23-COMPOSE"
    return "COORD"


def aggregate(legs, include_strap=False):
    """one row per (die, bus class): types, worst um, class, fix, owner"""
    cls = collections.defaultdict(lambda: dict(types=set(), fams=collections.Counter(), n=0, worst=0.0, cls=collections.Counter(), ex=None, rows=set()))
    for L in legs:
        if (L["strap"] and not include_strap) or L["um"] <= L["limit"]:
            continue
        c = cls[(L["die"], L["bus"])]
        c["types"].add(L["type"])
        c["fams"][L["family"]] += 1
        c["n"] += 1
        c["cls"][L["cls"]] += 1
        c["rows"].add(L["station_row"])
        if L["um"] > c["worst"]:
            c["worst"], c["ex"] = L["um"], L
    rows = []
    for (die, bus), c in cls.items():
        main = max(c["cls"].items(), key=lambda kv: (kv[1], kv[0]))[0]
        fam = c["fams"].most_common(1)[0][0]
        rows.append(dict(die=die, bus=bus, family=fam, families=len(c["fams"]), types=len(c["types"]), legs=c["n"], worst_um=c["worst"],
                         cls=main, cls_mix="".join(f"{k}{v}" for k, v in sorted(c["cls"].items())), station_row="/".join(sorted(c["rows"])),
                         fix=FIX[main], owner=owner_of(die, fam, bus), example=f"{c['ex']['type']}: {c['ex']['launch']} -> {c['ex']['capture']}"))
    return sorted(rows, key=lambda r: (r["die"], -r["worst_um"]))


TSV_COLS = ["die", "bus", "family", "types", "legs", "worst_um", "cls", "cls_mix", "station_row", "fix", "owner", "example"]
LEG_COLS = ["die", "type", "bus", "um", "rank1", "limit", "launch_edge", "capture_edge", "fcls", "legacy_um", "changed", "launch", "launch_kind", "launch_fixed", "capture", "capture_kind", "capture_fixed", "station_row", "cls", "net", "kit"]


def write_tsv(path, rows, cols):
    Path(path).write_text("\t".join(cols) + "\n" + "".join("\t".join(str(r[c]) for c in cols) + "\n" for r in rows))


def summary_md(legs, agg, kits_ok, kits_failed, stamp):
    by = collections.defaultdict(lambda: collections.Counter())
    types = collections.defaultdict(set)
    worst = collections.defaultdict(float)
    chg = collections.defaultdict(collections.Counter)
    for L in legs:
        if L["changed"]:
            chg[L["die"]][L["changed"] + ("-" + L["cls"] if L["changed"] == "new" else "")] += 1
        if L["um"] <= L["limit"]:
            continue
        if L["strap"]:
            by[L["die"]]["strap/tie (excluded)"] += 1
            continue
        by[L["die"]][L["cls"]] += 1
        types[L["die"]].add(L["type"])
        worst[L["die"]] = max(worst[L["die"]], L["um"])
    o = [f"# LONG-LEG-CENSUS ({stamp})", "",
         f"Every single-cycle placed leg longer than {REACH_UM:.0f} um (launch -> capture straight Manhattan; register / port / macro ends), "
         f"newest placed kit per (die, type). Kits scanned OK {kits_ok}, failed {kits_failed}. Tool: tools/die_plan/long_leg_census.py. "
         "Class a = both ends FIXED (station / relay row, +1 cycle); b = one end fixed (pin or macro-site move, or station); c = both movable (placement / region).", "",
         "Class r = reset-ring / reset-tree leg (kept, own class, COORD 11-20). Class h = half-cycle leg (launch or capture on a negedge face, limit 200 um instead of 405); its fixed / movable split is in the leg rows (fcls).", "",
         "| die | legs (excl. strap/tie) | a | b | c | h (half-cycle) | r (reset ring) | types hit | worst um | bus classes |", "|---|---|---|---|---|---|---|---|---|---|"]
    for die in sorted(by):
        c = by[die]
        n = c["a"] + c["b"] + c["c"] + c["h"] + c["r"]
        o.append(f"| {die} | {n} | {c['a']} | {c['b']} | {c['c']} | {c['h']} | {c['r']} | {len(types[die])} | {worst[die]:.0f} | {sum(1 for r in agg if r['die'] == die)} |")
    o += ["", "## Legs that changed because macro / hard-core ends now sit at the pin shape (COORD 11-19)", "",
          "Old measure = macro / core centre. `new` = over 405 um only with the pin location (by class a / b / c); `dropped` = over 405 um at the core centre, not at the pin. "
          "Class a / b / c does not depend on length: a leg keeps its class, it enters or leaves the census.", ""]
    for die in sorted(by):
        o.append(f"- {die}: " + (", ".join(f"{k} {v}" for k, v in sorted(chg[die].items())) or "none"))
    for die in sorted(by):
        o += ["", f"## {die}", "", "| bus class | family | types | legs | worst um | class | station row | owner |", "|---|---|---|---|---|---|---|---|"]
        for r in [r for r in agg if r["die"] == die][:25]:
            o.append(f"| {r['bus']} | {r['family']} | {r['types']} | {r['legs']} | {r['worst_um']:.0f} | {r['cls']} ({r['cls_mix']}) | {r['station_row']} | {r['owner']} |")
    return "\n".join(o) + "\n"


def dedupe(rows):
    """one row per (die, base type) across hosts: the newest kit epoch (a failed scan never displaces an OK one)"""
    best = {}
    for r in rows:
        if "die" not in r:
            continue
        k = (r["die"], base_type(r["type"]))
        rank = (r.get("status") == "OK", kit_parts(r.get("kit", ""))[1])
        if k not in best or rank > best[k][0]:
            best[k] = (rank, r)
    return [v[1] for v in best.values()]


def cmd_census(a):
    rows = []
    for d in a.inp:
        for f in sorted(Path(d).glob("*.scan.jsonl")):
            rows += [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
    rows = dedupe(rows)
    legs = classify_rows([r for r in rows if not getattr(a, "die", "") or r.get("die") == a.die])
    agg = aggregate(legs)
    ok = sum(1 for r in rows if r.get("status") == "OK")
    write_tsv(a.tsv, agg, TSV_COLS)
    if a.legs_tsv:
        write_tsv(a.legs_tsv, sorted(legs, key=lambda r: (r["die"], -r["um"])), LEG_COLS)
    Path(a.md).write_text(summary_md(legs, agg, ok, len(rows) - ok, time.strftime("%Y-%m-%d %H:%M")))
    print(f"census: {ok} kits OK of {len(rows)}, {len(legs)} legs, {len(agg)} bus classes -> {a.tsv}, {a.md}")
    return 0


def cmd_fleet(a):
    """hub side: stage tool, ot-run the scan on each gen host in parallel, pull the scans, census"""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stage = "/srv/opentallas-scratch2/claude/long-leg-census"
    roots = ",".join(f"/srv/opentallas-scratch{s}/claude/ot-jobs" for s in ("", "2", "3"))

    def host(h):
        sh = lambda c: subprocess.run(["timeout", "900", "ssh", "-n", "-o", "ControlPath=none", h, c], capture_output=True, text=True)  # noqa: E731
        sh(f"mkdir -p {stage}/out")
        for f in (HERE / "long_leg_census.py", OR_SCRIPT):
            subprocess.run(["timeout", "300", "scp", "-o", "ControlPath=none", str(f), f"{h}:{stage}/{f.name}"], capture_output=True)
        r = subprocess.run([OT_RUN, "--mem", "2", "--hosts", h, "--dir", stage, "--stage", stage, "--", "python3", "-I", f"{stage}/long_leg_census.py"]
                           + (["slack-scan", "--roots", roots, "--out", f"{stage}/out", "--max-kits", str(a.max_kits), "--mem-gb", "24"] if a.mode == "slack" else
                              ["scan", "--roots", roots, "--out", f"{stage}/out", "--jobs", str(a.jobs), "--mem-gb", str(a.mem_gb), "--dies", a.dies]), capture_output=True, text=True, timeout=14400)
        subprocess.run(["timeout", "600", "scp", "-o", "ControlPath=none", f"{h}:{stage}/out/*.{a.mode if a.mode == 'slack' else 'scan'}.jsonl", str(out)], capture_output=True)
        return h, r.returncode, (r.stdout + r.stderr)[-200:]

    with cf.ThreadPoolExecutor(len(a.hosts.split(","))) as ex:
        for h, rc, tail in ex.map(host, a.hosts.split(",")):
            print(f"{h}: rc {rc} {tail.strip().splitlines()[-1] if tail.strip() else ''}")
    if a.mode == "slack":
        return cmd_slack_report(argparse.Namespace(inp=[str(out)], md=a.md))
    if a.tsv and a.md:
        return cmd_census(argparse.Namespace(inp=[str(out)], tsv=a.tsv, md=a.md, legs_tsv=a.legs_tsv, die=""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scan")
    s.add_argument("--roots", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--jobs", type=int, default=4)
    s.add_argument("--mem-gb", type=int, default=8)
    s.add_argument("--max-age-h", type=float, default=72.0)
    s.add_argument("--dies", default="")
    ss = sp.add_parser("slack-scan")
    ss.add_argument("--roots", required=True)
    ss.add_argument("--out", required=True)
    ss.add_argument("--per-type", type=int, default=2)
    ss.add_argument("--max-kits", type=int, default=6)
    ss.add_argument("--mem-gb", type=int, default=24)
    sr = sp.add_parser("slack-report")
    sr.add_argument("--in", dest="inp", nargs="+", required=True)
    sr.add_argument("--md", required=True)
    c = sp.add_parser("census")
    c.add_argument("--in", dest="inp", nargs="+", required=True)
    c.add_argument("--tsv", required=True)
    c.add_argument("--md", required=True)
    c.add_argument("--legs-tsv", default="")
    c.add_argument("--die", default="")
    f = sp.add_parser("fleet")
    f.add_argument("--out", required=True)
    f.add_argument("--hosts", default=",".join(GEN_HOSTS))
    f.add_argument("--jobs", type=int, default=4)
    f.add_argument("--mem-gb", type=int, default=8)
    f.add_argument("--dies", default="")
    f.add_argument("--mode", choices=["scan", "slack"], default="scan")
    f.add_argument("--max-kits", type=int, default=6)
    f.add_argument("--tsv", default="")
    f.add_argument("--md", default="")
    f.add_argument("--legs-tsv", default="")
    a = ap.parse_args(argv)
    return {"scan": cmd_scan, "census": cmd_census, "fleet": cmd_fleet, "slack-scan": cmd_slack_scan, "slack-report": cmd_slack_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
