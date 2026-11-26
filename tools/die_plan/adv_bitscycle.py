#!/usr/bin/env python3
"""adv_bitscycle.py -- FP-CONVERGE-S81 11-25 (COORD ruling on FABLE-RC-S81 19:19), two report-only checks (WARN ADV-<NAME>, never a PRE verdict):

BITS-OVER-CYCLE  per dsdv_slice type: bits whose chain cannot make ONE CYCLE.  Two sources, both reported:
   PLAN    internal_stations / ft_slots chains (from_um -> regs_um -> to_um, Manhattan hops, horizontal first).  A chain is
           "over cycle" when its longest hop is > CYCLE_UM (580 um, the placed_scan cycle_um: one 833 ps cycle of repeated wire) and "over reach"
           when > REACH_UM (405 um, cbc_rules.REACH_GATE_UM).  Bits = the row's bits, else the width of the bus named by conn 'bus:<n>'
           in buses[], else the ft slot width; rows with no resolvable bits count as chains only.
   PLACED  the last placed_scan.json of the type (tools/autopilot/placed_scan.py: bits_over_cycle = bits whose PLACED hop > cycle_um,
           groups_need_station) found in $OT_PLACED_SCAN_DIRS (colon list; any dir below with geom/placed_scan.json or placed_scan.json,
           matched on the scan's "type"; newest mtime wins).  This is the measured number the gate is about.
   GATE    bits_over_cycle = PLACED if a scan exists else PLAN.  dsdv route goals must stay behind GATE = 0 (launch gate, launch_gates.py).
   Report-only; with OT_BITS_OVER_CYCLE_BLOCK=1 `gate_lines()` callers fail (adv_bitscycle.py CLI exits 1; kit_preflight fails the kit).
   Evidence (FABLE-RC-S81 19:19): 13 slice families, 2,864-8,763 bits over one cycle, 41-83 groups need a station per type, and
   REACH-STATION-C11 places only 11 stations, so it cannot close without pricing every flagged group.

PIN-FACE-KVLEAF  kv_leaf types (KVLEAF-T2 evidence: pin faces pointing away from consumers, GRT 16.8M): a station chain whose launch (or
   capture) pin sits on a face F of its hard core and whose OTHER end (the consumer) lies BEHIND F (dot((far - pin), outward normal) < -AWAY_UM):
   the chain has to wrap round the core.  Reported per type: chains / bits away, bits x wrap length (2 x |dot|, um), share of face-pin chains.
   Face rule = adv_seatgap._face (pin within 2 um of the core face).
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402
import adv_fpconv as F0  # noqa: E402
import adv_seatgap as S  # noqa: E402

CYCLE_UM = 580.0
REACH_UM = 405.0
AWAY_UM = 5.0
MAX_EX = 3


def _xy(v):
    return S._xy(v)


def _hops(pts):
    h = []
    for p, q in zip(pts, pts[1:]):
        h.append(abs(q[0] - p[0]) + abs(q[1] - p[1]))
    return h


def _conn_bus(conn):
    m = re.search(r"bus:([^|\s]+)", str(conn or ""))
    return m.group(1) if m else None


def _bus_bits(t):
    m = {}
    for b in t.get("buses") or []:
        if isinstance(b, dict) and b.get("name") is not None:
            try:
                m[str(b["name"])] = int(b.get("width") or b.get("bits") or 0)
            except (TypeError, ValueError):
                pass
    return m


def plan_bits(t):
    """-> dict(chains, over_cycle_bits, over_cycle_chains, over_reach_bits, over_reach_chains, unknown_bits_chains, worst_um)"""
    bm = _bus_bits(t)
    r = dict(chains=0, over_cycle_bits=0, over_cycle_chains=0, over_reach_bits=0, over_reach_chains=0, unknown=0, worst_um=0.0)
    rows = []
    for s in t.get("internal_stations") or []:
        if isinstance(s, dict):
            b = s.get("bits")
            if b is None:
                b = bm.get(_conn_bus(s.get("conn")))
            rows.append((s, b))
    for s in t.get("ft_slots") or []:
        if isinstance(s, dict):
            rows.append(({"from_um": None, "regs_um": s.get("regs_um"), "to_um": None, "_ft": True}, s.get("width")))
    for s, b in rows:
        pts = [p for p in [_xy(s.get("from_um"))] + [_xy(x) for x in s.get("regs_um") or []] + [_xy(s.get("to_um"))] if p]
        if len(pts) < 2:
            continue
        r["chains"] += 1
        w = max(_hops(pts))
        r["worst_um"] = max(r["worst_um"], w)
        try:
            bits = int(b)
        except (TypeError, ValueError):
            bits = None
        if bits is None:
            r["unknown"] += 1
            bits = 0
        if w > CYCLE_UM:
            r["over_cycle_chains"] += 1
            r["over_cycle_bits"] += bits
        if w > REACH_UM:
            r["over_reach_chains"] += 1
            r["over_reach_bits"] += bits
    return r


def load_scans(dirs=None, environ=None):
    """{type: (mtime, path, scan)} newest placed_scan.json per type under the dirs ($OT_PLACED_SCAN_DIRS, colon list)"""
    env = os.environ if environ is None else environ
    ds = dirs if dirs is not None else [x for x in (env.get("OT_PLACED_SCAN_DIRS") or "").split(":") if x]
    out = {}
    for d in ds:
        pats = [os.path.join(d, "placed_scan.json"), os.path.join(d, "geom", "placed_scan.json"),
                os.path.join(d, "*", "geom", "placed_scan.json"), os.path.join(d, "**", "placed_scan.json")]
        seen = set()
        for pat in pats:
            for f in glob.glob(pat, recursive=True):
                if f in seen:
                    continue
                seen.add(f)
                try:
                    sc = json.loads(Path(f).read_text())
                    ty = sc.get("type")
                    mt = os.path.getmtime(f)
                except (OSError, ValueError, AttributeError):
                    continue
                if ty and (ty not in out or mt > out[ty][0]):
                    out[ty] = (mt, f, sc)
    return out


def family(tn):
    return str(tn).split("__")[0]


def type_report(tn, t, scans):
    p = plan_bits(t)
    sc = scans.get(tn)
    d = dict(type=tn, family=family(tn), plan=p, placed=None)
    if sc:
        s = sc[2]
        d["placed"] = dict(bits_over_cycle=int(s.get("bits_over_cycle") or 0), bits_over_reach=int(s.get("bits_over_reach") or 0),
                           groups_need_station=int(s.get("groups_need_station") or 0), path=sc[1])
    d["gate_bits"] = d["placed"]["bits_over_cycle"] if d["placed"] else p["over_cycle_bits"]
    d["gate_source"] = "placed" if d["placed"] else "plan"
    return d


def census(raw, scans=None, prefix="dsdv_slice"):
    scans = load_scans() if scans is None else scans
    rows = [type_report(tn, t, scans) for tn, t in F0._types(raw) if tn.startswith(prefix)]
    fam = {}
    for r in rows:
        f = fam.setdefault(r["family"], dict(types=0, plan_bits=0, placed_types=0, placed_bits=0, groups=0))
        f["types"] += 1
        f["plan_bits"] += r["plan"]["over_cycle_bits"]
        if r["placed"]:
            f["placed_types"] += 1
            f["placed_bits"] += r["placed"]["bits_over_cycle"]
            f["groups"] += r["placed"]["groups_need_station"]
    return rows, fam


def findings(raw, plan_path, tree=None, **_k):
    rows, fam = census(raw)
    out = []
    for r in rows:
        p, pl = r["plan"], r["placed"]
        if r["gate_bits"] > 0 or p["over_reach_bits"] > 0:
            out.append(F0._w("BITS-OVER-CYCLE", r["type"],
                             f"gate {r['gate_bits']} bits over one cycle ({r['gate_source']}); plan {p['over_cycle_bits']} bits over {CYCLE_UM:g} um in "
                             f"{p['over_cycle_chains']} chain(s), {p['over_reach_bits']} over {REACH_UM:g} um in {p['over_reach_chains']} (worst hop {p['worst_um']:.0f} um)"
                             + (f"; placed {pl['bits_over_cycle']} bits, {pl['groups_need_station']} group(s) need a station" if pl else "; no placed scan")))
    for f, v in sorted(fam.items()):
        out.append(F0._w("BITS-OVER-CYCLE", f"family {f}: {v['types']} type(s), plan {v['plan_bits']} bits over a cycle, placed {v['placed_bits']} bits / "
                         f"{v['groups']} groups need a station in {v['placed_types']} scanned type(s)"))
    n = sum(1 for r in rows if r["gate_bits"] > 0)
    return out + [F0._w("BITS-OVER-CYCLE", f"summary {len(fam)} families, {n} of {len(rows)} dsdv_slice types with bits over one cycle (report only; "
                        f"OT_BITS_OVER_CYCLE_BLOCK=1 blocks route goals)")]


def blocking(environ=None):
    return (os.environ if environ is None else environ).get("OT_BITS_OVER_CYCLE_BLOCK") == "1"


def gate_lines(kit_type, goal, raw=None, scan_dirs=None, kit=None, environ=None):
    """launch-gate lines for ONE kit: a dsdv_slice kit at a ROUTE goal must have bits_over_cycle = 0.  [] for other types / goals."""
    env = os.environ if environ is None else environ
    if not str(kit_type).startswith("dsdv_slice") or str(goal or "").lower() != "route":
        return []
    ds = list(scan_dirs or []) + [x for x in (env.get("OT_PLACED_SCAN_DIRS") or "").split(":") if x]
    if kit:
        ds.append(str(kit))
    scans = load_scans(ds, env)
    t = ((raw or {}).get("partition_types") or {}).get(kit_type) or {}
    r = type_report(kit_type, t, scans)
    if r["gate_bits"] > 0:
        return [F0._w("BITS-OVER-CYCLE", kit_type, f"route goal refused: {r['gate_bits']} bits over one cycle ({r['gate_source']}"
                      + (f", {r['placed']['groups_need_station']} groups need a station" if r["placed"] else "") + "); run a place probe and close it first")]
    if not r["placed"]:
        return [F0._w("BITS-OVER-CYCLE", kit_type, "route goal with no placed scan: bits_over_cycle unknown (plan 0); run the place probe first")]
    return []


# ---------------------------------------------------------------- PIN-FACE-KVLEAF
def pin_face_away(t):
    """-> (away_chains, face_chains, away_bits, bits_x_wrap, [(conn, end, bits, wrap_um)])"""
    rects = G.hard_rects(t)
    bm = _bus_bits(t)
    aw = tot = 0
    abits = bw = 0
    ex = []
    for i, s in enumerate(t.get("internal_stations") or []):
        if not isinstance(s, dict):
            continue
        fr, to = _xy(s.get("from_um")), _xy(s.get("to_um"))
        try:
            bits = int(s.get("bits") if s.get("bits") is not None else bm.get(_conn_bus(s.get("conn")), 0) or 0)
        except (TypeError, ValueError):
            bits = 0
        for end, core_name, pin, far in (("launch", s.get("launch"), fr, to), ("capture", s.get("capture"), to, fr)):
            if pin is None or far is None or not core_name:
                continue
            r = S._core_of(core_name, rects)
            if r is None:
                continue
            n = S._face(pin, r)
            if n is None:
                continue
            tot += 1
            dot = (far[0] - pin[0]) * n[0] + (far[1] - pin[1]) * n[1]
            if dot < -AWAY_UM:
                wrap = 2.0 * -dot
                aw += 1
                abits += bits
                bw += bits * wrap
                ex.append((s.get("conn", f"#{i}"), end, bits, round(wrap)))
    return aw, tot, abits, bw, ex


def pin_face_findings(raw, plan_path, tree=None, **_k):
    out, n, ta, tt = [], 0, 0, 0
    for tn, t in F0._types(raw):
        if "kv_leaf" not in tn:
            continue
        a, tot, ab, bw, ex = pin_face_away(t)
        ta, tt = ta + a, tt + tot
        if a:
            n += 1
            out.append(F0._w("PIN-FACE-KVLEAF", tn, f"{a} of {tot} face-pin chain ends have the consumer behind the pin face ({100.0 * a / tot:.0f}%), "
                             f"{ab} bits, bits x wrap {bw:.0f}:", "; ".join(f"{c} {e} {b}b wrap {w}um" for c, e, b, w in sorted(ex, key=lambda x: -x[2] * x[3])[:MAX_EX])))
    return out + [F0._w("PIN-FACE-KVLEAF", f"summary {n} kv_leaf types flagged, {ta} of {tt} face-pin chain ends against (report only)")]


F = {"BITS-OVER-CYCLE": findings, "PIN-FACE-KVLEAF": pin_face_findings}
findings_by_check = {k: G._safe(k, v) for k, v in F.items()}


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a:
        print("usage: adv_bitscycle.py PLAN.json [TYPE_PREFIX]   (exit 1 only with OT_BITS_OVER_CYCLE_BLOCK=1 and bits over one cycle)")
        return 2
    raw = json.loads(Path(a[0]).read_text())
    rows, fam = census(raw, prefix=a[1] if len(a) > 1 else "dsdv_slice")
    for x in findings(raw, a[0]):
        print(x)
    bad = any(r["gate_bits"] > 0 for r in rows)
    return 1 if (bad and blocking()) else 0


if __name__ == "__main__":
    sys.exit(main())
