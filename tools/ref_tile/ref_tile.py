#!/usr/bin/env python3
"""Reference tile / cluster flow (OWNER 2026-10-11, agent ref-flow-1011): ONE mandatory way to turn tile or cluster RTL +
a slot contract into a closed, die-placeable hard block, with every flow-mechanics pitfall of 2026-10-11 prevented by
construction (see tools/ref_tile/README.md for the pitfall -> mechanism table).

    ref_tile.py gen  SPEC.json [--area-um2 A]      write the kit physical/ref_tile/<name>/ (+ job.json) from a tile spec
    ref_tile.py job  SPEC.json [--commit C]        (re)write only the closure-loop job spec (kit must exist)
    ref_tile.py export --orfs-dir D --kit K --out V   exact abstract + TT/FF/SS libs + clock insertion + child_lint of V

The kit is plain files under physical/ref_tile/<name>/ and is routed by tools/ref_tile/ref_route.sh through the
existing ORFS path (tools/run_abi3_physical.py, the route_master.sh invocation that closed the Qwen die masters):
  kit.env          route settings (TOP, SRCS, PARAMS, FW/FH, PINS, RLAYERS, PD, hooks, macro / child views)
  clock.sdc        plain route SDC (clock on the spec's clock port, 770 ps over-constraint, 0.2 T boundary)
  signoff.sdc      833.333 ps sign-off SDC (60 / 25 ps, die-context boundary io_ref_skew.sdc)
  place.tcl        macro / hard-child placement (on the asap7 track lattice, escaped/unescaped names matched)
  pdn.tcl          layer-contract power grid (full-length PG stripes on the top layer as pins; present-master guards)
  pre_cts.tcl / pre_grt.tcl / post_drt.tcl   composed step hooks (io_ref boundary, pin-access keepout, fwd clock)
  floorplan.json   the geometry the pre-route gate checks (outline, util, macro rects, channels, pin faces)
  job.json         closure-loop spec ("ref_tile": true) -> drop into the loop intake after committing the kit
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hier_contract"))
import check_macro_track_alignment as cmta  # noqa: E402
import child_lint  # noqa: E402

KIT_ROOT = "physical/ref_tile"
QDM = "physical/qwen_die_masters"
# floorplan lattice: die / core / macro origins snap to these (um).  2.16 = lcm(row 0.27, M4 track 0.048, site 0.054)
GRID_Y = 2.16
GRID_X = 0.432          # lcm(site 0.054, M5 track 0.048)
# hard-child origin lattice (hbm-vm8 DRT-0421: tile origins on the 10.8 / 5.4 um strap pitch but 0.032 um off the
# 0.064 um M6/M7 tracks): lcm(site 54, row 270, every track pitch M1-M7 36/48/64, PG strap pitch 5400/10800) nm
CHILD_LATTICE_UM = 43.2
TRACK_LATTICE_UM = 8.64  # lcm(site, row, M1-M7 track pitches): cluster outlines snap to it
CORE_MARGIN = 2.16
CHANNEL_UM = 20.0       # macro-macro and macro-core-edge channel
PIN_EDGE_UM = 20.0      # no macro within this distance of a face that carries pins
HALO_UM = 2.16          # placement halo around every macro (hard blockage)
UTIL_LO, UTIL_HI = 0.45, 0.60
UTIL_TARGET = 0.52
FACES = {"N": "top", "S": "bottom", "E": "right", "W": "left"}


class SpecError(ValueError):
    pass


def snap_up(v: float, g: float) -> float:
    return round(math.ceil(v / g - 1e-9) * g, 4)


def snap(v: float, g: float) -> float:
    return round(round(v / g) * g, 4)


def metal(layer):
    m = re.fullmatch(r"M(\d+)", str(layer or ""))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------------------------- spec
def load_spec(path: str) -> dict:
    s = json.loads(Path(path).read_text())
    for k in ("name", "top", "sources", "clock_port", "pins"):
        if k not in s:
            raise SpecError(f"spec: missing '{k}'")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]*", s["name"]):
        raise SpecError("spec: name must be [a-z0-9_]+ (it names the kit dir and the job)")
    s.setdefault("kind", "tile")
    if s["kind"] not in ("tile", "cluster"):
        raise SpecError("spec: kind must be tile or cluster")
    s.setdefault("params", {})
    s.setdefault("macros", [])
    s.setdefault("children", [])
    s.setdefault("route", {})
    s.setdefault("reset_ports", [])
    s.setdefault("inter", [])
    if s["kind"] == "cluster" and not s["children"]:
        raise SpecError("spec: a cluster needs hard children (children[])")
    if s["kind"] == "tile" and s["children"]:
        raise SpecError("spec: a leaf tile has no hard children (use kind cluster)")
    if s["pins"] == "auto":   # inputs S, outputs N, clock + resets W (a starting plan; set real faces per the die contract)
        import textbook_lint as TL  # noqa: E402
        mods = TL.rtl_modules([(ROOT / f).read_text(errors="replace") for f in s["sources"] if (ROOT / f).exists()])
        if s["top"] not in mods:
            raise SpecError(f"pins auto: top {s['top']} not found in the sources")
        dirs = TL.module_port_dirs(mods[s["top"]])
        side = set([s["clock_port"]] + list(s["reset_ports"]))
        s["pins"] = {"S": [p for p, d in dirs.items() if d == "input" and p not in side],
                     "N": [p for p, d in dirs.items() if d != "input" and p not in side],
                     "W": [p for p in dirs if p in side]}
    bad = [f for f in s["pins"] if f not in FACES and f != "ANY"]
    if bad:
        raise SpecError(f"spec: pins faces must be N/S/E/W (or ANY: placer's choice, all faces), got {bad}")
    for f, names in s["pins"].items():
        for n in names:
            if re.search(r"\[\s*\d+\s*(:\s*\d+\s*)?\]", n):
                raise SpecError(f"spec: pin plan names a bit/range '{n}' on {f}: name ports by base name only (a 1-bit "
                                f"[0:0] port is a scalar after synthesis: PPL-0061 'Pins {{ck[0]}} not found')")
    return s


def contract_slot(s: dict) -> dict | None:
    c = s.get("contract")
    if not c:
        return None
    return child_lint.contract_slot(str(ROOT / c["file"]), c["slot"])


def view_name(view: str) -> str:
    return Path(view.rstrip("/")).name


def read_view_lef(view: str) -> dict:
    p = ROOT / view / f"{view_name(view)}.lef"
    if not p.exists():
        raise SpecError(f"view {view}: {p.relative_to(ROOT)} missing")
    return child_lint.parse_lef(p.read_text(errors="replace"), view_name(view))


def track_macro(view: str) -> dict:
    p = ROOT / view / f"{view_name(view)}.lef"
    ms = cmta.parse_lef(p.read_text(errors="replace"))
    return next((m for m in ms if m["name"] == view_name(view)), ms[0])


# --------------------------------------------------------------------------------------------- layer contract
LEGACY_KITS = json.loads((Path(__file__).resolve().parent / "legacy_layer_kits.json").read_text())["kits"]
PIN_LAYERS = {"M5": ("M4", "M5"), "M6": ("M4 M6", "M5")}     # default (IO_PLACER_H, IO_PLACER_V) per tile cap


def tile_cap(s: dict, slot: dict | None) -> tuple[str, str]:
    """(cap, why) for a leaf tile under the 2026-10-12 layer contract (results/arch/hier_contract_1011/layer_usage_1012.md):
    signals AND PG stop at layer_cap = M5 (PG stripes on M5 as pins, pins on M4/M5, parent straps M6, die signals M6/M7
    over the tile, M8/M9 die power + global); M6 only by a die-lead exception (spec or slot layer_cap M6 + layer_cap_grant);
    kits generated before the cut (legacy_layer_kits.json) keep their old PG layer (M6/M7, signals <= M6)."""
    slot = slot or {}
    cap = s.get("layer_cap") or slot.get("layer_cap")
    if cap is None and s["name"] in LEGACY_KITS:
        return LEGACY_KITS[s["name"]], "legacy"
    if cap is None and s.get("pg_layer") not in (None, "M5"):
        raise SpecError(f"layer contract: a NEW leaf tile caps signals and PG at M5 (coordinator 2026-10-12): drop "
                        f"pg_layer {s['pg_layer']}, or set layer_cap M6 with the die lead's layer_cap_grant")
    cap = cap or "M5"
    if cap == "M6":
        if not (s.get("layer_cap_grant") or slot.get("layer_cap_grant")):
            raise SpecError("layer contract: layer_cap M6 is a per-tile exception the die lead grants (pin-dense edge "
                            "relays / stations): give layer_cap_grant '<lead>: <reason>' in the spec or the contract slot")
        return "M6", "granted"
    if cap != "M5":
        raise SpecError(f"layer contract: a leaf tile's layer_cap is M5 (default) or M6 (granted exception), not {cap}")
    return "M5", "contract"


def layer_contract(s: dict, slot: dict | None) -> dict:
    """leaf tile: signals AND PG <= layer_cap (M5 default, M6 granted), PG = full-length stripes on the cap layer as pins,
    parent strap = cap + 1; legacy kits: signals M2-M6, PG M6 or M7.
    cluster: children's PG layer L <= M6 each strapped from L+1; cluster PG = M7 stripes as pins; signals M2-M7."""
    pg = s.get("pg_layer") or (slot or {}).get("pg_layer")
    out = {"children": {}}
    if s["kind"] == "tile":
        cap, why = tile_cap(s, slot)
        if why == "legacy":
            out.update(pg_layer=cap, rlayers=("M2", "M6"), strap_layer=f"M{metal(cap) + 1}", layer_cap=cap,
                       cap_basis="legacy kit (pre-2026-10-12 contract; re-route at M5 per m5_reroute_priority.json)")
        else:
            out.update(pg_layer=cap, rlayers=("M2", cap), strap_layer=f"M{metal(cap) + 1}", layer_cap=cap, cap_basis=why)
        if slot:
            ok = {slot.get("layer_cap") or slot.get("pg_layer"), slot.get("view_cap") if why == "legacy" else None}
            if out["pg_layer"] not in ok:
                raise SpecError(f"layer contract: tile cap/PG {out['pg_layer']} != contract slot layer_cap "
                                f"{slot.get('layer_cap') or slot.get('pg_layer')}")
        return out
    for ch in s["children"]:
        m = read_view_lef(ch["view"])
        top = child_lint.check_pg(m)["top_layer"]
        if metal(top) is None or metal(top) > 6:
            raise SpecError(f"layer contract: child {view_name(ch['view'])} PG top layer {top}: a cluster child must "
                            f"expose PG on M5/M6 (the cluster straps one layer up on M7; M8/M9 are the die's)")
        out["children"][view_name(ch["view"])] = top
    pg = pg or "M7"
    if pg != "M7":
        raise SpecError("layer contract: a cluster's PG layer is M7 (straps over M5/M6 children; M8/M9 die only)")
    out.update(pg_layer="M7", rlayers=("M2", s.get("signal_max_layer", "M7")), strap_layer="M8")
    if slot and slot.get("pg_layer") and slot["pg_layer"] != out["pg_layer"]:
        raise SpecError(f"layer contract: spec PG {out['pg_layer']} != contract slot PG {slot['pg_layer']}")
    return out


def pin_layers(s: dict, lc: dict) -> tuple[str, str]:
    """(IO_PLACER_H, IO_PLACER_V) for the kit; every pin layer must be <= the tile's cap (no pin on the parent strap)."""
    r = s["route"]
    cap = lc.get("layer_cap")
    dh, dv = PIN_LAYERS.get(cap if cap in PIN_LAYERS else "M6")
    if lc.get("cap_basis", "").startswith("legacy"):
        dh, dv = PIN_LAYERS["M6"]
    h, v = r.get("pin_h", dh), r.get("pin_v", dv)
    if s["kind"] == "tile":
        pb = r.get("pin_balance") or {}
        used = (h + " " + v + " " + pb.get("h", "") + " " + pb.get("v", "")).split()
        over = sorted({x for x in used if (metal(x) or 0) > metal(lc["rlayers"][1])})
        if over:
            raise SpecError(f"layer contract: pin layers {over} above the tile's signal cap {lc['rlayers'][1]} "
                            f"(pins on M4/M5 under the M5 cap; the parent reaches them from M6)")
    return h, v


PDN_HEAD = """# generated by tools/ref_tile/ref_tile.py ({name}, {kind}): layer contract PG top {pg} as full-length stripes = the
# block's power pins; {note}
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDDPE$}}
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDDCE$}}
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSSE$}}
global_connect
set_voltage_domain -name {{CORE}} -power {{VDD}} -ground {{VSS}}
define_pdn_grid -name {{top}} -voltage_domains {{CORE}} -pins {{{pg}}}
add_pdn_stripe -grid {{top}} -layer {{M1}} -width {{0.018}} -pitch {{0.54}} -offset {{0}} -followpins
add_pdn_stripe -grid {{top}} -layer {{M2}} -width {{0.018}} -pitch {{0.54}} -offset {{0}} -followpins
add_pdn_stripe -grid {{top}} -layer {{M5}} -width {{0.12}} -spacing {{0.072}} -pitch {{5.4}} -offset {{0.300}}
"""
# Macro grids exist ONLY for masters present in the block (PDN-0217 'No grid found with name' otherwise: a macro grid
# with no matching instance is never created and its add_pdn_connect aborts).
PDN_GUARD = """proc ot_ref_has_master {pats} {
  foreach inst [[ord::get_db_block] getInsts] {
    set m [[$inst getMaster] getName]
    foreach p $pats { if {[string match $p $m]} { return 1 } }
  }
  return 0
}
proc ot_ref_present {cells} { set out {}; foreach c $cells { if {[ot_ref_has_master $c]} { lappend out $c } }; return $out }
"""


def gen_pdn(s: dict, lc: dict) -> str:
    pg = lc["pg_layer"]
    if s["kind"] == "tile" and pg == "M5":
        note = ("layer cap M5: signals M2-M5 route around the M5 stripes (pins); the parent straps M6, die signals use "
                "M6/M7 over the tile (coordinator 2026-10-12).")
        body = "add_pdn_connect -grid {top} -layers {M1 M2}\nadd_pdn_connect -grid {top} -layers {M2 M5}\n"
    elif s["kind"] == "tile" and pg == "M6":
        note = "signals M2-M6 route around the M6 stripes; the parent straps M7 (recipe pdn_qkvd_tile_m6.tcl)."
        # route.pg_pitch (5.4 or 10.8, both on the strap lattice): short tiles (< ~3 pitches tall) need 5.4 so the M6
        # PG pins span >= 50% of the height (child_lint (b); dsfd_vm_fsr r4 at 25.92 um: 2 stripes per net = 42%)
        pp = float(s.get("route", {}).get("pg_pitch", 10.8))
        assert pp in (5.4, 10.8), "route.pg_pitch must be 5.4 or 10.8"
        body = (f"add_pdn_stripe -grid {{top}} -layer {{M6}} -width {{0.288}} -spacing {{0.096}} -pitch {{{pp}}} -offset {{2.0}}\n"
                "add_pdn_connect -grid {top} -layers {M1 M2}\nadd_pdn_connect -grid {top} -layers {M2 M5}\n"
                "add_pdn_connect -grid {top} -layers {M5 M6}\n")
    elif s["kind"] == "tile":
        note = "signals stop at M6 (RLAYERS M2 M6), M7 = PG stripes only; the parent straps M8 (recipe g8p/pdn_gtile.tcl)."
        body = ("add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}\n"
                "add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}\n"
                "add_pdn_connect -grid {top} -layers {M1 M2}\nadd_pdn_connect -grid {top} -layers {M2 M5}\n"
                "add_pdn_connect -grid {top} -layers {M5 M6}\nadd_pdn_connect -grid {top} -layers {M6 M7}\n")
    else:
        note = ("cluster: M5/M6 stripes + M7 stripes (pins); each hard child strapped from the layer above its own PG pins "
                "(recipe physical/hgi_idx_hier/pdn_hier.tcl @8d848821f).")
        body = ("add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}\n"
                "add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}\n"
                "add_pdn_connect -grid {top} -layers {M1 M2}\nadd_pdn_connect -grid {top} -layers {M2 M5}\n"
                "add_pdn_connect -grid {top} -layers {M5 M6}\nadd_pdn_connect -grid {top} -layers {M6 M7}\n")
    t = PDN_HEAD.format(name=s["name"], kind=s["kind"], pg=pg, note=note) + body + PDN_GUARD
    by_layer: dict = {}
    for cell, top in lc["children"].items():
        by_layer.setdefault(top, []).append(cell)
    for top, cells in sorted(by_layer.items()):
        L = metal(top)
        t += (f"set ot_c [ot_ref_present {{{' '.join(sorted(cells))}}}]\n"
              f"if {{[llength $ot_c]}} {{\n"
              f"  define_pdn_grid -name {{hard_{top.lower()}}} -voltage_domains {{CORE}} -macro -cells $ot_c "
              f"-orient {{R0 R180 MX MY}} -halo {{2.0 2.0 2.0 2.0}}\n"
              f"  add_pdn_connect -grid {{hard_{top.lower()}}} -layers {{M{L} M{L + 1}}}\n}}\n")
    srams = sorted({view_name(m["view"]) for m in s["macros"]})
    if srams:
        t += (f"set ot_s [ot_ref_present {{{' '.join(srams)}}}]\n"
              "if {[llength $ot_s]} {\n"
              "  define_pdn_grid -name {sram} -voltage_domains {CORE} -macro -cells $ot_s -orient {R0 R180 MX MY} "
              "-halo {2.0 2.0 2.0 2.0}\n  add_pdn_connect -grid {sram} -layers {M4 M5}\n}\n")
    return t


# --------------------------------------------------------------------------------------------- floorplan
def outline(s: dict, slot: dict | None, area_um2: float | None, blocks: list) -> tuple[float, float, str]:
    if slot:
        return float(slot["outline"]["w"]), float(slot["outline"]["h"]), f"contract {s['contract']['slot']}"
    og = TRACK_LATTICE_UM if s["kind"] == "cluster" else GRID_Y
    if s.get("outline"):
        o = s["outline"]
        return snap_up(float(o["w"]), og), snap_up(float(o["h"]), og), "spec outline"
    area = area_um2 or s.get("std_area_um2")
    if not area:
        raise SpecError("outline: give outline {w,h}, a contract slot, or std_area_um2 / --area-um2 (the synthesis "
                        "smoke of pre_route_gate.py --remote reports it) with util (default 0.52)")
    util = float(s.get("util", UTIL_TARGET))
    mac = sum((b["w"] + 2 * HALO_UM) * (b["h"] + 2 * HALO_UM) for b in blocks)
    core = (area + mac) / util
    ar = float(s.get("aspect", 1.0))                   # w / h
    w = math.sqrt(core * ar) + 2 * CORE_MARGIN
    h = core / (w - 2 * CORE_MARGIN) + 2 * CORE_MARGIN
    for b in blocks:                                    # every macro must fit with channels on both sides
        w = max(w, b["w"] + 2 * CHANNEL_UM + 2 * CORE_MARGIN)
        h = max(h, b["h"] + 2 * CHANNEL_UM + 2 * CORE_MARGIN)
    return snap_up(w, og), snap_up(h, og), f"util {util} of std {area:.0f} + macros {mac:.0f} um2"


def blocks_of(s: dict) -> list:
    out = []
    for kind, items in (("macro", s["macros"]), ("child", s["children"])):
        for i, it in enumerate(items):
            m = read_view_lef(it["view"])
            out.append({"kind": kind, "view": it["view"], "master": m["name"], "inst": it.get("inst"),
                        "w": m["W"], "h": m["H"], "at": it.get("at"), "orient": it.get("orient", "R0"),
                        "count": int(it.get("count", 1))})
    # expand counts (identical instances placed in a row)
    exp = []
    for b in out:
        for k in range(b["count"]):
            c = dict(b)
            c["idx"] = k
            if b["count"] > 1 and b.get("at"):
                raise SpecError(f"{b['master']}: count > 1 with a fixed 'at' -- give one entry per instance")
            exp.append(c)
    return exp


def on_track(b: dict, x: float, y: float) -> tuple[float, float, int]:
    """nearest origin to (x, y) that puts the block's signal pins on the asap7 tracks (DRT-0255 / 0418 / 0419)"""
    if b.get("_tm") is None:
        b["_tm"] = track_macro(b["view"])
    tm = b["_tm"]
    ox, oy = round(x * 1000), round(y * 1000)
    import macro_grid_lint as mgl  # noqa: E402
    off, dx, dy = mgl.best_shift(tm, b["orient"], ox, oy)
    if dx or dy:
        # keep the shift and stay on the row lattice in y where it costs nothing
        ox, oy = ox + dx, oy + dy
    return ox / 1000.0, oy / 1000.0, off


def place_blocks(s: dict, W: float, H: float, blocks: list) -> list:
    """explicit 'at' wins; the rest go in rows away from the pin faces, >= CHANNEL_UM apart and from the core edge"""
    pin_faces = {f for f, v in s["pins"].items() if v}
    if pin_faces & {"ANY"}:
        pin_faces = set(FACES)
    x0c, y0c, x1c, y1c = CORE_MARGIN, CORE_MARGIN, W - CORE_MARGIN, H - CORE_MARGIN
    lo_x = x0c + max(CHANNEL_UM, PIN_EDGE_UM if "W" in pin_faces else 0)
    hi_x = x1c - max(CHANNEL_UM, PIN_EDGE_UM if "E" in pin_faces else 0)
    lo_y = y0c + max(CHANNEL_UM, PIN_EDGE_UM if "S" in pin_faces else 0)
    hi_y = y1c - max(CHANNEL_UM, PIN_EDGE_UM if "N" in pin_faces else 0)
    def lat(b):
        return (float(s.get("child_lattice_um", CHILD_LATTICE_UM)),) * 2 if b["kind"] == "child" else (GRID_X, GRID_Y)
    auto = [b for b in blocks if not b.get("at")]
    for b in blocks:
        if b.get("at"):
            b["_xy"] = (float(b["at"][0]), float(b["at"][1]))
    if auto:
        gx = max(lat(b)[0] for b in auto)
        gy = max(lat(b)[1] for b in auto)
        x0, y = snap_up(lo_x, gx), snap_up(lo_y, gy)
        x, row_h = x0, 0.0
        for b in auto:      # lattice-aware row packing: every channel >= CHANNEL_UM AFTER snapping
            if x + b["w"] > hi_x + 1e-6 and x > x0:
                x, y, row_h = x0, snap_up(y + row_h + CHANNEL_UM, gy), 0.0
            b["_xy"] = (x, y)
            x = snap_up(x + b["w"] + CHANNEL_UM, gx)
            row_h = max(row_h, b["h"])
        bx1 = max(b["_xy"][0] + b["w"] for b in auto)
        by1 = max(b["_xy"][1] + b["h"] for b in auto)
        sx = math.floor(max(0.0, (hi_x - bx1) / 2) / gx) * gx
        sy = math.floor(max(0.0, (hi_y - by1) / 2) / gy) * gy
        for b in auto:      # centre the array in the free window, on the lattice
            b["_xy"] = (round(b["_xy"][0] + sx, 4), round(b["_xy"][1] + sy, 4))
    for b in blocks:
        if b["kind"] == "child":
            # a hard tile built on the same lattice: its origin on the common lattice keeps every layer's pins on track
            g = float(s.get("child_lattice_um", CHILD_LATTICE_UM))
            bx, by = snap(b["_xy"][0], g), snap(b["_xy"][1], g)
            r = cmta.check_placement(track_macro(b["view"]) if b.get("_tm") is None else b["_tm"], b["orient"],
                                     round(bx * 1000), round(by * 1000))
            off = sum(v["offtrack"] for v in r["layers"].values())
            if off:   # off-lattice view (not built by this flow): nearest on-track origin instead
                bx, by, off = on_track(b, bx, by)
        else:
            bx, by = snap(b["_xy"][0], GRID_X), snap(b["_xy"][1], GRID_Y)
            bx, by, off = on_track(b, bx, by)
        b.update(x=bx, y=by, offtrack=off)
    return blocks


def floorplan_checks(s: dict, W: float, H: float, blocks: list, std_area: float | None) -> list:
    """(severity, check, message, fix) -- the geometry part of the pre-route gate, also run at gen time"""
    out = []
    pin_faces = {f for f, v in s["pins"].items() if v}
    if "ANY" in pin_faces:
        pin_faces = set(FACES)
    x0c, y0c, x1c, y1c = CORE_MARGIN, CORE_MARGIN, W - CORE_MARGIN, H - CORE_MARGIN
    for b in blocks:
        bx0, by0, bx1, by1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
        nm = f"{b['master']}#{b['idx']}"
        if bx0 < x0c - 1e-6 or by0 < y0c - 1e-6 or bx1 > x1c + 1e-6 or by1 > y1c + 1e-6:
            out.append(("FAIL", "macro_outside", f"{nm} at ({bx0},{by0}) leaves the core", "enlarge the outline"))
        for f, d in (("W", bx0 - x0c), ("E", x1c - bx1), ("S", by0 - y0c), ("N", y1c - by1)):
            need = PIN_EDGE_UM if f in pin_faces else CHANNEL_UM
            if d < need - 1e-6:
                out.append(("FAIL", "macro_edge", f"{nm} {d:.1f} um from the {f} core edge (< {need:.0f} um"
                            + (", a pin face" if f in pin_faces else "") + ")",
                            "move the macro inward / to a face without pins (sliver + pin-access blockage)"))
        if b.get("offtrack"):
            out.append(("FAIL", "macro_grid", f"{nm}: {b['offtrack']} signal pins off the asap7 tracks (M1-M9, each "
                        f"layer's own pitch / offset) at its origin",
                        "no origin fixes it: the view's LEF is off-lattice -- re-export the child on the track grid"))
        if b["kind"] == "child" and any(abs(v / CHILD_LATTICE_UM - round(v / CHILD_LATTICE_UM)) > 1e-6 for v in (b["x"], b["y"])):
            out.append(("WARN", "macro_grid", f"{nm}: origin ({b['x']}, {b['y']}) off the {CHILD_LATTICE_UM} um child "
                        "lattice (lcm of site, row, M1-M7 tracks, strap pitch)", "build the child on the common lattice"))
    for i, a in enumerate(blocks):
        for b in blocks[i + 1:]:
            gx = max(b["x"] - (a["x"] + a["w"]), a["x"] - (b["x"] + b["w"]))
            gy = max(b["y"] - (a["y"] + a["h"]), a["y"] - (b["y"] + b["h"]))
            gap = max(gx, gy)
            if gap < CHANNEL_UM - 1e-6:
                out.append(("FAIL", "channel", f"{a['master']}#{a['idx']} / {b['master']}#{b['idx']} channel {gap:.1f} um "
                            f"(< {CHANNEL_UM:.0f} um)", "spread the macros or abut them deliberately (gap 0, no cells)"))
    core = (x1c - x0c) * (y1c - y0c)
    mac = sum(b["w"] * b["h"] for b in blocks)
    if std_area:
        u = (std_area + mac) / core
        if not (UTIL_LO <= u <= UTIL_HI + 0.05):
            out.append(("FAIL" if u > 0.70 else "WARN", "util",
                        f"utilisation {u:.0%} outside {UTIL_LO:.0%}-{UTIL_HI:.0%} (std {std_area:.0f} + macro {mac:.0f} "
                        f"in core {core:.0f} um2)", "resize the outline to util 0.50-0.55 (drop 'outline', set util)"))
    long_side = max(W, H)
    if long_side > 600 and s["kind"] == "tile":
        out.append(("WARN", "clock_span", f"{W} x {H} um: one clock root over > 600 um",
                    "split into hardened sub-tiles with local roots (kind cluster) or keep the sink count small"))
    return out


# --------------------------------------------------------------------------------------------- generation
def pin_regex(names) -> str:
    return "^(" + "|".join(re.escape(n) for n in names) + r")(\[|$)"


def kit_dir(s: dict) -> str:
    return f"{KIT_ROOT}/{s['name']}"


def gen_place(s: dict, blocks: list) -> str:
    lines = [f"# generated by tools/ref_tile/ref_tile.py ({s['name']}): fixed macro / hard-child placement on the asap7",
             "# track lattice (origins from check_macro_track_alignment best shift), >= 20 um channels, no macro at a pin",
             "# face.  Instance names are matched with backslashes stripped on BOTH sides (the db holds g\\[1\\].u or g[1].u",
             "# depending on the stage).  A spec instance pattern (glob) picks among same-master instances; else dictionary",
             "# order.  The halo is MACRO_PLACE_HALO (rows cut by tapcell); NO extra placement blockage: a hard blockage over",
             "# the halo covers the row-end endcaps and fails detailed placement (DPL-0004 / DPL-0033, ref gate 2026-10-11).",
             "set b [ord::get_db_block]", "set dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
             "proc ot_ref_strip {n} { return [string map {\\\\ {}} $n] }",
             "set ot_ref_by {}",
             "set ot_ref_l {}",
             "foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { lappend ot_ref_l [list [ot_ref_strip [$i getName]] $i] } }",
             "foreach p [lsort -dictionary -index 0 $ot_ref_l] {",
             "  set i [lindex $p 1]; dict lappend ot_ref_by [[$i getMaster] getName] $i", "}",
             "set ot_ref_used {}",
             "proc ot_ref_pick {by master pat} {",
             "  upvar ot_ref_used used",
             "  if {![dict exists $by $master]} { error \"ref_tile place: no instance of $master in the netlist\" }",
             "  foreach i [dict get $by $master] {",
             "    set n [ot_ref_strip [$i getName]]",
             "    if {[lsearch -exact $used $n] >= 0} continue",
             "    if {$pat ne \"\" && ![string match [ot_ref_strip $pat] $n]} continue",
             "    lappend used $n; return $i", "  }",
             "  error \"ref_tile place: no unplaced instance of $master matching '$pat'\"", "}",
             "set ot_ref_n 0"]
    for bl in blocks:
        lines.append(f"set i [ot_ref_pick $ot_ref_by {bl['master']} {{{bl.get('inst') or ''}}}]")
        lines.append(f"$i setOrient {bl['orient']}; $i setLocation [expr {{round({bl['x']} * $dbu)}}] "
                     f"[expr {{round({bl['y']} * $dbu)}}]; $i setPlacementStatus FIRM")
        lines.append(f"puts \"REF_TILE place: [$i getName] {bl['master']} at {bl['x']} {bl['y']} {bl['orient']}\"")
    lines.append("set nb 0; dict for {k v} $ot_ref_by { incr nb [llength $v] }")
    lines.append(f"if {{$nb != {len(blocks)}}} {{ error \"ref_tile place: expected {len(blocks)} macros, netlist has $nb\" }}")
    return "\n".join(lines) + "\n"


def gen_sdc(s: dict, period_ps: float) -> str:
    io = s.get("io_budget", {})
    fin, fout = float(io.get("in", 0.2)), float(io.get("out", 0.2))
    return (f"# generated by tools/ref_tile/ref_tile.py ({s['name']}): route SDC (over-constrained {period_ps} ps; sign-off\n"
            f"# 833.333 in signoff.sdc), 60 / 25 ps uncertainty, boundary {fin} / {fout} x 833.333 ps outside the block.\n"
            f"# After CTS the hooks re-reference the boundary to the propagated tree (qwen_die_masters/io_ref_skew.sdc).\n"
            f"create_clock -name core_clk -period {period_ps} [get_ports {s['clock_port']}]\n"
            "set_clock_uncertainty -setup 60 [all_clocks]\nset_clock_uncertainty -hold 25 [all_clocks]\n"
            f"set_input_delay {833.333 * fin:.3f} -clock core_clk [all_inputs -no_clocks]\n"
            f"set_output_delay {833.333 * fout:.3f} -clock core_clk [all_outputs]\n"
            "set_max_fanout 32 [current_design]\nset_load 80 [all_outputs]\n"
            "set_input_transition 150 [all_inputs -no_clocks]\nset_max_transition 260 [current_design]\n"
            + sdc_extra(s))


def sdc_extra(s: dict) -> str:
    """spec 'sdc_extra': repo SDC files appended (inlined) to clock.sdc and signoff.sdc -- a second clock domain
    (e.g. a CDC adapter's controller clock) after core_clk exists"""
    out = ""
    for f in s.get("sdc_extra", []):
        out += f"# ---- sdc_extra {f}\n" + (ROOT / f).read_text()
    return out


def gen_signoff(s: dict, refglob: str, inter: str) -> str:
    io = (ROOT / QDM / "io_ref_skew.sdc").read_text()
    return (f"# {s['name']}: sign-off at 833.333 ps (generated by tools/ref_tile/ref_tile.py; same form as\n"
            f"# {QDM}/jobs/signoff_sdc.py): clock re-created at the real period, propagated, 60 / 25 ps uncertainty,\n"
            f"# die-context boundary io_ref_skew.sdc with this block's REFGLOB / INTER bound.\n"
            f"create_clock -name core_clk -period 833.333 [get_ports {s['clock_port']}]\n"
            "set_propagated_clock [all_clocks]\nset_clock_uncertainty -setup 60 [all_clocks]\n"
            "set_clock_uncertainty -hold 25 [all_clocks]\nset ::env(OT_IO_SKEW) 90\nset ::env(OT_IO_HOLD_SKEW) 50\n"
            f"set ::env(OT_REF_GLOB) {{{refglob}}}\nset ::env(OT_IO_INTER) {{{inter}}}\nset ::env(OT_IO_SKEW_INTER) 150\n"
            + io + sdc_extra(s))


def child_insertions(s: dict) -> dict:
    """{child master: clock-pin insertion ps} from each hard child's TT lib (max_clock_tree_path), 0 when absent"""
    out = {}
    for ch in s["children"]:
        v = ch["view"]
        p = ROOT / v / f"{view_name(v)}_tt.lib"
        ins = child_lint.clock_insertion(p.read_text(errors="replace")) if p.exists() else {}
        vals = [x["max_ps"] for x in ins.values() if x]
        out[view_name(v)] = round(max(vals), 1) if vals else 0.0
    return out


SPINE_INS = """# ref_tile cluster clock: the pre-placed balanced clock SPINE (physical/common_flow/clock_spine.tcl, el1011-hbm-attn
# c11a6e02a: attention halves leaf spread 1,634 -> 24 ps; idx w8 cluster 518 ps skew) replaces TritonCTS for the cluster
# clock.  Leaf target = arrival at the sink pin PLUS the hard child's own clock insertion (its TT lib max_clock_tree_path),
# so the spine balances the flops INSIDE the children against the cluster's own flops (CLOCK LATENCY ACROSS THE HIERARCHY).
set ::ot_ref_child_ins [dict create {ins}]
proc ot_sp_leaf_arrivals {{}} {{
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  set a [dict create]
  dict for {{n net}} $::ot_sp_leafnet {{
    set v 0.0
    foreach pin [get_pins -quiet -of_objects [get_nets -quiet [$net getName]] -filter "direction==input"] {{
      set x [get_property $pin arrival_max_rise]
      if {{$x eq "" || $x eq "INF" || $x eq "-INF"}} continue
      set c [get_cells -quiet -of_objects $pin]
      if {{[llength $c]}} {{
        set m [get_property $c ref_name]
        if {{[dict exists $::ot_ref_child_ins $m]}} {{ set x [expr {{$x + [dict get $::ot_ref_child_ins $m]}}] }}
      }}
      if {{$x > $v}} {{ set v $x }}
    }}
    dict set a $n $v
  }}
  return $a
}}
puts "REF_TILE spine: child insertion targets $::ot_ref_child_ins"
"""


HDLY_TCL = "physical/qwen_die_masters/hdly_dont_touch.tcl"


def gen_hooks(s: dict, kd: str) -> dict:
    fwd = bool(s.get("forwarded_clock"))
    spine = s["kind"] == "cluster" and s.get("clock", "spine") == "spine"
    pre_cts = ["# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl)"
               + (" + forwarded-clock subtree kept (hbm_w2_rb_station forwarded_subtree.tcl)" if fwd else "")
               + ("; cluster: balanced clock spine with child-insertion leaf targets (sourced FIRST, so the io_ref wrapper"
                  " below wraps it)" if spine else "")]
    files = {}
    if spine:
        pre_cts += ["source /src/physical/common_flow/clock_spine.tcl", f"source /src/{kd}/spine_ins.tcl"]
        ins = child_insertions(s)
        files["spine_ins.tcl"] = SPINE_INS.format(ins=" ".join(f"{k} {v}" for k, v in sorted(ins.items())))
    pre_cts.append(f"source /src/{QDM}/pre_cts_skew.tcl")
    if fwd:
        pre_cts.append("source /src/physical/hbm_w2_rb_station_20261006/forwarded_subtree.tcl")
    pre_grt = ["# ref_tile PRE_GLOBAL_ROUTE: io_ref boundary + pin-access keepout (the layer ABOVE the outer face-pin",
               "# column; created here, removed by post_drt.tcl, so the abstract carries only real metal: DRT-0073 at the parent)",
               f"source /src/{QDM}/pre_ref_skew.tcl",
               "source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl"]
    post_drt = ["# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC",
                "source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl",
                f"source /src/{QDM}/post_plain.tcl"]
    return {"pre_cts.tcl": "\n".join(pre_cts) + "\n", "pre_grt.tcl": "\n".join(pre_grt) + "\n",
            "post_drt.tcl": "\n".join(post_drt) + "\n", **files}


def shq(v: str) -> str:
    return "'" + v.replace("'", "'\"'\"'") + "'"


def gen_env(s: dict, kd: str, W: float, H: float, lc: dict, blocks: list) -> str:
    r = s["route"]
    ph, pv = pin_layers(s, lc)
    srcs = " ".join(s["sources"])
    params = " ".join(f"--param {k}={v}" for k, v in s["params"].items())
    # optional "pin_ranges" {port: [lo_um, hi_um]} (along the face, from its left / bottom end): one region per ranged port so
    # a face tile's bus pins sit at the end facing their die neighbour and >= the given margin off the tile corners
    # ([vm8cp] corner-pin DRT-0255 class); ports without a range keep the whole face.
    rng = s.get("pin_ranges") or {}
    regs = []
    for f, v in s["pins"].items():
        if not v or f == "ANY":
            continue
        plain = [n for n in v if n not in rng]
        if plain:
            regs.append(pin_regex(plain) + "=" + FACES[f])
        for n in v:
            if n in rng:
                lo, hi = rng[n]
                regs.append(pin_regex([n]) + "=" + FACES[f] + f":{float(lo):g}-{float(hi):g}")
    pins = " ".join(f"--pin-region {shq(r)}" for r in regs)
    views = sorted({b["view"] for b in blocks})
    extra = ["--orfs-var ADDER_MAP_FILE=", f"--orfs-var PDN_TCL=/src/{kd}/pdn.tcl",
             f"--orfs-var OT_PK_FRAC={s.get('pin_access', {}).get('frac', 0.5)}",
             # keep only the layer ABOVE each face pin clear (what the parent needs and child_lint (f) checks); also
             # blocking the layer below took the tile's own M3 access to a dense M4 face (hfd_hc 239-268 DRC, c95527ec0)
             f"--orfs-var OT_PK_ABOVE_ONLY={0 if s.get('pin_access', {}).get('both_sides') else 1}"]
    if blocks:
        extra.append(f"--orfs-var MACRO_PLACEMENT_TCL=/src/{kd}/place.tcl")
        extra += [f"--macro-view {view_name(v)}={v}" for v in views]
        h = float(s["route"].get("macro_halo_um", HALO_UM))
        extra.append(f"--macro-place-halo {h} {h}")
    if s["kind"] == "cluster" and s.get("clock", "spine") == "spine":
        extra.append(f"--orfs-var OT_SPINE_PORT={s['clock_port']}")
    # spec "defines": RTL defines the top's synthesis needs (e.g. the hardened-child body selected by `ifdef); written after
    # run_abi3's own "VERILOG_DEFINES = -DSYNTHESIS", so it keeps -DSYNTHESIS explicitly (the lint bench uses the same set).
    if s.get("defines"):
        extra.append("--orfs-var " + shq("VERILOG_DEFINES=" + " ".join(["-DSYNTHESIS"] + [f"-D{d}" for d in s["defines"]])))
    # spec "io_tcl" (el1011-hbm-smh): a repo place_pin file for a tile whose pins must sit at exact abutment tracks; it
    # replaces the face-region IO_CONSTRAINTS (the face groups in "pins" still drive the gate's checks and the keepout).
    if s.get("io_tcl"):
        extra.append(f"--orfs-var IO_CONSTRAINTS=/src/{s['io_tcl']}")
    # spec "orfs_vars" {NAME: value}: extra ORFS variables the RTL / structure needs; a value that is a repo file path
    # (el1011-hbm-smh POST_TAPCELL hooks) is passed as /src/<path>, anything else verbatim
    for k, v in sorted(s.get("orfs_vars", {}).items()):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", k) or re.search(r"\s", str(v)):
            raise SpecError(f"spec: orfs_vars {k}={v!r}: NAME=[A-Z0-9_]+, value without whitespace")
        vv = f"/src/{v}" if (not str(v).startswith("/") and os.path.isfile(str(v))) else v
        if k == "POST_TAPCELL_TCL" and s.get("io_tcl"):
            # io_tcl + a POST_TAPCELL pin-flop hook: ORFS sources IO_CONSTRAINTS only at 3_2_place_iop, so the hook saw
            # unplaced ports and FIRM-placed every boundary flop on the W face (smh_pt_e_ref_p40-lf: W 7410 / E 0, both
            # register stages + 6,860 hold buffers in one 24-um strip, GRT stuck at ~3,000 markers; the closed hand kit
            # placed pins at floorplan: W 3705 / E 3705).  The kit's post_tapcell.tcl places the exact pins first.
            vv = f"/src/{kd}/post_tapcell.tcl"
        extra.append(f"--orfs-var {k}={vv}")
    if s["route"].get("hold_delay"):
        # deterministic hold fix by construction (owner 10-10): the RTL's *u_hdly_* HB delay cells are dont_touch'ed at
        # PRE_FLOORPLAN so remove_buffers / repair passes keep them (tputx-cpf hgi_seq v2.3)
        extra.append(f"--step-tcl PRE_FLOORPLAN={HDLY_TCL}")
    # PD means what the spec says: ORFS's PLACE_DENSITY_LB_ADDON (0.05 in run_abi3's config) silently replaces PLACE_DENSITY
    # by lower-bound + addon (qkd_nhb_pbst: PD 0.50 -> target 0.1075, cells spread over 4.9% of the outline, GPL-0305
    # divergence with M2-M6 routing).  The addon is cleared for every kit; spec route.lb_addon re-enables it explicitly.
    if s["route"].get("lb_addon") is None:
        extra.append("--orfs-var PLACE_DENSITY_LB_ADDON=")
    else:
        extra.append(f"--orfs-var PLACE_DENSITY_LB_ADDON={float(s['route']['lb_addon'])}")
    if s.get("inhold"):
        # spec 'inhold': one dont_touch hold buffer between every data input port and its single capture flop, inserted
        # before global placement (owner 10-10: a hold-only miss on input captures -> delay stage at the inputs, no ECO)
        extra.append("--step-tcl PRE_GLOBAL_PLACE=physical/dsrom_window_source/leaf_inhold.tcl")
        # the hold cell sits AT its input pin with a strong resizable driver after it (vm8 181753c60), FIRM through GPL and
        # released before DPL: seeding it at the capture flop left a long dont_touch-loaded port net -> GPL repair_design
        # RSZ-3006 (s81hc crootrw/crootre d02b035e3), and a bare HB4 driving the long wire costs ~400 ps (vm8 r9)
        drv = s.get("inhold_drv", "BUFx4f_ASAP7_75t_R")
        if drv:
            extra.append(f"--orfs-var OT_INHOLD_DRV={drv}")
            extra.append("--step-tcl PRE_DETAIL_PLACE=physical/dsrom_window_source/leaf_inhold_release.tcl")
    refglob = s.get("refglob", "*")
    inter = ",".join(s["inter"]) or "none_*"
    return "\n".join([
        f"# generated by tools/ref_tile/ref_tile.py from {kd}/spec.json -- do not edit; re-run gen",
        f"TOP={s['top']}", f"SRCS={shq(srcs)}", f"PARAMS=({params})", f"FW={W}", f"FH={H}", f"PINS=({pins})",
        f"PINEX={0 if s['pins'].get('ANY') else 1}", f"INTER={shq(inter)}", f"REFGLOB={shq(refglob)}", f"CLKPORT={s['clock_port']}",
        f"PD={r.get('pd', 0.55)}", f"NC={r.get('threads', 8)}", f"PIN_H={shq(ph)}", f"PIN_V={shq(pv)}", f"PIN_MIN_TRACKS={r.get('pin_min_tracks', 2)}", "STAGES=pnr",
        f"RLAYERS={shq(' '.join(lc['rlayers']))}", f"ROUTE_PERIOD_NS={r.get('period_ps', 770) / 1000.0}",
        f"KIT=/src/{kd}", f"MACROS=({' '.join(views)})", f"EXTRA=({' '.join(extra)})", *pin_balance_env(r, lc), ""])


def pin_balance_env(r: dict, lc: dict | None = None) -> list:
    """optional route.pin_balance {group_max, h, v}: run_abi3_physical's balanced pin placer (place_pin, uniform over each
    port's range, layer alternating every group_max pins) instead of PPL ordered groups, which put a whole port on ONE
    layer ([vm8cp] 2k-bit relay buses: PPL-0107 / PPL-0093).  Needs disjoint per-port pin_ranges on a face."""
    pb = r.get("pin_balance")
    if not pb:
        return []
    return [f"export OT_PIN_GROUP_MAX={int(pb.get('group_max', 1))}",
            f"export OT_PIN_BALANCE_H={shq(pb.get('h', 'M4' if (lc or {}).get('rlayers', ('', 'M6'))[1] == 'M5' else 'M4 M6'))}", f"export OT_PIN_BALANCE_V={shq(pb.get('v', 'M3 M5'))}"]


def referenced_paths(s: dict, kd: str) -> list:
    """every repo file the routed flow reads (for the source-sync check of the gate)"""
    out = [*s["sources"], f"{kd}/kit.env", f"{kd}/clock.sdc", f"{kd}/signoff.sdc", f"{kd}/pdn.tcl", f"{kd}/pre_cts.tcl",
           f"{kd}/pre_grt.tcl", f"{kd}/post_drt.tcl", "tools/ref_tile/ref_route.sh",
           f"{QDM}/io_ref_skew.sdc", f"{QDM}/io_plain.sdc", f"{QDM}/repair_budget.tcl", f"{QDM}/pre_cts_skew.tcl",
           f"{QDM}/pre_ref_skew.tcl", f"{QDM}/post_plain.tcl",
           "physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl"]
    if s.get("forwarded_clock"):
        out.append("physical/hbm_w2_rb_station_20261006/forwarded_subtree.tcl")
    if s.get("io_tcl"):
        out.append(s["io_tcl"])
    out += sorted(str(v) for v in s.get("orfs_vars", {}).values() if not str(v).startswith("/") and os.path.isfile(str(v)))
    if s.get("inhold"):
        out.append("physical/dsrom_window_source/leaf_inhold.tcl")
        if s.get("inhold_drv", "BUFx4f_ASAP7_75t_R"):
            out.append("physical/dsrom_window_source/leaf_inhold_release.tcl")
    if s["route"].get("hold_delay"):
        out.append(HDLY_TCL)
    if s["kind"] == "cluster" and s.get("clock", "spine") == "spine":
        out += ["physical/common_flow/clock_spine.tcl", f"{kd}/spine_ins.tcl"]
    for it in s["macros"] + s["children"]:
        v = it["view"]
        out += [f"{v}/{view_name(v)}.lef"] + [f"{v}/{view_name(v)}_{c}.lib" for c in ("ss", "ff", "tt")]
    if s["macros"] or s["children"]:
        out.append(f"{kd}/place.tcl")
    return out


ROUTE_PREFIX = ("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC} && "
                "export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl "
                "physical/common_flow/link_budget_hook.tcl'; export OT_ORFS_CORNER_OVERRIDE=TC; ")


def lint_cmd(s: dict) -> str:
    """the auto 'lint' bench: Verilator over exactly what the route synthesises -- the same sources, -DSYNTHESIS (run_abi3's
    VERILOG_DEFINES) plus the spec defines, the top's params, the include dirs of orfs_vars VERILOG_INCLUDE_DIRS.
    -Wno-MODMISSING: hard macros / children are blackboxes in the route (LEF/LIB only), and Verilator links every parsed
    module, also ones outside the top's hierarchy; a module genuinely missing under the top still fails yosys
    'hierarchy -check' in the route.  (10-12: ~30 ref jobs NEEDS_RTL on a lint that omitted the defines that select the
    top's body / named blackbox children.)"""
    defs = ["-DSYNTHESIS"] + [f"-D{d}" for d in s.get("defines", [])]
    inc = [f"-I{d[len('/src/'):] if d.startswith('/src/') else d}"
           for d in str(s.get("orfs_vars", {}).get("VERILOG_INCLUDE_DIRS", "")).split() if d]
    # the top is linted under a one-line wrapper: verilator refuses --top-module on a module that another parsed source
    # instantiates (ot_hgi_hc_tile inside ot_hgi_hc_unit.sv, from claude/el1011-hcvm-hc4 7e3baed71); the top's params
    # become instance overrides (-G only reaches the top level); unconnected wrapper ports are lint warnings only
    pv = ", ".join(f".{k}({v})" for k, v in s.get("params", {}).items())
    inst = f"{s['top']} #({pv}) u_top ();" if pv else f"{s['top']} u_top ();"
    wrap = (f"mkdir -p {{RUN}} && printf '%s\\n' 'module ot_lint_top; {inst} endmodule' > {{RUN}}/ot_lint_top.sv && ")
    return wrap + " ".join(["verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING",
                     *defs, *inc, "--top-module", "ot_lint_top", "{RUN}/ot_lint_top.sv", *s["sources"]]) + " && echo lint-ok"


def gen_job(s: dict, kd: str, commit: str | None, blocks: list) -> dict:
    r, j = s["route"], s.get("job", {})
    hm = float(r.get("hold_margin_ns", 0.010))
    tag = j.get("tag", "ref")
    name = f"{s['name']}-{tag}-{(commit or 'COMMIT')[:9]}"
    lint = lint_cmd(s)
    benches = j.get("benches") or []
    if not any(b.get("name") == "lint" for b in benches):
        benches = [{"name": "lint", "cmd": lint, "expect": "pass", "threads": 1, "peak_ram_gb": 4,
                    "needs": ["verilator"]}] + benches
    views = sorted({b["view"] for b in blocks})
    vout = f"{{RUN}}/record/views/{s['top']}"
    mv = " ".join(f"--macro-view {v}" for v in views)
    spec = {
        "name": name, "block": s["top"], "ref_tile": True,
        "owner": j.get("owner", "Claude:ref-flow"),
        "purpose": j.get("purpose", f"reference tile flow ({s['kind']}) kit {kd}"),
        **({"hosts": j["hosts"]} if j.get("hosts") else {}),   # no default host list: the loop places jobs (EPYC2/3 retired 10-12)
        "threads": int(r.get("threads", 8)), "peak_ram_gb": int(r.get("peak_ram_gb", 32)),
        "source": {"branch": j.get("branch", "main"), "commit": commit or "COMMIT",
                   **({"extra_paths": j["extra_paths"]} if j.get("extra_paths") else {})},
        "stages": {
            "bench": benches,
            "calibrate": {"enabled": False, "reason": "ref_tile: boundary referenced in-run to the propagated tree "
                                                      "(io_ref_skew.sdc), as the Qwen die masters"},
            "route": {
                "cmd": ROUTE_PREFIX + f"HM={hm} OT_MM_FF_SDC='{kd}/signoff.sdc' SRC={{SRC}} OT_PIN_GROUP_MAX=32 "
                       f"bash tools/ref_tile/ref_route.sh {kd}/kit.env {{LABEL}} {{RUN}}/routes",
                "ok": "grep -q '^flow_rc=0' {RUN}/routes/{LABEL}/status && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/status",
                "logs": ["{RUN}/routes/{LABEL}/flow.log"],
                "threads": int(r.get("threads", 8)), "peak_ram_gb": int(r.get("peak_ram_gb", 32))},
            "collect": {
                "cmd": ("mkdir -p {RUN}/record/route {RUN}/record/views && cp {RUN}/routes/{LABEL}/corner_sta.json "
                        "{RUN}/routes/{LABEL}/status {RUN}/routes/{LABEL}/STATUS {RUN}/routes/{LABEL}/signoff.sdc "
                        "{RUN}/record/route/ && python3 tools/ref_tile/ref_tile.py export --orfs-dir "
                        f"{{RUN}}/routes/{{LABEL}}/work/orfs --kit {kd} --out {vout} {mv} "
                        "> {RUN}/record/route/export.log 2>&1")}},
        "verdict": {"corner_sta": "{RUN}/routes/{LABEL}/corner_sta.json",
                    "drc_metrics": "{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                    "checks": [{"name": "ttb_routed_at_TC",
                                "cmd": "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"}],
                    "post_sdc": [f"{kd}/signoff.sdc", "physical/common_flow/link_budget_consistent.sdc"],
                    "macros": views},
        "hold_eco": {"enabled": True, "session": "mm", "reason": "ref_tile: corrected FF hold flow"},
        "budget": {"enabled": False, "reason": "ref_tile: boundary budget 0.2 T applied in-run"},
        "record": [{"from": "{RUN}/record/views", "to": j.get("views_to", f"{kd}/views")},
                   {"from": "{RUN}/record/route", "to": j.get("record_to", f"results/rtl/ref_tile/{s['name']}") + f"/{name}"}],
        "cycles_added": int(j.get("cycles_added", 0)),
        "route_hold_corners": "mm", "route_hold_margin_ns": hm, "route_corner": "TC",
        "notes": j.get("notes", "generated by tools/ref_tile/ref_tile.py"),
        "merge_target": j.get("merge_target"),
    }
    if j.get("no_bench_reason"):
        spec["no_bench_reason"] = j["no_bench_reason"]
    return spec


def gen(spec_path: str, area_um2: float | None = None, commit: str | None = None, out_root: Path = ROOT,
        write: bool = True) -> dict:
    s = load_spec(spec_path)
    slot = contract_slot(s)
    lc = layer_contract(s, slot)
    blocks = blocks_of(s)
    W, H, why = outline(s, slot, area_um2, blocks)
    place_blocks(s, W, H, blocks)
    std = area_um2 or s.get("std_area_um2")
    findings = floorplan_checks(s, W, H, blocks, std)
    kd = kit_dir(s)
    fp = {"schema": "opentallas.ref_tile.floorplan.v1", "name": s["name"], "top": s["top"], "kind": s["kind"],
          "die": [0, 0, W, H], "core": [CORE_MARGIN, CORE_MARGIN, W - CORE_MARGIN, H - CORE_MARGIN], "why": why,
          "std_area_um2": std, "layer_contract": {k: (list(v) if isinstance(v, tuple) else v) for k, v in lc.items()},
          "pins": s["pins"], "clock_port": s["clock_port"],
          "blocks": [{k: b[k] for k in ("kind", "view", "master", "inst", "idx", "x", "y", "w", "h", "orient", "offtrack")}
                     for b in blocks],
          "findings": [list(f) for f in findings], "referenced": referenced_paths(s, kd)}
    files = {"kit.env": gen_env(s, kd, W, H, lc, blocks), "pdn.tcl": gen_pdn(s, lc),
             "clock.sdc": gen_sdc(s, float(s["route"].get("period_ps", 770))),
             "signoff.sdc": gen_signoff(s, s.get("refglob", "*"), ",".join(s["inter"]) or "none_*"),
             **gen_hooks(s, kd), "floorplan.json": json.dumps(fp, indent=1) + "\n",
             "spec.json": json.dumps({k: v for k, v in s.items()}, indent=1) + "\n"}
    if blocks:
        files["place.tcl"] = gen_place(s, blocks)
    if s.get("io_tcl") and s.get("orfs_vars", {}).get("POST_TAPCELL_TCL"):
        files["post_tapcell.tcl"] = (
            "# ref_tile: exact abutment pins first (IO_CONSTRAINTS is otherwise sourced only at 3_2_place_iop, where it\n"
            "# re-applies the same placement), then the spec's POST_TAPCELL hook (boundary flops FIRM at their pins)\n"
            f"source /src/{s['io_tcl']}\n"
            f"source /src/{s['orfs_vars']['POST_TAPCELL_TCL']}\n"
            "# then unplace the pins again: 3_2_place_iop re-sources io_tcl, and place_pins aborts in createIOGroup when\n"
            "# a pin group's (clk / reset) ports are already placed (smh_pt_e_ref_p40s gate, signal 6)\n"
            "foreach bt [[ord::get_db_block] getBTerms] { foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp } }\n")
    job = gen_job(s, kd, commit, blocks)
    files["job.json"] = json.dumps(job, indent=1) + "\n"
    if write:
        d = out_root / kd
        d.mkdir(parents=True, exist_ok=True)
        for k, v in files.items():
            (d / k).write_text(v)
    return {"kit": kd, "outline": [W, H], "why": why, "findings": findings, "files": sorted(files), "job": job["name"]}


# --------------------------------------------------------------------------------------------- export
def export(orfs_dir: str, kit: str, out: str, macro_views: list) -> int:
    """exact-shape abstract (write_abstract_lef, never -bloat_occupied_layers) + TT/FF/SS timing models from the routed
    odb + spef at the sign-off SDC, the routed clock insertion (ck_insertion.py), then child_lint of the result."""
    import subprocess
    fp = json.loads((ROOT / kit / "floorplan.json").read_text())
    top = fp["top"]
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "tools/tt_views/view_export.py"), "--orfs-dir", orfs_dir, "--name", top,
           "--out", str(o), "--interface-sdc", str(ROOT / kit / "signoff.sdc"), "--corners", "ss,ff,tt"]
    for v in macro_views:
        cmd += ["--macro-view", str(ROOT / v)]
    rc = subprocess.run(cmd).returncode
    base = next(Path(orfs_dir).glob("results/asap7/*/base"), None)
    ck = ROOT / "tools/closure_loop/ck_insertion.py"
    if base is not None and ck.exists():
        subprocess.run([sys.executable, str(ck), "--base", str(base), "--routed", "--output", str(o / "insertion.json")])
    lef = o / f"{top}.lef"
    res = child_lint.lint(str(lef), str(o)) if lef.exists() else {"verdict": "FAIL", "fails": ["no LEF exported"]}
    (o / "child_lint.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"REF_TILE export {top}: views rc={rc} child_lint {res['verdict']} "
          + "; ".join(res.get("fails", []) + res.get("warns", []))[:800])
    return 0 if (rc == 0 and res["verdict"] == "PASS") else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("spec")
    g.add_argument("--area-um2", type=float)
    g.add_argument("--commit")
    j = sub.add_parser("job")
    j.add_argument("spec")
    j.add_argument("--commit", required=True)
    j.add_argument("--area-um2", type=float)
    e = sub.add_parser("export")
    e.add_argument("--orfs-dir", required=True)
    e.add_argument("--kit", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--macro-view", action="append", default=[])
    a = ap.parse_args(argv)
    try:
        if a.cmd == "gen":
            r = gen(a.spec, a.area_um2, a.commit)
            for sev, chk, msg, fix in r["findings"]:
                print(f"REF_TILE {sev} {chk}: {msg} -> {fix}")
            print(f"REF_TILE kit {r['kit']} outline {r['outline'][0]} x {r['outline'][1]} um ({r['why']}); job {r['job']}")
            return 1 if any(f[0] == "FAIL" for f in r["findings"]) else 0
        if a.cmd == "job":
            r = gen(a.spec, a.area_um2, a.commit, write=False)
            s = load_spec(a.spec)
            job = gen_job(s, kit_dir(s), a.commit, place_blocks(s, *r["outline"], blocks_of(s)))
            p = ROOT / kit_dir(s) / "job.json"
            p.write_text(json.dumps(job, indent=1) + "\n")
            print(f"REF_TILE job {job['name']} -> {p.relative_to(ROOT)}")
            return 0
        return export(a.orfs_dir, a.kit, a.out, a.macro_view)
    except SpecError as ex:
        print(f"REF_TILE FAIL spec: {ex}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
