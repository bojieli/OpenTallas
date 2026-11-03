#!/usr/bin/env python3
"""DH58-RFPLAN (DIE-HEAD-58 RE-FORM batch, CLOSURE-LIST HEAD-046): HEAD plan event l48rf on a prepared HEAD dir.

OWNER 11-03 06:11 RE-FORM shape rules + 06:14 slot infra, applied as ONE plan delta with existing plan knobs only
(no gate, no limit, no tool change):

  grow     a type's outline grows into die whitespace (die channels, never another partition / reserve frame / seal
           ring) by (left, bottom, right, top) um in the TYPE frame.  Every type-frame coordinate (pins on their
           faces, windows, landing pins / bands / stages / anchors, straps, taps, islands, reserved sites, reset
           local taps, sink rows) is translated by (left, bottom) and every instance origin moves per orientation,
           so every object keeps its absolute die position: neighbours and die port windows are unchanged.  Die
           channels covered by the new slot are clipped; reset.in_sites of the type is re-planned by the wavefront
           planner (as the HK4 crop does).  Use: aspect <= 3:1 (OWNER 06:11) for ft / control strips whose length is
           fixed by the transit they carry.
  entries  'clock entry per region' (OWNER 06:14): the type's density taps also see every plan-fixed infra
           register the plan-time GEOM counts (reset relays / root / outs, landing stage groups, landed out-face
           registers) as clock.sink_sites_um rows (weight 1), iterated to a fixed point (relays are sited from the
           taps), so taps.density_taps places an entry within tap_radius_um of each of them and splits load at
           tap_target_sinks.  Entries stay on the slot (type pins), one per region of <= tap_max_sinks sinks.

usage: head_rf_plan_delta.py SRC_DIR OUT_DIR --spec SPEC.json [--report REPORT.json]
  SPEC: {"grow": {"<type>": [l, b, r, t], ...}, "entries": ["<type>", ...]}
"""
import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

# RF_TOOL_ROOT: judge with the same tool tree as the G0C that reviews the plan (frozen HEAD src)
ROOT = Path(os.environ.get("RF_TOOL_ROOT") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT / "tools" / "autopilot"))

TAG = "DH58-RFPLAN l48rf"
GRID = 8.64
SEAL = 103.68
# type-frame keys whose numeric lists are NOT coordinates (sizes / face-relative windows handled apart)
NOT_COORD = {"outline_um", "bit_site_cell_um", "in_window_um", "out_window_um", "window_um", "tap_pin_heights_um",
             "area_reserve_um2", "max_pin_to_band_hop_um", "tap_radius_um", "tap_pitch_um"}
RECT_KEYS = {"rect_um", "origin_rect_um"}
INFRA = ("relay:", "reset_root", "reset_out", "landing:", "plan_land_out")


def r3(v):
    return round(v + 0.0, 3)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _shift_list(v, key, dx, dy):
    """translate one numeric list by (dx, dy) by its shape: point [x, y(, n...)] / rect [x0, y0, x1, y1]."""
    if key in RECT_KEYS and len(v) == 4:
        return [r3(v[0] + dx), r3(v[1] + dy), r3(v[2] + dx), r3(v[3] + dy)]
    if len(v) >= 2:
        return [r3(v[0] + dx), r3(v[1] + dy)] + list(v[2:])
    return v


def shift_coords(o, dx, dy, key=None, coord=False):
    """recursively translate every type-frame coordinate under o.  coord: inside a coordinate-bearing key."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in NOT_COORD:
                continue
            c = coord or k.endswith("_um") or k in ("landing_status_anchors",)
            o[k] = shift_coords(v, dx, dy, k, c)
        return o
    if isinstance(o, list):
        if o and all(_is_num(v) for v in o):
            if not coord:
                return o
            if key in ("die_islands_um",) or (key in RECT_KEYS):
                return _shift_list(o, "rect_um", dx, dy) if len(o) == 4 else _shift_list(o, key, dx, dy)
            return _shift_list(o, key, dx, dy)
        if key == "die_islands_um":
            return [_shift_list(v, "rect_um", dx, dy) for v in o]
        return [shift_coords(v, dx, dy, key, coord) for v in o]
    return o


def grow_type(t, l, b, r, tp):
    """the type grown by (l, b, r, tp) um in its own frame; returns a new dict."""
    t = copy.deepcopy(t)
    W, H = t["outline_um"]
    for f in t.get("ft_slots", []):
        for fc, key in ((f["in_face"], "in_window_um"), (f["out_face"], "out_window_um")):
            d = b if fc in "WE" else l
            f[key] = [r3(v + d) for v in f[key]]
    for bb in t.get("buses", []):
        if "face" in bb and "window_um" in bb:
            d = b if bb["face"] in "WE" else l
            bb["window_um"] = [r3(v + d) for v in bb["window_um"]]
    for k in list(t):
        if k in ("ft_slots", "buses", "outline_um"):
            continue
        t[k] = shift_coords(t[k], l, b, k, k.endswith("_um"))
    for f in t.get("ft_slots", []):     # ft slot coordinate keys other than the windows (bit sites, regs)
        for k in list(f):
            if k not in NOT_COORD and k.endswith("_um"):
                f[k] = shift_coords(f[k], l, b, k, True)
    t["outline_um"] = [r3(W + l + r), r3(H + b + tp)]
    t["note"] = (t.get("note", "") + f" | {TAG}: slot grown by l {l} b {b} r {r} t {tp} um (type frame) into die "
                 "whitespace, every object at its old die position (OWNER 06:11 aspect <= 3:1)").strip(" |")
    return t


def new_origin(o, orient, W, H, R):
    """HK4 crop rule (head_channel_resize_delta.new_origin), R = new outline in the OLD type frame."""
    x0, y0, x1, y1 = R
    nx = o[0] + x0 if orient in ("R0", "MX") else o[0] + W - x1
    ny = o[1] + y0 if orient in ("R0", "MY") else o[1] + H - y1
    return [r3(nx), r3(ny)]


def part_rect(plan, p):
    w, h = plan["partition_types"][p["type"]]["outline_um"]
    return [p["origin_um"][0], p["origin_um"][1], r3(p["origin_um"][0] + w), r3(p["origin_um"][1] + h)]


def _ov(a, b, tol=1e-3):
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol


def subtract(c, r):
    """rect c minus rect r -> list of rects."""
    if not _ov(c, r):
        return [c]
    out = []
    x0, y0, x1, y1 = c
    if r[1] > y0:
        out.append([x0, y0, x1, r[1]])
    if r[3] < y1:
        out.append([x0, r[3], x1, y1])
    a, bb = max(y0, r[1]), min(y1, r[3])
    if r[0] > x0:
        out.append([x0, a, r[0], bb])
    if r[2] < x1:
        out.append([r[2], a, x1, bb])
    return [[r3(v) for v in q] for q in out if q[2] - q[0] > 1e-3 and q[3] - q[1] > 1e-3]


def apply_grow(plan, spec, rep):
    pt = plan["partition_types"]
    in_sites = plan.get("reset", {}).get("in_sites", {})
    for tn, (l, b, r, tp) in spec.items():
        for v in (l, b, r, tp):
            if v < 0 or abs(v / GRID - round(v / GRID)) > 1e-6:
                raise SystemExit(f"{tn}: growth {v} must be >= 0 and on the {GRID}-um grid")
        W, H = pt[tn]["outline_um"]
        R = [-l, -b, W + r, H + tp]
        row = dict(old_outline_um=[W, H], grow_ltrb_um=[l, b, r, tp], moves=[])
        for p in plan["partitions"]:
            if p["type"] != tn:
                continue
            o, orient = p["origin_um"], p.get("orient", "R0")
            if orient not in ("R0", "MX", "MY", "R180"):
                raise SystemExit(f"{p['name']}: orient {orient} not handled")
            no = new_origin(o, orient, W, H, R)
            row["moves"].append(dict(part=p["name"], orient=orient, old_origin_um=o, new_origin_um=no))
            p["origin_um"] = no
        pt[tn] = grow_type(pt[tn], l, b, r, tp)
        if tn in in_sites:              # the reset input keeps its die position (type frame shifts by l, b)
            old = in_sites[tn]
            in_sites[tn] = [r3(old[0] + l), r3(old[1] + b)] + list(old[2:])
            row["reset_in_site_um"] = [old, in_sites[tn]]
        row["new_outline_um"] = pt[tn]["outline_um"]
        nw, nh = pt[tn]["outline_um"]
        row["aspect_old"], row["aspect_new"] = r3(max(W, H) / min(W, H)), r3(max(nw, nh) / min(nw, nh))
        rep["grow"][tn] = row
    # legality: no partition overlap, inside the seal ring, off the reserve frames; clip covered die channels
    DW, DH = plan["die"]["outline_um"]
    rects = {p["name"]: part_rect(plan, p) for p in plan["partitions"]}
    grown = {m["part"] for row in rep["grow"].values() for m in row["moves"]}
    keep_ch = []
    for c in plan["die"].get("channels", []):
        if "seal ring" in c.get("reason", "") or "reserve frame" in c.get("reason", ""):
            for n in grown:
                if _ov(rects[n], c["rect_um"]):
                    raise SystemExit(f"{n}: grown slot {rects[n]} overlaps {c.get('reason', '')[:40]} {c['rect_um']}")
            keep_ch.append(c)
            continue
        pieces = [c["rect_um"]]
        for n in grown:
            pieces = [q for pc in pieces for q in subtract(pc, rects[n])]
        if len(pieces) == 1 and pieces[0] == c["rect_um"]:
            keep_ch.append(c)
            continue
        rep["channels_clipped"].append(dict(name=c.get("name"), old=c["rect_um"], new=pieces))
        for i, q in enumerate(pieces):
            keep_ch.append(dict(c, rect_um=q, name=(c.get("name") or "ch") + (f"_rf{i}" if len(pieces) > 1 else "")))
    plan["die"]["channels"] = keep_ch
    for n in grown:
        a = rects[n]
        if a[0] < SEAL - 1e-3 or a[1] < SEAL - 1e-3 or a[2] > DW - SEAL + 1e-3 or a[3] > DH - SEAL + 1e-3:
            raise SystemExit(f"{n}: grown slot {a} leaves the die core")
        for m, b in rects.items():
            if m != n and _ov(a, b):
                raise SystemExit(f"{n}: grown slot {a} overlaps partition {m} {b}")


ENTRY_RADIUS_UM = 180.0   # density leaf radius: plan-time reach limit 220 (geom_rules 200 x 1.10) less tap legalisation
ENTRY_TARGET = 1000       # density leaf load: TAP_SINKS_MAX 1500 on the nearest-tap split (kit rule) with margin


def apply_entries(plan, types, plan_path, rep, iters=8):
    import schema as S
    import plan_geom as PG
    import taps
    for tn in types:
        ck = plan["partition_types"][tn].setdefault("clock", {})
        base = [row for row in ck.get("sink_sites_um", [])]
        rows, hist = [], []
        opt = types[tn] if isinstance(types, dict) else {}
        old = dict(tap_radius_um=ck.get("tap_radius_um"), tap_target_sinks=ck.get("tap_target_sinks"))
        ck["tap_radius_um"] = float(opt.get("radius", ENTRY_RADIUS_UM))
        ck["tap_target_sinks"] = int(opt.get("target", ENTRY_TARGET))
        hist.append(dict(old=old, new=dict(tap_radius_um=ck["tap_radius_um"], tap_target_sinks=ck["tap_target_sinks"])))
        if ck.get("tap_mode") not in ("density",):
            hist.append(f"tap_mode {ck.get('tap_mode')} -> density")
            ck["tap_mode"] = "density"
        for it in range(iters):
            ck["sink_sites_um"] = base + rows
            taps._CACHE.clear()
            dedupe_local_reset_taps(plan, plan_path, [tn], rep)   # before the tree reads them (no duplicate tap)
            taps._CACHE.clear()
            P = S.Plan(copy.deepcopy(plan), Path(plan_path).resolve())
            G = PG.type_sites(P, tn)
            new = sorted({(r3(x), r3(y)) for x, y, w, k in G["sinks"] if k.startswith(INFRA)})
            new = [[x, y, 1] for x, y in new]
            m = PG.type_metrics(P, tn)
            hist.append(dict(it=it, infra_rows=len(rows), entries=m["clock_entries"], reach=m["clock_reach_max"],
                             far=m["clock_reach_far"], tap_sinks_max=m.get("grid_tap_sinks_max")))
            merged = sorted({tuple(q) for q in rows} | {tuple(q) for q in new})
            if [list(q) for q in merged] == rows:
                break
            rows = [list(q) for q in merged]     # monotone union: relays re-sited by the new taps keep coverage
        rep["entries"][tn] = dict(base_rows=len(base), infra_rows=len(rows), history=hist)


def _entries_one(plan, tn, opt, plan_path):
    src_ck = copy.deepcopy(plan["partition_types"][tn].get("clock", {}))
    plan = copy.deepcopy(plan)
    rep = dict(entries={})
    try:
        apply_entries(plan, {tn: opt}, plan_path, rep)
    except Exception as ex:          # the type keeps its clock record unchanged; reported
        print(f"entries {tn}: SKIPPED {type(ex).__name__}: {str(ex)[:160]}", flush=True)
        return tn, src_ck, dict(skipped=f"{type(ex).__name__}: {str(ex)[:300]}"), None
    print(f"entries {tn}: {rep['entries'][tn]['history'][-1]}", flush=True)
    rep["entries"][tn]["reset_local_taps_on_clock_entry"] = rep.get("reset_local_taps_on_clock_entry", {}).get(tn)
    return tn, plan["partition_types"][tn]["clock"], rep["entries"][tn], plan["partition_types"][tn].get("reset")


def _pins(o, acc):
    if isinstance(o, dict):
        if "name" in o and "source_instance" in o:
            acc.append(o)
        for v in o.values():
            _pins(v, acc)
    elif isinstance(o, list):
        for v in o:
            _pins(v, acc)
    return acc


def repoint_raw(plan, plan_path, src_plan, src_path, rep):
    """START raw reset exports follow the re-derived reset tree (DIE-HEAD-36 src25q precedent): a declared row whose
    relay no longer exists at its xy is re-pointed to the raw-role relay of the NEW tree nearest the row's old
    position (the row xy, already translated by grow_type: the same die position), same depth preferred.  The
    export pin moves with its relay (8.64 steps); its source_instance / source_copy_from_net follow the row.
    Reported per row: displacement um and depth delta (START hop / release-span inputs)."""
    import schema as S
    import reset_tree as RT

    def relays(P, tn):
        tr = RT.for_type(P, tn)
        rel = RT.start_relays(tr) if tr.get("start") else tr["relays"]
        return {r["name"]: r for r in rel if not tr.get("start") or r.get("role") in ("raw", "boot", "bootstrap_transport")}

    P0 = S.Plan(copy.deepcopy(src_plan), Path(src_path).resolve())
    P1 = S.Plan(copy.deepcopy(plan), Path(plan_path).resolve())
    out = rep.setdefault("raw_repoint", {})
    for tn, t in sorted(plan["partition_types"].items()):
        rows = [r for r in t.get("reset_start_raw_exports", []) if not r.get("existing_port")]
        if t.get("hard") or not rows:
            continue
        new = relays(P1, tn)
        old = relays(P0, tn)
        pins = {p["name"]: p for p in _pins(t, [])}
        used = {r["instance"] for r in rows if r["instance"] in new and new[r["instance"]]["q"] == r["net"]
                and all(abs(x - y) <= 1e-6 for x, y in zip(new[r["instance"]]["xy"], r["xy_um"]))}
        for r in rows:
            a = new.get(r["instance"])
            if a and a["q"] == r["net"] and all(abs(x - y) <= 1e-6 for x, y in zip(a["xy"], r["xy_um"])):
                continue
            o = old.get(r["instance"])
            od = o.get("depth", 0) if o else 0
            ox, oy = r["xy_um"][0], r["xy_um"][1]     # already in the new frame (grow_type shifted it)
            cand = [c for n, c in new.items() if n not in used] or list(new.values())
            c = min(cand, key=lambda c: (abs(c["xy"][0] - ox) + abs(c["xy"][1] - oy) + 50.0 * abs(c.get("depth", 0) - od), c["name"]))
            used.add(c["name"])
            d = abs(c["xy"][0] - ox) + abs(c["xy"][1] - oy)
            out.setdefault(tn, []).append(dict(port=r["port"], old=[r["instance"], r["net"], r["xy_um"], od],
                                               new=[c["name"], c["q"], list(c["xy"]), c.get("depth", 0)],
                                               move_um=r3(d), depth_delta=c.get("depth", 0) - od))
            ddx, ddy = c["xy"][0] - r["xy_um"][0], c["xy"][1] - r["xy_um"][1]
            r["instance"], r["net"], r["xy_um"] = c["name"], c["q"], list(c["xy"])   # exact: the check is 1e-6
            pin = pins.get(r["port"])
            if pin is not None and pin.get("xy_um"):
                # the export pin follows its raw FF (DIE-HEAD-36 src25q): moved by the relay displacement in whole
                # 8.64-um steps (keeps its track snap), kept inside the outline
                W, H = t["outline_um"]
                px, py = pin["xy_um"][:2]
                sx, sy = GRID * round(ddx / GRID), GRID * round(ddy / GRID)
                while not 0 <= px + sx <= W and sx:
                    sx -= math.copysign(GRID, sx)
                while not 0 <= py + sy <= H and sy:
                    sy -= math.copysign(GRID, sy)
                pin["xy_um"] = [r3(px + sx), r3(py + sy)] + list(pin["xy_um"][2:])
                out[tn][-1]["pin_move_um"] = [r3(sx), r3(sy)]
            if pin is not None:
                pin["source_instance"] = c["name"]
                if "source_copy_from_net" in pin:
                    pin["source_copy_from_net"] = c["q"]
                elif pin.get("source_net") not in (None, r["port"]):
                    pin["source_net"] = c["q"]
    allr = [x for v in out.values() for x in v]
    rep["raw_repoint_summary"] = dict(rows=len(allr), max_move_um=max([x["move_um"] for x in allr] or [0]),
                                      max_abs_depth_delta=max([abs(x["depth_delta"]) for x in allr] or [0]))


def dedupe_local_reset_taps(plan, plan_path, types, rep):
    """a type.reset.local_taps_um site that a new density clock entry now lands on exactly is already a reset
    consumer (clock taps are reset consumers first, reset_tree.consumer_taps): drop the duplicate local tap."""
    import schema as S
    import reset_tree as RT
    P = S.Plan(copy.deepcopy(plan), Path(plan_path).resolve())
    for tn in types:
        rs = plan["partition_types"][tn].get("reset", {})
        extra = rs.get("local_taps_um") or []
        if not extra:
            continue
        taps = RT._taps(P, tn)
        keep = [xy for xy in extra if not any(abs(xy[0] - a) < 1e-6 and abs(xy[1] - b) < 1e-6 for _, a, b in taps)]
        if len(keep) != len(extra):
            rep.setdefault("reset_local_taps_on_clock_entry", {})[tn] = [xy for xy in extra if xy not in keep]
            rs["local_taps_um"] = keep
            if not keep:
                rs.pop("local_taps_um")


REF_KEYS = ("raw_reset", "raw", "source_copy_from_net", "source_net")


def _all_relays(P, tn):
    import reset_tree as RT
    tr = RT.for_type(P, tn)
    out = {}
    for fam, rel in (("start", RT.start_relays(tr) if tr.get("start") else []), ("tree", tr["relays"])):
        for r in rel:                         # family = which list + net prefix: depths compare only inside one
            out[r["q"]] = dict(r, fam=(fam, re.sub(r"\d+$", "", r["q"])))
    memo = {}

    def chain(q, seen=()):                    # RTL depth = registered relays from the root (GEN depth())
        if q not in memo:
            r = out.get(q)
            memo[q] = 0 if r is None or q in seen else chain(r.get("d"), seen + (q,)) + 1
        return memo[q]
    for q, r in out.items():
        r["depth"] = chain(q)
    return out


def remap_raw_refs(plan, plan_path, src_plan, src_path, rep):
    """landing START / local-reset stages name their registered raw source by NET (landing_reader_start /
    landing_writer_start .stages[].raw_reset, landing_local_resets[].raw, landing pins source_net /
    source_copy_from_net), frozen from the l48h1 reset tree.  When a type's tree is re-derived (grown frame, new
    clock entries) each referenced net is mapped ONCE, by its l48h1 relay, to the relay of the new tree at the SAME
    wavefront depth nearest that relay's die position (release cycle unchanged by construction).  START raw export
    rows/pins are left to repoint_raw.  A net with no same-depth relay is an error for that type."""
    import schema as S
    P0 = S.Plan(copy.deepcopy(src_plan), Path(src_path).resolve())
    P1 = S.Plan(copy.deepcopy(plan), Path(plan_path).resolve())
    out = rep.setdefault("raw_ref_remap", {})
    bad = {}
    for tn, t in sorted(plan["partition_types"].items()):
        if t.get("hard") or tn not in src_plan["partition_types"]:
            continue
        ports = {r["port"] for r in t.get("reset_start_raw_exports", [])}
        refs = []

        def walk(o, path):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in REF_KEYS and isinstance(v, str):
                        if not (k.startswith("source_") and o.get("name") in ports):
                            refs.append((o, k))
                    elif isinstance(v, (dict, list)):
                        walk(v, path + "/" + k)
            elif isinstance(o, list):
                for v in o:
                    walk(v, path)
        walk(t.get("clock", {}), "clock")
        if not refs:
            continue
        old = _all_relays(P0, tn)
        new = _all_relays(P1, tn)
        l, b = (rep["grow"].get(tn, {}).get("grow_ltrb_um") or [0, 0])[:2]
        m, moves = {}, []
        for o, k in refs:
            n = o[k]
            if n not in old:
                continue                      # not a relay net (port / logic net): untouched
            if n not in m:
                r0 = old[n]
                ox, oy = r0["xy"][0] + l, r0["xy"][1] + b
                c = new.get(n)
                if not (c and c["depth"] == r0["depth"] and c["fam"] == r0["fam"] and abs(c["xy"][0] - ox) + abs(c["xy"][1] - oy) < 1e-6):
                    cand = [c for c in new.values() if c["depth"] == r0["depth"] and c["fam"][0] == r0["fam"][0]]
                    if not cand:
                        bad.setdefault(tn, []).append(n)
                        m[n] = n
                        continue
                    c = min(cand, key=lambda c: (c["fam"] != r0["fam"], abs(c["xy"][0] - ox) + abs(c["xy"][1] - oy), c["q"]))
                m[n] = c["q"]
                if c["q"] != n:
                    moves.append(dict(old=n, new=c["q"], depth=r0["depth"],
                                      move_um=r3(abs(c["xy"][0] - ox) + abs(c["xy"][1] - oy))))
            o[k] = m[n]
        if moves:
            out[tn] = dict(nets=len(moves), refs=len(refs),
                           max_move_um=max(x["move_um"] for x in moves), moves=moves)
    if bad:
        raise SystemExit(f"remap_raw_refs: no same-depth relay for {bad}")
    rep["raw_ref_remap_summary"] = {tn: (v["nets"], v["max_move_um"]) for tn, v in out.items()}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads(Path(a.spec).read_text())
    plan = json.loads((src / "source_plan.json").read_text())
    rep = dict(schema="opentallas.head_rf_plan_delta.v1", tag=TAG, src=str(src), src_sha256=sha(src / "source_plan.json"),
               spec=spec, grow={}, channels_clipped=[], entries={})
    apply_grow(plan, spec.get("grow", {}), rep)
    # assets resolve relative to the plan file: work inside OUT with the src assets linked
    for n in os.listdir(src):
        if n in ("source_plan.json", "wave_prepare.json") or n.endswith(".log"):
            continue
        dst = out / n
        if not dst.exists() and not dst.is_symlink():
            if (src / n).is_dir():
                os.symlink((src / n).resolve(), dst)
            else:
                shutil.copy2(src / n, dst)
    tmp = out / "source_plan.json"
    tmp.write_text(json.dumps(plan, indent=1) + "\n")
    if spec.get("entries"):
        ents = spec["entries"] if isinstance(spec["entries"], dict) else {tn: {} for tn in spec["entries"]}
        import multiprocessing as mp
        with mp.get_context("fork").Pool(min(len(ents), int(os.environ.get("RF_JOBS", "8")))) as pool:
            res = pool.starmap(_entries_one, [(plan, tn, opt, str(tmp)) for tn, opt in ents.items()])
        for tn, ck, r, rs in res:
            plan["partition_types"][tn]["clock"] = ck
            if rs is not None:
                plan["partition_types"][tn]["reset"] = rs
            rep["entries"][tn] = r
    tmp.write_text(json.dumps(plan, indent=1) + "\n")
    if spec.get("entries"):
        dedupe_local_reset_taps(plan, str(tmp), list(spec["entries"]), rep)
        tmp.write_text(json.dumps(plan, indent=1) + "\n")
    src_plan = json.loads((src / "source_plan.json").read_text())
    remap_raw_refs(plan, str(tmp), src_plan, str(src / "source_plan.json"), rep)
    tmp.write_text(json.dumps(plan, indent=1) + "\n")
    for it in range(4):           # re-pointing changes nothing the tree reads; a second pass must be empty
        before = rep.get("raw_repoint_summary", {}).get("rows")
        rep.pop("raw_repoint", None)
        repoint_raw(plan, str(tmp), src_plan, str(src / "source_plan.json"), rep)
        tmp.write_text(json.dumps(plan, indent=1) + "\n")
        if rep["raw_repoint_summary"]["rows"] == 0:
            break
        rep.setdefault("raw_repoint_passes", []).append(dict(rep["raw_repoint_summary"], raw_repoint=rep["raw_repoint"]))
    plan["note"] = (plan.get("note", "") + f" | {TAG}: RE-FORM batch plan event (grow {sorted(spec.get('grow', {}))}, "
                    f"entries {sorted(spec.get('entries', []))})").strip(" |")
    tmp.write_text(json.dumps(plan, indent=1) + "\n")
    rep["out_sha256"] = sha(tmp)
    Path(a.report or out / "rf_report.json").write_text(json.dumps(rep, indent=1, default=str) + "\n")
    print(json.dumps(dict(out=str(tmp), sha=rep["out_sha256"][:12], grow={k: [v["aspect_old"], v["aspect_new"]] for k, v in rep["grow"].items()},
                          entries={k: (v.get("history") or [v.get("skipped")])[-1] for k, v in rep["entries"].items()}), default=str))


if __name__ == "__main__":
    sys.exit(main())
