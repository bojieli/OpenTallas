#!/usr/bin/env python3
"""plan_geom_census.py -- EVENT-CENSUS absolute pre-launch check (ADOPT-CENSUS-1800, COORD scope add 11-20): plan geometry only,
no placement, minutes per die, run at event compose time so lanes fix rows before the bind and the proofs.

Per placed type of the plan, every finding over the 300-um hop cap (Manhattan, plan coordinates):

  HOP        a signal hop between registers / stations: internal_stations from -> regs -> to (face-bus chains from the worst
             bit of the pin window, precheck WINDOW-HOP), ft_slots in pin -> regs -> out pin, and sink-side relay_depth rows of
             signal ports (path_um / (D + 1)).
  RESET_LEG  a reset leg: reset relay_depth rows (path_um / (D + 1)); reset.relay_um; a hard-core reset pin to the nearest
             planned reset seat (relay_sites, reset.local_taps_um, inst_taps) when the type plans seats and no relay row covers it.
  CORE_WIRE  a hard-core port (core_conns.json of the die) whose wire to the other end (another core's outline, or the type
             face window of a bus) is over 300 um with no station / relay row naming that core port: the slew case.
             The distance is a lower bound (pin to the nearest point of the other end).
  UNREG_READ a type with ROM / SRAM macros whose RTL offers a registered-read selector (`ifdef X, X matching --regread-re,
             e.g. OT_S81SL_LEP_RIP1, OT_S81SL_VP_SRAMREG) that the type's defines leave off.  The RTL closure is a kit's rtl/
             (--kits, the newest kit of the type from any event), its files read from THIS tree when it has them.

  plan_geom_census.py run   --die DIE --plan PLAN [--tools DIR] [--kits K ...] [--types GLOB] --out DIR
  plan_geom_census.py calib --plan PLAN [--tools DIR] --placed P.placed.json ... --out DIR
        (estimated worst station hop of the plan vs the measured worst register leg of placed kits, kit_scan PLACED records:
         precision / recall of the 300-um flag and the estimate / measured ratio)

An estimator and a list for the die lane: it never holds anything (event_census.py holds regressions vs the previous event).
"""
import argparse
import collections
import fnmatch
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import event_census as EC  # noqa: E402
sys.path.pop(0)

CAP_UM = 300.0
RST = re.compile(r"(?:^|[_.])(?:rst|reset|rstn|rst_n|rsn|rsf)(?:$|[_.\[])|rst_n|reset", re.I)
MEM = re.compile(r"sram|rom|_mem|rf_|regfile", re.I)
CHECKS = ("HOP", "RESET_LEG", "CORE_WIRE", "UNREG_READ")


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def rect_dist(p, r):
    """L1 from point p to rect (x0, y0, x1, y1)"""
    dx = max(r[0] - p[0], 0.0, p[0] - r[2])
    dy = max(r[1] - p[1], 0.0, p[1] - r[3])
    return dx + dy


def core_rect(c):
    o, s = c.get("origin_um") or [0, 0], c.get("outline_um") or [0, 0]
    w, h = (s[1], s[0]) if str(c.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90") else (s[0], s[1])
    return (o[0], o[1], o[0] + w, o[1] + h)


def pin_abs(c, x, y):
    """a core pin (core frame) in type coordinates for R0 / MX / MY / R180 (lef_origin: origin = lower-left of the placed box)"""
    o, (w, h) = c.get("origin_um") or [0, 0], (c.get("outline_um") or [0, 0])[:2]
    ori = str(c.get("orient", "R0"))
    if ori in ("MX", "FS"):
        return (o[0] + x, o[1] + h - y)
    if ori in ("MY", "FN"):
        return (o[0] + w - x, o[1] + y)
    if ori in ("R180", "S"):
        return (o[0] + w - x, o[1] + h - y)
    return (o[0] + x, o[1] + y)


_PINS = {}


def core_pins(die_dir, c):
    """{port base name: [(x, y) type frame]} from the core's pins_file (relative to the die plan dir); {} when unreadable"""
    f = c.get("pins_file")
    if not f:
        return {}
    p = Path(f) if os.path.isabs(f) else Path(die_dir) / f
    if str(p) not in _PINS:
        try:
            d = json.loads(p.read_text())
        except (OSError, ValueError):
            d = {}
        pins = d.get("pins", d) if isinstance(d, dict) else d
        rows = []
        if isinstance(pins, list):
            for q in pins:
                if isinstance(q, dict) and q.get("name") is not None:
                    xy = q.get("xy_um") or ([q["x"], q["y"]] if "x" in q and "y" in q else None)
                    if xy:
                        rows.append((str(q["name"]), float(xy[0]), float(xy[1])))
        elif isinstance(pins, dict):
            for n, q in pins.items():
                xy = (q.get("xy_um") if isinstance(q, dict) else q) or None
                if isinstance(xy, (list, tuple)) and len(xy) >= 2:
                    rows.append((str(n), float(xy[0]), float(xy[1])))
        _PINS[str(p)] = rows
    out = collections.defaultdict(list)
    for n, x, y in _PINS[str(p)]:
        out[n.split("[", 1)[0]].append(pin_abs(c, x, y))
    return out


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


# ---------------------------------------------------------------- the four checks

def hop_findings(t, cap=CAP_UM):
    out = [(v, d) for v, d in EC.hops_list(t, cap)]
    for r in t.get("relay_depth") or []:
        if RST.search(str(r.get("port", ""))):
            continue
        L, D = r.get("path_um"), int(r.get("D") or 0)
        if isinstance(L, (int, float)) and L / (D + 1) > cap:
            out.append((round(L / (D + 1), 1), f"relay_depth {r.get('inst')}.{r.get('port')} path {L} um D {D}"))
    return out


def reset_findings(t, die_dir, cap=CAP_UM):
    out, covered = [], set()
    r = t.get("reset") or {}
    if isinstance(r.get("relay_um"), (int, float)) and r["relay_um"] > cap:
        out.append((float(r["relay_um"]), f"reset.relay_um {r['relay_um']}"))
    for row in t.get("relay_depth") or []:
        if not RST.search(str(row.get("port", ""))):
            continue
        covered.add(str(row.get("inst")))
        L, D = row.get("path_um"), int(row.get("D") or 0)
        if isinstance(L, (int, float)) and L / (D + 1) > cap:
            out.append((round(L / (D + 1), 1), f"reset relay_depth {row.get('inst')}.{row.get('port')} path {L} um D {D} (leg {L / (D + 1):.0f})"))
    seats = [tuple(v) for v in (t.get("relay_sites") or {}).values() if isinstance(v, (list, tuple)) and len(v) >= 2]
    seats += [tuple(v[:2]) if isinstance(v, (list, tuple)) else tuple((v.get("xy_um") or [])[:2]) for v in r.get("local_taps_um") or []
              if (isinstance(v, (list, tuple)) and len(v) >= 2) or (isinstance(v, dict) and v.get("xy_um"))]
    if seats:
        for c in t.get("hard_cores") or []:
            if any(str(c.get("inst", "")).endswith(x) or x.endswith(str(c.get("inst", ""))) for x in covered):
                continue
            pins = core_pins(die_dir, c)
            rp = [p for n, ps in pins.items() if RST.search(n) for p in ps]
            if not rp:
                continue
            p = centroid(rp)
            d = min(man(p, s) for s in seats)
            if d > cap:
                out.append((round(d, 1), f"core {c.get('inst')} reset pin ({p[0]:.0f}, {p[1]:.0f}) -> nearest planned reset seat {d:.0f} um"))
    return out


def registered_ports(t):
    """core ports a station / relay row already registers ("inst.port" strings)"""
    s = set()
    for e in t.get("internal_stations") or []:
        if not (e.get("regs_um") or e.get("sites") or e.get("stations")):
            continue
        for k in ("conn", "launch", "capture"):
            for part in str(e.get(k, "")).split("|"):
                s.add(part[5:] if part.startswith("core:") else part)
                s.add(part)
    for r in t.get("relay_depth") or []:
        s.add(f"{r.get('inst')}.{r.get('port')}")
    return s


def bus_point(t, name, toward):
    b = next((x for x in t.get("buses") or [] if x.get("name") == name), None)
    if not b or b.get("face") not in ("N", "S", "E", "W") or not b.get("window_um"):
        return None
    w, h = t.get("outline_um") or (0, 0)
    sys.path.insert(0, str(HERE))
    try:
        import precheck as PC
    finally:
        sys.path.pop(0)
    return PC.face_point(b["face"], b["window_um"], w, h, toward)


def core_wire_findings(t, die_dir, conns, cap=CAP_UM):
    if not conns:
        return []
    cores = {str(c.get("inst")): c for c in t.get("hard_cores") or []}
    reg = registered_ports(t)
    out = []
    for inst, ports in conns.items():
        c = cores.get(inst)
        if not c or not isinstance(ports, dict):
            continue
        pins = core_pins(die_dir, c)
        for port, dests in ports.items():
            if f"{inst}.{port}" in reg or not pins.get(port):
                continue
            p = centroid(pins[port])
            worst, wd = 0.0, ""
            for dst in dests if isinstance(dests, list) else [dests]:
                dst = str(dst)
                if dst in reg:
                    continue                # the bus / core end already carries a station chain
                if dst.startswith("core:"):
                    oc = cores.get(dst[5:].split(".")[0]) or cores.get(dst[5:]) or \
                        next((v for k, v in cores.items() if dst[5:].startswith(k + ".") or dst[5:] == k), None)
                    if not oc:
                        continue
                    d = rect_dist(p, core_rect(oc))
                elif dst.startswith(("bus:", "port:")):
                    q = bus_point(t, dst.split(":", 1)[1], p)
                    if q is None:
                        continue
                    d = man(p, q)
                else:
                    continue
                if d > worst:
                    worst, wd = d, dst
            if worst > cap:
                out.append((round(worst, 1), f"core {inst}.{port} ({p[0]:.0f}, {p[1]:.0f}) -> {wd} >= {worst:.0f} um, no station / relay row"))
    return out


class RtlIndex:
    """basename -> path of the tree's RTL (rtl/ and physical/die_plan/<die>/bind/source_modules), built once"""
    def __init__(self, tree, die):
        self.m = {}
        for root in (Path(tree) / "rtl", Path(tree) / "physical/die_plan" / die / "bind/source_modules"):
            for dp, _dn, fn in os.walk(root):
                for f in fn:
                    if f.endswith((".sv", ".v", ".svh", ".vh")):
                        self.m.setdefault(f, os.path.join(dp, f))


def unreg_read_findings(t, kit, defines, index=None, pat=EC.REGREAD_RE):
    mems = [c for c in (t.get("hard_cores") or []) + (t.get("contents") or [])
            if MEM.search(str(c.get("module", ""))) and (c.get("lef") or c.get("lib"))]
    if not mems:
        return [], 0
    if not kit:
        return [(None, f"{len(mems)} memory macros, no kit RTL closure of the type: UNMEASURED")], len(mems)
    rx = re.compile(pat)
    offered = {}
    for f in sorted(list(Path(kit, "rtl").glob("*.sv")) + list(Path(kit, "rtl").glob("*.v"))):
        src = Path(index.m[f.name]) if index and f.name in index.m else f
        try:
            for m in EC.IFDEF_RE.finditer(src.read_text(errors="replace")):
                if rx.search(m.group(1)):
                    offered.setdefault(m.group(1), f.name)
        except OSError:
            continue
    off = sorted(x for x in offered if not EC.has_define(defines, x))
    return [(len(off), f"{len(mems)} memory macros; registered-read selector(s) off: " + ", ".join(f"{x} ({offered[x]})" for x in off))] if off else [], len(mems)


# ---------------------------------------------------------------- run

def die_dir_of(tools, die):
    return Path(tools).resolve().parents[1] / "physical/die_plan" / die


def load_conns(die_dir):
    f = Path(die_dir) / "core_conns.json"
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return {}


def census(die, plan, tools, kits=(), types="*", tree=None):
    _raw, T = EC.load_plan(plan, tools)
    dd = die_dir_of(tools, die)
    conns = load_conns(dd)
    kd = EC.kit_dirs(kits)
    index = RtlIndex(tree or Path(tools).resolve().parents[1], die) if kd else None
    globs = [g for g in types.split(",") if g]
    rows, mem_types, errors = [], 0, []
    for tn in sorted(T):
        if not any(fnmatch.fnmatchcase(tn, g) for g in globs):
            continue
        t = T[tn]
        try:
            for v, d in hop_findings(t):
                rows.append((tn, "HOP", v, d))
            for v, d in reset_findings(t, dd):
                rows.append((tn, "RESET_LEG", v, d))
            for v, d in core_wire_findings(t, dd, conns.get(tn) or {}):
                rows.append((tn, "CORE_WIRE", v, d))
            kit = kd.get(tn)
            defs = set(str(x) for x in t.get("verilog_defines") or []) | (EC.kit_defines(kit) if kit else set())
            f, nm = unreg_read_findings(t, kit, defs, index)
            mem_types += 1 if nm else 0
            for v, d in f:
                rows.append((tn, "UNREG_READ" if v is not None else "UNREG_READ?", v, d))
        except Exception as e:  # noqa: BLE001 -- an estimator lists, never stops
            errors.append((tn, f"{type(e).__name__}: {str(e)[:160]}"))
    return rows, dict(types=len([t for t in T if any(fnmatch.fnmatchcase(t, g) for g in globs)]), mem_types=mem_types,
                      core_conns=len(conns), kits=len(kd), errors=errors)


def write(out, die, plan, rows, info, t0):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "ABS-CENSUS.tsv", "w") as f:
        f.write("type\tcheck\tvalue_um\tdetail\n")
        for tn, ck, v, d in sorted(rows, key=lambda r: (r[1], r[0], -(r[2] or 0))):
            f.write(f"{tn}\t{ck}\t{'' if v is None else v}\t{d}\n")
    by = collections.defaultdict(set)
    worst = {}
    for tn, ck, v, d in rows:
        by[ck].add(tn)
        if v is not None and (ck not in worst or v > worst[ck][0]):
            worst[ck] = (v, tn)
    rec = dict(schema="opentallas.plan_geom_census.v1", die=die, plan=str(plan), cap_um=CAP_UM, findings=len(rows),
               types_by_check={k: len(v) for k, v in by.items()}, rows_by_check=dict(collections.Counter(r[1] for r in rows)),
               worst={k: dict(um=v[0], type=v[1]) for k, v in worst.items()}, seconds=round(time.time() - t0, 1), **info)
    (out / "abs_census.json").write_text(json.dumps(rec, indent=1))
    parts = [f"{k} {rec['rows_by_check'][k]} rows / {len(by[k])} types" + (f" (worst {worst[k][0]:.0f} um {worst[k][1]})" if k in worst and k != "UNREG_READ" else "")
             for k in sorted(by)]
    rec["summary"] = (f"ABS-CENSUS {die} (plan geometry, cap {CAP_UM:.0f} um, {rec['types']} types, {rec['seconds']:.0f} s): "
                      + ("; ".join(parts) or "no finding") + f". Rows {out}/ABS-CENSUS.tsv")
    print(rec["summary"])
    return rec


# ---------------------------------------------------------------- calibration

def placed_worst(rec, classes=("logic", "channel")):
    """worst measured register leg of a kit_scan PLACED record (pairs [a, b, n, um, example, class])"""
    w = 0.0
    for p in rec.get("pairs") or []:
        if len(p) >= 6 and p[5] in classes and isinstance(p[3], (int, float)):
            w = max(w, float(p[3]))
    return w


def kit_type(name):
    return re.split(r"-(?:route|place|grt|cts|finish|sta)-", Path(name).name)[0]


def calib(plan, tools, placed, cap=CAP_UM):
    _raw, T = EC.load_plan(plan, tools)
    rows = []
    for f in placed:
        tn = kit_type(f)
        if tn not in T:
            continue
        try:
            rec = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        if rec.get("status") not in (None, "OK", "ok") and not rec.get("pairs"):
            continue
        est = max([v for v, _ in EC.hops_list(T[tn], 0.0)] or [0.0])
        rows.append((tn, est, placed_worst(rec), Path(f).name))
    tp = sum(1 for r in rows if r[1] > cap and r[2] > cap)
    fp = sum(1 for r in rows if r[1] > cap and r[2] <= cap)
    fn = sum(1 for r in rows if r[1] <= cap and r[2] > cap)
    tn_ = sum(1 for r in rows if r[1] <= cap and r[2] <= cap)
    ratios = sorted(r[2] / r[1] for r in rows if r[1] > 0 and r[2] > 0)
    med = ratios[len(ratios) // 2] if ratios else None
    return rows, dict(kits=len(rows), tp=tp, fp=fp, fn=fn, tn=tn_, precision=round(tp / (tp + fp), 3) if tp + fp else None,
                      recall=round(tp / (tp + fn), 3) if tp + fn else None, median_measured_over_est=round(med, 3) if med else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("--die", required=True)
    r.add_argument("--plan", required=True)
    r.add_argument("--tools", default="")
    r.add_argument("--kits", nargs="*", default=[])
    r.add_argument("--types", default="*")
    r.add_argument("--out", required=True)
    c = sp.add_parser("calib")
    c.add_argument("--plan", required=True)
    c.add_argument("--tools", default="")
    c.add_argument("--placed", nargs="+", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    tools = a.tools or str(EC.tree_tools(a.plan))
    t0 = time.time()
    if a.cmd == "run":
        rows, info = census(a.die, a.plan, tools, a.kits, a.types)
        write(a.out, a.die, a.plan, rows, info, t0)
        return 0
    rows, s = calib(a.plan, tools, a.placed)
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    with open(o / "CALIB.tsv", "w") as f:
        f.write("type\test_worst_hop_um\tmeasured_worst_leg_um\tkit\n")
        for tn, e, m, k in rows:
            f.write(f"{tn}\t{e:.1f}\t{m:.1f}\t{k}\n")
    (o / "calib.json").write_text(json.dumps(s, indent=1))
    print(f"CALIB {len(rows)} placed kits: " + json.dumps(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
