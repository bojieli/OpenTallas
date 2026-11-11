#!/usr/bin/env python3
"""PLAN-GEN-RULES-1 (OWNER 2026-11-10, all dies): two structural plan-generator rules, applied as ONE plan event per die.

RULE A  port-hold virtual clock from the PLANNED insertion.
    A hard core's IO virtual clock (vclk) stood for the die common latency (250 TT / 202.5 FF = 0.81 x 250) while the
    measured core insertion was 295-434 ps (HBM dma_back vPose2 TT 370-434 / FF 295-350; q3bc_CF2 port hold -427).
    In a core kit the FF sign-off is 'bound-ff' (vclk_ref.py: no rebind inside a core), so the 202.5 bound is what the
    core is signed against.  The 12.3 v5.0 / owner 5e core clock contract already has the right form: the core's
    internal insertion I sits on the parent's core tap (clock.taps[] kind core, insertion_ps / insertion_ff_ps), the
    parent feeds that tap I - common early, and the core's IO vclk = I.  Rule A fills I from the plan where it is
    still the die default:
      * a core tap that already carries a non-default insertion (measured view, or a planned value with a basis)
        keeps it;
      * a default tap of a MEASURED core (--measured-cores: a signed / measured view, e.g. HBM core_insertion_b2l.json)
        takes the measured value;
      * any other default tap gets I = the 12.9d analytic core insertion model (master_plan.core_insertion,
        TT = A + B x L_max, L_max = centre entry -> farthest core corner = (w + h) / 2; fitted on 6 measured
        centre-entry trees, LOO max error 10.9 ps) when that exceeds the default by more than the model's LOO error
        and L_max is within the R4 tap pitch (400 um: one tree; larger cores are multi-tree and listed);
        FF = FF_TT_INSERTION_RATIO (0.81) x TT, the existing corner rule;
      * only types with clock.core_taps 'early' are touched (the only kits whose SDC reads a core tap).
    Rule AT (opt-in, not in the default event): a partition type's own insertion (clock.insertion_ps, the vsN4 / vsN6
    form with insertion_basis) planned the same way from its tap reach (grid cell half-perimeter, single-tap farthest
    corner, density tap radius).  Not default: partition kits sign off FF hold against the routed pin-register mean
    ('rebind', vclk_ref.py), their tap trees are balanced to clock.insertion_ps (KV-P6), and check.py G0 still holds
    the R4 one-die-wide insertion target, so a type move is a die-owner form choice (vsN4 / vsN6 did it by hand).
    The core kit generators read the same tap value (--io-insertion plan; core_io_insertion()), so the parent tap
    and the core vclk come from ONE plan source.  Landing-ring ports are not touched: they are timed against their
    forwarded fclk_in_<b> (landing_contract.ring_input_sdc), not vclk.

RULE B  clock taps from sink count.
    CTS stalls when a tap carries more than OT_TAP_MAX_SINKS (3000; gen_phys._tap_cap) sinks (QC sle_hc0 77k on 15
    taps, HBM vsN6 92k on 20).  For every grid-tap type (tap_mode absent / grid+sinks) the event lowers
    clock.tap_pitch_um (the vsN4 form C knob) to the pitch whose grid has the fewest taps >= ceil(sinks / cap),
    cap = the kit's own OT_TAP_MAX_SINKS (clock.tap_max_sinks, else 3000 grid / 1500 density).
    Sinks = measured synth flops (+ latches / ICGs) of the type's latest kit-wave row (harvest_flops), else the
    plan estimate (cells.py cells x the die's measured flop share; flat estimates of types WITH hard cores are not
    used, they include the cores).  A density-tap type (tap_mode density) gets no pitch: its taps come from the sink
    inventory, so an under-tapped one is listed for the QC hc0 sink_bins mechanism (clock.sink_bins_file from a placed
    netlist, taps.py) instead.  explicit / grid+explicit / tap_edge_y_um / bare hard types are listed only.

The event never changes RTL, pins, outlines, hard cores or cycles; every other key stays byte-identical (checked).

    python3 -I tools/die_plan/plan_gen_rules.py event BASE OUT RECORD [--rules A,B] [--measured FLOPS.json]
                [--sinks SINKS.json] [--measured-cores TABLE.json] [--exclude-cores m1,m2] [--die D]
    python3 -I tools/die_plan/plan_gen_rules.py core-io PLAN MODULE         # -> "TT FF basis" (core kit binding)
    python3 -I tools/die_plan/plan_gen_rules.py flops SYNTH_STAT...          # -> JSON {path: {flops, cells, area}}
"""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

RULE = "PLAN-GEN-RULES-1 (OWNER 2026-11-10)"
FF_RATIO = S.FF_TT_INSERTION_RATIO          # 0.81, the existing corner rule (gen_phys / core_flow / HBM / KV gens)
TAP_CAP_DEFAULT = 3000                      # gen_phys._tap_cap default (grid kits): OT_TAP_MAX_SINKS
PITCH_STEP_UM = 0.01
# clock sinks in a Yosys ASAP7 stat: flops (DFF*, ASYNC_DFF*, SDF*), latches (DHL*, DLL*), clock gates (ICG*)
TAP_REF_RE = re.compile(r"\bclk_t\d+\b")
SINK_CELL_RE = re.compile(r"^(?:DFF|ASYNC_DFF|SDF|DHL|DLL|ICG)\w*_ASAP7\w*$")


# --------------------------------------------------------------------------------------------- insertion model (A)
def _model():
    import master_plan as M
    return M


def model_insertion(reach_um):
    """(TT, FF) of the 12.9d analytic core insertion model at L_max = reach_um (FF = 0.81 x TT)."""
    M = _model()
    tt = round(M.CAL_A + M.CAL_B * float(reach_um), 1)
    return tt, round(FF_RATIO * tt, 1)


def model_error_ps():
    """the model's leave-one-out max error: a planned value within it of the current bound is no change."""
    return float(_model().CAL_LOO_MAX_PS)


def core_reach_um(w, h):
    """centre clock entry (12.8a) -> farthest core corner, Manhattan."""
    return (float(w) + float(h)) / 2.0


def common_ps(P):
    return float(P.clock["insertion_ps"])


def _default_tap(tp, common):
    tt = float(tp.get("insertion_ps", common))
    ff = float(tp.get("insertion_ff_ps", round(FF_RATIO * tt, 3)))
    return abs(tt - common) < 0.05 and abs(ff - round(FF_RATIO * common, 1)) < 0.1 and not tp.get("insertion_basis")


def _core_of_tap(t, tp):
    """the hard_cores[] entry a core tap names (`<inst>` or `<inst>.<pin>`), else None."""
    nm = str(tp.get("name", ""))
    for hc in t.get("hard_cores", []) or []:
        if nm == hc["inst"] or nm.startswith(hc["inst"] + "."):
            return hc
    return None


def type_reach_um(P, tn):
    """(L_max of the type's tap trees, basis) or (None, why) when the model does not apply."""
    t = P.types[tn]
    ck = t.get("clock", {}) or {}
    if t.get("hard"):
        return None, "hard type (own core contract)"
    w, h = map(float, t["outline_um"])
    mode = ck.get("tap_mode")
    if mode == "density":
        return float(ck.get("tap_radius_um", 200.0)), "density tap radius"
    if mode in ("explicit", "grid+explicit") or ck.get("tap_edge_y_um"):
        n = max(1, len(S.tap_grid(P, tn)))
        return math.sqrt(w * h / n), f"{n} taps, sqrt(area / taps)"
    pitch = S.tap_pitch(P, tn)
    nx, ny = max(1, math.ceil(w / pitch - 1e-9)), max(1, math.ceil(h / pitch - 1e-9))
    if nx == 1 and ny == 1:
        x, y = ck.get("tap_um", [w / 2, h / 2])
        return max(abs(float(x) - a) + abs(float(y) - b) for a in (0, w) for b in (0, h)), "single tap, farthest corner"
    return (w / nx + h / ny) / 2.0, f"grid {nx}x{ny} cell half-perimeter"


def type_planned_insertion(P, tn):
    """{tt, ff, basis, planned} of a partition type: a planned type value (insertion_basis) stands, else the model."""
    ck = P.types[tn].get("clock", {}) or {}
    common = common_ps(P)
    if "insertion_ps" in ck and ck.get("insertion_basis"):
        tt = float(ck["insertion_ps"])
        return dict(tt=tt, ff=float(ck.get("insertion_ff_ps", round(FF_RATIO * tt, 1))), basis=ck["insertion_basis"],
                    planned=False)
    L, why = type_reach_um(P, tn)
    if L is None:
        return None
    tt, ff = model_insertion(L)
    return dict(tt=tt, ff=ff, reach_um=round(L, 2), basis=f"12.9d model at L_max {L:.1f} um ({why})", planned=True)


def core_io_insertion(P, module):
    """(TT, FF, basis) the core kit binds its IO vclk to: the parent plan's core-tap insertion of `module` (every tap
    of that module agrees, else ValueError), or None when no non-default tap names it (the generator's own default)."""
    common = common_ps(P)
    seen = set()
    for tn, t in P.types.items():
        for tp in (t.get("clock", {}) or {}).get("taps", []) or []:
            if tp.get("kind") != "core":
                continue
            hc = _core_of_tap(t, tp)
            mod = (hc or {}).get("module") or tp.get("budget_owner")
            if mod != module or _default_tap(tp, common):
                continue
            tt = float(tp["insertion_ps"])
            ff = float(tp.get("insertion_ff_ps", round(FF_RATIO * tt, 1)))
            seen.add((tt, ff, tp.get("insertion_basis") or "plan core tap (measured view)"))
    if not seen:
        return None
    if len({(a, b) for a, b, _ in seen}) > 1:
        raise ValueError(f"core {module}: parent core taps disagree on insertion {sorted(seen)[:4]}")
    return sorted(seen)[0]


def reach_max_um(P):
    """the model is applied up to the R4 tap pitch (budgets.tap_pitch_um, 400): one CTS tree from a centre entry spans
    at most that by the plan rules.  A larger reach (single-tap SM tiles at a 5.8-mm pitch, multi-region cores) is a
    multi-tree clock the model does not describe: listed, not planned."""
    return float(P.budgets.get("tap_pitch_um", 400.0))


def load_measured_cores(path):
    """{module: (TT, FF, basis)} from a measured core insertion table: the HBM core_insertion_b2l.json form (views[]
    module / status MEASURED / insertion_mean_ps / insertion_ff_mean_ps) or {module: [TT, FF] | {tt, ff, basis}}."""
    d = json.loads(Path(path).read_text())
    out = {}
    if isinstance(d, dict) and isinstance(d.get("views"), list):
        for v in d["views"]:
            if v.get("status") == "MEASURED" and v.get("module") and v.get("insertion_mean_ps"):
                tt = float(v["insertion_mean_ps"])
                ff = float(v.get("insertion_ff_mean_ps") or round(FF_RATIO * tt, 1))
                out.setdefault(v["module"], (tt, ff, f"measured view {v.get('view')} ({Path(path).name})"))
        return out
    for m, v in d.items():
        if isinstance(v, (list, tuple)):
            out[m] = (float(v[0]), float(v[1]), f"measured ({Path(path).name})")
        elif isinstance(v, dict) and v.get("tt"):
            out[m] = (float(v["tt"]), float(v.get("ff") or round(FF_RATIO * float(v["tt"]), 1)),
                      v.get("basis") or f"measured ({Path(path).name})")
    return out


def rule_a(Q, types_too=False, measured=None, exclude=()):
    """in place on raw plan Q: plan the default core taps (and with types_too the partition types' own insertion);
    -> record rows.  Core taps are planned only on types with clock.core_taps 'early' (the only kits that read them).
    measured {module: (TT, FF, basis)} (a signed / measured core view) wins over the model; exclude = modules left as
    they are (listed)."""
    P = S.Plan(Q)
    measured = measured or {}
    half = float(P.die["period_ps"]) / 2.0
    common, err, lmax = common_ps(P), model_error_ps(), reach_max_um(P)
    cores, types, listed = {}, {}, {}
    for tn, t in Q["partition_types"].items():
        ck = t.get("clock")
        if not isinstance(ck, dict):
            continue
        for tp in (ck.get("taps", []) or []) if ck.get("core_taps") == "early" else []:
            if tp.get("kind") != "core" or not _default_tap(tp, common):
                continue
            hc = _core_of_tap(t, tp)
            if not hc or not hc.get("outline_um"):
                continue
            if hc["module"] in exclude:
                listed.setdefault(hc["module"], dict(why="excluded by the die owner (--exclude-cores)"))
                continue
            if hc["module"] in measured:
                tt, ff, mb = measured[hc["module"]]
                if abs(tt - common) < 0.05:
                    continue
                if tt - common > half:
                    listed.setdefault(hc["module"], dict(tt=tt, why=f"measured insertion {tt:g} ps: early tap "
                                                         f"{tt - common:g} ps > T/2 {half:g} (a tap moved by more than half "
                                                         "a cycle changes the related edge): die-owner form, not planned"))
                    continue
                tp["insertion_ps"], tp["insertion_ff_ps"] = tt, ff
                tp["insertion_basis"] = f"{RULE} rule A: {mb}"
                c = cores.setdefault(hc["module"], dict(tt=tt, ff=ff, outline_um=hc["outline_um"], taps=0,
                                                        parents=set(), basis="measured"))
                c["taps"] += 1
                c["parents"].add(tn)
                continue
            L = core_reach_um(*hc["outline_um"])
            if L > lmax + 1e-9:
                listed.setdefault(hc["module"], dict(reach_um=round(L, 1), why=f"core reach {L:.0f} um > R4 pitch "
                                                     f"{lmax:g}: multi-tree core clock, model not applied"))
                continue
            tt, ff = model_insertion(L)
            if tt - common <= err:
                continue
            tp["insertion_ps"], tp["insertion_ff_ps"] = tt, ff
            tp["insertion_basis"] = (f"{RULE} rule A: 12.9d core insertion model, centre entry L_max "
                                     f"{core_reach_um(*hc['outline_um']):.1f} um (core {hc['outline_um'][0]:g} x "
                                     f"{hc['outline_um'][1]:g}); FF = {FF_RATIO:g} x TT")
            cores.setdefault(hc["module"], dict(tt=tt, ff=ff, outline_um=hc["outline_um"], taps=0, parents=set(),
                                                basis="12.9d model"))
            cores[hc["module"]]["taps"] += 1
            cores[hc["module"]]["parents"].add(tn)
        pl = type_planned_insertion(P, tn) if types_too else None
        if not pl or not pl["planned"] or t.get("hard"):
            continue
        if pl["reach_um"] > lmax + 1e-9:
            listed[tn] = dict(reach_um=pl["reach_um"], why=f"type tap reach > R4 pitch {lmax:g}: model not applied")
            continue
        cur = float(ck.get("insertion_ps", common))
        if pl["tt"] - cur <= err:
            continue
        ck["insertion_ps"], ck["insertion_basis"] = pl["tt"], f"{RULE} rule A: {pl['basis']}; FF = {FF_RATIO:g} x TT"
        ck.pop("insertion_ff_ps", None)
        types[tn] = dict(from_ps=cur, tt=pl["tt"], ff=pl["ff"], reach_um=pl["reach_um"])
    for v in cores.values():
        v["parents"] = sorted(v["parents"])
    return dict(cores=cores, types=types, listed=listed)


# --------------------------------------------------------------------------------------------- tap count (B)
def grid_taps(w, h, pitch):
    return max(1, math.ceil(w / pitch - 1e-9)) * max(1, math.ceil(h / pitch - 1e-9))


def pitch_for(w, h, need, pitch_max):
    """the pitch <= pitch_max whose grid has the FEWEST taps >= need (largest such pitch on a tie).  The grid cells are
    w / nx x h / ny (schema._grid_taps), so only the breakpoints side / k (0.01-um grid, rounded UP so ceil(side / p)
    is exactly k) give distinct grids."""
    if grid_taps(w, h, pitch_max) >= need:
        return pitch_max
    cands = set()
    for k in range(1, int(need) + 2):
        for side in (w, h):
            p = math.ceil(side / k / PITCH_STEP_UM - 1e-9) * PITCH_STEP_UM
            if 0 < p <= pitch_max:
                cands.add(round(p, 2))
    ok = [p for p in cands if grid_taps(w, h, p) >= need]
    return min(ok, key=lambda p: (grid_taps(w, h, p), -p)) if ok else None


def tap_cap(t):
    ck = t.get("clock", {}) or {}
    return int(ck.get("tap_max_sinks", 1500 if ck.get("tap_mode") == "density" else TAP_CAP_DEFAULT))


def rule_b(Q, sinks):
    """in place on raw plan Q: tap_pitch_um so taps >= ceil(sinks / cap); -> record rows {type: row}."""
    P = S.Plan(Q)
    rows = {}
    for tn, t in Q["partition_types"].items():
        s = sinks.get(tn)
        ck = t.get("clock")
        if not s or not isinstance(ck, dict) or S.bare_hard(t):
            continue
        n_s, basis = int(s["sinks"]), s["basis"]
        cap = tap_cap(t)
        need = math.ceil(n_s / cap)
        mode = ck.get("tap_mode")
        bins_why = ("density taps: add clock.sink_bins_file (QC hc0 sink_bins mechanism, taps.py from a placed "
                    "netlist) so density_taps sizes the taps by the real inventory")
        w, h = map(float, t["outline_um"])
        plain = mode in (None, "grid+explicit") and not ck.get("tap_edge_y_um")
        n_add = len(ck.get("added_taps") or []) if mode == "grid+explicit" else 0
        try:
            # a plain grid is counted from its pitch (schema._grid_taps: ceil(w / p) x ceil(h / p)); other modes ask the
            # plan tool itself
            have = grid_taps(w, h, S.tap_pitch(P, tn)) + n_add if plain else len(S.tap_grid(P, tn))
        except Exception as e:  # a tap mode whose inputs are not on this host (sink_bins_file): listed, no change
            why = f"tap_grid: {type(e).__name__}: {e}"[:200]
            rows[tn] = dict(action="list", why=(bins_why + "; " + why) if mode == "density" else why, sinks=n_s,
                            sinks_basis=basis, need=need)
            continue
        if have >= need:
            continue
        row = dict(sinks=n_s, sinks_basis=basis, cap=cap, need=need, taps_before=have)
        if mode == "density":
            row.update(action="list", why=bins_why)
        elif mode == "explicit" or ck.get("tap_edge_y_um"):
            row.update(action="list", why=f"tap_mode {mode or 'tap_edge_y_um'}: taps are listed explicitly in the plan")
        else:
            old = S.tap_pitch(P, tn)
            extra = have - grid_taps(w, h, old)            # grid+sinks / grid+explicit added taps stay
            p = pitch_for(w, h, need - max(0, extra), old)
            # a re-pitch renumbers the grid taps (clk, clk_t1.. row-major) and so the added taps after them: a type
            # whose plan names a tap port (landing source_clock_port, added_taps clk_t<n>, ...) keeps its taps
            refs = sorted(set(TAP_REF_RE.findall(json.dumps(t))))
            if p is None:
                row.update(action="list", why="no grid pitch reaches the tap count")
            elif refs or mode == "grid+explicit":
                row.update(action="list", proposed_um=p, taps_proposed=grid_taps(w, h, p) + max(0, extra),
                           why=("the plan names tap ports " + ", ".join(refs[:6]) + (" ..." if len(refs) > 6 else "")
                                if refs else "grid+explicit") + ": a re-pitch renumbers them, die-owner form "
                           "(proposed pitch given)")
            else:
                ck["tap_pitch_um"] = p
                row.update(action="tap_pitch_um", from_um=old, to_um=p, taps_after=grid_taps(w, h, p) + max(0, extra))
        rows[tn] = row
    return rows


# --------------------------------------------------------------------------------------------- sinks
def parse_stat(text):
    """Yosys stat -> {cells, area_um2, flops}: the totals of the top (design hierarchy 'including submodules' block
    when present, else the last module block)."""
    blk = text
    if "=== design hierarchy ===" in text:
        blk = text.rsplit("=== design hierarchy ===", 1)[1]
    cells = flops = None
    rows = re.findall(r"^\s+(\d+)\s+(\S+)(?:\s+\S+\s+\S+)?\s+(\S+)\s*$", blk, re.M)
    if rows:
        tot = [int(c) for c, _a, n in rows if n == "cells"]
        cells = tot[-1] if tot else None
        # cell rows after the LAST 'cells' total row belong to the top's totals table
        last = max(i for i, r in enumerate(rows) if r[2] == "cells") if tot else -1
        flops = sum(int(c) for c, _a, n in rows[last + 1:] if SINK_CELL_RE.match(n))
    if cells is None:                                   # older flat format: "Number of cells: N" + "   CELL   N"
        m = re.findall(r"Number of cells:?\s+(\d+)", text)
        cells = int(m[-1]) if m else None
        flops = sum(int(n) for c, n in re.findall(r"^\s+(\S+_ASAP7\S*)\s+(\d+)\s*$", text, re.M) if SINK_CELL_RE.match(c))
    area = re.findall(r"Chip area for (?:top )?module [^:]*:\s*([\d.eE+]+)", text)
    return dict(cells=cells, flops=flops, area_um2=float(area[-1]) if area else None)


def base_names(n):
    """type name, then the landing-cohort / sid bases it was derived from (route_supply._base_names)."""
    out = [n]
    while True:
        m = re.match(r"(.+?)(__cl[0-9a-f]{8}|__sid\w+|__v[0-9a-f]{6,})$", out[-1])
        if not m:
            return out
        out.append(m.group(1))


def sinks_table(raw, die, measured, plan_dir=None):
    """{type: {sinks, basis}}: measured flops (exact type, then cohort base) else cells.py x the die's measured
    flop share (types without hard cores only)."""
    meas = (measured or {}).get(die, {}) if measured else {}
    share = sorted(v["flops"] / v["cells"] for v in meas.values() if v.get("flops") and v.get("cells"))
    med = share[len(share) // 2] if share else None
    est = {}
    try:
        import cells as C
        est, _ = C.estimate(raw, plan_dir=plan_dir)
    except Exception as e:  # advisory: no estimate is not an error
        print(f"# cells.py estimate unavailable: {e}", file=sys.stderr)
    out = {}
    for tn, t in raw["partition_types"].items():
        hit = next((b for b in base_names(tn) if (meas.get(b) or {}).get("flops")), None)
        if hit:
            out[tn] = dict(sinks=int(meas[hit]["flops"]), basis="measured synth flops " +
                           (hit if hit == tn else f"{hit} (base of {tn})") + f" [{meas[hit].get('src', '')}]")
        elif med and est.get(tn) and est[tn][0] and not t.get("hard_cores"):
            out[tn] = dict(sinks=int(round(est[tn][0] * med)),
                           basis=f"ESTIMATE cells.py {int(est[tn][0])} x die median flop share {med:.3f}")
    return out


# --------------------------------------------------------------------------------------------- event
def _dumps_style(raw_bytes, P):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n"):
        if f(P).encode() == raw_bytes:
            return f
    return lambda p: json.dumps(p, indent=1) + "\n"


def _strip(t, keys):
    """a type with the event's keys removed (core taps: their insertion keys), for the preservation check."""
    w = json.loads(json.dumps(t))
    ck = w.get("clock") or {}
    for k in keys:
        ck.pop(k, None)
    for tp in ck.get("taps", []) or []:
        if tp.get("kind") == "core":
            for k in ("insertion_ps", "insertion_ff_ps", "insertion_basis"):
                tp.pop(k, None)
    return w


def apply(P0, rules=("A", "B"), sinks=None, measured=None, exclude=()):
    """-> (new raw plan, record).  Rule B runs first (its pitch sets the tap reach rule A plans with)."""
    Q = json.loads(json.dumps(P0))
    rec = {}
    if "B" in rules:
        rec["B"] = rule_b(Q, sinks or {})
    if "A" in rules or "AT" in rules:
        rec["A"] = rule_a(Q, types_too="AT" in rules, measured=measured, exclude=exclude)
    keys = ("tap_pitch_um", "insertion_ps", "insertion_ff_ps", "insertion_basis")
    for k in P0:
        if k != "partition_types" and json.dumps(P0[k], sort_keys=True) != json.dumps(Q[k], sort_keys=True):
            raise AssertionError(f"top-level key {k} changed")
    for tn, t in P0["partition_types"].items():
        if json.dumps(_strip(t, keys), sort_keys=True) != json.dumps(_strip(Q["partition_types"][tn], keys), sort_keys=True):
            raise AssertionError(f"type {tn} changed beyond the event keys")
    return Q, rec


def affected_types(P0, Q):
    """types whose kit inputs change: every type whose JSON differs (core-tap / insertion / pitch keys)."""
    return sorted(tn for tn in P0["partition_types"]
                  if json.dumps(P0["partition_types"][tn], sort_keys=True) != json.dumps(Q["partition_types"][tn], sort_keys=True))


def cmd_event(a):
    base, out, recp = Path(a.base), Path(a.out), Path(a.record)
    raw = base.read_bytes()
    P0 = json.loads(raw)
    die = a.die or P0["die"]["name"]
    meas = json.loads(Path(a.measured).read_text()) if a.measured else None
    sinks = json.loads(Path(a.sinks).read_text()) if a.sinks else (sinks_table(P0, die, meas, base.parent) if meas else {})
    rules = tuple(x.strip().upper() for x in a.rules.split(",") if x.strip())
    mc = load_measured_cores(a.measured_cores) if a.measured_cores else {}
    ex = tuple(x for x in (a.exclude_cores or "").split(",") if x)
    Q, rec = apply(P0, rules, sinks, mc, ex)
    data = _dumps_style(raw, P0)(Q).encode()
    out.write_bytes(data)
    aff = affected_types(P0, Q)
    cores = sorted((rec.get("A") or {}).get("cores", {}))
    r = dict(schema="opentallas.plan_gen_rules_event.v1", rule=RULE, die=die, rules=list(rules),
             base_plan=str(base), base_plan_sha256=hashlib.sha256(raw).hexdigest(),
             plan_output=str(out), plan_output_sha256=hashlib.sha256(data).hexdigest(),
             affected_types=aff, affected_cores=cores,
             core_kit_args={m: ["--io-tt-ps", f"{v['tt']:g}", "--io-ff-ps", f"{v['ff']:g}"]
                            for m, v in (rec.get("A") or {}).get("cores", {}).items()},
             data_cycles=0, pin_cycles=0, rtl_change=False,
             preservation="every top-level key and every type key outside clock.tap_pitch_um / clock.insertion_ps / "
                          "insertion_ff_ps / insertion_basis and core-tap insertion keys byte-identical (apply())",
             record=rec, sinks=sinks)
    recp.write_text(json.dumps(r, indent=1, default=sorted) + "\n")
    nb = sum(1 for v in (rec.get("B") or {}).values() if v.get("action") == "tap_pitch_um")
    nl = sum(1 for v in (rec.get("B") or {}).values() if v.get("action") == "list")
    print(f"{die}: {len(aff)} types change (A: {len((rec.get('A') or {}).get('types', {}))} type insertions, "
          f"{len(cores)} core modules on {sum(v['taps'] for v in (rec.get('A') or {}).get('cores', {}).values())} taps; "
          f"B: {nb} tap pitches, {nl} listed); {hashlib.sha256(raw).hexdigest()[:12]} -> {out.name} "
          f"{hashlib.sha256(data).hexdigest()[:12]}")


def cmd_core_io(a):
    P = S.Plan(json.loads(Path(a.plan).read_text()))
    v = core_io_insertion(P, a.module)
    print("none" if v is None else f"{v[0]:g} {v[1]:g} {v[2]}")


def cmd_flops(a):
    print(json.dumps({p: parse_stat(Path(p).read_text(errors="replace")) for p in a.stats}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("event")
    e.add_argument("base"), e.add_argument("out"), e.add_argument("record")
    e.add_argument("--rules", default="A,B", help="A = core taps + core kit vclk (default), AT = A plus the partition "
                   "types' own insertion (opt-in), B = tap count")
    e.add_argument("--die")
    e.add_argument("--sinks", help="{type: {sinks, basis}} (overrides --measured)")
    e.add_argument("--measured", help="{die: {type: {flops, cells, src}}} harvested synth flops")
    e.add_argument("--measured-cores", help="measured core insertion table (HBM core_insertion_b2l.json form or "
                   "{module: [TT, FF]}): those modules' default taps take the measured value, not the model")
    e.add_argument("--exclude-cores", help="comma list of core modules the event leaves as they are")
    c = sub.add_parser("core-io")
    c.add_argument("plan"), c.add_argument("module")
    f = sub.add_parser("flops")
    f.add_argument("stats", nargs="+")
    a = ap.parse_args(argv)
    {"event": cmd_event, "core-io": cmd_core_io, "flops": cmd_flops}[a.cmd](a)


if __name__ == "__main__":
    main()
