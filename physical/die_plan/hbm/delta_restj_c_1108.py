#!/usr/bin/env python3
"""HBM plan event RESTJ-C-1108 (DIE-HBM-92-RESTJ 11-08, COORD 09:2x approval of HBM-HARD-6 09:10 form C).

Hard core ot_hgi_sfu_split3_ctl_rest_1c (q_b113 / q_b113__physical_v1 u_sfucore_Q_ctl__rest, orient MY).  HBM-HARD-6
vB failed GRT on a north-south cut (5,880 nets across y = mid at 181 um width).  Form C keeps the B source and pin order
and widens the core to 267.84 x 267.84 inside the existing 427.68 x 453.6 slot.  The vC kit
(epyc6 .../hbm-hard-6/kits/restj_C/ot_hgi_sfu_split3_ctl_rest_1c_vC) was built at that outline from its own pin table
(plan_pins.json, sha256 518cf1d2, 12373 pins, the same names and order as the d44v table).  This event makes the plan
name exactly that geometry, so the kit is a build of the plan.

Changes (nothing else):
  1. pins table: cores/<module>__267.84x267.84__restjC.json, byte-equal to the kit's plan_pins.json (--kit-pins,
     checked against --expect-kit-sha).  The old d44v table is left in place.
  2. die_plan.json, every hard_cores row of the module (both q_b113 types):
     - outline 427.68 x 453.6 -> 267.84 x 267.84;
     - origin_um / track_offset_um chosen so that the clock tap stays at its absolute point.  The origin sits on the
       die lattice (grid_um) with a sub-lattice offset (|d| < 2.16, check.py), and the offset changes only by whole
       multiples of TRACK_GRAIN (0.192 = lcm of the M4/M5 0.048 and M6/M7 0.064 pitches), so every pin keeps its
       track residue.  x is exact (origin 587.52, dx -0.096, the same M5 PG alignment as before).  In y, no legal
       origin reaches the exact point, so the nearest one is taken and the receipt records the residual;
     - pins_file -> the new table;
     - clock.taps[inst].xy = origin + offset + orient(new entry).
  3. clock_entries.json: the module's entries (both types) xy_um -> NEW_ENTRY (the kit clk pin's entry: x on the 4.32
     lattice, which the generator snaps to the kit pin's M5 track 133.896; y = the kit pin's y), island +-4.32.
  4. core_macros.json: cores[<module>].outline_um -> the new outline (no macros, status unchanged).
internal_stations, buses, contents, core_conns and every other type are untouched: PIN CYCLES 0, stations 0.  The
station end points (from_um / to_um) that face this core are re-measured against the new pins and reported in the
receipt (station_hops); they are not moved here.

usage: delta_restj_c_1108.py BASE_PLAN_DIR OUT_DIR --kit-pins F [--expect-kit-sha SHA]
OUT_DIR is made by hard-linking every file of BASE_PLAN_DIR; the changed files are unlinked first and written new (a
hard-linked base file is never written through).  SHA256SUMS gets the changed / new rows."""
import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

EVENT = "RESTJ-C-1108"
MOD = "ot_hgi_sfu_split3_ctl_rest_1c"
OLD_OUTLINE, NEW_OUTLINE = [427.68, 453.6], [267.84, 267.84]
OLD_ENTRY, NEW_ENTRY = [216.0, 224.64], [133.92, 133.824]
SUFFIX = "__267.84x267.84__restjC.json"
SUBLAT = 2.16          # schema.BASE_LATTICE_UM: |track_offset| must stay below it (check.py)
TRACK_GRAIN = 0.192    # lcm(0.048, 0.064): offset steps that keep every M4..M7 pin on its track
REACH_UM = 405.0
TAG = (f"DIE-HBM-92-RESTJ {EVENT} (COORD 09:2x, HBM-HARD-6 09:10 form C): {MOD} outline "
       f"{OLD_OUTLINE[0]:g}x{OLD_OUTLINE[1]:g} -> {NEW_OUTLINE[0]:g}x{NEW_OUTLINE[1]:g} inside the same slot, vC kit pin "
       f"table, clock entry {OLD_ENTRY} -> {NEW_ENTRY}")


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def r4(v):
    return round(float(v) + 0.0, 4)


def orient_pt(o, w, h, x, y):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o or "R0"]


def solve_axis(frame, grid, old_off):
    """lattice origin + sub-lattice offset (old_off + n * TRACK_GRAIN, |offset| < SUBLAT) nearest to frame.
    -> (origin, offset, residual = origin + offset - frame)."""
    best = None
    for k in range(math.floor(frame / grid) - 1, math.ceil(frame / grid) + 2):
        o = k * grid
        nmax = int(math.ceil((SUBLAT + abs(old_off)) / TRACK_GRAIN))
        for n in range(-nmax, nmax + 1):
            off = old_off + n * TRACK_GRAIN
            if abs(off) >= SUBLAT - 1e-9:
                continue
            res = o + off - frame
            key = (round(abs(res), 6), abs(off))
            if best is None or key < best[0]:
                best = (key, r4(o), r4(off), r4(res))
    if best is None:
        raise SystemExit(f"{EVENT}: no lattice origin for frame {frame}")
    return best[1:]


def place_core(hc, tap_xy, grid):
    """new origin_um / track_offset_um for one hard_cores row so that origin + offset + orient(NEW_ENTRY) is as close
    as the lattice allows to the old tap point.  -> (origin, offset, new tap xy, residual)."""
    o = hc.get("orient", "R0")
    w1, h1 = NEW_OUTLINE
    ex, ey = orient_pt(o, w1, h1, *NEW_ENTRY)
    dx0, dy0 = hc.get("track_offset_um", [0.0, 0.0])
    ox, offx, resx = solve_axis(tap_xy[0] - ex, grid, dx0)
    oy, offy, resy = solve_axis(tap_xy[1] - ey, grid, dy0)
    new_tap = [r4(ox + offx + ex), r4(oy + offy + ey)]
    return [ox, oy], [offx, offy], new_tap, [resx, resy]


def apply_plan(P):
    """die_plan: every hard_cores row of MOD -> new outline / origin / offset / pins_file, and its clock tap.
    -> (new plan, changed rows, placements {type: dict})."""
    Q = copy.deepcopy(P)
    grid = float(Q["die"]["grid_um"])
    hits, changed, place = [], [], {}
    for tk, t in Q["partition_types"].items():
        for hc in t.get("hard_cores") or []:
            if hc.get("module") != MOD:
                continue
            hits.append(tk)
            inst = hc["inst"]
            if [r4(v) for v in hc["outline_um"]] != OLD_OUTLINE:
                raise SystemExit(f"{EVENT}: {tk}/{inst} outline {hc['outline_um']} is not the expected {OLD_OUTLINE}")
            taps = [x for x in t["clock"]["taps"] if x.get("name") == inst]
            if len(taps) != 1:
                raise SystemExit(f"{EVENT}: {tk} clock.taps needs one {inst}")
            tp = taps[0]
            o = hc.get("orient", "R0")
            dx0, dy0 = hc.get("track_offset_um", [0.0, 0.0])
            ex0, ey0 = orient_pt(o, *OLD_OUTLINE, *OLD_ENTRY)
            old_xy = [r4(hc["origin_um"][0] + dx0 + ex0), r4(hc["origin_um"][1] + dy0 + ey0)]
            if [r4(v) for v in tp["xy"]] != old_xy:
                raise SystemExit(f"{EVENT}: {tk} tap xy {tp['xy']} != origin + offset + orient(old entry) {old_xy}")
            org, off, new_xy, res = place_core(hc, old_xy, grid)
            if abs(res[0]) > 1e-6:
                raise SystemExit(f"{EVENT}: {tk}/{inst} x tap not kept exactly (residual {res[0]})")
            # placed box inside the old slot box
            b0 = (hc["origin_um"][0] + dx0, hc["origin_um"][1] + dy0)
            b1 = (org[0] + off[0], org[1] + off[1])
            if not (b0[0] - 1e-6 <= b1[0] and b1[0] + NEW_OUTLINE[0] <= b0[0] + OLD_OUTLINE[0] + 1e-6 and
                    b0[1] - 1e-6 <= b1[1] and b1[1] + NEW_OUTLINE[1] <= b0[1] + OLD_OUTLINE[1] + 1e-6):
                raise SystemExit(f"{EVENT}: {tk}/{inst} new box {b1} leaves the old slot {b0}")
            old = dict(origin_um=list(hc["origin_um"]), track_offset_um=[dx0, dy0], outline_um=list(hc["outline_um"]),
                       pins_file=hc["pins_file"], tap=old_xy)
            hc["origin_um"], hc["track_offset_um"], hc["outline_um"] = org, off, list(NEW_OUTLINE)
            hc["pins_file"] = None   # set by the caller (same new table for every row)
            hc["note"] = hc.get("note", "") + " | " + TAG
            tp["xy"] = new_xy
            tp["note"] = tp.get("note", "") + " | " + TAG
            place[tk] = dict(inst=inst, orient=o, old=old,
                             new=dict(origin_um=org, track_offset_um=off, outline_um=list(NEW_OUTLINE), tap=new_xy),
                             tap_residual_um=res, slot_box=[r4(b0[0]), r4(b0[1]), r4(b0[0] + OLD_OUTLINE[0]),
                                                            r4(b0[1] + OLD_OUTLINE[1])],
                             new_box=[r4(b1[0]), r4(b1[1]), r4(b1[0] + NEW_OUTLINE[0]), r4(b1[1] + NEW_OUTLINE[1])])
            for f in ("origin_um", "track_offset_um", "outline_um", "pins_file"):
                changed.append(dict(path=f"partition_types.{tk}.hard_cores[inst={inst}].{f}", old=old[f]))
            changed.append(dict(path=f"partition_types.{tk}.clock.taps[name={inst}].xy", old=old_xy, new=new_xy))
    if not hits:
        raise SystemExit(f"{EVENT}: no hard_cores row of {MOD}")
    Q["note"] = TAG + " <- " + Q.get("note", "")
    changed.append(dict(path="note", old="<prev chain>", new=TAG + " <- <prev chain>"))
    return Q, changed, place


def move_entries(ce, types):
    ce = copy.deepcopy(ce)
    hit = []
    for tk, blk in ce.items():
        if not isinstance(blk, dict):
            continue
        for tap, e in blk.items():
            if isinstance(e, dict) and e.get("module") == MOD:
                if [r4(v) for v in e["xy_um"]] != OLD_ENTRY:
                    raise SystemExit(f"{EVENT}: {tk}/{tap} entry {e['xy_um']} is not the expected {OLD_ENTRY}")
                e["xy_um"] = list(NEW_ENTRY)
                e["island_um"] = [r4(NEW_ENTRY[0] - 4.32), r4(NEW_ENTRY[1] - 4.32),
                                  r4(NEW_ENTRY[0] + 4.32), r4(NEW_ENTRY[1] + 4.32)]
                e["source"] = e.get("source", "") + " | " + TAG
                hit.append(tk)
    if sorted(hit) != sorted(types):
        raise SystemExit(f"{EVENT}: clock_entries rows {sorted(hit)} != hard-core types {sorted(types)}")
    return ce


def station_hops(Q, plan_dir, pins_by_name):
    """the internal_stations rows that end on this core: their recorded end point, the new pin centroid of the port
    they name (outbound rows only: 'inst.port|...'), and the end-hop length both ways (um, Manhattan)."""
    out = []
    for tk, t in Q["partition_types"].items():
        for hc in t.get("hard_cores") or []:
            if hc.get("module") != MOD:
                continue
            inst, o = hc["inst"], hc.get("orient", "R0")
            (ox, oy), (dx, dy) = hc["origin_um"], hc["track_offset_um"]
            w, h = hc["outline_um"]
            for e in t.get("internal_stations") or []:
                a, _, b = str(e.get("conn", "")).partition("|")
                if not a.startswith(inst + ".") or not e.get("regs_um"):
                    continue
                port = a.split(".", 1)[1]
                bits = [p for n, p in pins_by_name.items() if re.sub(r"\[\d+\]$", "", n) == port]
                if not bits:
                    continue
                pts = [(ox + dx + orient_pt(o, w, h, p["x"], p["y"])[0], oy + dy + orient_pt(o, w, h, p["x"], p["y"])[1])
                       for p in bits]
                reg = e["regs_um"][0]
                worst = max(abs(x - reg[0]) + abs(y - reg[1]) for x, y in pts)
                rec = e["from_um"]
                out.append(dict(type=tk, conn=e["conn"], bits=len(bits), recorded_from_um=rec,
                                recorded_hop_um=r4(abs(rec[0] - reg[0]) + abs(rec[1] - reg[1])),
                                new_worst_bit_hop_um=r4(worst), over_reach=worst > REACH_UM))
    return out


def link_tree(src, dst):
    src, dst = Path(src), Path(dst)
    if dst.exists():
        raise SystemExit(f"{EVENT}: {dst} exists (never overwrite a plan dir)")
    for root, dirs, files in os.walk(src):
        r = Path(root)
        (dst / r.relative_to(src)).mkdir(parents=True, exist_ok=True)
        for f in files:
            s = r / f
            d = dst / r.relative_to(src) / f
            if s.is_symlink():
                os.symlink(os.readlink(s), d)
            else:
                os.link(s, d)


def write_new(path, data):
    path = Path(path)
    if path.exists() or path.is_symlink():
        path.unlink()           # never write through a hard link into the base dir
    path.write_bytes(data)


def gz(data):
    return gzip.compress(data, mtime=0)


def run(base, out, kit_pins, expect_kit_sha=None):
    base, out = Path(base), Path(out)
    if base.resolve() != base.absolute() and base.is_symlink():
        raise SystemExit(f"{EVENT}: base {base} is a symlink; pass its realpath")
    kit_b = Path(kit_pins).read_bytes()
    kit_sha = sha_b(kit_b)
    if expect_kit_sha and not kit_sha.startswith(expect_kit_sha):
        raise SystemExit(f"{EVENT}: kit pins sha {kit_sha[:8]} != expected {expect_kit_sha}")
    kit = json.loads(kit_b)
    kpins = kit["pins"] if isinstance(kit, dict) else kit
    P = json.loads((base / "die_plan.json").read_bytes())
    old_pfs = sorted({h["pins_file"] for t in P["partition_types"].values() for h in t.get("hard_cores") or []
                      if h.get("module") == MOD})
    if len(old_pfs) != 1:
        raise SystemExit(f"{EVENT}: expected one pins table for {MOD}, got {old_pfs}")
    old_pf = old_pfs[0]
    pins0 = json.loads((base / old_pf).read_bytes())
    pins0 = pins0["pins"] if isinstance(pins0, dict) else pins0
    if [p["name"] for p in pins0] != [p["name"] for p in kpins]:
        raise SystemExit(f"{EVENT}: kit pin names / order differ from {old_pf}")
    w1, h1 = NEW_OUTLINE
    for p in kpins:
        if not (-1e-6 <= p["x"] <= w1 + 1e-6 and -1e-6 <= p["y"] <= h1 + 1e-6):
            raise SystemExit(f"{EVENT}: kit pin {p['name']} ({p['x']}, {p['y']}) outside {NEW_OUTLINE}")
    new_pf = str(Path(old_pf).parent / (MOD + SUFFIX))

    Q, changed, place = apply_plan(P)
    for t in Q["partition_types"].values():
        for hc in t.get("hard_cores") or []:
            if hc.get("module") == MOD:
                hc["pins_file"] = new_pf
    for c in changed:
        if c["path"].endswith(".pins_file"):
            c["new"] = new_pf
        elif c["path"].split(".")[-1] in ("origin_um", "track_offset_um", "outline_um"):
            tk = c["path"].split(".")[1]
            c["new"] = place[tk]["new"][c["path"].split(".")[-1]]
    ce1 = move_entries(json.loads((base / "clock_entries.json").read_bytes()), list(place))
    cm = json.loads((base / "core_macros.json").read_bytes())
    cme = cm["cores"][MOD]
    if [r4(v) for v in cme["outline_um"]] != OLD_OUTLINE or cme.get("macros"):
        raise SystemExit(f"{EVENT}: core_macros {MOD} is not the expected macro-free {OLD_OUTLINE} row")
    cme["outline_um"] = list(NEW_OUTLINE)
    cme["note"] = cme.get("note", "") + " | " + TAG

    link_tree(base, out)
    ce_b = (json.dumps(ce1) + "\n").encode()
    write_new(out / "clock_entries.json", ce_b)
    if (base / "clock_entries.json.gz").exists():
        write_new(out / "clock_entries.json.gz", gz(ce_b))
    # the kit's clk pin is the generator's clock pin for the new entry (gen_core_kit_hbm via clock_entry_pins)
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "physical/die_plan/hbm_arch_cores"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/die_plan"))
    import clock_entry_pins as CEP  # noqa: E402
    mv, _ = CEP.entry_pins(out / "clock_entries.json", MOD, kpins, w1, h1, CEP.m5_of(P))
    if mv:
        raise SystemExit(f"{EVENT}: the generator would move kit clock pins {mv} for entry {NEW_ENTRY}")
    write_new(out / new_pf, kit_b)
    write_new(out / (new_pf + ".gz"), gz(kit_b))
    cm_b = (json.dumps(cm, indent=1) + "\n").encode()
    write_new(out / "core_macros.json", cm_b)
    plan_b = json.dumps(Q).encode()
    write_new(out / "die_plan.json", plan_b)
    if (base / "die_plan.json.gz").exists():
        write_new(out / "die_plan.json.gz", gz(plan_b))

    clk = next(p for p in kpins if p["name"] == "clk")
    files = {}
    for f in ("die_plan.json", "die_plan.json.gz", "clock_entries.json", "clock_entries.json.gz", "core_macros.json",
              new_pf, new_pf + ".gz"):
        if (out / f).exists():
            files[f] = dict(sha_in=sha_b((base / f).read_bytes()) if (base / f).exists() else None,
                            sha_out=sha_b((out / f).read_bytes()))
    rc = dict(schema="opentallas.hbm_plan_event.v1", event=EVENT, lane="DIE-HBM-92-RESTJ", tag=TAG,
              base=str(base), out=str(out), module=MOD, changed_types=sorted(place),
              old_pins_file=old_pf, new_pins_file=new_pf, kit_pins_sha256=kit_sha, pins=len(kpins),
              kit_clk_pin=[clk["x"], clk["y"]], clock_entry=dict(old=OLD_ENTRY, new=NEW_ENTRY),
              placements=place, die_plan_rows=changed, files=files,
              station_hops=station_hops(Q, out, {p["name"]: p for p in kpins}),
              pin_cycles_added=0, internal_stations_changed=0)
    sums = out / "SHA256SUMS"
    if sums.exists():
        keep = [ln for ln in sums.read_text().splitlines() if ln.split("  ", 1)[-1] not in files]
        add = [f"{v['sha_out']}  {k}" for k, v in files.items()]
        write_new(sums, ("\n".join(keep + add) + "\n").encode())
    write_new(out / "restjC_1108_event.json", (json.dumps(rc, indent=1) + "\n").encode())
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--kit-pins", required=True, help="the vC kit plan_pins.json")
    ap.add_argument("--expect-kit-sha", default=None, help="sha256 prefix of the kit plan_pins.json (518cf1d2)")
    a = ap.parse_args(argv)
    rc = run(a.base, a.out, a.kit_pins, a.expect_kit_sha)
    print(json.dumps({k: rc[k] for k in ("event", "changed_types", "new_pins_file", "kit_pins_sha256", "placements",
                                          "files")}, indent=1))
    over = [s for s in rc["station_hops"] if s["over_reach"]]
    print(f"station end hops over {REACH_UM:g} um: {len(over)} of {len(rc['station_hops'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
