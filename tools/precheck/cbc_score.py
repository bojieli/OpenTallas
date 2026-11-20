#!/usr/bin/env python3
"""cbc_score.py -- CBC-ALL-0200 (OWNER 11-20): per-type close-by-construction SCORE of a die plan, one row per type, so
every daily plan event shows which CBC rules each type already meets before it binds.  Called by precheck.py (writes
cbc_score.tsv + a section in family_summary.md); advisory, except rule 6 (bundle depth), which bind --strict already
blocks (bundle_depth_check.py).

Rules scored from the plan alone (status PASS / FLAG / ERROR / n/a, value, detail):
  R1  HOP      planned station / ft hops (worst bit of a face window, pin to pin) <= the placed-hop cap (300 um,
               OWNER 11-20 #6; cbc_rules.hop_cap_um(die) when present); value = worst hop, count of chains over.
  R2  ZL-TAP   zero-logic register hops (station and ft chains) whose two registers sit on different nearest clock taps and
               carry no hop lockup latch (clock.ft_hop_lockup) -- the rows DIE-LEVEL-CHECK writes; latched hops longer than
               the 200-um half-cycle cap are flagged too.
  R3  TAP      planned sinks per tap <= 1,000 and each tap's sink region W + H <= 300 um (tap_resolve span rule); with a
               sink_bins_file the planned row registers (stations / ft / face) are added on top (rule 3: station rows count
               in the bins; an upper bound when the bins were measured after the rows).
  R4  RESET    reset relay reach (reset.relay_um, type then die, default reset_tree.REACH_UM) <= the hop cap.
  R5  REGREAD  hard memory cores (SRAM / ROM / RF masters) of the type: INFO count; registered reads are an RTL /
               generator parameter, not visible in the plan (S81-DIE-R3 / ROM owners).
  R6  BUNDLE   relay_depth valid / data bundles at one D (bundle_depth_check.check) -- ERROR, the only blocking rule.
  R7  KIT      CTS subtree balance + cross-tap hold guard: live in the kit (kit_scan.py), n/a here.
  R8  LATTICE  hard-core origins on the parent PG lattice: x (x + W for MY / R180) = 0 mod 8.64, y = 0 mod 4.32.
  R9  RETAP    tap-named rows (landing_contract clock pins source_clock_port / _tap, reset consumer rst_n_t<i>) name a
               tap the type's current tap set has.
Score = PASS rules / scored rules (n/a and INFO excluded).
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import cbc_rules as CBC  # noqa: E402
sys.path.pop(0)

OWNER_HOP_CAP_UM = 300.0          # OWNER 11-20 #6 (generator default on every die)
HALF_HOP_CAP_UM = float(getattr(CBC, "HALF_CYCLE_HOP_CAP_UM", 200.0))
LATTICE_X_UM = 8.64               # schema.GRID_UM: M6 / M7 PG lattice (FABLE-CBC-QK-0130 2.3)
LATTICE_Y_UM = 4.32
LATTICE_TOL_UM = 0.01
MEM_MASTER = re.compile(r"(sram|_rom|rom_|^rom|regfile|_rf_|ot_mem|fakeram)", re.I)
RULES = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9")
FWD_KEYS = ("source_clock_port", "source_clock_tap")
TAPQ = re.compile(r"^rst_n_t(\d+)$")


def hop_cap(die):
    f = getattr(CBC, "hop_cap_um", None)
    try:
        return float(f(die)) if callable(f) else OWNER_HOP_CAP_UM
    except Exception:  # noqa: BLE001
        return OWNER_HOP_CAP_UM


def lattice_resid(core):
    """max residual (um) of a hard core's origin against the PG lattice, orientation-aware"""
    o, s = core.get("origin_um"), core.get("outline_um")
    if not o or not s:
        return None
    w, h = s
    orient = str(core.get("orient", "R0"))
    if orient in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    x = o[0] + (w if orient in ("MY", "R180") else 0.0)
    y = o[1] + (h if orient in ("MX", "R180") else 0.0)

    def res(v, g):
        r = v % g
        return min(r, g - r)
    return max(res(x, LATTICE_X_UM), res(y, LATTICE_Y_UM))


def nearest(taps, p):
    return min(taps, key=lambda t: (t[1] - p[0]) ** 2 + (t[2] - p[1]) ** 2)[0] if taps else None


def chains(t):
    """[(name, [points], latched_fn)] zero-logic register chains of a type: internal_stations (from -> regs -> to) and
    ft_slots (regs only; the face pins are the neighbour's registers)"""
    out = []
    for i, e in enumerate(t.get("internal_stations") or []):
        regs = [tuple(r) for r in (e.get("regs_um") or [])]
        if len(regs) >= 2:
            out.append((f"internal_stations[{i}] {e.get('conn', '')}", regs, None))
    for s in t.get("ft_slots") or []:
        regs = [tuple(r) for r in (s.get("regs_um") or [])]
        if len(regs) >= 2:
            out.append((f"ft_slot {s.get('name')}", regs, s.get("name")))
    return out


def ft_latched(raw, tn, slot, k):
    lk = ((raw or {}).get("clock") or {}).get("ft_hop_lockup") or {}
    if not lk:
        return False
    on = bool(lk.get("all")) and tn not in (lk.get("except") or []) or tn in (lk.get("types") or [])
    if not on:
        return False
    hops = (lk.get("hops") or {}).get(tn)
    return hops is None or int(k) in [int(x) for x in (hops.get(slot) or [])]


def tap_regions(taps, sinks):
    """{tap: [load, x0, y0, x1, y1]} nearest-tap assignment"""
    reg = {}
    for x, y, w in sinks:
        n = nearest(taps, (x, y))
        r = reg.setdefault(n, [0.0, x, y, x, y])
        r[0] += w
        r[1], r[2], r[3], r[4] = min(r[1], x), min(r[2], y), max(r[3], x), max(r[4], y)
    return reg


def planned_row_sinks(t):
    pts = []
    for e in t.get("internal_stations") or []:
        b = int(e.get("bits") or 1)
        pts += [(r[0], r[1], b) for r in e.get("regs_um") or []]
    for s in t.get("ft_slots") or []:
        b = int(s.get("width") or 1)
        pts += [(r[0], r[1], b) for r in s.get("regs_um") or []]
    return pts


def score_type(die, raw, tn, t, taps=None, sinks=None, reach_fn=None, bundle_errors=(), reset_default=405.0):
    """-> {rule: (status, value, detail)} for one plan type"""
    cap = hop_cap(die)
    out = {}
    # R1
    if reach_fn is not None:
        f = reach_fn(t, cap, 1.0)
        out["R1"] = ("FLAG", max(v for v, _ in f), f"{len(f)} chains with a hop > {cap:.0f} um; worst {max(f)[1][:140]}") if f else \
            ("PASS", 0, f"every planned station / ft hop <= {cap:.0f} um")
    else:
        out["R1"] = ("n/a", "", "no reach estimator")
    # R2
    if taps:
        xt = lat_long = n = 0
        ex = ""
        for name, pts, slot in chains(t):
            for k, (a, b) in enumerate(zip(pts, pts[1:])):
                n += 1
                lat = slot is not None and ft_latched(raw, tn, slot, k)
                if lat:
                    if abs(a[0] - b[0]) + abs(a[1] - b[1]) > HALF_HOP_CAP_UM:
                        lat_long += 1
                    continue
                if nearest(taps, a) != nearest(taps, b):
                    xt += 1
                    ex = ex or f"{name} hop {k} {nearest(taps, a)} -> {nearest(taps, b)}"
        out["R2"] = (("FLAG" if (xt or lat_long) else "PASS"), xt,
                     f"{xt} of {n} zero-logic hops on different nearest taps, unlatched (upper bound: <= 5 unshared stages also passes, needs the die tree); {lat_long} latched hops > {HALF_HOP_CAP_UM:.0f} um"
                     + (f"; e.g. {ex}" if ex else ""))
    else:
        out["R2"] = ("n/a", "", "no tap set (hard or single-tap type)")
    # R3
    if taps and sinks:
        ck = t.get("clock") or {}
        snk = list(sinks) + (planned_row_sinks(t) if ck.get("sink_bins_file") else [])
        reg = tap_regions(taps, snk)
        tcap = min(int(ck.get("tap_max_sinks") or CBC.TAP_MAX_SINKS), CBC.TAP_MAX_SINKS)
        over = [k for k, r in reg.items() if r[0] > tcap]
        wide = [k for k, r in reg.items() if (r[3] - r[1]) + (r[4] - r[2]) > CBC.TAP_REGION_WH_UM]
        mx = max(r[0] for r in reg.values())
        mwh = max((r[3] - r[1]) + (r[4] - r[2]) for r in reg.values())
        out["R3"] = (("FLAG" if over or wide else "PASS"), round(mx),
                     f"{len(taps)} taps; max {round(mx)} sinks / tap (cap {tcap}), {len(over)} over; max region W+H {mwh:.0f} um, "
                     f"{len(wide)} over {CBC.TAP_REGION_WH_UM:.0f}" + ("; bins + planned row registers" if ck.get("sink_bins_file") else ""))
    else:
        out["R3"] = ("n/a", "", "no tap set or sinks")
    # R4
    rr = (t.get("reset") or {}).get("relay_um") or ((raw.get("reset") or {}).get("relay_um")) or reset_default
    out["R4"] = (("PASS" if float(rr) <= cap else "FLAG"), float(rr),
                 f"reset relay reach {float(rr):.0f} um vs hop cap {cap:.0f} um (type, then die reset.relay_um, then reset_tree default)")
    # R5
    mem = [c.get("name") or c.get("inst") or c.get("module") for c in t.get("hard_cores") or []
           if MEM_MASTER.search(str(c.get("module") or c.get("master") or c.get("macro") or c.get("name") or ""))]
    out["R5"] = ("INFO", len(mem), f"{len(mem)} memory hard cores" + (f" ({', '.join(map(str, mem[:4]))})" if mem else "")
                 + "; registered read = RTL / generator parameter")
    # R6
    be = [e for e in bundle_errors if f" {tn}:" in e]
    out["R6"] = (("ERROR" if be else "PASS"), len(be), be[0][:200] if be else "relay_depth bundles at one D")
    # R7
    out["R7"] = ("n/a", "", "kit-level (kit_scan.py: subtree balance + cross-tap guard applied)")
    # R8
    res = [(lattice_resid(c), c.get("name") or c.get("inst")) for c in t.get("hard_cores") or []]
    res = [(r, n) for r, n in res if r is not None]
    if res:
        off = [(r, n) for r, n in res if r > LATTICE_TOL_UM]
        w = max(res)
        out["R8"] = (("FLAG" if off else "PASS"), round(w[0], 3),
                     f"{len(off)} of {len(res)} hard-core origins off the {LATTICE_X_UM} x {LATTICE_Y_UM} lattice; worst {w[1]} {w[0]:.3f} um")
    else:
        out["R8"] = ("n/a", "", "no hard cores")
    # R9
    if taps:
        names = {n for n, _, _ in taps}
        idx = {int(m.group(1)) for m in (re.fullmatch(r"clk_t(\d+)", n) for n in names) if m} | ({0} if "clk" in names else set())
        bad = []
        for q in ((t.get("clock") or {}).get("landing_contract") or {}).get("pins") or []:
            if q.get("kind") == "clock" and q.get("dir") == "out":
                bad += [f"{q.get('name')}.{k}={q[k]}" for k in FWD_KEYS if q.get(k) and q[k] != "clk" and q[k] not in names]
        for r in (t.get("reset") or {}).get("consumer_localization") or []:
            g = TAPQ.match(str(r.get("new_reset", "")))
            if g and int(g.group(1)) not in idx:
                bad.append(f"{r.get('instance')}.{r.get('pin')}={r['new_reset']}")
        out["R9"] = (("FLAG" if bad else "PASS"), len(bad), (f"stale tap names: {', '.join(bad[:4])} (retap.py)" if bad else "tap-named rows match the tap set"))
    else:
        out["R9"] = ("n/a", "", "no tap set")
    return out


def summarize(scores):
    ok = sum(1 for s, _, _ in scores.values() if s == "PASS")
    n = sum(1 for s, _, _ in scores.values() if s in ("PASS", "FLAG", "ERROR"))
    return ok, n


def write_tsv(path, rows):
    """rows: [(type, family, scores)]"""
    with open(path, "w") as fh:
        fh.write("type\tfamily\tscore\t" + "\t".join(f"{r}\t{r}_value" for r in RULES) + "\tdetail\n")
        for tn, fam, sc in rows:
            ok, n = summarize(sc)
            det = " | ".join(f"{r} {sc[r][2]}" for r in RULES if sc[r][0] in ("FLAG", "ERROR"))
            fh.write("\t".join([tn, fam, f"{ok}/{n}"] + [x for r in RULES for x in (sc[r][0], str(sc[r][1]))] + [det.replace("\t", " ")]) + "\n")


def summary_md(rows, die, cap):
    L = [f"## CBC score per type (CBC-ALL-0200, advisory; R6 bundle depth is the bind error)", "",
         f"Hop cap {cap:.0f} um, half-cycle {HALF_HOP_CAP_UM:.0f} um; tap <= {CBC.TAP_MAX_SINKS} sinks, region W+H <= "
         f"{CBC.TAP_REGION_WH_UM:.0f} um; lattice {LATTICE_X_UM} x {LATTICE_Y_UM} um.", "",
         "| rule | PASS | FLAG | ERROR | n/a / INFO |", "|---|---|---|---|---|"]
    for r in RULES:
        c = {k: 0 for k in ("PASS", "FLAG", "ERROR", "other")}
        for _, _, sc in rows:
            s = sc[r][0]
            c[s if s in c else "other"] += 1
        L.append(f"| {r} | {c['PASS']} | {c['FLAG']} | {c['ERROR']} | {c['other']} |")
    full = sum(1 for _, _, sc in rows if summarize(sc)[0] == summarize(sc)[1])
    L += ["", f"{full} of {len(rows)} types meet every scored rule.", ""]
    return L
