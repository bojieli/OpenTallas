"""Plan-time AUTO-GEOM estimate in G0C (OWNER 12.23 (A), 2026-10-30 22:55; lane AUTOBUILD-GATE-1).

Owner: "the build should be fully automatic and you should be only looking at timing or routing failures"; approved (A):
the EXISTING GEOM checks run at PLAN time.  This module evaluates the SAME AUTO-GEOM rules at the SAME limits
(tools/autopilot/geom_rules.py constants, imported, never copied) on the geometry the plan alone fixes, so a plan
defect fails G0C in seconds instead of AUTO-GEOM hours later on a placed kit.  NO new rule and NO new limit.

Per non-hard partition type the plan fixes (all in the type frame, exactly what gen / kit placement reads):
  clock entries   gen_phys.tap_pins: every clock tap port (clk, clk_t<i>), early core taps and edge (forwarded) clocks
  clock sinks     taps.sink_sites (face registers at their pins, ft stations at regs_um / bit sites / route points, the
                  plan's sink_sites_um inventory, control-pin registers), reset relays (reset_tree.for_type relays,
                  root + out registers), landing groups (landing_place.tcl cland_groups: collectors at their relay
                  sites, monitors, status stages; ring bands = forwarded-clock write flops + local-read flops)
  pins            gen_phys.type_pins (name, bit, layer, x, y, face)

Rules (AUTO-GEOM id -> plan-time reading; limits from geom_rules):
  clock_reach     every plan sink within CLK_REACH_MAX x CLK_REACH_TOL (220 um) of its NEAREST clock entry
                  (AUTO-GEOM: sink to the nearest rooted clock port / pre-placed clock cell).  A ring band counts by its
                  farthest corner (its flops fill the band).
  clock_tap_sinks with >= 2 grid taps: die-clock sinks per grid tap on the nearest-tap split <= TAP_SINKS_MAX (1500).
                  Forwarded-clock (fclk) ring write flops are not die-clock sinks (AUTO-GEOM counts only sinks rooted
                  at a grid tap) -- the granted forwarded-clock tap-load exception.  Plan sinks are a LOWER bound of the
                  netlist (internal logic registers are only counted when the plan declares them: sink_sites_um /
                  sink_bins_file), so a FAIL here is certain, a PASS is not.
  pin_reg         pin -> its plan register site (face register, ft station 0, the exact face bit site, or the nearest
                  point of the pin's landing ring band): p90 <= PINREG_P90 (30) and max <= PINREG_HARD (150).  Clock
                  ports and strap_* pins exempt (as AUTO-GEOM).
  r2r             plan register-to-register stages <= R2R_MAX (405): consecutive ft stations (ring band -> station 1
                  for a landing slot), reset relay chain d -> q hops, and each reset leaf relay (rst_n_t<k>) -> the
                  farthest die-clock sink of its tap k (the registers it resets).
  aspect          outline max/min <= ASPECT_MAX (2.0)
  partial_face    from the plan pin table: a face with >= PARTIAL_FACE_PINS pins on < PARTIAL_FACE_OCC of its 10-um
                  windows at >= PARTIAL_FACE_DENS pins/um (geom_rules.partial_face_metrics on the plan pins)
Granted exceptions (kept, as AUTO-GEOM / kit_wave keep them): fill/empty (OWNER standing fill rule 10-30) are not
evaluated at plan time; EXCEPTIONS below (partial_face of the S81 stform2 ft-column station form, COORD RULING
2026-10-30 22:24 (a)).  Rules that need a real placement (fill, empty, std_band, channel demand / col_v, GRT,
pin_density, relay_collapse, tree shape) stay at AUTO-GEOM.

    python3 tools/die_plan/plan_geom.py PLAN.json [--types REGEX] [--json OUT]
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import geom_rules as GR  # noqa: E402  (the AUTO-GEOM limits: one source)

CLK_REACH = round(GR.CLK_REACH_MAX * GR.CLK_REACH_TOL, 1)
CHECKS = ("geom_clock_reach", "geom_tap_sinks", "geom_pin_reg", "geom_r2r", "geom_aspect", "geom_partial_face")
# Granted GEOM exceptions (die name, rule, type regex, source).  Only COORD/OWNER-granted items belong here.
EXCEPTIONS = (
    ("s81", "partial_face", r"^slice_station__",
     "COORD RULING 2026-10-30 22:24 (a): partial_face from the stform2 ft-column station pin form"),
    ("qwen_compute", "aspect", r"^sl[ew]_",
     "COORD RULING 2026-10-30 18:54: QC slice lattice-wide aspect exception (0.945 mm2 slots in the 2471x5357 column)"),
)
_GROUP_RE = re.compile(r"^\s*\{(\S+) \{([-\d.eE ]+)\} (\S+)\}\s*$")


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _rect_pts(r):
    x0, y0, x1, y1 = r
    return [((x0 + x1) / 2, (y0 + y1) / 2), (x0, y0), (x0, y1), (x1, y0), (x1, y1)]


def _rect_dist(p, r):
    x0, y0, x1, y1 = r
    return max(x0 - p[0], 0.0, p[0] - x1) + max(y0 - p[1], 0.0, p[1] - y1)


def landing_groups(P, tn):
    """[(instance, rect, tag)] of the kit's landing placement (landing_place.tcl, the very text the kit sources)."""
    if not P.types[tn].get("clock", {}).get("landing_contract"):
        return []
    import landing_place as LP
    out, on = [], False
    for ln in LP.tcl(P, tn).splitlines():
        if ln.startswith("set cland_groups") or ln.startswith("set cland_optional_groups"):
            on = True
            continue
        if ln.strip() == "}":
            on = False
            continue
        m = _GROUP_RE.match(ln) if on else None
        if m:
            out.append((m.group(1), [float(v) for v in m.group(2).split()], m.group(3)))
    return out


def type_sites(P, tn):
    """the plan-fixed geometry of type tn: entries, die-clock sinks, forwarded-clock sinks, pins, stage hops."""
    import gen_phys
    import reset_tree as RT
    import taps as TP
    t = P.types[tn]
    w, h = t["outline_um"]
    ports = gen_phys.tap_pins(P, tn)
    entries = [(n, float(x), float(y)) for n, x, y in ports if n not in ("arst_n", "start_i")]
    pins = gen_phys.type_pins(P, tn)
    sinks = [(float(x), float(y), float(wt), "plan") for x, y, wt in TP.sink_sites(P, tn)]
    bands_decl = t.get("clock", {}).get("landing_contract", {}).get("bands", {})
    landed = {s["name"] for s in t.get("ft_slots", []) if s["name"] + "_i" in bands_decl
              and not t.get("clock", {}).get("sink_bins_file")}
    if landed:
        # face_flops.tcl FLOW-KITFAIL-2: a landed slot's in bit is captured by its landing ring (counted below) and its
        # k stations sit after the ring at L*(j+1)/k, the LAST at the out face; taps.planned_sinks puts station 0 at the
        # in pin instead.  Same sites j = 1..k-1; the in-pin station moves to the out-face register.
        drop, add = defaultdict(int), []
        outs = {(n[:-2], b): (x, y, f) for n, b, _, x, y, f in pins if n[-2:] == "_o"}
        for n, b, _, x, y, f in pins:
            if n[-2:] == "_i" and n[:-2] in landed:
                drop[TP._inset(x, y, f, w, h)] += 1
                o = outs.get((n[:-2], b))
                if o:
                    add.append(TP._inset(o[0], o[1], o[2], w, h) + (1.0, "plan_land_out"))
        kept = []
        for s in sinks:
            k = (s[0], s[1])
            if drop.get(k, 0) > 0 and s[2] == 1.0:
                drop[k] -= 1
                continue
            kept.append(s)
        sinks = kept + [(float(a), float(b), c, d) for a, b, c, d in add]
    fwd = []                                            # (x, y) forwarded-clock (fclk) sinks: reach only, no tap load
    hops = []                                           # (um, label)
    notes = []
    T = None
    try:
        T = RT.for_type(P, tn)
    except Exception as ex:                            # plan without a generated reset tree for this type
        notes.append(f"reset tree n/a ({type(ex).__name__}: {str(ex)[:80]})")
    if T:
        xy = {"rst_root_n": tuple(T["root"])}
        for r in T.get("relays", []):
            xy[r["q"]] = tuple(r["xy"])
            sinks.append((r["xy"][0], r["xy"][1], 1.0, "relay:" + r["name"]))
        sinks.append((T["root"][0], T["root"][1], 1.0, "reset_root"))
        for o in T.get("outs") or []:
            sinks.append((float(o[0]), float(o[1]), 1.0, "reset_out"))
        for r in T.get("relays", []):
            if r["d"] in xy:
                hops.append((_d(xy[r["d"]], r["xy"]), f"reset {r['d']}->{r['name']}"))
    bands = {}
    for inst, rect, tag in landing_groups(P, tn):
        if tag.startswith("ring:"):
            name = tag[5:].split("+")[0]
            b = t["clock"]["landing_contract"].get("bands", {}).get(name, {})
            bands[name] = rect
            roles = b.get("clock_roles") or {}
            for p in _rect_pts(rect):
                fwd.append(p + (f"ring:{name}",))
            cx, cy = _rect_pts(rect)[0]
            nl = float(roles.get("local_read_flops", 0) or 0)
            if nl:
                sinks.append((cx, cy, nl, f"ring_read:{name}"))
            for p in _rect_pts(rect)[1:]:              # reach: the band's farthest corner (weight 0, no load)
                sinks.append((p[0], p[1], 0.0, f"ring_read:{name}"))
        else:
            c = _rect_pts(rect)[0]
            sinks.append((c[0], c[1], 1.0, f"landing:{inst}"))
    return dict(w=w, h=h, entries=entries, sinks=sinks, fwd=fwd, hops=hops, bands=bands, pins=pins, reset=T,
                notes=notes)


def _nearest(p, pts):
    best, bi = math.inf, -1
    for i, q in enumerate(pts):
        d = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if d < best:
            best, bi = d, i
    return best, bi


def type_metrics(P, tn):
    """AUTO-GEOM metrics of type tn from the plan alone (keys follow geom_rules where the rule is the same)."""
    t = P.types[tn]
    G = type_sites(P, tn)
    w, h = G["w"], G["h"]
    m = dict(type=tn, outline=[w, h], aspect=round(max(w, h) / max(min(w, h), 1e-9), 3), notes=G["notes"])
    ent = [(x, y) for _, x, y in G["entries"]]
    # clock_reach: every sink (die clock + forwarded) to its nearest entry
    reach, far = 0.0, None
    if ent:
        for x, y, _, kind in G["sinks"]:
            d, _ = _nearest((x, y), ent)
            if d > reach:
                reach, far = d, f"{kind} ({x:.1f}, {y:.1f})"
        for x, y, kind in G["fwd"]:
            d, _ = _nearest((x, y), ent)
            if d > reach:
                reach, far = d, f"{kind} ({x:.1f}, {y:.1f})"
    m.update(clock_entries=len(ent), clock_reach_max=round(reach, 2) if ent else None, clock_reach_far=far)
    # tap load: die-clock sinks on the nearest grid tap (AUTO-GEOM nearest mode)
    grid = [(n, x, y) for n, x, y in G["entries"] if GR.GRID_TAP_RE.match(n)]
    m["grid_taps"] = len(grid)
    load = defaultdict(float)
    gxy = [(x, y) for _, x, y in grid]
    if grid:
        for x, y, wt, kind in G["sinks"]:
            _, i = _nearest((x, y), gxy)
            load[grid[i][0]] += wt
        worst = max(load.items(), key=lambda kv: kv[1]) if load else (None, 0)
        m.update(grid_tap_sinks_max=round(worst[1], 1), grid_tap_sinks_worst=worst[0])
    # pin -> plan register site
    import taps as TP
    slots = {s["name"]: s for s in t.get("ft_slots", [])}
    exact = {e["conn"][4:]: e for e in t.get("internal_stations", [])
             if e.get("conn", "").startswith("bus:") and e.get("face_bit_sites_um")}
    strap = re.compile(GR.STRAP_RE_DEFAULT)
    pr = []
    for name, bit, _ln, x, y, face in G["pins"]:
        if GR.CLOCK_PIN_RE.search(name) or strap.search(name) or name.startswith("fclk_"):
            continue
        base, sfx = (name[:-2], name[-2:]) if name[-2:] in ("_i", "_o") else (name, "")
        if name in G["bands"]:
            d = _rect_dist((x, y), G["bands"][name])
        elif name in exact:
            e = exact[name]
            cw, ch = e["bit_site_cell_um"]
            bx, by = e["face_bit_sites_um"][bit]
            d = _d((x, y), (bx + cw / 2, by + ch / 2))
        elif base in slots and sfx == "_o":
            continue                                   # registered by the last station / the neighbour's station 0
        else:
            d = TP.FACE_INSET_UM                       # face register / ft station 0 at its pin (R2)
        pr.append((d, f"{name}[{bit}]"))
    if pr:
        pr.sort()
        m.update(pin_reg_p90=round(GR.q([d for d, _ in pr], .9), 2), pin_reg_max=round(pr[-1][0], 2),
                 pin_reg_worst=[f"{d:.1f} {n}" for d, n in pr[::-1][:2]])
    # r2r: ft stations (+ ring band -> station 1), reset chain, reset leaf -> its tap's sinks
    hops = list(G["hops"])
    for s in t.get("ft_slots", []):
        k = int(s.get("stations", 1))
        regs = [tuple(r) for r in s.get("regs_um", [])]
        if len(regs) >= 2:
            hops += [(_d(a, b), f"ft {s['name']} s{j}->s{j + 1}") for j, (a, b) in enumerate(zip(regs, regs[1:]))]
        band = G["bands"].get(s["name"] + "_i")
        if band and k >= 2:
            if len(regs) >= 2:
                hops.append((max(_d(p, regs[1]) for p in _rect_pts(band)[1:]), f"ft {s['name']} ring->s1"))
    T = G["reset"]
    if T and grid:
        leaf = {}
        for r in T.get("relays", []):
            mm = re.fullmatch(r"rst_n_t(\d+)", r["q"])
            if mm:
                leaf[int(mm.group(1))] = r
        far_by = defaultdict(lambda: (0.0, None))
        names = [n for n, _, _ in grid]
        for x, y, wt, kind in G["sinks"]:
            if wt <= 0 or not kind.startswith("plan"):
                continue
            _, i = _nearest((x, y), gxy)
            r = leaf.get(i) if names[i] == ("clk" if i == 0 else f"clk_t{i}") else None
            if r is None:
                continue
            d = _d(r["xy"], (x, y))
            if d > far_by[i][0]:
                far_by[i] = (d, f"reset leaf {r['name']}->sink ({x:.1f}, {y:.1f}) of {names[i]}")
        lv = [v for v in far_by.values() if v[1]]
        if lv:
            mx = max(lv)
            m.update(reset_leaf_max=round(mx[0], 2), reset_leaf_worst=mx[1])
    if hops:
        mx = max(hops)
        m.update(r2r_max=round(mx[0], 2), r2r_worst=mx[1], r2r_gt405=sum(1 for d, _ in hops if d > GR.R2R_MAX))
    # partial_face on the plan pin table (geom_rules.partial_face_metrics)
    D = type("PlanPins", (), {})()
    D.die = (0.0, 0.0, w, h)
    D.pins = [dict(sig="SIGNAL", x=x, y=y) for _, _, _, x, y, _ in G["pins"]]
    m.update(GR.partial_face_metrics(D, None))
    return m


def exception_for(die, tn, rule):
    for d, r, rx, src in EXCEPTIONS:
        if d == die and r == rule and re.search(rx, tn):
            return src
    return None


def judge(m, die=None):
    """[rule dicts] for one type: status PASS | FAIL | EXCEPTION | INFO (same limits as geom_rules.judge)."""
    R = []
    tn = m["type"]

    def add(rule, v, limit, ok, src, detail=""):
        st = "PASS" if ok else "FAIL"
        if not ok:
            ex = exception_for(die, tn, rule)
            if ex:
                st, detail = "EXCEPTION", ex + ("; " + detail if detail else "")
        R.append(dict(rule=rule, status=st, value=v, limit=limit, source=src, detail=detail))
    add("aspect", m["aspect"], f"<={GR.ASPECT_MAX}", m["aspect"] <= GR.ASPECT_MAX, "METHODOLOGY 1.14 aspect <= ~2:1")
    if m.get("clock_reach_max") is not None:
        add("clock_reach", m["clock_reach_max"], f"<={CLK_REACH}", m["clock_reach_max"] <= CLK_REACH,
            "METHODOLOGY 12.8b entry-to-sink ~<=200 um (geom_rules CLK_REACH_MAX x TOL)", f"far {m['clock_reach_far']}")
    if m.get("grid_taps", 0) >= 2:
        v = m["grid_tap_sinks_max"]
        add("clock_tap_sinks", v, f"<={GR.TAP_SINKS_MAX}", v <= GR.TAP_SINKS_MAX,
            "METHODOLOGY 3.3 (~1000-1500 sinks/tap), plan sinks = lower bound", f"tap {m['grid_tap_sinks_worst']}")
    if m.get("pin_reg_p90") is not None:
        add("pin_reg_p90", m["pin_reg_p90"], f"<={GR.PINREG_P90}", m["pin_reg_p90"] <= GR.PINREG_P90,
            "METHODOLOGY 1.9 (R2 p90 <= 30)", ", ".join(m["pin_reg_worst"]))
        add("pin_reg_max", m["pin_reg_max"], f"<={GR.PINREG_HARD}", m["pin_reg_max"] <= GR.PINREG_HARD,
            "layout_review.py 150 backstop", ", ".join(m["pin_reg_worst"][:1]))
    if m.get("r2r_max") is not None:
        add("r2r", m["r2r_max"], f"<={GR.R2R_MAX}", m["r2r_max"] <= GR.R2R_MAX, "METHODOLOGY 1.3/4.2 reach 405",
            f"{m['r2r_gt405']} plan stages > 405; worst {m['r2r_worst']}")
    if m.get("reset_leaf_max") is not None and m["reset_leaf_max"] > GR.R2R_MAX:
        # estimate only (the kit's reset_taps.tcl re-points every FIRM placed register to its nearest tap's leaf and
        # sinks sit within a cell of their plan site): reported, never gating
        R.append(dict(rule="r2r_reset_leaf", status="WARN", value=m["reset_leaf_max"], limit=f"<={GR.R2R_MAX}",
                      source="METHODOLOGY 1.3/4.2 reach 405 (estimate: nearest-tap reset consumers)",
                      detail=m["reset_leaf_worst"]))
    add("partial_face", m["partial_faces"], "<=0", m["partial_faces"] == 0,
        "tile-review-pin-clustering-1017 (pins on partial faces)", "; ".join(m.get("partial_face_detail") or []))
    return R


GATE_MODES = ("enforce", "report", "off")
# AUTOBUILD-GATE-1 10-30: validated 0 false FAIL on the measured S81 station + QC kit-wave GEOMs, but the ~190 S81
# non-station types FAIL clock_reach/tap load at plan time with no measured kit yet (KIT-WAVE-2 builds them now).
# Default = report (WARN "[G0C-GEOM]") until COORD flips it to enforce after the first non-station measured wave.
DEFAULT_MODE = "report"


def check(P, R=None, types=None, max_msgs=400, mode=DEFAULT_MODE):
    """G0C hook: every non-hard type used by a partition; each FAIL -> R.err('geom_<rule>', ..., type=tn) when
    mode == 'enforce', R.warn('geom_<rule>', '[G0C-GEOM] ...') when mode == 'report'."""
    assert mode in GATE_MODES, mode
    if mode == "off":
        return dict(mode="off")

    def emit(chk, msg, tn):
        if R is None:
            return
        if mode == "enforce":
            R.err(chk, msg, type=tn)
        else:
            R.warn(chk, "[G0C-GEOM] " + msg, type=tn, g0c=True)
    used = {p["type"] for p in P.parts.values()} if hasattr(P, "parts") else set(P.types)
    out, n = dict(mode=mode, types=0, fail_types=0, by_rule=defaultdict(int), exceptions=defaultdict(int),
                  errors=[], fail_list=[]), 0
    for tn in sorted(used):
        t = P.types[tn]
        if t.get("hard") or (types and not re.search(types, tn)):
            continue
        out["types"] += 1
        try:
            m = type_metrics(P, tn)
        except Exception as ex:
            msg = f"type {tn}: plan geometry not evaluable ({type(ex).__name__}: {str(ex)[:160]})"
            out["errors"].append(msg)
            if R is not None:   # the plan input itself is broken (e.g. landing band absent): other G0C checks own it
                R.warn("geom_clock_reach", msg, type=tn)
            continue
        bad = False
        for r in judge(m, P.name):
            if r["status"] == "EXCEPTION":
                out["exceptions"][r["rule"]] += 1
            if r["status"] != "FAIL":
                continue
            bad = True
            out["by_rule"][r["rule"]] += 1
            chk = {"clock_tap_sinks": "geom_tap_sinks", "pin_reg_p90": "geom_pin_reg", "pin_reg_max": "geom_pin_reg"}.get(
                r["rule"], "geom_" + r["rule"])
            if n < max_msgs:
                emit(chk, f"type {tn}: plan-time AUTO-GEOM {r['rule']} {r['value']} (limit {r['limit']}; "
                          f"{r['source']}) {r['detail']}"[:400], tn)
                n += 1
        out["fail_types"] += bad
        if bad:
            out["fail_list"].append(tn)
    out["by_rule"] = dict(out["by_rule"])
    out["exceptions"] = dict(out["exceptions"])
    return out


def main(argv=None):
    import schema as S
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--types", help="regex of type names (default: every non-hard type with a partition)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    P = S.Plan(S.load(a.plan), Path(a.plan).resolve())
    rows = []
    used = {p["type"] for p in P.parts.values()}
    for tn in sorted(used):
        if P.types[tn].get("hard") or (a.types and not re.search(a.types, tn)):
            continue
        try:
            m = type_metrics(P, tn)
        except Exception as ex:
            print(f"{tn}\tERROR\t{type(ex).__name__}: {str(ex)[:200]}")
            rows.append(dict(type=tn, verdict="ERROR", error=str(ex)))
            continue
        rules = judge(m, P.name)
        fails = [r for r in rules if r["status"] == "FAIL"]
        print(f"{tn}\t{'FAIL' if fails else 'PASS'}\t" + " ".join(
            f"{r['rule']}={r['status']}({r['value']})" for r in rules))
        rows.append(dict(type=tn, verdict="FAIL" if fails else "PASS", metrics=m, rules=rules))
    if a.json:
        Path(a.json).write_text(json.dumps(dict(schema="opentallas.plan_geom.v1", plan=str(a.plan), types=rows),
                                           indent=1, default=str) + "\n")
    return 1 if any(r["verdict"] != "PASS" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
