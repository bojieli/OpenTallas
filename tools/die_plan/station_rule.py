#!/usr/bin/env python3
"""LOCKUP-STATION-1130 (FABLE-CLOSURE-STRATEGY 11-20 section 1.2; OWNER: hold by structure -- shared taps, launch-side
lockup latches, CTS balance -- never by changing the clock): ONE die-agnostic station rule for every generated
register hop, on all dies.

Why (measured): the pre-route hold repair adds 8 to 14 % of the instances on the families that stall in GRT (S81 leaf,
slice C, QC su_c / coll_core, HEAD hd_lep0N 17k cells).  On S81 leaf t39 (D8i kit, 4_cts) 23,153 of 29,864 zero-logic
register -> register pairs hang on two different clock taps (zl_pairs.tcl); the pre-repair hold census of the same
kit is cross_tap 14,281 / port_out 1,884 / port_in 1,167 / same_tap 41 ends, and the repair adds 47,483 cells.  A
cross-tap zero-logic pair loses the tap window (no CRPR across tap ports), so it is padded with buffers by that much.

The rule (four parts, one module; every number from tools/die_plan/cbc_rules.py):
  1. COUNT     a lane of pin-to-pin length L takes n = max(1, ceil(L / REACH_UM_PER_HOP)) registers, the first rank
               included: n - 1 = ceil(L / 300) - 1 intermediate stations (cbc_rules.REACH_UM_PER_HOP, 300 um).
  2. SITE      each bit's stations sit at equal pitch on THAT bit's own pin -> pin route (stage j at j / n of it), so a
               stage of a bus is a line across the bus, never a packed bank; snapped to free legal row sites with the
               ft_spread allocator (macro keep-off, other slots' sites).
  3. FIRST     stage 0 is seated at the in pin (regs_um[0] = in-window centre, explicit_stage0, keep_firm).
  4. LOCKUP    every zero-logic hop whose launch and capture registers are predicted on different clock taps gets the
               launch-side transparent-low lockup latch ot_dp_lk u_fl_* with the station (0 cycles; clock_taps.tcl
               hangs it on the launch tap, lec.py latch_to_wire).  Prediction: ft slots by the plan tap grid
               (ft_xtap.predict_slot: nearest tap, unknown = cross); every other station class (internal stations,
               landing pads, relay and leaf stage registers) from the newest kit's measured pairs (zl_pairs.tcl on
               its 4_cts.odb), as a kit_zl_lockup spec the generator applies at GEN (plan clock.zl_lockup).
               Margin (KV arithmetic): T/2 = 416.5 ps against tap-to-tap skew + library hold: windows up to ~290 ps.

Emits rows for the die owners' plan events; it never edits a plan of record and is never a gate.

    station_rule.py rows PLAN --out ROWS.json [--types RE] [--reach-um 300]
          ft-slot rows: stations have / need (+cycles), stage-0 seat, per-bit sites, cross-tap hops (latch list)
    station_rule.py derive ZL_PAIRS.tsv RTL_DIR --type T --out SPEC.json [--min-pairs 1]
          kit_zl_lockup spec (instances + flattened registers) for every capture class with a cross-tap pair
    station_rule.py apply PLAN ROWS.json OUT_PLAN RECEIPT [--specs T=SPEC.json ...] [--sites]
          plan copy: clock.ft_hop_lockup types / hops from the rows, clock.zl_lockup from the specs, and (--sites) the
          stage-0 seat + per-bit sites of every slot whose station count is unchanged; every other key byte-identical.
"""
import argparse
import collections
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cbc_rules as RULES  # noqa: E402

CELL = (1.404, .27)
FACE_AXIS = {"S": ("y", 0), "N": ("y", 1), "W": ("x", 0), "E": ("x", 1)}
# capture module -> its data input ports (the latch goes on these; epoch / enable bits ride with the data)
DATA_PORTS = {"ot_dp_st": ["d", "ea"], "ot_dp_ste": ["d", "ea"], "ot_dp_dly": ["d"], "ot_dp_dly_keep": ["d"],
              "ot_dp_rrelay": ["d"]}


def _sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


# ------------------------------------------------------------------------------------------- 1 COUNT
def stations_needed(length_um, reach_um=None):
    """registers on a lane of pin-to-pin length L, the first rank at the pin included: every hop <= reach."""
    r = float(reach_um or RULES.REACH_UM_PER_HOP)
    return max(1, int(math.ceil(float(length_um) / r - 1e-9)))


# ------------------------------------------------------------------------------------------- 2 SITE / 3 FIRST
def route_point(a, b, f, axis="x"):
    """point at fraction f of the Manhattan route a -> b that runs along `axis` first (L-route), so every bit of a bus
    keeps its own line and the stage-j points of the bus form a line across it."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    L = abs(dx) + abs(dy)
    if L <= 0:
        return (ax, ay)
    s = f * L
    first, second = (abs(dx), abs(dy)) if axis == "x" else (abs(dy), abs(dx))
    if axis == "x":
        if s <= first:
            return (ax + math.copysign(s, dx), ay)
        return (bx, ay + math.copysign(s - first, dy))
    if s <= first:
        return (ax, ay + math.copysign(s, dy))
    return (ax + math.copysign(s - first, dx), by)


def lane_sites(a, b, n, in_face="W"):
    """[[(x, y) per bit] per stage j = 1 .. n - 1] for bits with in pins a[i] and out pins b[i] (stage 0 = the in pin).
    The route leaves the in face along its normal (W/E faces: x first; N/S faces: y first)."""
    axis = "x" if in_face in ("W", "E") else "y"
    m = max(len(a), len(b))
    return [[route_point(a[min(i, len(a) - 1)], b[min(i, len(b) - 1)], j / n, axis) for i in range(m)]
            for j in range(1, n)]


def hop_lengths(a, sites, b):
    """max over bits of every hop pin -> s1 -> .. -> pin."""
    chain = [a] + list(sites) + [b]
    out = []
    for p, q in zip(chain, chain[1:]):
        m = max(len(p), len(q))
        out.append(max(abs(p[min(i, len(p) - 1)][0] - q[min(i, len(q) - 1)][0]) +
                       abs(p[min(i, len(p) - 1)][1] - q[min(i, len(q) - 1)][1]) for i in range(m)))
    return out


def _centre(win, face, outline):
    w, h = outline
    lo, hi = float(win[0]), float(win[1])
    c = (lo + hi) / 2
    return {"W": (0.0, c), "E": (w, c), "S": (c, 0.0), "N": (c, h)}[face]


def _window_pins(s, outline, nb):
    """bit pins spread evenly over the in / out windows (the plan form when no pin table is given)."""
    def spread(win, face):
        w, h = outline
        lo, hi = (float(win[0]), float(win[1])) if win else ((0.0, h) if face in "WE" else (0.0, w))
        pts = []
        for i in range(nb):
            c = lo + (hi - lo) * (i + .5) / nb
            pts.append({"W": (0.0, c), "E": (w, c), "S": (c, 0.0), "N": (c, h)}[face])
        return pts
    return spread(s.get("in_window_um"), s.get("in_face", "W")), spread(s.get("out_window_um"), s.get("out_face", "E"))


def _plan_pins(P, tn, s):
    try:
        import gen_phys
        import gen_rtl
        pins = gen_phys.type_pins(P, tn)
    except Exception:
        return None, None
    ii, oo = gen_rtl.sv_id(s["name"] + "_i"), gen_rtl.sv_id(s["name"] + "_o")
    a = {int(b): (float(x), float(y)) for bn, b, _l, x, y, _f in pins if gen_rtl.sv_id(bn) == ii}
    o = {int(b): (float(x), float(y)) for bn, b, _l, x, y, _f in pins if gen_rtl.sv_id(bn) == oo}
    if not a or not o:
        return None, None
    return [a[k] for k in sorted(a)], [o[k] for k in sorted(o)]


def _snap(sites, t, alloc_cache):
    """legal row sites for ideal points (ft_spread allocator); None when the allocator is unavailable."""
    try:
        import numpy as np
        import ft_spread as FS
        from ft_corridor import project
    except Exception:
        return None
    if "alloc" not in alloc_cache:
        try:
            alloc_cache["alloc"] = FS._allocator(t)
        except Exception:
            alloc_cache["alloc"] = None
    if alloc_cache["alloc"] is None:
        return None
    alloc, boxes, bounds = alloc_cache["alloc"]
    out = []
    for st in sites:
        q, dist = project(np.asarray(st, float), boxes, bounds)
        row = []
        for p in q:
            try:
                got, _ = alloc.allocate(p, 1, max_radius_um=FS.MAX_PROJ_UM * 6)
                row.append((float(got[0][0]), float(got[0][1])))
            except ValueError:
                return None
        out.append(row)
    return out


# ------------------------------------------------------------------------------------------- 4 LOCKUP (ft slots)
def nearest_tap(taps, x, y):
    best, bd = None, None
    for name, tx, ty in taps:
        d = abs(x - tx) + abs(y - ty)
        if bd is None or d < bd:
            best, bd = name, d
    return best


def cross_tap_hops(stages, taps):
    """[k] of hops k -> k+1 whose bits do not all share one nearest tap (a stage with no sites = cross, safe side)."""
    if len(taps) < 2:
        return []
    out = []
    for k in range(len(stages) - 1):
        a, b = stages[k], stages[k + 1]
        if not a or not b:
            out.append(k)
            continue
        m = max(len(a), len(b))
        if any(nearest_tap(taps, *a[min(i, len(a) - 1)]) != nearest_tap(taps, *b[min(i, len(b) - 1)]) for i in range(m)):
            out.append(k)
    return out


def slot_row(tn, t, s, pins=None, taps=(), reach_um=None, snap=None):
    """the rule applied to one ft slot -> row dict (see module doc)."""
    outline = tuple(map(float, t["outline_um"]))
    nb = int(s.get("width", 1)) + 1                      # data + epoch
    a, b = pins if pins and pins[0] else _window_pins(s, outline, nb)
    L = max(abs(a[min(i, len(a) - 1)][0] - b[min(i, len(b) - 1)][0]) + abs(a[min(i, len(a) - 1)][1] - b[min(i, len(b) - 1)][1])
            for i in range(max(len(a), len(b))))
    have = int(s.get("stations", 1))
    need = stations_needed(L, reach_um)
    n = max(have, need)
    ideal = lane_sites(a, b, n, s.get("in_face", "W"))
    sites = (snap(ideal) if snap else None) or ideal
    hops = hop_lengths(a, sites, b)
    stages = [list(a)] + [list(x) for x in sites]
    xt = cross_tap_hops(stages, list(taps))
    in_c = (sum(p[0] for p in a) / len(a), sum(p[1] for p in a) / len(a))
    regs = [[round(in_c[0], 4), round(in_c[1], 4)]] + [
        [round(sum(p[0] for p in st) / len(st), 4), round(sum(p[1] for p in st) / len(st), 4)] for st in sites]
    lim = float(reach_um or RULES.REACH_UM_PER_HOP) + RULES.SITE_MARGIN_UM
    # a straight per-bit line that crosses a hard core snaps far off its line: those slots need the macro-aware route
    # (ft_channel_route.py / ft_spread) before sites are written; count, first rank and lockup rows stay valid
    form = "line" if not hops or max(hops) <= lim else "needs_route"
    return dict(type=tn, slot=s["name"], width=int(s.get("width", 1)), pin_to_pin_um=round(L, 1), site_form=form,
                stations_have=have, stations_need=need, delta_cycles=max(0, need - have),
                first_rank="pin", worst_hop_um=round(max(hops), 1) if hops else 0.0,
                hops_um=[round(h, 1) for h in hops], snapped=bool(snap and sites is not ideal),
                regs_um=regs, bit_sites_um=[[[round(x - CELL[0] / 2, 4), round(y - CELL[1] / 2, 4)] for x, y in st]
                                            for st in sites],
                lockup_hops=xt)


def plan_rows(P, types_re=None, reach_um=None, snap=True):
    """rows for every ft slot (>= 1 station) of the matching types of a schema.Plan."""
    import schema as S
    rx = re.compile(types_re) if types_re else None
    rows = []
    for tn in sorted(P.types):
        if rx and not rx.search(tn):
            continue
        t = P.types[tn]
        slots = [s for s in t.get("ft_slots", []) or [] if s.get("in_face") != s.get("out_face") or s.get("turnaround")]
        if not slots:
            continue
        try:
            taps = S.tap_grid(P, tn)
        except Exception:
            taps = []
        cache = {}
        for s in slots:
            pins = _plan_pins(P, tn, s)
            sn = (lambda ideal, _t=t, _c=cache: _snap(ideal, _t, _c)) if snap else None
            rows.append(slot_row(tn, t, s, pins=pins if pins[0] else None, taps=taps, reach_um=reach_um, snap=sn))
    return rows


# ------------------------------------------------------------------------------------------- 4 LOCKUP (measured)
def read_pairs(path):
    """zl_pairs.tcl TSV -> [(launch, capture, launch_tap, capture_tap, dist_um, launch_master, capture_master)]"""
    out = []
    for ln in Path(path).read_text().splitlines():
        f = ln.split("\t")
        if len(f) >= 5:
            out.append((f[0], f[1], f[2], f[3], float(f[4]), *(f[5:7] + ["", ""])[:2]))
    return out


def _cell_obj(name):
    """netlist register name -> (instance or None, register base) in the bound module's frame.
    'u_bound.u_ft_ft1_o_2/q[5]$_DFF_P_' -> ('u_ft_ft1_o_2', 'q'); 'u_bound.g_x_q[3]$_DFF_P_' -> (None, 'g_x_q')"""
    n = name.replace("\\", "")
    n = re.sub(r"\$_.*$", "", n)
    n = re.sub(r"(\[\d+\])+$", "", n)
    if "/" in n:
        head, reg = n.rsplit("/", 1)
        inst = re.split(r"[./]", head)[-1]
        return inst, reg
    parts = n.split(".")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return None, parts[-1]


def generalize(name):
    """class regex of an instance / register name: index runs -> \\d+, long hex hashes -> [0-9a-f]+."""
    out, i = [], 0
    for m in re.finditer(r"[0-9a-f]{16,}|\d+", name):
        out.append(re.escape(name[i:m.start()]))
        out.append(r"[0-9a-f]+" if len(m.group()) >= 16 and re.search(r"[a-f]", m.group()) else r"\d+")
        i = m.end()
    out.append(re.escape(name[i:]))
    return "".join(out)


def _rtl_objects(rtl_dir):
    """{instance name: module type} and {register name} over the kit RTL (instances via kit_zl_lockup.instances)."""
    import kit_zl_lockup as ZL
    insts, regs, modregs = {}, set(), collections.defaultdict(set)
    for f in sorted(Path(rtl_dir).glob("*.sv")) + sorted(Path(rtl_dir).glob("*.v")):
        txt = f.read_text(errors="replace")
        try:
            for mt, _p, name, *_r in ZL.instances(txt):
                insts.setdefault(name, mt)
        except ZL.LkError:
            pass                                  # a file the instance parser cannot read: its registers still count
        regs.update(re.findall(r"\breg\b\s*(?:\[[^\]]*\])?\s*([A-Za-z_]\w*)\s*;", txt))
        for m in re.finditer(r"(?s)\bmodule\s+([A-Za-z_]\w*).*?\bendmodule\b", txt):
            modregs[m.group(1)].update(re.findall(r"\breg\b\s*(?:\[[^\]]*\])?\s*([A-Za-z_]\w*)\s*[,;)]", m.group(0)))
    return insts, regs, modregs


RESET_RE = re.compile(r"(rrelay|rst|reset|u_[rs]rl_\d)")
SRAM_RE = re.compile(r"sram")


def _clean_cell(name):
    return name.replace("\\", "")


def classify(cap, insts, modregs):
    """capture register (flat netlist name) -> (form, class regex, module, wrapper prefix)
       form: "inst" (RTL instance data ports, kit_zl_lockup hops), "netlist" (post-synth DLL latch on the flat register,
       FABLE-CLOSURE-1315 (2): generate-block / nested registers need no RTL parser), "tap_group" (inside an SRAM wrapper:
       the wrapper goes on one tap instead, (3)), "reset" (reset relay cells: reset.relay_lockup owns them)."""
    inst, reg = _cell_obj(cap)
    mt = insts.get(inst)
    flat = _clean_cell(cap)
    if mt in DATA_PORTS and mt != "ot_dp_rrelay":
        return "inst", generalize(inst), mt, None
    if RESET_RE.search(mt or "") or RESET_RE.search(inst or "") or mt == "ot_dp_rrelay":
        return "reset", generalize(inst or reg), mt, None
    if SRAM_RE.search(mt or "") or re.search(r"(^|[./])u_[^./]*sram[^./]*/", flat):
        head = re.split(r"[/]", flat)[0] if "/" in flat else flat.rsplit(".", 1)[0]
        return "tap_group", generalize(head), mt, head
    return "netlist", generalize(flat), mt, None


def read_hold_ends(path):
    """pregrt_ff_hold_open(_before).tsv -> [(slack, class, start, end)] (end = register pin, '/D' dropped)"""
    out = []
    for ln in Path(path).read_text().splitlines()[1:]:
        f = ln.split("\t")
        if len(f) >= 4:
            out.append((float(f[0]), f[1], f[2], re.sub(r"/[A-Za-z0-9_]+$", "", f[3].replace("\\", ""))))
    return out


def derive_spec(pairs, rtl_dir, type_name, min_pairs=1, guard=None, hold_ends=None, exclude=None, ends_only=False):
    """zl_lockup spec for every capture class with >= min_pairs cross-tap zero-logic pairs, + the census.
    Forms: RTL instances (hops), flat netlist registers (netlist), SRAM wrappers -> tap_group rows (never latched)."""
    insts, _regs, modregs = _rtl_objects(rtl_dir)
    cls, same = collections.Counter(), collections.Counter()
    heads = collections.defaultdict(set)
    ex = re.compile(exclude) if exclude else None
    ends = collections.defaultdict(set)                     # class -> capture ENDS (one per register bit), not pairs
    for _a, cap, lt, ct, _d, *_m in pairs:
        form, rx, mt, head = classify(cap, insts, modregs)
        if ex and ex.search(_clean_cell(cap)):
            form = "excluded"
        if lt != ct:
            ends[(form, rx, mt)].add(_clean_cell(cap))
        key = (form, rx, mt)
        (cls if lt != ct else same)[key] += 1
        if head:
            heads[key].add(head)
    hops, netlist, groups, census = [], [], set(), []
    for key, n in sorted(cls.items(), key=lambda kv: -kv[1]):
        form, rx, mt = key
        emit = n >= min_pairs and form in ("inst", "netlist", "tap_group")
        census.append(dict(form=form, match=rx, module=mt, cross_tap=n, cross_tap_ends=len(ends[key]),
                           same_tap=same.get(key, 0), emitted=emit))
        if not emit:
            continue
        if form == "inst":
            hops.append({"inst": rx, "types": [mt], "ports": DATA_PORTS[mt], "allow_missing": True})
        elif form == "netlist":
            netlist.append(rx)
        else:
            groups.add(rx)
    spec = {"guard": guard, "note": f"LOCKUP-STATION-1130 station_rule.derive {type_name}: launch-side lockup on every "
                                   f"capture class with >= {min_pairs} cross-tap zero-logic pair(s) (measured); RTL "
                                   f"instances via hops, flat registers via netlist (post-synth)", "hops": hops,
            "netlist": netlist}
    tap_group = {"re": "^(" + "|".join(sorted(groups)) + ")[./]", "note": "LOCKUP-STATION-1130: one tap per SRAM wrapper "
                 "(FABLE-CLOSURE-1315 (3)); fold into partition_types.<T>.clock.tap_group"} if groups else None
    rec = dict(type=type_name, pairs=len(pairs), cross_tap=sum(1 for _a, _c, lt, ct, *_r in pairs if lt != ct),
               classes=census, tap_group=tap_group)
    rec["cross_tap_covered"] = sum(c["cross_tap"] for c in census if c["emitted"] and c["form"] != "tap_group")
    rec["cross_tap_tap_group"] = sum(c["cross_tap"] for c in census if c["emitted"] and c["form"] == "tap_group")
    rec["cross_tap_ends"] = sum(c["cross_tap_ends"] for c in census)
    rec["cross_tap_ends_covered"] = sum(c["cross_tap_ends"] for c in census if c["emitted"] and c["form"] != "tap_group")
    rec["cross_tap_ends_tap_group"] = sum(c["cross_tap_ends"] for c in census if c["emitted"] and c["form"] == "tap_group")
    if hold_ends is not None:
        inst_res = [re.compile(h["inst"]) for h in hops]
        net_res = [re.compile(r) for r in netlist]
        grp_re = re.compile(tap_group["re"]) if tap_group else None
        by = collections.Counter()
        for _s, hc, _st, end in hold_ends:
            if hc in ("port_in", "port_out"):
                by[hc] += 1
                continue
            ei = _cell_obj(end)[0] or ""
            if any(r.fullmatch(ei) for r in inst_res):
                by["inst"] += 1
            elif any(r.fullmatch(end) for r in net_res):
                by["netlist"] += 1
            elif grp_re and grp_re.match(end):
                by["tap_group"] += 1
            else:
                by["uncovered"] += 1
        rec["hold_ends"] = dict(total=len(hold_ends), by=dict(by),
                                covered=by.get("inst", 0) + by.get("netlist", 0), tap_group=by.get("tap_group", 0))
    if ends_only:
        if hold_ends is None:
            raise ValueError("--ends-only needs --hold-ends (pregrt_ff_hold_open_before.tsv)")
        # FABLE-CLOSURE-1515 (3): latch ONLY the captures that violate hold before repair, on a cross-tap zero-logic pair
        # of an emitted (non tap_group) class: one exact netlist name each, no RTL hop classes
        xt = {_clean_cell(c) for _a, c, lt, ct, *_r in pairs if lt != ct}
        live = {(c["form"], c["match"]) for c in census if c["emitted"] and c["form"] in ("inst", "netlist")}
        keep = sorted({end for sl, hc, _st, end in hold_ends if sl < 0 and hc == "cross_tap" and end in xt
                       and classify(end, insts, modregs)[:2] in live})
        spec = dict(spec, hops=[], netlist=["=" + e for e in keep],
                    note=spec["note"] + "; ends-only: the cross-tap ends that violate hold before repair")
        rec["ends_only"] = dict(violating_cross_tap=sum(1 for sl, hc, *_r in hold_ends if sl < 0 and hc == "cross_tap"),
                                latched=len(keep))
    return spec, rec


# ------------------------------------------------------------------------------------------- apply (plan copy)
def apply_rows(raw, rows, specs=None, sites=False, note=None, seams=None):
    """plan copy with the rule's rows; asserts every other key byte-identical.  Station-count deltas are reported,
    never applied here (they change lane latency: the die owner's event prices them)."""
    new = copy.deepcopy(raw)
    clk = new.setdefault("clock", {})
    by_type = collections.defaultdict(dict)
    for r in rows:
        if r.get("lockup_hops"):
            by_type[r["type"]][r["slot"]] = sorted(set(int(k) for k in r["lockup_hops"]))
    if by_type:
        lk = dict(clk.get("ft_hop_lockup") or {})
        if lk.get("all") or lk.get("except"):
            raise ValueError("plan uses ft_hop_lockup all/except; edit it explicitly")
        old_types = set(lk.get("types", []))
        hops = {k: dict(v) for k, v in (lk.get("hops") or {}).items()}
        for tn, d in by_type.items():
            if tn in old_types and tn not in hops:
                continue                                   # already latched on every hop
            cur = hops.setdefault(tn, {})
            for sl, ks in d.items():
                cur[sl] = sorted(set(cur.get(sl, [])) | set(ks))
        lk["types"] = sorted(old_types | set(by_type))
        lk["hops"] = hops
        if note:
            lk["note"] = note
        clk["ft_hop_lockup"] = lk
    if specs:
        zl = dict(clk.get("zl_lockup") or {})
        for tn, sp in specs.items():
            zl[tn] = sp
        clk["zl_lockup"] = zl
    # FABLE-CLOSURE-1930 lever 2: sender-side seam latch on every output bus abutted on all instances (seam_rows)
    seam_types = []
    for tn, r in sorted((seams or {}).items()):
        if not r.get("ports") or tn not in new.get("partition_types", {}):
            continue
        zl = dict(clk.get("zl_lockup") or {})
        sp = dict(zl.get(tn) or {"guard": None, "note": "LOCKUP-STATION-1130 station_rule.apply --seams"})
        sp["ports"] = sorted(set(sp.get("ports", [])) | set(r["ports"]))
        zl[tn] = sp
        clk["zl_lockup"] = zl
        seam_types.append(tn)
    moved = []
    if sites:
        for r in rows:
            if r["stations_need"] > r["stations_have"] or r.get("site_form", "line") != "line":
                continue
            t = new["partition_types"][r["type"]]
            s = next(x for x in t.get("ft_slots", []) if x["name"] == r["slot"])
            if s.get("stations", 1) != len(r["regs_um"]):
                continue
            s["regs_um"] = r["regs_um"]
            s["bit_sites_um"] = r["bit_sites_um"]
            s["bit_site_cell_um"] = list(CELL)
            s["explicit_stage0"] = True
            s["keep_firm"] = True
            moved.append((r["type"], r["slot"]))
    for k in raw:
        if k not in ("clock", "partition_types"):
            assert _sha(raw[k]) == _sha(new[k]), k
    for k in raw.get("clock", {}):
        if k not in ("ft_hop_lockup", "zl_lockup"):
            assert _sha(raw["clock"][k]) == _sha(new["clock"][k]), k
    if not sites:
        assert _sha(raw.get("partition_types")) == _sha(new.get("partition_types"))
    rec = dict(tool="tools/die_plan/station_rule.py", lane="LOCKUP-STATION-1130", plan_in_sha256=_sha(raw),
               plan_out_sha256=_sha(new), latch_types=sorted(by_type),
               latch_hops=sum(len(v) for d in by_type.values() for v in d.values()),
               zl_lockup_types=sorted(set(specs or {}) | set(seam_types)), seam_types=len(seam_types),
               seam_ports=sum(len((seams or {})[t]["ports"]) for t in seam_types), sited_slots=len(moved),
               cycles_needed=[dict(type=r["type"], slot=r["slot"], have=r["stations_have"], need=r["stations_need"])
                              for r in rows if r["delta_cycles"]])
    return new, rec


def summary(rows):
    return dict(slots=len(rows), types=len({r["type"] for r in rows}),
                over_reach=sum(1 for r in rows if r["delta_cycles"]),
                added_stations=sum(r["delta_cycles"] for r in rows),
                latch_hops=sum(len(r["lockup_hops"]) for r in rows),
                latch_bits=sum(len(r["lockup_hops"]) * (r["width"] + 1) for r in rows),
                needs_route=sum(1 for r in rows if r.get("site_form") == "needs_route"),
                worst_line_hop_um=max((r["worst_hop_um"] for r in rows if r.get("site_form") != "needs_route"), default=0.0))


def seam_rows(P, types_re=None):
    """FABLE-CLOSURE-1515 (4): per type, the OUTPUT buses that are abutted (no die.channels entry, partner is a partition,
    not the die edge) on EVERY instance of the type: the sender-side seam lockup latch (kit_zl_lockup.apply_ports,
    plan clock.zl_lockup.<T>.ports) goes only there.  -> {type: {"ports": [...], "abutted": n, "channel_or_edge": m}}"""
    import gen_phys as G
    rx = re.compile(types_re) if types_re else None
    by = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for pid, pr in P.ports.items():
        src, dst = pr["src"]["part"], pr["dst"]["part"]
        if src == G.DIE_PART or src not in P.parts:
            continue
        tn = P.parts[src]["type"]
        if rx and not rx.search(tn):
            continue
        ok = dst != G.DIE_PART and dst in P.parts and P.channel_of(pid) is None
        by[tn][pr["src"]["bus"]][0 if ok else 1] += 1
    out = {}
    for tn, buses in sorted(by.items()):
        ports = sorted(b for b, (a, c) in buses.items() if a and not c)
        out[tn] = dict(ports=ports, abutted=len(ports), channel_or_edge=sum(1 for a, c in buses.values() if c))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("rows")
    a.add_argument("plan")
    a.add_argument("--out", required=True)
    a.add_argument("--types")
    a.add_argument("--reach-um", type=float)
    a.add_argument("--no-snap", action="store_true")
    d = sub.add_parser("derive")
    d.add_argument("pairs")
    d.add_argument("rtl_dir")
    d.add_argument("--type", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--min-pairs", type=int, default=1)
    d.add_argument("--guard")
    d.add_argument("--ends-only", action="store_true", help="exact netlist names of the violating cross-tap ends only")
    d.add_argument("--exclude", help="regex on capture names left out (e.g. a later plan row rewrites them)")
    d.add_argument("--hold-ends", help="pregrt_ff_hold_open_before.tsv (OT_PREGRT_OPEN_BEFORE=1): coverage on hold ends")
    e = sub.add_parser("seams")
    e.add_argument("plan")
    e.add_argument("--out", required=True)
    e.add_argument("--types")
    p = sub.add_parser("apply")
    p.add_argument("plan")
    p.add_argument("rows")
    p.add_argument("out")
    p.add_argument("receipt")
    p.add_argument("--specs", nargs="*", default=[])
    p.add_argument("--sites", action="store_true")
    p.add_argument("--note")
    p.add_argument("--seams", help="station_rule seams output: seam latch rows (clock.zl_lockup.<T>.ports)")
    x = ap.parse_args(argv)
    if x.cmd == "rows":
        import schema as S
        rows = plan_rows(S.Plan(json.loads(Path(x.plan).read_text())), x.types, x.reach_um, snap=not x.no_snap)
        Path(x.out).write_text(json.dumps(dict(summary=summary(rows), rows=rows), indent=1) + "\n")
        print(json.dumps(summary(rows)))
        return 0
    if x.cmd == "seams":
        import schema as S
        rows = seam_rows(S.Plan(json.loads(Path(x.plan).read_text())), x.types)
        Path(x.out).write_text(json.dumps(rows, indent=1) + "\n")
        print(json.dumps({"types": len(rows), "abutted_ports": sum(r["abutted"] for r in rows.values())}))
        return 0
    if x.cmd == "derive":
        spec, rec = derive_spec(read_pairs(x.pairs), x.rtl_dir, x.type, x.min_pairs, x.guard,
                                read_hold_ends(x.hold_ends) if x.hold_ends else None, x.exclude,
                                x.ends_only)
        Path(x.out).write_text(json.dumps(dict(spec=spec, census=rec), indent=1) + "\n")
        print(json.dumps({k: rec[k] for k in ("pairs", "cross_tap", "cross_tap_covered", "cross_tap_tap_group", "cross_tap_ends",
                                                   "cross_tap_ends_covered", "cross_tap_ends_tap_group", "hold_ends", "ends_only")
                          if k in rec}))
        return 0
    raw = json.loads(Path(x.plan).read_text())
    rows = json.loads(Path(x.rows).read_text())["rows"]
    specs = {}
    for kv in x.specs:
        tn, f = kv.split("=", 1)
        sp = json.loads(Path(f).read_text())
        specs[tn] = sp.get("spec", sp)
    new, rec = apply_rows(raw, rows, specs, x.sites, x.note,
                          json.loads(Path(x.seams).read_text()) if x.seams else None)
    Path(x.out).write_text(json.dumps(new, indent=1) + "\n")
    Path(x.receipt).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rec[k] for k in ("latch_hops", "sited_slots", "zl_lockup_types")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
