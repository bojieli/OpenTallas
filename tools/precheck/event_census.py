#!/usr/bin/env python3
"""event_census.py -- EVENT-CENSUS (ADOPT-CENSUS-1800, FABLE-FLOW-1800 class 2): a plan event against the event before it, per type.

Nothing compared S81 J5 with 3fa87b84b18: 29 landing-monitor pins moved 300 to 2,904 um away from their monitor and the first
reader was a timing report after place.  This census runs in the PRECHECK-1119 path (precheck_hook.py after an apply, or by
hand on a sealed candidate) and needs no build: the metrics come from the two plans, and from one generated kit per side when
given (--prev-kits / --new-kits; gen dirs, item dirs or a kit-wave items root).

  metric         source                                           REGRESS when (the stated step)
  MON_UM         landing_contract bands monitor_i -> cland_dn_*_i   new > 300 um and new > prev + 1 um
                 pins (Manhattan, worst pin of the ring)
  HOPS_300       station hops over 300 um (precheck reach_findings,  new count > prev count
                 margin 1.0: internal_stations + ft_slots)
  DEFINES        plan verilog_defines (+ config.mk VERILOG_DEFINES)  a define of the previous event is gone
  UNREG_READS    registered-read selectors (`ifdef X, X matching    new count > prev count
                 --regread-re) in the kit rtl/ that the defines do
                 not set (kit only)
  RESET_UM       reset.relay_um, and bound_native_reset.json         new > 300 um and new > prev + 1 um
                 planned_native_max_hop_um of the kit
  RESET_ROWS     reset.inst_taps + reset.local_taps_um + reset       new < prev (the event dropped reset leg rows)
                 relay_depth rows of the type

A type is matched by name, else by its param / landing base type.  A type with a REGRESS row is NOT LAUNCHED: `hold` (run on
the hub) adds one hold_items key per type ("EVENT-CENSUS <event>: ...") through kit_wave_edit and removes the census keys of
types that no longer regress.  The event itself still applies; functional errors block as before.  This is a stop on known-bad
work, not a design gate; the die owner releases a type by removing its key (or naming it intended in the post).

  event_census.py run  --die DIE --prev-plan P0 --new-plan P1 [--prev-tools T0] [--new-tools T1] [--prev-kits K ...]
                       [--new-kits K ...] [--types GLOB] --out DIR [--event EV]
  event_census.py hold --die DIE --census DIR/census.json|- [--event EV] [--lane LANE] [--coord ~/coord] [--dry-run]
"""
import argparse
import contextlib
import fnmatch
import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOP_UM = 300.0
STEP_UM = 1.0
REGREAD_RE = r"^(?!.*_MUT_)\w*(?:SRAMREG|RDREG|READREG|_RIP\d+)$"     # _MUT_ = a bench mutant, never a build selector
HOLD_TAG = "EVENT-CENSUS"
METRICS = ("MON_UM", "HOPS_300", "DEFINES", "DEFINES_KIT", "UNREG_READS", "RESET_UM", "RESET_ROWS")
IGNORED_DEFINES = {"SYNTHESIS"}     # every config.mk sets it


def load_plan(plan, tools):
    """(raw, {type: resolved type dict}) through the tree's own schema.Plan"""
    tools = str(tools)
    sys.path.insert(0, tools)
    try:
        sys.modules.pop("schema", None)
        import schema as S
        raw = json.loads(Path(plan).read_text())
        with contextlib.redirect_stdout(io.StringIO()):
            P = S.Plan(raw, str(plan))
        placed = {p.get("type") for p in raw.get("partitions") or [] if p.get("type")}
        return raw, {tn: t for tn, t in P.types.items() if not placed or tn in placed}
    finally:
        sys.path.remove(tools)
        sys.modules.pop("schema", None)


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def centre(rect):
    return ((rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0)


MON_PIN = re.compile(r"^(?:cland_dn_ready|cland_dn_fault|fclk_in_cland_dn)_(\d+)$")


def monitor_um(t):
    """(worst Manhattan um from a monitor ring band centre to its own cland_dn pins, detail) or (None, '') without monitors"""
    c = ((t.get("clock") or {}).get("landing_contract")) or {}
    bands = dict(c.get("bands") or {})
    bands.update({k: v for k, v in (((t.get("clock") or {}).get("band_fixed_um")) or {}).items() if k not in bands})
    pins = {}
    for p in c.get("pins") or []:
        m = MON_PIN.match(str(p.get("name", "")))
        if m and p.get("xy_um"):
            pins.setdefault(m.group(1), []).append((p["name"], tuple(p["xy_um"])))
    worst, det = None, ""
    for k, b in bands.items():
        if not k.startswith("monitor_") or not (b or {}).get("rect_um"):
            continue
        i = k.split("_", 1)[1]
        cen = centre(b["rect_um"])
        for name, xy in pins.get(i, []):
            d = man(cen, xy)
            if worst is None or d > worst:
                worst, det = d, f"{k} seat ({cen[0]:.0f}, {cen[1]:.0f}) -> {name} ({xy[0]:.0f}, {xy[1]:.0f})"
    return (round(worst, 1) if worst is not None else None), det


def hops_list(t, reach=HOP_UM):
    """[(worst hop of the chain, detail)] of every station chain with a hop over reach (precheck.reach_findings, margin 1.0)"""
    sys.path.insert(0, str(HERE))
    try:
        import precheck as PC
    finally:
        sys.path.remove(str(HERE))
    return PC.reach_findings(t, reach=reach, margin=1.0)


def has_define(defs, name):
    """name set; a bare-name selector in the plan (319f91aaf1: RIP1 selects OT_S81SL_LEP_RIP1) also counts"""
    return name in defs or any(name.endswith("_" + d) for d in defs if d and "_" not in d)


def hops_300(t, reach=HOP_UM):
    """(count of station chains with a hop over reach, worst hop, detail) from precheck.reach_findings at margin 1.0"""
    f = hops_list(t, reach)
    if not f:
        return 0, 0.0, ""
    v, d = max(f, key=lambda x: x[0])
    return len(f), v, d


def reset_rows(t):
    r = t.get("reset") or {}
    n = len(r.get("inst_taps") or []) + len(r.get("local_taps_um") or [])
    for row in t.get("relay_depth") or []:
        if re.search(r"rst|reset", json.dumps(row), re.I):
            n += 1
    return n


def reset_um(t):
    r = t.get("reset") or {}
    v = r.get("relay_um")
    return float(v) if isinstance(v, (int, float)) else None


# ---------------------------------------------------------------- kits

def kit_dirs(roots):
    """{type: newest gen dir} from gen dirs (with config.mk), item dirs (gen/*, attempt_*/gen/*) or an items root"""
    found = {}
    for r in roots or []:
        p = Path(r)
        if (p / "config.mk").is_file():
            cands = [p]
        else:
            cands = [c.parent for pat in ("gen/*/config.mk", "attempt_*/gen/*/config.mk", "*/gen/*/config.mk", "*/attempt_*/gen/*/config.mk")
                     for c in p.glob(pat)]
        for g in cands:
            tn = g.name
            try:
                mt = (g / "config.mk").stat().st_mtime
            except OSError:
                continue
            if tn not in found or mt > found[tn][1]:
                found[tn] = (str(g), mt)
    return {k: v[0] for k, v in found.items()}


DEF_RE = re.compile(r"^\s*(?:export\s+)?VERILOG_DEFINES\s*[:+?]?=\s*(.*)$", re.M)
IFDEF_RE = re.compile(r"^\s*`if(?:n)?def\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)


def kit_defines(g):
    try:
        txt = (Path(g) / "config.mk").read_text(errors="replace")
    except OSError:
        return set()
    out = set()
    for m in DEF_RE.finditer(txt):
        for tok in m.group(1).split():
            if tok.startswith("-D"):
                out.add(tok[2:].split("=", 1)[0])
    return out


def unreg_reads(g, defines, pat=REGREAD_RE):
    """(count, names): registered-read selectors the kit RTL offers (`ifdef X) that the kit's defines leave off"""
    rx = re.compile(pat)
    offered = set()
    for f in list(Path(g, "rtl").glob("*.sv")) + list(Path(g, "rtl").glob("*.v")):
        try:
            offered.update(m.group(1) for m in IFDEF_RE.finditer(f.read_text(errors="replace")) if rx.search(m.group(1)))
        except OSError:
            continue
    off = sorted(x for x in offered if not has_define(defines, x))
    return len(off), off


def kit_reset_um(g):
    try:
        d = json.loads((Path(g) / "bound_native_reset.json").read_text())
    except (OSError, ValueError):
        return None
    v = d.get("planned_native_max_hop_um")
    return float(v) if isinstance(v, (int, float)) else None


# ---------------------------------------------------------------- census

def type_metrics(t, kit=None, regread=REGREAD_RE):
    m = {}
    mon, md = monitor_um(t)
    m["MON_UM"] = (mon, md)
    n, worst, hd = hops_300(t)
    m["HOPS_300"] = (n, f"worst {worst:.0f} um: {hd}" if n else "")
    pdefs = set(str(x) for x in t.get("verilog_defines") or [])
    defs = pdefs | (kit_defines(kit) if kit else set())
    m["DEFINES"] = (sorted(pdefs - IGNORED_DEFINES), "plan")
    m["DEFINES_KIT"] = (sorted(defs - IGNORED_DEFINES) if kit else None, "config.mk + plan")
    if kit:
        c, names = unreg_reads(kit, defs, regread)
        m["UNREG_READS"] = (c, ", ".join(names))
    else:
        m["UNREG_READS"] = (None, "no kit")
    ru, kru = reset_um(t), kit_reset_um(kit) if kit else None
    vals = [x for x in (ru, kru) if x is not None]
    m["RESET_UM"] = (max(vals) if vals else None, f"plan relay_um {ru}, kit planned_native_max_hop_um {kru}")
    m["RESET_ROWS"] = (reset_rows(t), "")
    return m


def counterpart(tn, t, prev):
    if tn in prev:
        return tn
    for k in ("param_base_type", "landing_base_type", "type_template"):
        b = t.get(k)
        if isinstance(b, str) and b in prev:
            return b
    return None


def compare(metric, pv, nv):
    """(verdict, why) for one metric"""
    if pv is None or nv is None:
        return "UNMEASURED", ""
    if metric in ("MON_UM", "RESET_UM"):
        if nv > HOP_UM and nv > pv + STEP_UM:
            return "REGRESS", f"{pv:.0f} -> {nv:.0f} um (over {HOP_UM:.0f})"
        return ("IMPROVED" if nv < pv - STEP_UM else "OK"), ""
    if metric in ("HOPS_300", "UNREG_READS"):
        if nv > pv:
            return "REGRESS", f"{pv} -> {nv}"
        return ("IMPROVED" if nv < pv else "OK"), ""
    if metric == "RESET_ROWS":
        if nv < pv:
            return "REGRESS", f"reset leg rows {pv} -> {nv}"
        return "OK", ""
    if metric in ("DEFINES", "DEFINES_KIT"):
        lost = sorted(set(pv) - set(nv))
        if lost:
            return "REGRESS", "lost " + ", ".join(lost)
        return "OK", ""
    return "OK", ""


def fmt(v):
    if isinstance(v, list):
        return " ".join(v) or "-"
    return "-" if v is None else str(v)


def census(prev_types, new_types, prev_kits, new_kits, types_glob="*", regread=REGREAD_RE):
    rows, held = [], {}
    globs = [g for g in types_glob.split(",") if g]
    for tn in sorted(new_types):
        if not any(fnmatch.fnmatchcase(tn, g) for g in globs):
            continue
        t = new_types[tn]
        pn = counterpart(tn, t, prev_types)
        nm = type_metrics(t, new_kits.get(tn), regread)
        if pn is None:
            for k in METRICS:
                rows.append(dict(type=tn, prev_type="", metric=k, prev="-", new=fmt(nm[k][0]), verdict="NEW", why="", detail=nm[k][1]))
            continue
        pm = type_metrics(prev_types[pn], prev_kits.get(pn) or prev_kits.get(tn), regread)
        for k in METRICS:
            v, why = compare(k, pm[k][0], nm[k][0])
            rows.append(dict(type=tn, prev_type=pn, metric=k, prev=fmt(pm[k][0]), new=fmt(nm[k][0]), verdict=v, why=why,
                             detail=nm[k][1] if v == "REGRESS" else ""))
            if v == "REGRESS":
                held.setdefault(tn, []).append(f"{k} {why}")
    return rows, held


def tree_tools(plan):
    """TREE/tools/die_plan of the source tree that holds the plan (nearest ancestor with tools/die_plan/schema.py)"""
    for p in Path(plan).resolve().parents:
        if (p / "tools/die_plan/schema.py").is_file():
            return p / "tools/die_plan"
    return HERE.parent / "die_plan"


def cmd_run(a):
    t0 = time.time()
    _, prev = load_plan(a.prev_plan, a.prev_tools or tree_tools(a.prev_plan))
    _, new = load_plan(a.new_plan, a.new_tools or tree_tools(a.new_plan))
    pk, nk = kit_dirs(a.prev_kits), kit_dirs(a.new_kits)
    rows, held = census(prev, new, pk, nk, a.types, a.regread)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "EVENT-CENSUS.tsv", "w") as f:
        f.write("type\tprev_type\tmetric\tprev\tnew\tverdict\twhy\tdetail\n")
        for r in rows:
            f.write("\t".join(str(r[k]) for k in ("type", "prev_type", "metric", "prev", "new", "verdict", "why", "detail")) + "\n")
    cnt = {}
    for r in rows:
        if r["verdict"] == "REGRESS":
            cnt[r["metric"]] = cnt.get(r["metric"], 0) + 1
    rec = dict(schema="opentallas.event_census.v1", die=a.die, event=a.event, prev_plan=str(a.prev_plan), new_plan=str(a.new_plan),
               types=len({r["type"] for r in rows}), new_types=len({r["type"] for r in rows if r["verdict"] == "NEW"}),
               kits=dict(prev=len(pk), new=len(nk)), regress_by_metric=cnt, held=held, seconds=round(time.time() - t0, 1),
               at=time.strftime("%Y-%m-%d %H:%M:%S"))
    (out / "census.json").write_text(json.dumps(rec, indent=1))
    rec["summary"] = summary(rec, out)
    print(rec["summary"])
    return 0


def summary(rec, out=""):
    held = rec.get("held") or {}
    ex = "; ".join(f"{t}: {', '.join(w)[:120]}" for t, w in sorted(held.items())[:6])
    return (f"EVENT-CENSUS {rec['die']} {rec.get('event') or ''}: {rec['types']} types vs the previous event ({rec['new_types']} new), "
            f"kits prev {rec['kits']['prev']} / new {rec['kits']['new']}; REGRESS {len(held)} types "
            f"({', '.join(f'{k} {v}' for k, v in sorted(rec['regress_by_metric'].items())) or 'none'})"
            + (f": {ex}{' ...' if len(held) > 6 else ''}" if held else "") + (f". Rows {out}/EVENT-CENSUS.tsv" if out else ""))


# ---------------------------------------------------------------- hold (runs on the hub)

def ptr(s):
    return s.replace("~", "~0").replace("/", "~1")


def hold_patch(cfg, die, held, event):
    """kit_wave_edit patch: add one hold_items key per regressed type, remove census keys of types that no longer regress"""
    d = cfg["dies"][die]
    cur = d.get("hold_items") or {}
    ops = []
    if not isinstance(cur, dict):
        raise ValueError(f"dies.{die}.hold_items is not a map")
    if "hold_items" not in d:
        ops.append({"op": "add", "path": f"/dies/{die}/hold_items", "value": {}})
    for tn, why in sorted(held.items()):
        txt = f"{HOLD_TAG} {event}: regressed vs the previous event ({'; '.join(why)})"[:600] + \
              " -- not launched; the event applies; release = remove this key or a census without the regression"
        if cur.get(tn) != txt:
            ops.append({"op": "add", "path": f"/dies/{die}/hold_items/{ptr(tn)}", "value": txt})
    for k, v in sorted(cur.items()):
        if str(v).startswith(HOLD_TAG + " ") and k not in held:
            ops.append({"op": "remove", "path": f"/dies/{die}/hold_items/{ptr(k)}"})
    return ops


def cmd_hold(a):
    C = Path(os.path.expanduser(a.coord))
    rec = json.loads(sys.stdin.read() if a.census == "-" else Path(a.census).read_text())
    cfg = json.loads(subprocess.run(["git", "-C", str(C), "show", "HEAD:autopilot/kit_wave.json"], capture_output=True, text=True, check=True).stdout)
    ops = hold_patch(cfg, a.die, rec.get("held") or {}, a.event or rec.get("event") or "?")
    print(json.dumps(ops, indent=1) if a.dry_run else f"EVENT-CENSUS hold: {len(ops)} op(s)")
    if not ops or a.dry_run:
        return 0
    r = subprocess.run([sys.executable, "-I", str(HERE.parent / "autopilot/kit_wave_edit.py"), "--coord", str(C), "--message",
                        f"{a.lane}: EVENT-CENSUS {a.die} {a.event or rec.get('event')}: {len(rec.get('held') or {})} regressed type(s) not launched",
                        "--patch", json.dumps(ops)], capture_output=True, text=True, timeout=600)
    print((r.stdout + r.stderr)[-600:])
    return r.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("--die", required=True)
    r.add_argument("--prev-plan", required=True)
    r.add_argument("--new-plan", required=True)
    r.add_argument("--prev-tools", default="", help="die_plan tools of the previous tree (default: <tree>/tools/die_plan from the plan path)")
    r.add_argument("--new-tools", default="")
    r.add_argument("--prev-kits", nargs="*", default=[])
    r.add_argument("--new-kits", nargs="*", default=[])
    r.add_argument("--types", default="*")
    r.add_argument("--regread", default=REGREAD_RE, help="regex of registered-read selector macros")
    r.add_argument("--event", default="")
    r.add_argument("--out", required=True)
    h = sp.add_parser("hold")
    h.add_argument("--die", required=True)
    h.add_argument("--census", required=True, help="census.json, or - for stdin")
    h.add_argument("--event", default="")
    h.add_argument("--lane", default="PRECHECK-1119")
    h.add_argument("--coord", default="~/coord")
    h.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else cmd_hold(a)


if __name__ == "__main__":
    sys.exit(main())
