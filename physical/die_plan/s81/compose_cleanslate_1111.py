#!/usr/bin/env python3
"""DIE-S81-85 DS85-COMPOSE-1111: the ONE combined S81 clean-slate placement plan event (COORD 11-11 02:0x, cut 12:00 PST).
DO_NOT_COUNT.

Applies to BASE_1200 (64eb2c89 SVCPROV-PHYSINST -> FEED-BAL-2 -> DS85-VIEWS), in this order:
  (a) positions/orients deltas  {type: {inst: [x, y, orient]}}  (one JSON per clean-slate family, N files)
        - every type exists, every inst is a hard_cores[] (or placed contents[]) entry of that type;
        - no two files touch the same type (no overlapping deltas);
        - orient in R0/MX/MY/R180 only (a hard core is never re-pinned or rotated: its LEF / pins / lib are untouched);
        - x, y on the plan lattice die.grid_um ... checked by G0 (hard_cores origin rule), not re-implemented;
        - only origin_um / orient of the named entries move.  DERIVED by construction (reported, not an input): the
          early core clock taps (clock.taps[] kind 'core', named <inst> or <inst>.<pin>) of a moved core keep their
          core-frame point (rigid transform with the core), because schema.core_taps reads tap xy as the die clock
          early-tap site;  a stale tap would make the die clock tool route to the old core position (DIE-S81-85 ruling
          11-11: approved as a derived key, reported per type: count + max displacement; the moved tap must be inside
          the outline and pass the kit snap gen_phys.core_tap_pins under --phys; a tap shared by two cores, a
          core_group tap, or a plain (non-core) tap on a moved core's old box FAILS: the die owner's call).
  (b) optional face-window delta  {type: {bus: {window_um: [lo, hi], layers: [..]}}}  (OFF unless --face; e.g. the
      SLICE-LP-W candidate delta_lepw_eface_1111.json with --face-script delta_lepw_eface_1111.py as a cross-check,
      and --keep-clear for its keep-clear rules on any positions delta of the same types)
        - matched neighbour: for every ports[] row touching a changed (type, bus) on any partition of the type, the
          die-frame windows of both ends coincide after the delta (both ends must be changed together); a port's own
          window_um that equalled the old die-frame window follows the new one (derived, reported).
  (d) optional signed box heights (--resize spec; applied after (b), before (c)): svc provider rows take the signed
      SIZE + signed view, origin kept; view/pins sha, pins inside, taps/regs inside, top-edge abutment checked.
  (c) optional late-tap pad delta (DS85-LATETAP-1111 pads_delta.json), applied by
        delta_latetap_pad_1111.py apply-delta PLAN_IN PLAN_OUT PADS_DELTA [REPORT]  (adds clock.cohort.tap_pad only).
        OFF unless --pad is given.

Every stage records its input and output plan sha256.  The output keeps the base's json.dumps form.

Gates on the composed plan (and per stage where cheap):
  EQ by construction   only the keys above move (asserted by restore-and-compare against BASE);
  legality (per changed type, NEW findings vs BASE only; inherited ones listed):
      in_outline   every placed core box (origin + track_offset, outline) inside the type outline, >= --edge from it;
      overlap      no two core boxes of the type overlap;
      street       every pair of distinct cores is abutted (gap 0) or >= --gap apart (B34 street, default 34.56);
      sites        no clock tap (type clock.tap_um, core taps), ft_slots regs_um, internal_stations regs_um under a core;
  G0                   tools/die_plan/check.py on BASE and on the output: 0 NEW errors (findings compared
                       by (check, msg)); --no-g0 skips it (dry runs);
  phys                 gen_phys content_physical_identity / window_port_names / type_macros on every changed type and
                       die_trial.clock_taps on the plan (the SVCPROV-PHYSINST check form), --phys.

usage:
  compose_cleanslate_1111.py compose BASE.json OUT_DIR [--pos D.json ...] [--face F.json] [--pad PADS_DELTA.json
          --pad-script delta_latetap_pad_1111.py] [--base-sha SHA] [--no-g0] [--phys] [--dry-run] [--gap 34.56] [--edge 0]
  compose_cleanslate_1111.py --check OUT_DIR      re-derive OUT_DIR/plan.json from OUT_DIR/record.json, assert equal
"""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(HERE), str(REPO / "tools" / "die_plan")]

TAG = "DS85-COMPOSE-1111"
ORIENTS = ("R0", "MX", "MY", "R180")
BASES = {}                      # BASE_1200 sha256 -> label; filled in when BASE_1200 is published
EPS = 1e-6


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fsha(p):
    return sha(Path(p).read_bytes())


def dump_form(plan, raw):
    for name, f in (("compact_nl", lambda d: json.dumps(d) + "\n"), ("indent1_nl", lambda d: json.dumps(d, indent=1) + "\n")):
        if f(plan).encode() == raw:
            return name, f
    raise SystemExit("plan is not in a json.dumps form (compact / indent=1, + newline): refuse to restyle")


def opt(o, w, h, x, y):
    """core-frame point -> placed offset (check._orient_pt; the four orients are involutions)."""
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


def box(hc):
    (x, y), (dx, dy), (w, h) = hc["origin_um"], hc.get("track_offset_um", [0.0, 0.0]), hc["outline_um"]
    return (x + dx, y + dy, x + dx + w, y + dy + h)


def core_tap_inst(name, insts):
    for i in sorted(insts, key=len, reverse=True):
        if name == i or name.startswith(i + "."):
            return i
    return None


def core_tap_matches(name, insts):
    """every inst a core tap name can denote (<inst> or <inst>.<pin>); > 1 = a tap shared by two cores."""
    return [i for i in insts if name == i or name.startswith(i + ".")]


# ------------------------------------------------------------------------------------------- (a) positions / orients
def split_sheet(arg):
    """--pos DELTA.json[::INTENT_SHEET] (COORD 02:1x adoption gate: the family's intent sheet is recorded per delta)."""
    p, _, sh = arg.partition("::")
    return p, (sh or None)


def load_pos(paths):
    out, owner = [], {}
    for p in paths:
        p, _ = split_sheet(p)
        d = json.loads(Path(p).read_text())
        assert isinstance(d, dict) and d, f"{p}: not a non-empty {{type: {{inst: [x, y, orient]}}}}"
        for tn, m in d.items():
            assert isinstance(m, dict), f"{p}: {tn}: not an {{inst: [x, y, orient]}} map"
            if tn in owner:
                raise SystemExit(f"OVERLAPPING DELTAS: type {tn} is in {owner[tn]} and {p}")
            owner[tn] = str(p)
            for inst, v in m.items():
                assert (isinstance(v, list) and len(v) == 3 and all(isinstance(a, (int, float)) for a in v[:2])
                        and isinstance(v[2], str)), f"{p}: {tn} {inst}: value {v!r} is not [x, y, orient]"
        out.append((str(p), fsha(p), d))
    return out


def apply_pos(plan, deltas):
    """moves origin_um / orient; returns the per-type record and the derived core-tap moves."""
    T = plan["partition_types"]
    rec, problems = {}, []
    for path, dsha, d in deltas:
        for tn, m in sorted(d.items()):
            if tn not in T:
                problems.append(f"{path}: type {tn} not in the plan")
                continue
            t = T[tn]
            idx = {}
            for k in ("hard_cores", "contents"):
                for e in t.get(k) or []:
                    if "origin_um" in e and "outline_um" in e:
                        idx.setdefault(e["inst"], (k, e))
            moved, unchanged = [], 0
            old = {}
            for inst, (x, y, o) in sorted(m.items()):
                if inst not in idx:
                    problems.append(f"{path}: {tn}: inst {inst} is not a placed hard_cores/contents entry")
                    continue
                if o not in ORIENTS:
                    problems.append(f"{path}: {tn} {inst}: orient {o} not in {ORIENTS} (no rotation / re-pin)")
                    continue
                k, e = idx[inst]
                o0 = e.get("orient", "R0")
                if [float(x), float(y)] == [float(v) for v in e["origin_um"]] and o == o0:
                    unchanged += 1
                    continue
                old[inst] = (copy.deepcopy(e["origin_um"]), o0, box(e))
                e["origin_um"] = [x, y]
                if "orient" in e or o != "R0":
                    e["orient"] = o
                moved.append(dict(inst=inst, list=k, module=e.get("module"), lef=e.get("lef"),
                                  from_=[*old[inst][0], o0], to=[x, y, o]))
            # derived: early core taps of moved cores follow their core (rigid, core frame kept)
            taps = []
            hc = {e["inst"]: e for e in t.get("hard_cores") or []}
            for tp in (t.get("clock") or {}).get("taps", []) or []:
                if tp.get("kind") != "core":
                    continue
                i = core_tap_inst(tp["name"], hc)
                if i is None or i not in old:
                    continue
                if "core_group" in tp:
                    problems.append(f"{tn}: core tap {tp['name']} is a core_group tap of moved core {i}: not derivable "
                                    "(needs the die owner's call)")
                    continue
                mm = core_tap_matches(tp["name"], hc)
                if len(mm) > 1 and any(m in old for m in mm):
                    problems.append(f"{tn}: core tap {tp['name']} is shared by cores {mm}: not derivable "
                                    "(needs the die owner's call)")
                    continue
                (ox, oy), o0, b0 = old[i]
                w, h = hc[i]["outline_um"]
                u, v = opt(o0, w, h, tp["xy"][0] - b0[0], tp["xy"][1] - b0[1])
                b1 = box(hc[i])
                px, py = opt(hc[i].get("orient", "R0"), w, h, u, v)
                new = [round(b1[0] + px, 4), round(b1[1] + py, 4)]
                dist = max(b0[0] - tp["xy"][0], 0, tp["xy"][0] - b0[2], b0[1] - tp["xy"][1], 0, tp["xy"][1] - b0[3])
                taps.append(dict(tap=tp["name"], core=i, from_=list(tp["xy"]), to=new, off_core_um=round(dist, 3)))
                tp["xy"] = new
            # a plain (non-core) tap on / under a moved core's old box: not derivable, the die owner decides
            for tp in (t.get("clock") or {}).get("taps", []) or []:
                if tp.get("kind") == "core":
                    continue
                for i, (_, _, b0) in old.items():
                    if b0[0] - EPS <= tp["xy"][0] <= b0[2] + EPS and b0[1] - EPS <= tp["xy"][1] <= b0[3] + EPS:
                        problems.append(f"{tn}: plain clock tap {tp['name']} at {tp['xy']} sits on moved core {i}'s "
                                        "old box: not derivable (needs the die owner's call)")
            W, H = t["outline_um"]
            for r in taps:
                if not (-EPS <= r["to"][0] <= W + EPS and -EPS <= r["to"][1] <= H + EPS):
                    problems.append(f"{tn}: moved core tap {r['tap']} -> {r['to']} outside the outline {W}x{H}")
                r["displacement_um"] = round(abs(r["to"][0] - r["from_"][0]) + abs(r["to"][1] - r["from_"][1]), 4)
            rec[tn] = dict(delta=path, delta_sha256=dsha, moved=moved, unchanged_listed=unchanged,
                           core_taps_moved=taps, core_taps_moved_n=len(taps),
                           core_tap_max_displacement_um=max((r["displacement_um"] for r in taps), default=0.0))
    return rec, problems


# ------------------------------------------------------------------------------------------- (b) face windows
def die_window(plan, part, bus):
    p = next(q for q in plan["partitions"] if q["name"] == part)
    t = plan["partition_types"][p["type"]]
    b = next((b for b in t.get("buses") or [] if b["name"] == bus), None)
    if b is None or "window_um" not in b:
        return None
    w, h = t["outline_um"]
    o = p.get("orient", "R0")
    lo, hi = b["window_um"]
    if b["face"] in "NS":
        if o in ("MY", "R180"):
            lo, hi = w - hi, w - lo
        return (round(p["origin_um"][0] + lo, 4), round(p["origin_um"][0] + hi, 4))
    if o in ("MX", "R180"):
        lo, hi = h - hi, h - lo
    return (round(p["origin_um"][1] + lo, 4), round(p["origin_um"][1] + hi, 4))


def apply_face(plan, path):
    d = json.loads(Path(path).read_text())
    T = plan["partition_types"]
    problems, rec = [], {}
    before = json.loads(json.dumps(plan))
    for tn, m in sorted(d.items()):
        if tn not in T:
            problems.append(f"face: type {tn} not in the plan")
            continue
        for bus, v in sorted(m.items()):
            b = next((b for b in T[tn].get("buses") or [] if b["name"] == bus), None)
            if b is None:
                problems.append(f"face: {tn} has no bus {bus}")
                continue
            assert set(v) <= {"window_um", "layers"}, (tn, bus, sorted(v))
            rec.setdefault(tn, {})[bus] = dict(from_={k: b.get(k) for k in v}, to=v)
            b.update(copy.deepcopy(v))
    for tn, m in rec.items():           # a moved window must not overlap another window on its face (buses + ft slots)
        t = T[tn]
        for bus in m:
            b = next(x for x in t["buses"] if x["name"] == bus)
            lo, hi = b["window_um"]
            if not (0 <= lo < hi <= t["outline_um"][0 if b["face"] in "NS" else 1] + EPS):
                problems.append(f"face: {tn}.{bus} window {b['window_um']} outside the {b['face']} face")
            others = [(o["name"], o["window_um"]) for o in t["buses"] if o is not b and o["face"] == b["face"]]
            others += [(f"ft {f['name']}", f[w]) for f in t.get("ft_slots") or []
                       for fk, w in (("in_face", "in_window_um"), ("out_face", "out_window_um")) if f.get(fk) == b["face"]]
            for on, (olo, ohi) in others:
                if not (ohi <= lo + EPS or olo >= hi - EPS):
                    problems.append(f"face: {tn}.{bus} window {b['window_um']} overlaps {on} {[olo, ohi]}")
    changed = {(tn, bus) for tn, m in rec.items() for bus in m}
    ptype = {q["name"]: q["type"] for q in plan["partitions"]}
    ports = []
    for q in plan["ports"]:
        ends = [(e.get("part"), e.get("bus")) for e in (q["src"], q["dst"])]
        if not any(ptype.get(a) and (ptype[a], b) in changed for a, b in ends):
            continue
        if not all(ptype.get(a) for a, _ in ends):
            problems.append(f"face: port {q['id']} has a die end ({ends}): change not matched by a neighbour")
            continue
        wa, wb = (die_window(plan, a, b) for a, b in ends)
        oa = die_window(before, *ends[0])
        if wa is None or wb is None or wa != wb:
            problems.append(f"face: port {q['id']} {ends}: die-frame windows {wa} vs {wb} after the delta (unmatched)")
            continue
        if "window_um" in q and oa is not None and tuple(round(v, 4) for v in q["window_um"]) == oa and wa != oa:
            ports.append(dict(port=q["id"], from_=q["window_um"], to=list(wa)))
            q["window_um"] = list(wa)
        if "layers" in q:
            la = next(b for b in plan["partition_types"][ptype[ends[0][0]]]["buses"] if b["name"] == ends[0][1])["layers"]
            lb = next(b for b in plan["partition_types"][ptype[ends[1][0]]]["buses"] if b["name"] == ends[1][1])["layers"]
            if la != lb:
                problems.append(f"face: port {q['id']}: layers {la} vs {lb} (unmatched)")
            elif q["layers"] != la:
                ports.append(dict(port=q["id"], layers_from=q["layers"], layers_to=la))
                q["layers"] = copy.deepcopy(la)
    return dict(delta=str(path), delta_sha256=fsha(path), types=rec, ports_derived=ports), problems


def keep_clear(plan, path):
    """keep-clear rules of an accompanying face event: rect rule = no placed core (with obs_min: whose obs_max layer
    >= obs_min) intersects rect_um (type frame, open interior); max_top rule = every core whose module matches
    module_re has box top <= max_top_um."""
    import re
    rules = json.loads(Path(path).read_text())
    bad = []
    for r in rules:
        t = plan["partition_types"][r["type"]]
        for e in t.get("hard_cores") or []:
            x0, y0, x1, y1 = box(e)
            if "rect_um" in r:
                X0, Y0, X1, Y1 = r["rect_um"]
                lvl = int(str(e.get("obs_max", "M9"))[1:] or 9)
                if lvl >= int(r.get("obs_min", 0)) and x0 < X1 - EPS and x1 > X0 + EPS and y0 < Y1 - EPS and y1 > Y0 + EPS:
                    bad.append(f"{r['type']} {e['inst']} ({e['module']}, obs {e.get('obs_max')}) box "
                               f"{[round(v, 3) for v in (x0, y0, x1, y1)]} in keep-clear {r['rect_um']} ({r.get('why', '')})")
            if "module_re" in r and re.search(r["module_re"], e["module"]) and y1 > r["max_top_um"] + EPS:
                bad.append(f"{r['type']} {e['inst']} ({e['module']}) top {y1:.3f} > {r['max_top_um']} ({r.get('why', '')})")
    return dict(pass_=not bad, rules=path, rules_sha256=fsha(path), violations=bad)


# ------------------------------------------------------------------------------------------- (d) signed box heights
def lef_size(path, macro):
    import re
    txt = Path(path).read_text()
    m = re.search(r"^MACRO\s+%s\s*$(.*?)^END\s+%s" % (re.escape(macro), re.escape(macro)), txt, re.S | re.M)
    z = re.search(r"^\s*SIZE\s+(\S+)\s+BY\s+(\S+)\s*;", m.group(1), re.M)
    return [float(z.group(1)), float(z.group(2))]


def apply_resize(plan, spec_path):
    """stage (d): rows of a module whose width == the signed width and height in from_heights take the signed SIZE and
    the signed view; origin kept.  Checks per row: view sha + LEF SIZE, pins table sha + every pin inside the new box,
    every core tap / ft reg / station reg / plain tap that was inside the old box is inside the new one, and no core
    that abutted the old box's top edge (it would lose its abutment)."""
    spec = json.loads(Path(spec_path).read_text())
    problems, rec = [], {}
    for r in spec["rows"]:
        for k, f in (("lef_sha256", "lef"), ("lib_sha256", "lib")):
            if fsha(REPO / r[f]) != r[k]:
                problems.append(f"resize: {r[f]} sha != {r[k][:12]}")
        size = lef_size(REPO / r["lef"], r["module"])
        if abs(size[0] - r["width"]) > EPS or abs(size[1] - r["to_height"]) > EPS:
            problems.append(f"resize: {r['module']} LEF SIZE {size} != {r['width']} x {r['to_height']}")
        pt = HERE / r["pins_file"]
        if not pt.is_file() or fsha(pt) != r["pins_table_sha256"]:
            problems.append(f"resize: pins table {r['pins_file']} missing or sha != {r['pins_table_sha256'][:12]}")
            pins = []
        else:
            pj = json.loads(pt.read_text())
            pins = pj.get("pins", pj) if isinstance(pj, dict) else pj
        for pn in pins if isinstance(pins, list) else []:
            xy = pn.get("xy") or pn.get("xy_um")
            if xy and not (-EPS <= xy[0] <= r["width"] + EPS and -EPS <= xy[1] <= r["to_height"] + EPS):
                problems.append(f"resize: {r['module']} pin {pn.get('name')} {xy} outside {r['width']}x{r['to_height']}")
        for tn, t in sorted(plan["partition_types"].items()):
            hcs = t.get("hard_cores") or []
            for e in hcs:
                w, h = e["outline_um"]
                if e["module"] != r["module"] or abs(w - r["width"]) > EPS or not any(abs(h - x) < EPS for x in r["from_heights"]):
                    continue
                b0 = box(e)
                if e.get("orient", "R0") not in ("R0", "MY"):
                    problems.append(f"resize: {tn} {e['inst']} orient {e.get('orient')}: origin-kept shrink is not top-edge")
                e["outline_um"] = [r["width"], r["to_height"]]
                e["lef"], e["lib"] = r["lef"], r["lib"]
                b1 = box(e)
                inside = lambda q, b: b[0] - EPS <= q[0] <= b[2] + EPS and b[1] - EPS <= q[1] <= b[3] + EPS  # noqa: E731
                pts = [(f"tap {tp['name']}", tp["xy"]) for tp in (t.get("clock") or {}).get("taps", []) or []]
                pts += [(f"ft {f_['name']} reg {i}", q) for f_ in t.get("ft_slots") or [] for i, q in enumerate(f_.get("regs_um") or [])]
                pts += [(f"istation {st.get('conn', j)} reg {i}", q) for j, st in enumerate(t.get("internal_stations") or [])
                        for i, q in enumerate(st.get("regs_um") or [])]
                for nm, q in pts:
                    if inside(q, b0) and not inside(q, b1):
                        problems.append(f"resize: {tn} {e['inst']}: {nm} at {q} was inside the old box, outside the new one")
                for o in hcs:
                    if o is e:
                        continue
                    ob = box(o)
                    if abs(ob[1] - b0[3]) < EPS and min(ob[2], b0[2]) - max(ob[0], b0[0]) > EPS:
                        problems.append(f"resize: {tn} {e['inst']}: {o['inst']} abutted the old top edge (y {b0[3]:g}); "
                                        f"it would sit {b0[3] - b1[3]:g} um off")
                rec.setdefault(tn, []).append(dict(inst=e["inst"], module=e["module"], from_=[w, h], to=e["outline_um"]))
    return dict(spec=str(spec_path), spec_sha256=fsha(spec_path), types=rec,
                rows=sum(len(v) for v in rec.values())), problems


# ------------------------------------------------------------------------------------------- EQ gate
def eq_gate(base, out, pos_rec, face_rec, pad_on, resize_rec=None):
    """restore every key the event may move from BASE and compare: anything else moved = FAIL."""
    x = json.loads(json.dumps(out))
    T, B = x["partition_types"], base["partition_types"]
    for tn, r in pos_rec.items():
        bi = {e["inst"]: e for k in ("hard_cores", "contents") for e in B[tn].get(k) or []}
        for k in ("hard_cores", "contents"):
            for e in T[tn].get(k) or []:
                if e["inst"] in bi:
                    for f in ("origin_um", "orient"):
                        if f in bi[e["inst"]]:
                            e[f] = copy.deepcopy(bi[e["inst"]][f])
                        else:
                            e.pop(f, None)
        bt = {tp["name"]: tp for tp in (B[tn].get("clock") or {}).get("taps", []) or []}
        for tp in (T[tn].get("clock") or {}).get("taps", []) or []:
            if tp["name"] in bt:
                tp["xy"] = copy.deepcopy(bt[tp["name"]]["xy"])
    if face_rec:
        for tn, m in face_rec["types"].items():
            bb = {b["name"]: b for b in B[tn]["buses"]}
            for b in T[tn]["buses"]:
                if b["name"] in m:
                    for f in ("window_um", "layers"):
                        if f in bb[b["name"]]:
                            b[f] = copy.deepcopy(bb[b["name"]][f])
        bp = {q["id"]: q for q in base["ports"]}
        for q in x["ports"]:
            for f in ("window_um", "layers"):
                if f in bp[q["id"]]:
                    q[f] = copy.deepcopy(bp[q["id"]][f])
    for tn, rows in (resize_rec or {}).get("types", {}).items():
        bi = {e["inst"]: e for e in B[tn].get("hard_cores") or []}
        for e in T[tn].get("hard_cores") or []:
            if e["inst"] in {r["inst"] for r in rows}:
                for f in ("outline_um", "lef", "lib"):
                    e[f] = copy.deepcopy(bi[e["inst"]][f])
    if pad_on:
        x["clock"]["cohort"].pop("tap_pad", None)
    bad = [k for k in set(x) | set(base) if x.get(k) != base.get(k)]
    if "partition_types" in bad:
        bad.remove("partition_types")
        bad += [f"partition_types.{t}" for t in set(T) | set(B) if T.get(t) != B.get(t)]
    return dict(pass_=not bad, moved_outside_event_keys=sorted(bad)[:50])


# ------------------------------------------------------------------------------------------- legality
def legality(plan, types, gap, edge):
    """per type: findings as (kind, key) -> message."""
    out = {}
    T = plan["partition_types"]
    for tn in types:
        t = T[tn]
        W, H = t["outline_um"]
        cores = [(e["inst"], box(e)) for k in ("hard_cores", "contents") for e in t.get(k) or []
                 if "origin_um" in e and "outline_um" in e and (k == "hard_cores" or e.get("lef"))]
        f = {}
        for i, (x0, y0, x1, y1) in cores:
            if x0 < edge - EPS or y0 < edge - EPS or x1 > W - edge + EPS or y1 > H - edge + EPS:
                f[("in_outline", i)] = f"{i} box {[round(v, 3) for v in (x0, y0, x1, y1)]} not inside {W}x{H} - {edge}"
        cs = sorted(cores, key=lambda c: c[1][0])
        for a in range(len(cs)):
            ia, A = cs[a]
            for b in range(a + 1, len(cs)):
                ib, Bx = cs[b]
                if Bx[0] - A[2] >= gap - EPS:
                    break
                gx = max(Bx[0] - A[2], A[0] - Bx[2])
                gy = max(Bx[1] - A[3], A[1] - Bx[3])
                key = tuple(sorted((ia, ib)))
                if gx < -EPS and gy < -EPS:
                    f[("overlap",) + key] = f"{ia} / {ib} overlap"
                    continue
                g = max(gx, gy)
                if EPS < g < gap - EPS:
                    f[("street",) + key] = f"{ia} / {ib} gap {g:.3f} < {gap} (not abutted)"
        pts = []
        ck = t.get("clock") or {}
        if ck.get("tap_um"):
            pts.append(("clock.tap_um", ck["tap_um"]))
        pts += [(f"tap {tp['name']}", tp["xy"]) for tp in ck.get("taps", []) or [] if tp.get("kind") != "core"]
        for s in t.get("ft_slots") or []:
            pts += [(f"ft {s['name']} reg {k}", r) for k, r in enumerate(s.get("regs_um") or [])]
        for k, s in enumerate(t.get("internal_stations") or []):
            pts += [(f"istation {s.get('conn', k)} reg {j}", r) for j, r in enumerate(s.get("regs_um") or [])]
        hcs = {e["inst"] for e in t.get("hard_cores") or []}
        for tp in ck.get("taps", []) or []:
            if tp.get("kind") == "core":
                pts.append((f"core tap {tp['name']}|{core_tap_inst(tp['name'], hcs)}", tp["xy"]))
        for nm, (px, py) in pts:
            own = nm.split("|")[1] if "|" in nm else None
            for i, (x0, y0, x1, y1) in cores:
                if i != own and x0 + EPS < px < x1 - EPS and y0 + EPS < py < y1 - EPS:
                    f[("site", nm.split("|")[0], i)] = f"{nm.split('|')[0]} at ({px:g},{py:g}) under core {i}"
        out[tn] = f
    return out


def legality_diff(base, out, types, gap, edge):
    lb, lo = legality(base, types, gap, edge), legality(out, types, gap, edge)
    res = {}
    for tn in types:
        new = {k: v for k, v in lo[tn].items() if k not in lb[tn]}
        res[tn] = dict(new=sorted(new.values()), inherited=len(set(lo[tn]) & set(lb[tn])),
                       fixed=len(set(lb[tn]) - set(lo[tn])))
    return dict(pass_=all(not r["new"] for r in res.values()), gap_um=gap, edge_um=edge, types=res)


# ------------------------------------------------------------------------------------------- G0 / phys
def g0(plan_path, out_dir):
    """check.py reads its sidecars from PLANDIR (census/, core_conns.json, r8/, lat/ ... of physical/die_plan/s81):
    the plan is copied into this directory under a temporary dot-name for the run and removed after."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = HERE / f".compose_g0_{fsha(plan_path)[:16]}_{out_dir.name}.json"
    tmp.write_bytes(Path(plan_path).read_bytes())
    try:
        r = subprocess.run([sys.executable, "-I", str(REPO / "tools/die_plan/check.py"), str(tmp), "--out",
                            str(out_dir), "--quiet"], capture_output=True, text=True, cwd=REPO)
    finally:
        tmp.unlink()
    (out_dir / "g0.log").write_text(r.stdout + r.stderr)
    if not (out_dir / "g0_report.json").is_file():
        raise SystemExit(f"G0 did not run on {plan_path}: {(r.stdout + r.stderr)[-1500:]}")
    return json.loads((out_dir / "g0_report.json").read_text())


def g0_diff(rb, ro):
    key = lambda i: (i.get("check"), i.get("msg"))  # noqa: E731
    eb = {key(i) for i in rb["findings"] if i.get("level") == "ERROR"}
    eo = [i for i in ro["findings"] if i.get("level") == "ERROR" and key(i) not in eb]
    return dict(pass_=not eo, base_errors=rb["errors"], out_errors=ro["errors"], new_errors=len(eo),
                new=[f"[{i.get('check')}] {i.get('msg')}" for i in eo[:40]], base_verdict=rb["verdict"],
                out_verdict=ro["verdict"])


def phys(plan_path, types, tap_types=()):
    """SVCPROV-PHYSINST check form + (tap_types) the kit snap of every early core tap of the types whose cores moved:
    gen_phys.core_tap_pins (PG-legal snap, explicit-entry track rule, macro-edge clearing) must succeed and every
    snapped tap must lie inside the type outline."""
    import schema as S
    import gen_phys as GP
    import die_trial as DT
    P = S.Plan(S.load(str(plan_path)), Path(plan_path))
    errs, n = {}, 0
    for tn in sorted(types):
        try:
            for k in ("contents", "hard_cores"):
                for c in P.types[tn].get(k) or []:
                    GP.content_physical_identity(c)
                    n += 1
            GP.window_port_names(P, tn)
            GP.type_macros(P, tn)
            if tn in tap_types:
                W, H = P.types[tn]["outline_um"]
                for port, x, y in GP.core_tap_pins(P, tn):
                    if not (-EPS <= x <= W + EPS and -EPS <= y <= H + EPS):
                        raise ValueError(f"snapped core tap {port} ({x:g},{y:g}) outside the outline {W}x{H}")
        except Exception as e:  # noqa: BLE001 - recorded per type
            errs[tn] = f"{type(e).__name__}: {e}"
    try:
        taps = len(DT.clock_taps(P))
        terr = None
    except Exception as e:  # noqa: BLE001
        taps, terr = None, f"{type(e).__name__}: {e}"
    return dict(pass_=not errs and terr is None, types=len(types), type_errors=errs, n_identity=n, clock_taps=taps,
                clock_taps_error=terr)


# ------------------------------------------------------------------------------------------- compose
def compose(a):
    t0 = time.time()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = Path(a.base).read_bytes()
    bsha = sha(raw)
    allowed = set(BASES) | set(a.base_sha or [])
    if not allowed or bsha not in allowed:
        raise SystemExit(f"base {bsha[:12]} is not BASE_1200 ({[b[:12] for b in allowed]}); pass --base-sha")
    base = json.loads(raw)
    form, dump = dump_form(base, raw)
    plan = json.loads(raw)
    stages, problems = [], []
    cur = bsha
    pos_rec, face_rec = {}, None
    if a.pos:
        deltas = load_pos(a.pos)
        pos_rec, pr = apply_pos(plan, deltas)
        problems += pr
        s_out = sha(dump(plan).encode())
        sheets = [split_sheet(x)[1] for x in a.pos]
        for sh in sheets:
            if sh and not Path(sh).is_file():
                problems.append(f"intent sheet {sh} does not exist")
        stages.append(dict(stage="a_positions",
                           inputs=[dict(path=p, sha256=s, intent_sheet=sh,
                                        intent_sheet_sha256=fsha(sh) if sh and Path(sh).is_file() else None)
                                   for (p, s, _), sh in zip(deltas, sheets)],
                           in_sha256=cur, out_sha256=s_out, types=sorted(pos_rec),
                           moved=sum(len(r["moved"]) for r in pos_rec.values()),
                           core_taps_moved=sum(len(r["core_taps_moved"]) for r in pos_rec.values()),
                           core_tap_max_displacement_um=max((r["core_tap_max_displacement_um"]
                                                             for r in pos_rec.values()), default=0.0)))
        cur = s_out
    if a.face:
        pre = dump(plan).encode()
        face_rec, pr = apply_face(plan, a.face)
        problems += pr
        s_out = sha(dump(plan).encode())
        ins = [dict(path=a.face, sha256=fsha(a.face))]
        cross = None
        if a.face_script:
            # the event's own applier (e.g. delta_lepw_eface_1111.py --rebase) on the same pre-stage plan: its output
            # must be byte-identical to the generic apply (cross-check of both implementations)
            mid, fo = out_dir / "pre_face_plan.json", out_dir / "face_script_plan.json"
            mid.write_bytes(pre)
            r = subprocess.run([sys.executable, "-I", a.face_script, "--rebase", str(mid), str(fo),
                                str(out_dir / "face_script_report.json")], capture_output=True, text=True, cwd=REPO)
            if r.returncode:
                problems.append(f"face script failed: {(r.stdout + r.stderr)[-1500:]}")
            else:
                cross = dict(script_out_sha256=fsha(fo), generic_out_sha256=s_out, identical=fsha(fo) == s_out)
                if not cross["identical"]:
                    problems.append(f"face: {Path(a.face_script).name} output {cross['script_out_sha256'][:12]} != generic "
                                    f"apply {s_out[:12]}")
                fo.unlink()
            mid.unlink()
            ins.append(dict(path=a.face_script, sha256=fsha(a.face_script)))
        stages.append(dict(stage="b_face_windows", inputs=ins, in_sha256=cur, out_sha256=s_out,
                           types=sorted(face_rec["types"]), ports_derived=len(face_rec["ports_derived"]),
                           script_cross_check=cross))
        cur = s_out
    resize_rec = None
    if getattr(a, "resize", None):
        resize_rec, pr = apply_resize(plan, a.resize)
        problems += pr
        s_out = sha(dump(plan).encode())
        stages.append(dict(stage="d_signed_box_height", inputs=[dict(path=a.resize, sha256=fsha(a.resize))],
                           in_sha256=cur, out_sha256=s_out, rows=resize_rec["rows"],
                           per_type={t: len(v) for t, v in resize_rec["types"].items()}))
        cur = s_out
    text = dump(plan).encode()
    if a.pad:
        if problems:
            raise SystemExit("PROBLEMS before the pad stage:\n  " + "\n  ".join(problems))
        mid = out_dir / "pre_pad_plan.json"
        mid.write_bytes(text)
        padout = out_dir / "plan.json"
        r = subprocess.run([sys.executable, "-I", a.pad_script, "apply-delta", str(mid), str(padout), a.pad,
                            str(out_dir / "pad_report.json")], capture_output=True, text=True, cwd=REPO)
        if r.returncode:
            raise SystemExit(f"pad stage failed: {r.stdout[-2000:]}{r.stderr[-2000:]}")
        text = padout.read_bytes()
        stages.append(dict(stage="c_latetap_pad", inputs=[dict(path=a.pad, sha256=fsha(a.pad)),
                                                          dict(path=a.pad_script, sha256=fsha(a.pad_script))],
                           in_sha256=cur, out_sha256=sha(text), sidecar="tap_pad_residual.json",
                           sidecar_sha256=fsha(out_dir / "tap_pad_residual.json")))
        mid.unlink()
        plan = json.loads(text)
        cur = sha(text)
    out_sha = sha(text)
    changed_types = sorted(set(pos_rec) | set((face_rec or {}).get("types", {})) | set((resize_rec or {}).get("types", {})))
    eq = eq_gate(base, plan, pos_rec, face_rec, bool(a.pad), resize_rec)
    leg = legality_diff(base, plan, changed_types, a.gap, a.edge)
    if a.keep_clear:
        kc = keep_clear(plan, a.keep_clear)
        leg["keep_clear"] = kc
        leg["pass_"] = leg["pass_"] and kc["pass_"]
    rec = dict(schema="opentallas.s81.compose_cleanslate.v1", event=TAG, do_not_count=True,
               created=time.strftime("%Y-%m-%d %H:%M:%S %Z"), base=str(a.base), base_plan_sha256=bsha,
               serialisation=form, args=dict(pos=a.pos or [], face=a.face, face_script=a.face_script,
                                             keep_clear=a.keep_clear, resize=getattr(a, "resize", None),
                                             pad=a.pad, pad_script=a.pad_script if a.pad else None,
                                             gap=a.gap, edge=a.edge),
               stages=stages, output_plan_sha256=out_sha, changed_types=changed_types,
               eq_gate=dict(eq, rtl_change=False, pin_change=False, outline_change=False, cycle_change=False),
               legality=leg, problems=problems, positions=pos_rec, face=face_rec, resize=resize_rec)
    if not a.dry_run:
        (out_dir / "plan.json").write_bytes(text)
    if not a.no_g0:
        pp = out_dir / "plan.json"
        if a.dry_run:
            pp = out_dir / "dry_plan.json"
            pp.write_bytes(text)
        gb_dir = Path(a.g0_base) if getattr(a, "g0_base", None) else out_dir / "g0_base"   # cached per base sha
        rb = json.loads((gb_dir / "g0_report.json").read_text()) if (
            (gb_dir / "g0_report.json").is_file() and (gb_dir / "base.sha").is_file()
            and (gb_dir / "base.sha").read_text().strip() == bsha) else None
        if rb is None:
            rb = g0(Path(a.base), gb_dir)
            (gb_dir / "base.sha").write_text(bsha + "\n")
        ro = g0(pp, out_dir / "g0_out")
        rec["g0"] = g0_diff(rb, ro)
        if a.dry_run:
            pp.unlink()
    if a.phys:
        pp = out_dir / ("plan.json" if not a.dry_run else "dry_plan.json")
        if a.dry_run:
            pp.write_bytes(text)
        rec["phys"] = phys(pp, changed_types or list(plan["partition_types"]),
                           tap_types={t for t, r in pos_rec.items() if r["core_taps_moved"]})
        if a.dry_run:
            pp.unlink()
    ok = (not problems and eq["pass_"] and leg["pass_"] and rec.get("g0", {}).get("pass_", True)
          and rec.get("phys", {}).get("pass_", True))
    rec["verdict"] = "PASS" if ok else "FAIL"
    rec["seconds"] = round(time.time() - t0, 1)
    (out_dir / ("record.json" if not a.dry_run else "dry_record.json")).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(verdict=rec["verdict"], base=bsha[:12], out=out_sha[:12], changed_types=len(changed_types),
                          problems=problems[:10], eq=eq["pass_"], legality=leg["pass_"],
                          legality_new={t: r["new"][:3] for t, r in leg["types"].items() if r["new"]},
                          g0=rec.get("g0", {}).get("new_errors"), phys=rec.get("phys", {}).get("pass_"),
                          phys_errors=dict(list(rec.get("phys", {}).get("type_errors", {}).items())[:5]),
                          core_taps_moved=sum(len(r["core_taps_moved"]) for r in pos_rec.values()),
                          stages=[(s["stage"], s["in_sha256"][:12], s["out_sha256"][:12]) for s in stages])))
    return 0 if ok else 1


def check(out_dir):
    out_dir = Path(out_dir)
    rec = json.loads((out_dir / "record.json").read_text())
    ar = rec["args"]
    for s in rec["stages"]:
        for i in s["inputs"]:
            assert fsha(i["path"]) == i["sha256"], (s["stage"], i["path"], "input changed")
    tmp = out_dir / "check_rederive"
    ns = argparse.Namespace(base=rec["base"], out_dir=str(tmp), pos=ar["pos"], face=ar["face"], pad=ar["pad"],
                            face_script=ar.get("face_script"), keep_clear=ar.get("keep_clear"), resize=ar.get("resize"),
                            pad_script=ar["pad_script"], base_sha=[rec["base_plan_sha256"]], no_g0=True, phys=False,
                            dry_run=False, gap=ar["gap"], edge=ar["edge"])
    compose(ns)
    a, b = fsha(tmp / "plan.json"), fsha(out_dir / "plan.json")
    assert a == b == rec["output_plan_sha256"], ("re-derivation differs", a, b, rec["output_plan_sha256"])
    print("CHECK PASS", a)


def main():
    if sys.argv[1:2] == ["--check"]:
        check(sys.argv[2])
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["compose"])
    ap.add_argument("base")
    ap.add_argument("out_dir")
    ap.add_argument("--pos", action="append", help="positions/orients delta JSON[::intent sheet] (repeatable)")
    ap.add_argument("--face", help="face-window delta JSON")
    ap.add_argument("--face-script", help="the face event's own applier, run with --rebase on the same pre-stage plan; "
                                          "its output must equal the generic apply")
    ap.add_argument("--keep-clear", help="keep-clear rules JSON [{type, rect_um, obs_min?, why}, "
                                         "{type, module_re, max_top_um, why}]")
    ap.add_argument("--resize", help="stage (d) signed box heights spec (events/compose_cleanslate_1111/resize_svcprov_1111.json)")
    ap.add_argument("--pad", help="DS85-LATETAP-1111 pads_delta.json (optional stage c, default OFF)")
    ap.add_argument("--pad-script", default=str(HERE / "delta_latetap_pad_1111.py"))
    ap.add_argument("--base-sha", action="append", help="accepted base sha256 (in addition to BASES)")
    ap.add_argument("--no-g0", action="store_true")
    ap.add_argument("--g0-base", help="shared dir caching BASE's G0 report (reused when its base.sha matches)")
    ap.add_argument("--phys", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="validate + gates, write dry_record.json only")
    ap.add_argument("--gap", type=float, default=34.56, help="B34 street: non-abutted cores >= gap apart")
    ap.add_argument("--edge", type=float, default=0.0, help="core box >= edge from the type outline")
    a = ap.parse_args()
    if a.pos:
        a.pos = ["::".join(str(Path(x).resolve()) for x in split_sheet(p) if x) for p in a.pos]
    for k in ("face", "face_script", "keep_clear", "resize", "pad", "base"):
        if getattr(a, k):
            setattr(a, k, str(Path(getattr(a, k)).resolve()))
    a.pad_script = str(Path(a.pad_script).resolve())
    return compose(a)


if __name__ == "__main__":
    sys.exit(main())
