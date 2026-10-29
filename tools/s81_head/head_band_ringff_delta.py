#!/usr/bin/env python3
"""DIE-HEAD-21 HK3: re-compose the HEAD non-tile landing bands at ring_ff / band_spread / ring_place ff (plan delta).

COORD ruling 2026-10-28 (HEAD-KITS-2): every non-tile HEAD kit placement failed on the plan_hk1/hk2 landing bands.  Those
bands come from the default "padded" reserve (2636 um2 for a W=567 ring), while the mapped count-aligned ring needs
1.4166 um2 per flop (DIE-HEAD-11, measured on hd_tile u_cland_i: GPL "OT_CLAND no legal site").  The hd_tile fix
(DIE-HEAD-11/12/13/14) is main `compose(band_reserve="ring_ff", band_spread=2.0, band_ring="ff")`.  A full re-compose
would re-split the cohorts and rename types, so this delta re-runs ONLY the band sizing/placement of main
clock_landing_plan._storage_band (same function, same obstacles, same 405-um reach rule, same spread step-down) for every
band of the selected types, in the compose order (buses sorted, earlier bands are obstacles of later ones).  Order is
infrastructure first: the bands are composed against the FIXED objects (die clock islands, die clock-tree sites, ft
slots, non-SRAM hard cores such as lep_pair); SRAM macros are then re-placed around the new bands with the HK2 placer
(head_kit_macros_delta: lanes / greedy fill / nearest legal site), and reset local taps a macro blocks move as in HK2.

Per band it writes the new rect into landing_contract.bands[bus], the matching collector_local_sources[].band and the
reserved_sites_um landing_ring_bank rect (ref u_cland_<bus>).  Optional --core-move INST=X,Y moves a hard core before the
bands are composed (DIE-HEAD-21 HK3 (b): hd_lep0N g_pp[3]).
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "die_plan"))
import clock_landing_plan as CLP  # noqa: E402
import head_kit_macros_delta as D  # noqa: E402

TAG = "DIE-HEAD-21 HK3"


def is_sram(h):
    return bool(h.get("lef")) and "sram" in h.get("module", "")


def fixed_view(t):
    """type copy whose obstacles are only the fixed objects: SRAM hard cores / macro contents removed (re-placed later)."""
    v = copy.deepcopy(t)
    v["hard_cores"] = [h for h in v.get("hard_cores", []) or [] if not is_sram(h)]
    v["contents"] = [c for c in v.get("contents", []) or [] if not c.get("lef")]
    # hard cores carry a track offset; the band obstacle is the real outline
    for h in v["hard_cores"]:
        dx, dy = h.get("track_offset_um", [0, 0])
        h["origin_um"] = [h["origin_um"][0] + dx, h["origin_um"][1] + dy]
        if h.get("orient") in ("MY", "MX", "R180"):
            h["orient"] = "R0"      # mirror keeps the outline; blockages() only swaps for 90-degree turns
    return v


def has_epoch(b):
    return b.get("live_data_storage_flops") == 5 * (b["width"] + 1)


def compose_bands(t, spread=2.0, ring="ff"):
    """new bands {bus: band} for every band of type t (compose order), ring_ff reserve, spread, ring_place."""
    old = (t["clock"].get("landing_contract", {}) or {}).get("bands", {}) or {}
    v = fixed_view(t)
    CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING = "ring_ff", float(spread), ring
    try:
        used, new, fail = [], {}, {}
        for bus in sorted(old):
            ob = old[bus]
            name = bus
            if bus.startswith("monitor_"):
                name = "cland_dn_ready_" + bus.split("_", 1)[1]
            try:
                nb = CLP._storage_band(v, name, int(ob["width"]), used, has_epoch=has_epoch(ob) if not
                                       bus.startswith("monitor_") else False)
            except ValueError as e:
                fail[bus] = str(e)
                continue
            used.append(nb["rect_um"])
            for k in ("instance", "monitor_bits"):
                if k in ob:
                    nb[k] = copy.deepcopy(ob[k])
            nb["placement"] = f"{TAG}: ring_ff reserve x spread {spread}, ring_place {ring} (main _storage_band); " \
                              f"was {ob.get('rect_um')} ({ob.get('area_reserve_um2')} um2 padded)"
            new[bus] = nb
        return new, fail
    finally:
        CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING = "padded", 1.0, "all"


def apply_bands(t, new):
    lc = t["clock"]["landing_contract"]
    for bus, nb in new.items():
        lc["bands"][bus] = nb
    for s in lc.get("collector_local_sources", []) or []:
        if s.get("name") in new and "band" in s:
            s["band"] = copy.deepcopy(new[s["name"]])
    inst = {nb.get("instance", "u_cland_" + bus): nb["rect_um"] for bus, nb in new.items()}
    hit = 0
    for r in t["clock"].get("reserved_sites_um", []) or []:
        if r.get("kind") == "landing_ring_bank" and r.get("ref") in inst:
            r["rect_um"] = list(inst[r["ref"]])
            hit += 1
    return hit


def core_rects(t, sram):
    out = []
    for h in t.get("hard_cores", []) or []:
        if is_sram(h) != sram:
            continue
        dx, dy = h.get("track_offset_um", [0, 0])
        w, hh = h["outline_um"]
        if h.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        x, y = h["origin_um"][0] + dx, h["origin_um"][1] + dy
        out.append(((x, y, x + w, y + hh), h["inst"]))
    return out


def replace_srams(plan, tn, census, out_dir):
    """SRAM_TYPES: re-run the HK2 placer from scratch against the new bands; others (hd_lep0N parent SRAM): an SRAM that
    touches a keepout / a fixed core moves to the nearest legal site (HK2 lep rule)."""
    t = plan["partition_types"][tn]
    if tn in D.SRAM_TYPES and census and tn in census:
        before = {h["inst"]: list(h["origin_um"]) for h in t.get("hard_cores", []) if is_sram(h)}
        r = D.sram_delta(plan, tn, [tuple(x) for x in census[tn]], out_dir)
        after = {h["inst"]: list(h["origin_um"]) for h in t.get("hard_cores", []) if is_sram(h)}
        r["sram_moved"] = sum(1 for k in after if before.get(k) != after[k])
        return r
    W, H = t["outline_um"]
    ko = D.keepouts(plan, tn)
    fixed = core_rects(t, sram=False)
    srs = [h for h in t.get("hard_cores", []) or [] if is_sram(h)]
    rect = dict((n, r) for r, n in core_rects(t, sram=True))
    moved = []
    for h in srs:
        others = [(rect[o["inst"]], o["inst"]) for o in srs if o is not h] + fixed
        r = rect[h["inst"]]
        hit = next((k for k_r, k in ko if D.ov(r, k_r)), None) or \
            next((n for o, n in fixed if D.ov(r, o, D.XGAP, D.YGAP)), None)
        if not hit:
            continue
        w, hh = h["outline_um"]
        dx, dy = h.get("track_offset_um", [0, 0])
        got = D.place_greedy([(h["inst"], h["module"])], {h["module"]: (w, hh)}, (r[0] + w / 2, r[1] + hh / 2),
                             W, H, ko, others, step=D.G)
        if not got:
            raise SystemExit(f"{tn} {h['inst']} touches {hit} and has no legal site nearby")
        _, _, x, y = got[0]
        moved.append([h["inst"], hit, list(h["origin_um"]), [x, y]])
        h["origin_um"] = [x, y]
        h["note"] = h.get("note", "") + f"; {TAG}: moved off {hit}"
        rect[h["inst"]] = (x + dx, y + dy, x + dx + w, y + dy + hh)
    taps = D.move_reset_taps(t, [r for r, _ in fixed] + list(rect.values()))
    return dict(placed=True, sram_moved=len(moved), moved=moved, reset_taps_moved=taps)


def check_type(plan, tn):
    """hard overlaps after the delta: band x band, band x fixed core, band x island / die-clock site, core x keepout."""
    t = plan["partition_types"][tn]
    ck = t["clock"]
    bands = {b: v["rect_um"] for b, v in ck["landing_contract"]["bands"].items()}
    islands = [tuple(r) for r in ck.get("die_islands_um", []) or []]
    sites = [tuple(r["rect_um"]) for r in ck.get("reserved_sites_um", []) or [] if r.get("kind") == "die_clock_tree"]
    cores = core_rects(t, sram=False) + core_rects(t, sram=True)
    errs = []
    names = sorted(bands)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if D.ov(bands[a], bands[b], -1e-6):
                errs.append(f"band {a} x band {b}")
        for r in islands:
            if D.ov(bands[a], r, -1e-6):
                errs.append(f"band {a} x island {r}")
        for r in sites:
            if D.ov(bands[a], r, -1e-6):
                errs.append(f"band {a} x die_clock_tree {r}")
        for r, n in cores:
            if D.ov(bands[a], r, -1e-6):
                errs.append(f"band {a} x core {n}")
    for i, (r, n) in enumerate(cores):
        for r2 in islands + sites:
            if D.ov(r, r2, -1e-6):
                errs.append(f"core {n} x clock {r2}")
        for r2, n2 in cores[i + 1:]:
            if D.ov(r, r2, -1e-6):
                errs.append(f"core {n} x core {n2}")
    return errs


def run(plan, types, census, out_dir, spread=2.0, ring="ff", core_moves=(), sram_shifts=()):
    rep = {"spread": spread, "ring_place": ring, "core_moves": [], "sram_shifts": [], "types": {}}
    for tn, x0, dx in sram_shifts:      # shift a whole SRAM field (origin x >= x0) as one block: keeps its bank pattern
        hs = [h for h in plan["partition_types"][tn]["hard_cores"] if is_sram(h) and h["origin_um"][0] >= x0]
        for h in hs:
            h["origin_um"] = [round(h["origin_um"][0] + dx, 3), h["origin_um"][1]]
            h["note"] = h.get("note", "") + f"; {TAG}: SRAM field x>={x0} shifted {dx} um with its pair core"
        rep["sram_shifts"].append([tn, x0, dx, len(hs)])
    for tn, inst, xy in core_moves:
        h = next(h for h in plan["partition_types"][tn]["hard_cores"] if h["inst"] == inst)
        rep["core_moves"].append([tn, inst, list(h["origin_um"]), list(xy)])
        h["note"] = h.get("note", "") + f"; {TAG}: moved {h['origin_um']} -> {list(xy)} (E landing bands, see README)"
        h["origin_um"] = list(xy)
    for tn in types:
        t = plan["partition_types"][tn]
        old = copy.deepcopy(t["clock"]["landing_contract"]["bands"])
        new, fail = compose_bands(t, spread, ring)
        if fail:
            rep["types"][tn] = dict(fail=fail)
            continue
        nres = apply_bands(t, new)
        r = dict(bands={b: dict(old_rect=old[b]["rect_um"], old_um2=old[b]["area_reserve_um2"], rect=nb["rect_um"],
                                reserve_um2=nb["area_reserve_um2"], spread=nb.get("spread"),
                                area_um2=round((nb["rect_um"][2] - nb["rect_um"][0]) * (nb["rect_um"][3] - nb["rect_um"][1]), 1),
                                hop_um=nb["max_pin_to_band_hop_um"], ring_place=nb.get("ring_place"))
                     for b, nb in new.items()}, reserved_bank_rects_updated=nres)
        if any(is_sram(h) for h in t.get("hard_cores", []) or []):
            r["sram"] = replace_srams(plan, tn, census, out_dir)
        r["overlaps"] = check_type(plan, tn)
        rep["types"][tn] = r
    plan["note"] = (plan.get("note", "") + f" | plan_hk3 ({TAG}): landing bands re-composed ring_ff x spread {spread}, "
                    f"ring_place {ring} on {len(types)} non-tile types; SRAM re-placed around them").strip(" |")
    return rep


def render(plan, tn, rep, png):
    D.render(plan, tn, rep, png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--census", help="HK2 sram_census.json (re-place the SRAM_TYPES macros)")
    ap.add_argument("--types", help="comma list (default: every type with landing bands except hd_tile)")
    ap.add_argument("--spread", type=float, default=2.0)
    ap.add_argument("--ring", default="ff", choices=["ff", "all"])
    ap.add_argument("--core-move", action="append", default=[], help="TYPE:INST=X,Y")
    ap.add_argument("--sram-shift", action="append", default=[], help="TYPE:X0:DX shift every SRAM with origin x >= X0")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    ap.add_argument("--png-dir")
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text())
    census = json.loads(Path(a.census).read_text()) if a.census else None
    T = plan["partition_types"]
    types = a.types.split(",") if a.types else sorted(
        n for n, t in T.items() if n != "hd_tile" and (t.get("clock", {}).get("landing_contract", {}) or {}).get("bands"))
    moves = []
    for m in a.core_move:
        tn, rest = m.split(":", 1)
        inst, xy = rest.rsplit("=", 1)
        moves.append((tn, inst, [float(v) for v in xy.split(",")]))
    out = Path(a.out)
    shifts = [(m.split(":")[0], float(m.split(":")[1]), float(m.split(":")[2])) for m in a.sram_shift]
    rep = run(plan, types, census, out.parent.resolve(), a.spread, a.ring, moves, shifts)
    out.write_text(json.dumps(plan, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    if a.png_dir:
        Path(a.png_dir).mkdir(parents=True, exist_ok=True)
        for tn in types:
            render(plan, tn, rep["types"][tn].get("sram"), Path(a.png_dir) / f"{tn}.png")
    bad = 0
    for tn, r in rep["types"].items():
        if "fail" in r:
            bad += 1
            print(f"{tn}: FAIL {r['fail']}")
            continue
        bad += bool(r["overlaps"]) or (r.get("sram", {}).get("placed") is False)
        bs = " ".join(f"{b}:{v['area_um2']:.0f}um2@{v['spread']}/hop{v['hop_um']:.0f}" for b, v in r["bands"].items())
        print(f"{tn}: {bs} | sram {r.get('sram', {}).get('placed', '-')} moved {r.get('sram', {}).get('sram_moved', '-')}"
              f" | overlaps {len(r['overlaps'])} {r['overlaps'][:3]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
