#!/usr/bin/env python3
"""CBC-RULES-1119 (COORD r713 + amendment 11-19 02:0x): CLOSE-BY-CONSTRUCTION plan pass, die-agnostic.

Per-die plan key `cbc` (die-level, default ON for new plan events; `"cbc": false` opts a die out, an object overrides the
thresholds).  Given a die plan and the bound RTL of a bind of that plan, the pass emits the rows of every rule for all
types, and the lane-latency K deltas, as ONE row file the die owner folds into the next plan event (and proves on a private
kit, r712).  It reuses the generators that already exist; it re-implements none of them:

  rule 1 BOUNDARY  every lane end registered on both sides (schema.lane_natural boundary == number of partition ends; an
                   ft crossing has >= 1 station).  Rows: lanes / slots that are not.
  rule 2 REACH     405 um per placed leg (amendment: not 300; legs the plan never declares count).  0-cycle forms FIRST:
                   relay_branch.py (S81-RLYBR-1 / S81-GEOM-OPUS: branch copies, station join, in-bus trunk aimed at the
                   bit-weighted sink centroid = rule 5); only what is still over the reach gets cycles: relay_depth.py rows
                   (core-to-core, +D) and ft_slots stations (span > 405 x stations -> ceil(span / 405), +delta per lane).
  rule 3 DEPTH     logic levels per cycle <= 13: read from precheck_synth DEPTH output when given (--depth TSV:
                   type, endpoint, levels); rows = cones to pipeline (ceil(levels / 13) - 1 stages) for the generators.
  rule 4 TAP/RESET clock tap <= 1,000 planned sinks (clock.tap_max_sinks = 1000; over-cap taps after the kit's 200-um
                   rebalance get the taps to append, tap_resolve.solve with the 300-um region span); boundary-bank reset relay tree <= 32 per
                   leaf (bank_reset_delta.py: bank_taps 0 cycles on tree types, equal-depth port_relays on hard types).
  rule 5 AIM       inside rule 2 (relay_branch trunk / copies).
Feedback loops (credit returns, state loops: relay_depth read_loops, relay_branch unfixed) keep their form and are listed.

  python3 -I cbc_pass.py --die D --plan PLAN.json --rtl BOUND_RTL_DIR --out DIR [--types RE] [--depth DEPTH.tsv]
                         [--skip relay,reset,taps] [--cycles-per-token N --layers L]
Outputs in DIR: cbc_rows.json (rows per rule and type), k_deltas.tsv (lane, cycles before, after, delta, cause),
cbc_summary.md (per die: added cycles per lane, added flops, paths still over limit, token cost), cbc.json (run record).
Estimator + row writer only: it never edits a live plan, never holds or gates (owner r703/r704).
"""
import argparse
import collections
import contextlib
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "precheck"))

# ONE threshold set, shared with tools/precheck (PRECHECK-1119): import these, do not copy the numbers
import cbc_rules as RULES
import leg_class as LC   # COORD 11-19: every threshold from the shared rule module (PRECHECK-1119 imports it too)
HOP_UM = RULES.REACH_UM_PER_HOP
DEPTH_LEVELS = RULES.DEPTH_LEVELS_MAX      # pre-screen only; rule 3 is RULES.LOGIC_PS_MAX (zero_wire.py)
TAP_SINKS = RULES.TAP_MAX_SINKS
RESET_LEAF = RULES.RESET_LEAF_MAX_FANOUT
TAP_RADIUS_UM = RULES.TAP_RADIUS_UM
LOGIC_PS = RULES.LOGIC_PS_MAX
DEFAULTS = dict(hop_um=HOP_UM, depth_levels=DEPTH_LEVELS, tap_sinks=TAP_SINKS, reset_leaf=RESET_LEAF)


def cbc_settings(raw):
    """(enabled, thresholds) from the die-level plan key `cbc`: absent or true = on with DEFAULTS, false = off,
    an object = on with its overrides (enabled: false turns it off)."""
    v = raw.get("cbc", True)
    if v is False:
        return False, dict(DEFAULTS)
    if isinstance(v, dict):
        return bool(v.get("enabled", True)), dict(DEFAULTS, **{k: v[k] for k in DEFAULTS if k in v})
    return True, dict(DEFAULTS)


def family(t):
    return re.split(r"__(?:t\d+|cl[0-9a-f]{6,}|pv[0-9a-f]{6,})", t)[0]


def ft_span(t, sl):
    """check.py geometry (face to face): kept for reference only -- the corner form (w + h) / 2 is NOT the crossing a lane
    makes (FABLE-PD-QC-0407: QC cbx a22 98 um pin-to-pin priced as 1,884); ft_station_rows uses ft_pin_legs"""
    w, h = t["outline_um"]
    fs = {sl["in_face"], sl["out_face"]}
    return w if fs == {"E", "W"} else h if fs == {"N", "S"} else (w + h) / 2.0


def _face_xy(face, c, W, H):
    return {"N": (c, H), "S": (c, 0.0), "E": (W, c), "W": (0.0, c)}[face]


def _slot_pin_coords(sl, stem, W, H):
    """[coord along the face] per bit of ft slot port <slot>_i (stem in) / <slot>_o (stem out), TYPE frame: the
    deterministic pin table (schema.pin_positions, the one gen phys and bind use, so these are the bound pin sites);
    without layers an even spread over the window; without a window the face centre"""
    import schema as S
    face, n = sl[stem + "_face"], int(sl.get("width") or 1)
    ext = H if face in ("E", "W") else W
    win = sl.get(stem + "_window_um")
    lays = sl.get(stem + "_layers", sl.get("layers"))
    if win and lays:
        try:
            port = dict(id=f"{sl['name']}_{stem[0]}", width=n, epoch=False, face=face, window_um=list(win), layers=list(lays),
                        order=sl.get(stem + "_order", sl.get("order", "lsb_low")))
            got = {b: c for b, _ln, c in S.pin_positions(port, {L["name"]: L for L in S.ASAP7_LAYERS})}
            if len(got) >= n:
                return [got[i] for i in range(n)]
        except (ValueError, KeyError, TypeError):
            pass
    lo, hi = (sorted(win) if win else (ext / 2.0, ext / 2.0))
    if sl.get(stem + "_order", sl.get("order", "lsb_low")) == "lsb_high":
        lo, hi = hi, lo
    return [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]


def ft_pin_legs(t, sl):
    """[(in pin xy, out pin xy)] per bit of an ft slot, type frame (bit i enters on <slot>_i[i], leaves on <slot>_o[i])"""
    W, H = t["outline_um"]
    ci, co = _slot_pin_coords(sl, "in", W, H), _slot_pin_coords(sl, "out", W, H)
    return [(_face_xy(sl["in_face"], a, W, H), _face_xy(sl["out_face"], b, W, H)) for a, b in zip(ci, co)]


# ------------------------------------------------------------------------------------------------ rule 1 + 2 (ft)
def boundary_rows(P, rtl_dir=None, types=()):
    """rule 1 on the AS-BOUND RTL (the plan model counts both ends by construction): every bus of a type has its own
    boundary bank u_bin_<bus> / u_bout_<bus> (ot_dp_st / ste / lk), every ft slot >= 1 station.  A registered-pin hard
    partition (no flop of ours inside) is listed once as hard-IP-registered, not as a row."""
    rows = []
    for tn, t in P.types.items():
        for sl in t.get("ft_slots") or []:
            if int(sl.get("stations", 1) or 0) < 1:
                rows.append(dict(type=tn, slot=sl.get("name"), stations=sl.get("stations"), rule="ft crossing without a station"))
    if not rtl_dir:
        return rows
    import bank_reset_delta as B
    for tn in types:
        t = P.types[tn]
        try:
            sv = B.bound_rtl(rtl_dir, tn, t).read_text()
        except B.DeltaError:
            continue
        if "registered-pin hard partition" in sv:
            continue
        insts = set(re.findall(r"\b(u_b(?:in|out)_\w+)\s*\(", sv))
        for b in t.get("buses") or []:
            want = f"u_b{'in' if b.get('dir') == 'in' else 'out'}_{b['name']}"
            if want not in insts and not any(i.startswith(want + "_") for i in insts):
                rows.append(dict(type=tn, bus=b["name"], dir=b.get("dir"), width=b.get("width"), rule="bus without its boundary bank"))
    return rows


def ft_station_rows(P, hop):
    """ft slots whose crossing needs more stations than it has (+delta cycles on every crossing lane).  The crossing is
    PIN TO PIN (FABLE-PD-QC-0407 11-19): every bit's leg from its <slot>_i pin to its <slot>_o pin, priced by the shared
    leg class (leg_class.classify_pts on cbc_rules.classify_leg): an ft slot is a pure register chain, so over
    REACH_CORE_SPAN_UM of hard core it takes the reach (hop) per station, else it is buffered (REACH_BUFFERED_UM); strap /
    tie slots never count.  The slot needs the worst bit's hops.  Stations already built (built_station_extra) and
    cross-tap hop stations (ft_hop_xtap) count, as in schema.lane_natural."""
    import schema as S
    rows = {}
    for tn, t in P.types.items():
        rects = LC.core_rects(t)
        for sl in t.get("ft_slots") or []:
            k = int(sl.get("stations", 1) or 1)
            try:
                k += S.built_station_extra(P.raw, tn, sl["name"]) + len(S.ft_hop_xtap(P.raw, tn, sl["name"]))
            except Exception:  # noqa: BLE001 -- a fake plan in tests has no raw
                pass
            best = None
            for a, b in ft_pin_legs(t, sl):
                cls, hops, core = LC.classify_pts(a, b, rects, launch=f"port:{sl['name']}_i", capture=f"port:{sl['name']}_o")
                if cls == "core" and hop != RULES.REACH_UM_PER_HOP:
                    hops = max(1, math.ceil((abs(a[0] - b[0]) + abs(a[1] - b[1])) / hop - 1e-9))
                L = abs(a[0] - b[0]) + abs(a[1] - b[1])
                key = (hops, L)
                if best is None or key > best[0]:
                    best = (key, cls, core)
                if cls == "static":
                    break
            if best is None:
                continue
            (need, span), cls, core = best
            if need > k:
                rows[(tn, sl["name"])] = dict(type=tn, slot=sl["name"], stations=k, set_stations=need, delta=need - k,
                                              span_um=round(span, 1), corner_span_um=round(ft_span(t, sl), 1),
                                              width=sl.get("width"), leg_class=cls, core_span_um=round(core, 1))
    return rows


def k_deltas(P, ft_rows):
    """per lane: plan cycles now, + the ft station deltas of every crossed slot"""
    out = []
    for lid in P.lanes:
        add, why = 0, []
        for part, slot, _a, _b in P.lane_crossings(lid):
            if not slot:
                continue
            r = ft_rows.get((P.parts[part]["type"], slot))
            if r:
                add += r["delta"]
                why.append(f"{part}.{slot}+{r['delta']}")
        if add:
            cyc = P.lane_natural(lid)["cycles"]
            out.append(dict(lane=lid, before=cyc, after=cyc + add, delta=add, cause=",".join(why)))
    return out


# ------------------------------------------------------------------------------------------------ rule 2/5 relays
def stage_rtl(rtl_dir, types, work):
    """relay_branch / relay_depth / reset read BOUND_DIR/<type>.sv; binds name files <prefix>_<type>.sv, <type>_part.sv or
    <type>_bound.sv, and a die may bind in several binders (KV: bound_binder2, bound_pv, ...): rtl_dir is one directory or a
    comma list, the first directory holding a type wins.  Links them by type."""
    d = Path(work) / "bound"
    d.mkdir(parents=True, exist_ok=True)
    names = {}
    for src in [Path(x) for x in str(rtl_dir).split(",") if x]:
        for p in sorted(src.glob("*.sv")):
            names.setdefault(p.stem, p)
    n = 0
    for tn in types:
        p = names.get(tn) or names.get(tn + "_part") or names.get(tn + "_bound") or \
            next((names[s] for s in names if re.fullmatch(r"[A-Za-z0-9]+_" + re.escape(tn), s)), None)
        if p is None:
            continue
        q = d / f"{tn}.sv"
        if not q.exists():
            q.symlink_to(p.resolve())
        n += 1
    return d, n


def run_tool(args, log):
    with open(log, "w") as fh:
        r = subprocess.run([sys.executable, "-I"] + [str(a) for a in args], stdout=fh, stderr=subprocess.STDOUT)
    return r.returncode


def relay_rows(plan_path, type_re, bound, work, hop):
    """relay_branch (0 cycles first) then relay_depth on the branch-applied plan (cycles for what is left)"""
    br_plan, br_rep = Path(work) / "plan_branch.json", Path(work) / "relay_branch.json"
    rc1 = run_tool([HERE / "relay_branch.py", plan_path, type_re, bound, "--plan-dir", Path(plan_path).resolve().parent,
                    "--limit", hop, "--out-plan", br_plan, "--report", br_rep], Path(work) / "relay_branch.log")
    base = br_plan if rc1 == 0 and br_plan.is_file() else plan_path
    dp_rep = Path(work) / "relay_depth.json"
    rc2 = run_tool([HERE / "relay_depth.py", base, type_re, bound, "--limit", hop, "--report", dp_rep],
                   Path(work) / "relay_depth.log")
    br = json.loads(br_rep.read_text()) if br_rep.is_file() else []
    dp = json.loads(dp_rep.read_text()) if dp_rep.is_file() else []
    return dict(rc_branch=rc1, rc_depth=rc2, branch=br, depth=dp)


def summarise_relays(rel):
    out = dict(copies=0, far_copies=0, joins=0, trunks=0, depth_rows=0, depth_cycles=0, unfixed=[], read_loops=[], per_type={},
               branch_stages_added=0, far_need_stages=0)
    for r in rel["branch"]:
        if r.get("error"):
            continue
        cp = [c for x in r.get("relay_branch") or [] for c in x["copies"]]
        out["copies"] += len(cp)
        out["far_copies"] += sum(1 for c in cp if c.get("D"))
        # internal stages the branch rows add (0 unless relay_branch.py --add-cycles): never reported as 0-cycle
        out["branch_stages_added"] += sum(int(d.get("D", 0)) for d in r.get("relay_depth_sink") or [])
        far_need = [u for u in r.get("detail") or [] if u.get("need_D")]
        out["far_need_stages"] += len(far_need)
        for u in far_need:
            out["unfixed"].append(dict(type=r["type"], relay=u["relay"], copy=u["copy"], need_D=u["need_D"], path_um=u["path_um"],
                                       reason="far branch over the reach: needs stages (cycles) or a re-site, not emitted"))
        out["joins"] += sum(len(v) for v in (r.get("joins") or {}).values())
        out["trunks"] += len(r.get("trunks") or {})
        if cp or r.get("joins") or r.get("trunks"):
            out["per_type"].setdefault(r["type"], {})["zero_cycle"] = dict(copies=len(cp), joins=sum(len(v) for v in (r.get("joins") or {}).values()),
                                                                          trunks=len(r.get("trunks") or {}))
    for r in rel["depth"]:
        if r.get("error"):
            continue
        rows = r.get("rows_data") or r.get("rows") or []
        if isinstance(rows, list) and rows:
            out["depth_rows"] += len(rows)
            mx = max(int(x.get("D", 0)) for x in rows)
            out["depth_cycles"] = max(out["depth_cycles"], mx)
            out["per_type"].setdefault(r["type"], {})["relay_depth"] = dict(rows=len(rows), max_D=mx,
                                                                            flops=sum(int(x.get("D", 0)) * max(1, int(x.get("bits", 1) if isinstance(x.get("bits"), int) else (x["bits"][1] - x["bits"][0] + 1 if isinstance(x.get("bits"), list) else 1))) for x in rows))
        for k in ("unfixed", "read_loops"):
            for u in r.get(k) or []:
                out[k].append(dict(type=r["type"], **(u if isinstance(u, dict) else {"path": u})))
    return out


# ------------------------------------------------------------------------------------------------ rule 4 taps
def tree_root(plan_path):
    """the source tree a plan lives in (<root>/physical/die_plan/...): its repo-relative plan inputs (sink bins) resolve there"""
    s = str(Path(plan_path).resolve())
    return Path(s.split("/physical/", 1)[0]) if "/physical/" in s else None


TAP_REGION = RULES.TAP_REGION_WH_UM


TILE_UM = 150.0           # FABLE-PD-QC-0407: a type with fewer taps than occupied 150-um sink tiles is flagged
SOLVE_PTS_MAX = 20000     # sink points handed to tap_resolve.solve (larger types are scaled; region W + H is geometric)


def region_wh(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (max(xs) - min(xs)) + (max(ys) - min(ys))


def sink_tiles(sinks, tile=TILE_UM):
    """occupied tile x tile um tiles of [(x, y, w)]"""
    return len({(int(x // tile), int(y // tile)) for x, y, w in sinks if w > 0})


def solve_taps(P, tn, t, grid, sinks, cap, span=None, radius=None):
    """COORD 11-19: ONE implementation of the tap-region rule -- tap_resolve.solve with span (= tap_resolve.py --span-um,
    FABLE-FIX-S81-LEPE) on the plan sink sites.  Taps are only appended (legal sites: outline, tap_clear halo of hard cores,
    placed macros, keepouts, spacing).  -> (added [(x, y)], stats before, stats after, scale) with stats per tap
    (load, beyond radius, p95, max, W + H) at scale (sink weights x scale)."""
    import schema as S
    import tap_resolve as TR
    from placement_obstacles import placement_boxes
    span = RULES.TAP_REGION_WH_UM if span is None else span
    radius = RULES.TAP_RADIUS_UM if radius is None else radius
    ck = t.get("clock") or {}
    clear = S.type_tap_clear(t)
    boxes = list(placement_boxes(t, halo=clear).values())
    boxes += [(x0 - clear, y0 - clear, x1 + clear, y1 + clear) for x0, y0, x1, y1 in ck.get("keepouts_um", [])]
    legal = TR.make_legal(t["outline_um"], clear, boxes)
    try:
        core = [(x, y) for _, x, y, _ in S.core_taps(P, tn)]
    except Exception:  # noqa: BLE001 -- a plan without core taps
        core = []
    total = sum(w for *_, w in sinks) or 1.0
    f = min(1.0, SOLVE_PTS_MAX / total)
    pts, acc = [], 0.0
    for x, y, w in sinks:                     # weights -> points (carry the rounding, so the count is kept)
        acc += w * f
        n = int(acc)
        acc -= n
        pts += [(x, y)] * n
    exist = [(x, y) for _, x, y in grid]
    target = max(1, int(cap * f))
    s0 = TR.tap_stats(exist, pts, radius)
    over = any(q[4] > span or q[0] > target for q in s0)
    need = math.ceil(total / cap) + sink_tiles(sinks)
    added = TR.solve(exist, pts, legal, target, radius, core, max_add=max(80, min(600, 2 * need)),
                     min_new=max(1, int(8 * f)), span=span) if over else []
    return added, s0, TR.tap_stats(exist + added, pts, radius) if added else s0, f


def tap_rows(P, cap, plan_path=None):
    import precheck as PC
    import schema as S
    import taps as T
    root = tree_root(plan_path) if plan_path else None
    if root is not None:
        T._root = lambda: root                     # plan inputs from the plan's own tree, not this tool checkout
        T.PLAN_DIR = str(Path(plan_path).resolve().parent)
    rows, errs = [], []
    for tn, t in P.types.items():
        if t.get("hard"):
            continue
        ck = t.get("clock") or {}
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                grid = [(n, float(x), float(y)) for n, x, y in S.tap_grid(P, tn)]
                sinks = T.sink_sites(P, tn)
        except Exception as e:  # noqa: BLE001 -- estimator
            errs.append((tn, f"{type(e).__name__}: {str(e)[:160]}"))
            continue
        if not grid or not sinks:
            continue
        # COORD 11-19 (FABLE-CLOSURE-STRATEGY 03:30): PRIMARY rule = one tap's sink region W + H <= TAP_REGION_WH_UM on
        # nearest-tap sinks with NO spill; TAP_MAX_SINKS stays the secondary cap.  Solved by tap_resolve.solve (span), the
        # same solver as tap_resolve.py --span-um: the row lists the taps to APPEND (clock.taps / clock.added_taps).
        cur = int(ck.get("tap_max_sinks") or 0)
        tiles = sink_tiles(sinks)
        try:
            added, s0, s1, f = solve_taps(P, tn, t, grid, sinks, cap)
        except Exception as e:  # noqa: BLE001 -- estimator
            errs.append((tn, f"tap_resolve {type(e).__name__}: {str(e)[:160]}"))
            continue
        worst0 = max((q[4] for q in s0), default=0.0)
        worst1 = max((q[4] for q in s1), default=0.0)
        few = len(grid) < tiles
        if not added and not few and cur and cur <= cap and worst0 <= TAP_REGION:
            continue
        mode = ck.get("tap_mode", "grid")
        n0 = len(grid)
        rows.append(dict(type=tn, family=family(tn), tap_mode=mode, set={"clock.tap_max_sinks": cap},
                         was_tap_max_sinks=cur or None, taps=n0, planned_sinks=round(sum(w for *_, w in sinks)),
                         sink_tiles_150um=tiles, taps_below_tiles=few,
                         worst_region_wh_um=round(worst0, 1), taps_over_region=sum(1 for q in s0 if q[4] > TAP_REGION),
                         append_to="clock.taps" if mode == "explicit" else "clock.added_taps",
                         add_taps=[dict(name=f"clk_t{n0 + i}", xy=[round(x, 2), round(y, 2)], sinks=round(q[0] / f),
                                        region_wh_um=round(q[4], 1)) for i, ((x, y), q) in enumerate(zip(added, s1[n0:]))],
                         taps_after=n0 + len(added), worst_region_wh_after_um=round(worst1, 1),
                         taps_over_region_after=sum(1 for q in s1 if q[4] > TAP_REGION),
                         max_load_after=round(max((q[0] for q in s1), default=0) / f)))
    return rows, errs


# ------------------------------------------------------------------------------------------------ rule 4 reset
def reset_rows(raw, rtl_dir, types, hop, leaf):
    import bank_reset_delta as B
    out, errs = {}, []
    for tn in types:
        t = json.loads(json.dumps(raw["partition_types"][tn]))
        try:
            sv = B.bound_rtl(rtl_dir, tn, t).read_text()
        except B.DeltaError:
            continue
        if not B.banks_on_rst(sv):
            continue
        try:
            r = B.type_delta(tn, t, sv, None, hop, leaf)
        except Exception as e:  # noqa: BLE001 -- estimator: list, never stop
            errs.append((tn, f"{type(e).__name__}: {str(e)[:200]}"))
            continue
        worst = max([d.get("was_hop_um") or 0 for d in r.get("detail") or []], default=0)
        if r["rows"] and worst > hop:
            out[tn] = dict(form=r["form"], rows=r["rows"], relay_sites=r.get("relay_sites"), reset_depth=r.get("reset_depth"),
                           added_reset_cycles=r["added_reset_cycles"], flops=r["flops"], was_hop_max_um=round(worst, 1))
    return out, errs


# ------------------------------------------------------------------------------------------------ rule 3 depth
def depth_rows(path, limit):
    rows = []
    if not path:
        return rows
    for ln in Path(path).read_text().splitlines():
        f = ln.split("\t")
        if len(f) < 3 or not f[2].strip().isdigit():
            continue
        lv = int(f[2])
        if lv > limit:
            rows.append(dict(type=f[0], endpoint=f[1], levels=lv, add_stages=math.ceil(lv / limit) - 1))
    return rows


# ------------------------------------------------------------------------------------------------ token cost
def token_cost(kd, cycles_per_token, layers, freq_hz):
    """bounds on the tokens/s cost of the K deltas: low = the largest lane delta once per layer (parallel lanes, one
    traversal); high = the sum of all lane deltas once per layer (every changed lane serial on the token path).
    A count-aligned pad that already exceeds the delta absorbs it (0) -- not modelled here, so low is still an upper
    bound of the true cost of an absorbed lane."""
    if not cycles_per_token or not kd:
        return None
    lo = max(x["delta"] for x in kd) * layers
    hi = sum(x["delta"] for x in kd) * layers
    base = freq_hz / cycles_per_token
    return dict(base_tok_s=round(base, 1), cycles_per_token=cycles_per_token, layers=layers,
                low=dict(add_cycles=lo, tok_s=round(freq_hz / (cycles_per_token + lo), 1), loss_pct=round(100 * lo / (cycles_per_token + lo), 3)),
                high=dict(add_cycles=hi, tok_s=round(freq_hz / (cycles_per_token + hi), 1), loss_pct=round(100 * hi / (cycles_per_token + hi), 3)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--die", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--rtl", help="bound RTL dir of a bind of this plan (bind out/rtl)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--types", default=".*", help="regex over type names")
    ap.add_argument("--depth", help="precheck_synth DEPTH tsv: type, endpoint, levels")
    ap.add_argument("--skip", default="", help="comma list of relay,reset,taps")
    ap.add_argument("--cycles-per-token", type=float)
    ap.add_argument("--layers", type=int, default=1)
    ap.add_argument("--freq-hz", type=float)
    a = ap.parse_args(argv)
    import schema as S
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    raw = json.loads(Path(a.plan).read_text())
    on, th = cbc_settings(raw)
    rec = dict(die=a.die, plan=str(a.plan), rtl=a.rtl, cbc=on, thresholds=th)
    if not on:
        (out / "cbc.json").write_text(json.dumps(dict(rec, note="plan key cbc: false -- no rows"), indent=1))
        print(f"CBC {a.die}: off by plan key")
        return 0
    with contextlib.redirect_stdout(io.StringIO()):
        P = S.Plan(raw, a.plan)
    skip = {s.strip() for s in a.skip.split(",") if s.strip()}
    types = sorted(t for t in P.types if re.search(a.types, t) and t in {p["type"] for p in P.parts.values()})
    bound, n_bound = stage_rtl(a.rtl, types, out) if a.rtl else (None, 0)
    rows = dict(boundary=boundary_rows(P, bound, types))
    ftr = ft_station_rows(P, th["hop_um"])
    rows["ft_stations"] = sorted(ftr.values(), key=lambda r: (r["type"], r["slot"]))
    kd = k_deltas(P, ftr)
    rel = None
    if a.rtl and "relay" not in skip:
        rel = relay_rows(a.plan, a.types, bound, out, th["hop_um"])
        rows["relays"] = summarise_relays(rel)
        rows["relays"]["bound_types"] = n_bound
    if "taps" not in skip:
        rows["taps"], tap_err = tap_rows(P, th["tap_sinks"], a.plan)
    else:
        tap_err = []
    if a.rtl and "reset" not in skip:
        rows["reset"], rs_err = reset_rows(raw, bound, types, th["hop_um"], th["reset_leaf"])
    else:
        rs_err = []
    rows["depth"] = depth_rows(a.depth, th["depth_levels"])
    freq = a.freq_hz or 1e12 / float(raw["die"].get("period_ps", 833))
    cost = token_cost(kd, a.cycles_per_token, a.layers, freq)
    (out / "cbc_rows.json").write_text(json.dumps(rows, indent=1) + "\n")
    with open(out / "k_deltas.tsv", "w") as fh:
        fh.write("lane\tbefore\tafter\tdelta\tcause\n")
        for x in kd:
            fh.write(f"{x['lane']}\t{x['before']}\t{x['after']}\t{x['delta']}\t{x['cause']}\n")
    # summary
    flops_ft = sum(r["delta"] * int(r.get("width") or 0) for r in rows["ft_stations"])
    rl = rows.get("relays") or {}
    flops_rel = sum(v.get("relay_depth", {}).get("flops", 0) for v in (rl.get("per_type") or {}).values())
    flops_rst = sum(v["flops"] for v in (rows.get("reset") or {}).values())
    by_delta = collections.Counter(x["delta"] for x in kd)
    L = [f"# CBC {a.die}", "", f"plan `{a.plan}`; bound RTL `{a.rtl}`; thresholds {th}; {len(types)} placed types; "
         f"{time.time() - t0:.0f} s.", "Row writer / estimator only (r703/r704): nothing here holds a build.", "",
         "## Cycles per lane (K deltas)",
         f"- {len(kd)} of {len(P.lanes)} lanes change; delta histogram {dict(sorted(by_delta.items()))}; "
         f"ft slots re-stationed: {len(rows['ft_stations'])} (families {sorted({family(r['type']) for r in rows['ft_stations']})[:12]})",
         f"- core-to-core relay_depth rows after 0-cycle fixes: {rl.get('depth_rows', 0)} (max D {rl.get('depth_cycles', 0)}; "
         "internal pipe cycles, bind_core_input_pipe / compiler, not plan lanes)" if rel else "- relays: not run (no --rtl)",
         f"- relay fixes in plan_branch.json: {rl.get('copies', 0)} branch copies, {rl.get('joins', 0)} station joins, "
         f"{rl.get('trunks', 0)} trunk re-aims; internal stages these rows ADD: {rl.get('branch_stages_added', 0)} "
         f"(0 = stage count kept, the 0-cycle form); far branches left over the reach (need stages, not emitted): "
         f"{rl.get('far_need_stages', 0)}; leaves matched: S81 ot_s81_rly*/dsfd_rly_* and ot_dp_dly/ot_dp_dly_keep" if rel else "",
         f"- reset: {len(rows.get('reset') or {})} types get bank relay rows, "
         f"+{max([v['added_reset_cycles'] for v in (rows.get('reset') or {}).values()], default=0)} reset-release cycles max (boot-only)",
         "", "## Added flops",
         f"- ft stations {flops_ft}; relay_depth {flops_rel}; reset relays {flops_rst}; total {flops_ft + flops_rel + flops_rst}", "",
         "## Still over limit (kept form: feedback / read loops)",
         f"- relay_depth unfixed {len(rl.get('unfixed') or [])}, read loops {len(rl.get('read_loops') or [])}" if rel else "- n/a",
         f"- boundary rows {len(rows['boundary'])}; depth rows {len(rows['depth'])} (needs precheck_synth DEPTH)" ,
         "", "## Taps (cap " + str(th["tap_sinks"]) + ")",
         f"- {len(rows.get('taps') or [])} types need tap_max_sinks {th['tap_sinks']}; "
         f"{sum(1 for r in rows.get('taps') or [] if r['add_taps'])} with taps over the region (W+H > {TAP_REGION:.0f} um, no spill) or the cap "
         f"({sum(r['taps_over_region'] for r in rows.get('taps') or [])} taps over the region), "
         f"{sum(len(r['add_taps']) for r in rows.get('taps') or [])} added taps (tap_resolve.solve, span {TAP_REGION:.0f}), "
         f"{sum(r['taps_over_region_after'] for r in rows.get('taps') or [])} taps still over the region after",
         f"- {sum(1 for r in rows.get('taps') or [] if r['taps_below_tiles'])} types with fewer taps than occupied {TILE_UM:.0f}-um sink tiles: "
         + ", ".join(f"{r['type']} {r['taps']}<{r['sink_tiles_150um']}" for r in sorted(rows.get('taps') or [], key=lambda r: r['taps'] - r['sink_tiles_150um']) if r['taps_below_tiles'])[:1500], ""]
    if cost:
        L += ["## Token cost", f"- base {cost['base_tok_s']} tok/s ({cost['cycles_per_token']:.0f} cycles/token, {cost['layers']} traversals); "
              f"low +{cost['low']['add_cycles']} cycles -> {cost['low']['tok_s']} ({cost['low']['loss_pct']} %); "
              f"high +{cost['high']['add_cycles']} -> {cost['high']['tok_s']} ({cost['high']['loss_pct']} %)", ""]
    errs = [("taps",) + e for e in tap_err] + [("reset",) + e for e in rs_err]
    if errs:
        L += ["## Errors (listed, not blocking)"] + [f"- {k} {t}: {e[:200]}" for k, t, e in errs[:40]]
    (out / "cbc_summary.md").write_text("\n".join(x for x in L if x is not None) + "\n")
    (out / "cbc.json").write_text(json.dumps(dict(rec, seconds=round(time.time() - t0, 1), lanes_changed=len(kd),
                                                  flops=dict(ft=flops_ft, relay=flops_rel, reset=flops_rst), token=cost,
                                                  errors=errs[:200]), indent=1) + "\n")
    print(f"CBC {a.die}: {len(kd)} lanes +K, ft {len(rows['ft_stations'])}, taps {len(rows.get('taps') or [])}, reset "
          f"{len(rows.get('reset') or {})}, relays {'run' if rel else 'skipped'}, {time.time() - t0:.0f} s -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
