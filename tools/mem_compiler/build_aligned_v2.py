#!/usr/bin/env python3
"""Track-aligned (v2) successors of every generated ASAP7 macro abstract: pins on track in R0/MX/MY/R180.

Why (results/uarch/macro_pin_access_audit_20261003): every generated abstract puts its signal pin centres
at 0.012 um mod 0.048 (the M4/M5 track offset is pitch/4).  A mirror maps a centre c to (D - c), so the
pins stay on the same origin residue in the mirrored orientation only if the flipped dimension
D = 2 * 0.012 = 0.024 (mod 0.048).  The v1 generators snap H to the 0.270 row and W to 0.216 / 0.432 and
never check it: 18 of 21 catalog abstracts are off-track in MX/R180 under an origin snapped to 0 mod
0.048, the HBM PHYs in MY/R180, and two v1 V4.1 PHYs have no legal origin in any orientation.

This builder leaves every v1 generator and every pinned view byte-identical.  It re-runs the SAME
generators, from the same specs, with four successor rules injected at their outline/width call sites:

  * H (M4 pins on the vertical edges)  -> smallest H' >= H with H' = 0.024 mod 0.048
  * W (M4 pins on both vertical edges) -> smallest W' >= W with W' = 0.024 mod 0.048, so an M5 track
    crosses the pins of BOTH edges (the secondary x-phase issue behind the residual edge DRCs)
  * W (M5 pins on the top edge, HBM PHYs) -> W' = 0.024 mod 0.048, pin rects starting on the 0.048 grid
    (the v1 PHY's centred pin block can never be mirror-invariant: a centred block of 0.192-pitch
    pins mirrors onto itself shifted by 24 nm, so its v2 starts the block on the 0.048 grid)
  * SYMMETRY X Y R90 -> X Y: no rotated orientation has a legal origin (pins and M4 straps rotate
    off their preferred direction)

so ONE origin rule -- x = 0 and y = 0 mod 0.048 on the site/row grid -- puts every pin of every v2
abstract on track in every legal orientation.  Every v2 abstract is verified with
tools/check_macro_track_alignment.py before it is written; a failure aborts the build.

Macro names are unchanged (the netlists bind them); the v2 views live in NEW directory sets:
    physical/asap7_memory_macros_v2/<name>/        (catalog ROM/SRAM + HBM PHYs) + index.json
    physical/asap7_v41x_pdie_macros_v2/<name>/     (reduced-die p-die macros)      + index.json
Use them exactly as v1: tools/run_abi3_physical.py --macro-view <name>=physical/asap7_memory_macros_v2/<name>

    python3 tools/mem_compiler/build_aligned_v2.py [--check-only]
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import math
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import asap7  # noqa: E402
import hbm_phy_gen  # noqa: E402
import rom_gen  # noqa: E402
import sram_gen  # noqa: E402
import views  # noqa: E402
import check_macro_track_alignment as cmta  # noqa: E402

ROOT = asap7.ROOT
V1_DIR = ROOT / "physical/asap7_memory_macros"
V2_DIR = ROOT / "physical/asap7_memory_macros_v2"
PDIE_V1_DIR = ROOT / "physical/asap7_v41x_pdie_macros"
PDIE_V2_DIR = ROOT / "physical/asap7_v41x_pdie_macros_v2"
EW_V2_DIR = ROOT / "physical/asap7_memory_macros_v2_ew"
SCHEMA = "opentallas.asap7-memory-macros.aligned-v2"
ALIGN_VERSION = "aligned-v2"

TRACK_NM = 48          # M4 (horizontal) and M5 (vertical) track pitch, platform make_tracks.tcl
TRACK_OFF_NM = 12      # both layers' track offset
INVARIANT_DIM_NM = 2 * TRACK_OFF_NM   # D = 2c mod pitch, c = 12 nm

# DS-V4.1 ROM die macro counts (results/uarch/macro_pin_access_audit_20261003 die_pricing_ds_v41_rom)
DIE_COUNTS = {"ds_v41_rom_die": {"ot_rom_4096x274_m8": 8192, "ot_rom_4096x72_m8": 14336}}


def nm(v: float) -> int:
    return int(round(v * 1000))


def align_up_nm(dim_nm: int) -> int:
    """Smallest D' >= D with D' = 24 mod 48 (nm)."""
    return dim_nm + (INVARIANT_DIM_NM - dim_nm) % TRACK_NM


def align_up_um(dim_um: float) -> float:
    return align_up_nm(nm(dim_um)) / 1000.0


def row_grid_alternative_nm(dim_nm: int) -> int:
    """Smallest row multiple (0.270) that is also 24 mod 48: k = 4 mod 8 rows (H = 1.08 mod 2.16 um)."""
    k = -(-dim_nm // 270)
    while (k * 270) % TRACK_NM != INVARIANT_DIM_NM:
        k += 1
    return k * 270


# ------------------------------------------------------------------------------------------- verification

def verify_lef(text: str, path: str = "") -> dict[str, Any]:
    """Every pin layer: legal origin 0 mod track in R0/MX/MY/R180 (invariant), checker-verified."""
    out = {}
    for m in cmta.parse_lef(text):
        if m["class"] != "BLOCK":
            continue
        rec = cmta.audit_macro(m, cmta.ASAP7_TRACKS_NM, cmta.ASAP7_LAYERS, path)
        layers = {}
        for lay, s in rec.get("summary", {}).items():
            rules = s["origin_rule_mod_track_nm"]
            ok = (s["orientation_invariant"] and not s["no_legal_origin"]
                  and all(0 in (rules[o] if not rules[o] or isinstance(rules[o][0], int) else
                                [v for a, b in rules[o] for v in range(a, b + 1)]) for o in rules))
            layers[lay] = {"rule_mod_track_nm": rules, "orientation_invariant": s["orientation_invariant"],
                           "origin_0_legal_all_orientations": ok}
        m5 = {}
        for o in ("R0", "MY"):
            va = rec["orientations"].get("M4", {}).get(o, {}).get("adjacent_layer_via_access", {}).get("M5")
            if isinstance(va, dict):
                m5[o] = {e: v["origin_0_crosses_all"] for e, v in va["by_edge"].items()}
        out[m["name"]] = {"size_um": rec["size_um"], "symmetry": rec["symmetry"],
                          "allowed_orientations": rec["allowed_orientations"], "signal_pins": rec["signal_pins"],
                          "layers": layers, "m5_crossing_at_origin_0": m5,
                          "pass": bool(layers) and all(v["origin_0_legal_all_orientations"] for v in layers.values())
                          and not any(o.startswith(("R90", "R270", "MXR", "MYR")) for o in rec["allowed_orientations"])}
    return out


def drop_r90(text: str) -> str:
    new = text.replace("  SYMMETRY X Y R90 ;", "  SYMMETRY X Y ;")
    return new


# ------------------------------------------------------------------------------------------- injection

@contextlib.contextmanager
def patched(obj, **attrs):
    old = {k: getattr(obj, k) for k in attrs}
    for k, v in attrs.items():
        setattr(obj, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(obj, k, v)


def aligned_outline(core_w, core_h, pins):
    """views.macro_outline, then grow H and W to 0.024 mod 0.048 (reported in the outline info)."""
    w, h, info = views.macro_outline(core_w, core_h, pins)
    w2, h2 = align_up_um(w), align_up_um(h)
    info = dict(info)
    info["aligned_v2"] = {
        "rule": "H and W = 0.024 mod 0.048 um: pins on track at origin 0 mod 0.048 in R0/MX/MY/R180, "
                "M5 crossing on both pin edges",
        "v1_width_um": w, "v1_height_um": h, "width_um": w2, "height_um": h2,
        "delta_width_nm": nm(w2) - nm(w), "delta_height_nm": nm(h2) - nm(h),
        "row_multiple": nm(h2) % 270 == 0,
    }
    return w2, h2, info


def aligned_write_lef(name, w, h, pins, props):
    text = views.write_lef(name, w, h, pins, props)
    text = text.replace("# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view",
                        "# OpenTallas memory compiler (tools/mem_compiler), ASAP7 abstract view, "
                        "track-aligned v2 (build_aligned_v2.py)", 1)
    return drop_r90(text)


class _AlignedAsap7:
    """asap7 module proxy for hbm_phy_gen: width snaps are followed by the v2 width rule, never below
    ``floor_um`` (the v1 width), so a v2 PHY fits any slot its v1 reserved."""

    def __init__(self, floor_um: float = 0.0):
        self.floor_um = floor_um

    def __getattr__(self, k):
        return getattr(asap7, k)

    def snap_up(self, value, step):
        r = asap7.snap_up(value, step)
        # 0.216 (v1 PHY width snap), 0.432 (v41x_legal joint grid) or 0.024 (that grid while patched below)
        if any(abs(step - g) < 1e-9 for g in (asap7.METAL["width_snap_um"], 0.432, 0.024)):
            return align_up_um(max(r, self.floor_um))
        return r


def hbm_v1_write_lef_aligned(w, h, plist, pitch):
    """hbm_phy_gen.write_lef with the pin block's start rounded DOWN to the 0.048 track grid (v1 centres it,
    which no width can make mirror-invariant); otherwise byte-for-byte the v1 writer."""
    x0_v1 = round(max(2.0, (w - sum(p.width for p in plist) * pitch) / 2.0), 3)
    x0 = math.floor(nm(x0_v1) / TRACK_NM) * TRACK_NM / 1000.0
    # explicit re-implementation of the v1 body (hbm_phy_gen.write_lef) with x0 on the track grid
    NAME = hbm_phy_gen.NAME
    L = ["# OpenTallas tools/mem_compiler/hbm_phy_gen.py: HBM3E PHY + controller hard-macro ABSTRACT",
         "# controller-side pins only; the package side (DQ, CA, clocks, bumps) is a blackbox under the macro",
         "# track-aligned v2 (build_aligned_v2.py): W = 0.024 mod 0.048, pin block starts on the 0.048 grid",
         "VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {NAME}",
         f"  FOREIGN {NAME} 0 0 ;", "  SYMMETRY X Y ;", f"  SIZE {w:.3f} BY {h:.3f} ;", "  CLASS BLOCK ;"]
    bits = [(p, b) for p in plist for b in p.bits()]
    pw, pl = 0.024, 0.192
    for i, (p, b) in enumerate(bits):
        x = x0 + i * pitch
        L += [f"  PIN {b}", f"    DIRECTION {p.direction.upper()} ;",
              "    USE CLOCK ;" if p.kind == "clock" else "    USE SIGNAL ;", "    SHAPE ABUTMENT ;",
              "    PORT", "      LAYER M5 ;", f"      RECT {x:.3f} {h - pl:.3f} {x + pw:.3f} {h:.3f} ;", "    END",
              f"  END {b}"]
    span = len(bits) * pitch
    sw, sp = 0.288, 2.4
    straps: dict[str, list[float]] = {"VDD": [], "VSS": []}
    y, k = 1.0, 0
    while y + sw < h - 1.0:
        straps["VDD" if k % 2 == 0 else "VSS"].append(y)
        y += sp / 2
        k += 1
    for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M4 ;"]
        L += [f"      RECT 0.500 {yy:.3f} {w - 0.5:.3f} {yy + sw:.3f} ;" for yy in straps[net]]
        L += ["    END", f"  END {net}"]
    L += ["  OBS"]
    for layer in ("M1", "M2", "M3", "M4"):
        L += [f"    LAYER {layer} ;", f"    RECT 0 0 {w:.3f} {h:.3f} ;"]
    L += ["    LAYER M5 ;", f"    RECT 0 0 {w:.3f} {h - 0.4:.3f} ;"]
    L += ["  END", f"END {NAME}", "", "END LIBRARY"]
    return "\n".join(L) + "\n", {"signal_pins": len(bits), "pin_span_um": round(span, 3),
                                   "pin_pitch_um": pitch, "pin_layer": "M5", "pin_edge": "top (core-facing)",
                                   "pin_block_x_um": [x0, round(x0 + span, 3)], "fits_on_edge": x0 + span <= w - 2.0,
                                   "v1_pin_block_start_um": x0_v1}


# ------------------------------------------------------------------------------------------- builders

def v1_sheet(d: Path, name: str) -> dict:
    return json.loads((d / name / f"{name}.json").read_text())


def finish(out: Path, name: str, v1: dict | None, v1_dims: tuple[float, float], extra: dict) -> dict:
    """Verify the written LEF, add the alignment block to the sheet json, return the index entry."""
    d = out / name
    lef_path = d / f"{name}.lef"
    ver = verify_lef(lef_path.read_text(), str(lef_path))[name]
    if not ver["pass"]:
        raise SystemExit(f"{name}: v2 abstract is NOT on track in every orientation: {json.dumps(ver)[:600]}")
    w2, h2 = ver["size_um"]
    w1, h1 = v1_dims
    a1, a2 = w1 * h1, w2 * h2
    block = {
        "version": ALIGN_VERSION, "builder": "tools/mem_compiler/build_aligned_v2.py",
        "origin_rule": "x = 0 and y = 0 mod 0.048 um (on the site / row grid) in R0, MX, MY and R180",
        "v1": {"width_um": w1, "height_um": h1, "area_um2": round(a1, 3),
               "views": (v1 or {}).get("views")},
        "v2": {"width_um": w2, "height_um": h2, "area_um2": round(a2, 3)},
        "delta": {"width_nm": nm(w2) - nm(w1), "height_nm": nm(h2) - nm(h1),
                  "area_um2": round(a2 - a1, 4), "area_pct": round(100.0 * (a2 - a1) / a1, 4)},
        "row_grid_alternative": {"height_um": row_grid_alternative_nm(nm(h1)) / 1000.0,
                                 "area_um2_delta": round(w2 * row_grid_alternative_nm(nm(h1)) / 1000.0 - a1, 3),
                                 "note": "H on the 0.270 row grid AND 0.024 mod 0.048 (k = 4 mod 8 rows); "
                                         "not emitted, priced only"},
        "verification": ver, **extra,
    }
    sheet_path = d / f"{name}.json"
    sheet = json.loads(sheet_path.read_text()) if sheet_path.exists() else {}
    sheet["alignment_v2"] = block
    sheet_path.write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
    views_d = {p.name: asap7.sha256_file(p) for p in sorted(d.iterdir())}
    return {"kind": sheet.get("kind", extra.get("kind")), "width_um": w2, "height_um": h2,
            "area_um2": round(a2, 3), "delta": block["delta"], "row_grid_alternative": block["row_grid_alternative"],
            "symmetry": ver["symmetry"], "pin_layers": sorted(ver["layers"]),
            "m5_crossing_at_origin_0": ver["m5_crossing_at_origin_0"], "views": views_d,
            "v1_dir": str((V1_DIR if (V1_DIR / name).exists() else PDIE_V1_DIR).relative_to(ROOT)) + f"/{name}"}


def build_catalog(out: Path) -> dict:
    entries = {}
    names = sorted(p.name for p in V1_DIR.iterdir() if p.is_dir())
    rom_sram = [n for n in names if n.startswith(("ot_rom_", "ot_sram_"))]
    with patched(rom_gen, macro_outline=aligned_outline, write_lef=aligned_write_lef,
                 GENERATOR_VERSION=f"{rom_gen.GENERATOR_VERSION}+{ALIGN_VERSION}"), \
         patched(sram_gen, macro_outline=aligned_outline, write_lef=aligned_write_lef,
                 GENERATOR_VERSION=f"{sram_gen.GENERATOR_VERSION}+{ALIGN_VERSION}"):
        for n in rom_sram:
            v1 = v1_sheet(V1_DIR, n)
            spec = v1["spec"]
            if v1["kind"] == "rom":
                rom_gen.compile_macro(rom_gen.RomSpec(**spec), out)
            else:
                sram_gen.compile_macro(sram_gen.SramSpec(**spec), out)
            a = v1["area"]
            entries[n] = finish(out, n, v1, (a["macro_width_um"], a["macro_height_um"]),
                                {"kind": v1["kind"], "spec": spec})
    # HBM PHYs: generic v1 PHY and the V4.1 PHYs (the two defective v1 writers are replaced by the legal
    # writer under their own names at their own 12.0 mm edge; the e8p5 PHY keeps its edge)
    proxy = _AlignedAsap7(v1_sheet(V1_DIR, hbm_phy_gen.NAME)["footprint"]["width_um"])
    with patched(hbm_phy_gen, asap7=proxy, write_lef=hbm_v1_write_lef_aligned):
        hbm_phy_gen.generate(out)
    n = hbm_phy_gen.NAME
    v1 = v1_sheet(V1_DIR, n)
    entries[n] = finish(out, n, v1, (v1["footprint"]["width_um"], v1["footprint"]["height_um"]),
                        {"kind": "hbm_phy_abstract", "change": "W to 0.024 mod 0.048; pin block start on the "
                         "0.048 grid (v1 centred it: never mirror-invariant)"})
    v41 = [("ot_hbm3e_phy_v41x", 28, 12.0), ("ot_hbm3e_phy_v41x_aw30", 30, 12.0),
           ("ot_hbm3e_phy_v41x_aw30_e8p5", 30, 8.5)]
    for name, k_aw, edge in v41:
        proxy = _AlignedAsap7(v1_sheet(V1_DIR, name)["footprint"]["width_um"])
        with patched(hbm_phy_gen, asap7=proxy, JOINT_X_UM=0.024,
                     v41x_legal_name=lambda k, e, _n=name: _n):
            hbm_phy_gen.generate_v41x_legal(out, edge_mm=edge, k_aw=k_aw)
        v1 = v1_sheet(V1_DIR, name)
        # the legal writer's sheet still says R0/MX (its v1 claim); the verified v2 statement replaces it
        sj = out / name / f"{name}.json"
        s = json.loads(sj.read_text())
        s["pins"]["on_track_orientations"] = ["R0", "MX", "MY", "R180"]
        sj.write_text(json.dumps(s, indent=2, sort_keys=True) + "\n")
        change = ("v1 writer had no legal origin in any orientation (24 pin phases); v2 uses the legal "
                  "writer (hbm_phy_gen.write_lef_v41x_legal) at the v1 12.0 mm edge, W = 0.024 mod 0.048, "
                  "H on the 2.16 um grid" if edge == 12.0 else "W from the 0.432 joint grid to 0.024 mod 0.048")
        entries[name] = finish(out, name, v1, (v1["footprint"]["width_um"], v1["footprint"]["height_um"]),
                               {"kind": "hbm_phy_abstract", "change": change, "edge_mm": edge, "k_aw": k_aw})
    return entries


def grow_lef_outline(text: str, name: str, w2: float, h2: float) -> str:
    """Grow a committed abstract's outline (no generator reproduces it): SIZE, edge-touching OBS rects
    extend, edge-touching PIN rects move with the edge.  Interior geometry is unchanged."""
    m = re.search(r"SIZE\s+(\S+)\s+BY\s+(\S+)\s*;", text)
    w1, h1 = float(m.group(1)), float(m.group(2))
    dw, dh = w2 - w1, h2 - h1
    out, in_obs, in_pin_power = [], False, False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("SIZE"):
            line = line.replace(m.group(0), f"SIZE {w2:.3f} BY {h2:.3f} ;")
        elif s == "OBS":
            in_obs = True
        elif s == "END" and in_obs:
            in_obs = False
        elif s.startswith("RECT"):
            v = [float(x) for x in s.replace(";", "").split()[1:5]]
            x1, y1, x2, y2 = v
            if in_obs:
                x2 = x2 + dw if abs(x2 - w1) < 1e-6 else x2
                y2 = y2 + dh if abs(y2 - h1) < 1e-6 else y2
            else:
                if abs(x2 - w1) < 1e-6 and x1 > 0:
                    x1, x2 = x1 + dw, x2 + dw
                if abs(y2 - h1) < 1e-6 and y1 > 0:
                    y1, y2 = y1 + dh, y2 + dh
            fmt = lambda a: f"{a:.3f}" if (a != 0 or "RECT 0 " not in s) else "0"  # noqa: E731
            line = line[:len(line) - len(line.lstrip())] + "RECT " + " ".join(fmt(a) for a in (x1, y1, x2, y2)) + " ;"
        out.append(line)
    return drop_r90("\n".join(out) + ("\n" if text.endswith("\n") else ""))


def build_pdie(out: Path) -> dict:
    sys.path.insert(0, str(ROOT / "tools"))
    import v41x_die_pnr as die
    from chip_assembly import macros as mc
    entries = {}
    specs = die.pdie_specs()
    v1_index = json.loads((PDIE_V1_DIR / "index.json").read_text())["macros"]
    for name, spec in specs.items():
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        if mc.lef_text(spec) != (PDIE_V1_DIR / name / f"{name}.lef").read_text():
            # the generator no longer reproduces this pinned view (its RTL port list moved on): grow the
            # committed abstract's outline instead, and carry its other views with the area updated
            src = PDIE_V1_DIR / name
            v1_text = (src / f"{name}.lef").read_text()
            mv = re.search(r"SIZE\s+(\S+)\s+BY\s+(\S+)", v1_text)
            w1, h1 = float(mv.group(1)), float(mv.group(2))
            w2, h2 = align_up_um(w1), align_up_um(h1)
            (d / f"{name}.lef").write_text(grow_lef_outline(v1_text, name, w2, h2))
            for f in sorted(src.iterdir()):
                if f.suffix == ".lib":
                    t = f.read_text()
                    t = re.sub(r"area : [0-9.]+;", f"area : {w2 * h2:.3f};", t, count=1)
                    (d / f.name).write_text(t)
                elif f.name.endswith("_bb.v"):
                    shutil.copy2(f, d / f.name)
            how = "committed v1 abstract outline grown (generator no longer reproduces the pinned view)"
            dims = (w1, h1)
        else:
            w2, h2 = align_up_um(spec.width_um), align_up_um(spec.height_um)
            spec2 = dataclasses.replace(spec, width_um=w2, height_um=h2)
            (d / f"{name}.lef").write_text(drop_r90(mc.lef_text(spec2)))
            (d / f"{name}_tt.lib").write_text(mc.liberty_text(spec2))
            (d / f"{name}_bb.v").write_text(mc.verilog_stub(spec2))
            how = "regenerated by tools/chip_assembly/macros.py from v41x_die_pnr.pdie_specs() at the v2 outline"
            dims = (spec.width_um, spec.height_um)
        sheet = dict(v1_index.get(name, {}), width_um=w2, height_um=h2, area_um2=round(w2 * h2, 3))
        (d / f"{name}.json").write_text(json.dumps(sheet, indent=1, sort_keys=True) + "\n")
        entries[name] = finish(out, name, {"views": {f.name: asap7.sha256_file(f) for f in sorted((PDIE_V1_DIR / name).iterdir())}},
                               dims, {"kind": v1_index.get(name, {}).get("kind"), "how": how})
    return entries


def die_pricing(entries: dict) -> dict:
    out = {}
    for die_name, counts in DIE_COUNTS.items():
        rows, tot, tot_row = {}, 0.0, 0.0
        for m, n in counts.items():
            e = entries[m]
            d = e["delta"]["area_um2"] * n / 1e6
            r = e["row_grid_alternative"]["area_um2_delta"] * n / 1e6
            rows[m] = {"count_per_die": n, "delta_um2_each": e["delta"]["area_um2"],
                       "delta_nm_wh": [e["delta"]["width_nm"], e["delta"]["height_nm"]],
                       "die_delta_mm2": round(d, 4), "row_grid_alternative_die_delta_mm2": round(r, 4)}
            tot += d
            tot_row += r
        out[die_name] = {"macros": rows, "die_delta_mm2": round(tot, 4),
                         "row_grid_alternative_die_delta_mm2": round(tot_row, 4),
                         "basis": "counts from results/uarch/macro_pin_access_audit_20261003 (8,192 weight + "
                                  "14,336 cfg ROMs per DS-V4.1 ROM die); macro area only, no floorplan re-pack"}
    return out


# ------------------------------------------------------------------------------- east/west-edge HBM PHY

def hbm_ew_write_lef(w, h, plist, pitch):
    """ot_hbm3e_phy for an EAST/WEST die edge (Qwen ROM near-HBM B2-EW frame): the same port list and
    footprint turned on its side.  The shoreline (v1 width) becomes the height, the depth the width; the
    controller-side pins are M4 (the horizontal layer, so they leave the vertical edge in their preferred
    direction) on the macro's WEST edge, 0.192 um pitch, rect starts on the 0.048 grid (centres on the
    0.012-offset M4 track).  H and W = 0.024 mod 0.048, SYMMETRY X Y: R0 on the die's east edge (pins face
    the core to the west), MY on the west edge; MX/R180 also legal.  Same origin rule as every v2 view."""
    NAME = hbm_phy_gen.NAME
    W, H = h, w                                   # turned: depth across, shoreline up
    bits = [(p, b) for p in plist for b in p.bits()]
    span = len(bits) * pitch
    y0_c = max(2.0, (H - span) / 2.0)
    y0 = math.floor(nm(y0_c) / TRACK_NM) * TRACK_NM / 1000.0
    pw, pl = 0.024, 0.192
    L = ["# OpenTallas tools/mem_compiler/build_aligned_v2.py: HBM3E PHY + controller hard-macro ABSTRACT, "
         "east/west-edge (v2_ew)",
         "# controller-side pins only, M4 on the west edge; the package side is a blackbox under the macro",
         "VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {NAME}",
         f"  FOREIGN {NAME} 0 0 ;", "  SYMMETRY X Y ;", f"  SIZE {W:.3f} BY {H:.3f} ;", "  CLASS BLOCK ;"]
    for i, (p, b) in enumerate(bits):
        y = y0 + i * pitch
        L += [f"  PIN {b}", f"    DIRECTION {p.direction.upper()} ;",
              "    USE CLOCK ;" if p.kind == "clock" else "    USE SIGNAL ;", "    SHAPE ABUTMENT ;",
              "    PORT", "      LAYER M4 ;", f"      RECT 0.000 {y:.3f} {pl:.3f} {y + pw:.3f} ;", "    END",
              f"  END {b}"]
    # VDD/VSS: vertical-run-free M4 straps 0.288 um wide, centred on M4 tracks every 1.2 um, starting
    # 0.48 um in from the pin edge; the parent's M5 stripes reach them with M4-M5 vias (M5 not obstructed)
    sw, step = 0.288, 25 * TRACK_NM / 1000.0
    ys = TRACK_OFF_NM / 1000.0 + 21 * TRACK_NM / 1000.0 - sw / 2
    straps: dict[str, list[float]] = {"VDD": [], "VSS": []}
    y, k = ys, 0
    while y + sw < H - 1.0:
        straps["VDD" if k % 2 == 0 else "VSS"].append(round(y, 3))
        y += step
        k += 1
    for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M4 ;"]
        L += [f"      RECT 0.480 {yy:.3f} {W - 0.48:.3f} {yy + sw:.3f} ;" for yy in straps[net]]
        L += ["    END", f"  END {net}"]
    L += ["  OBS"]
    for layer in ("M1", "M2", "M3"):
        L += [f"    LAYER {layer} ;", f"    RECT 0 0 {W:.3f} {H:.3f} ;"]
    L += ["    LAYER M4 ;", f"    RECT 0.400 0 {W:.3f} {H:.3f} ;"]   # pin strip x < 0.192 clear by 0.208
    L += ["  END", f"END {NAME}", "", "END LIBRARY"]
    return "\n".join(L) + "\n", {"signal_pins": len(bits), "pin_span_um": round(span, 3), "pin_pitch_um": pitch,
                                   "pin_layer": "M4", "pin_edge": "west (core-facing when placed R0 on the die's "
                                   "east edge; MY on the west edge)", "pin_block_y_um": [y0, round(y0 + span, 3)],
                                   "fits_on_edge": y0 + span <= H - 2.0, "turned": True}


class _AlignedAsap7Both(_AlignedAsap7):
    """Width AND row-height snaps aligned (the turned PHY's depth becomes a width)."""

    def snap_up(self, value, step):
        r = super().snap_up(value, step)
        if abs(step - asap7.METAL["height_snap_um"]) < 1e-9:
            return align_up_um(r)
        return r


def build_ew(out: Path) -> dict:
    n = hbm_phy_gen.NAME
    v1 = v1_sheet(V1_DIR, n)
    w1, h1 = v1["footprint"]["width_um"], v1["footprint"]["height_um"]
    with patched(hbm_phy_gen, asap7=_AlignedAsap7Both(w1), write_lef=hbm_ew_write_lef):
        hbm_phy_gen.generate(out)
    sj = out / n / f"{n}.json"
    s = json.loads(sj.read_text())
    s["footprint"]["orientation_note"] = ("turned for an east/west die edge: LEF SIZE is depth x shoreline "
                                          "(width_um/height_um above are shoreline/depth as the v1 sheet)")
    sj.write_text(json.dumps(s, indent=2, sort_keys=True) + "\n")
    return {n: finish(out, n, v1, (h1, w1), {"kind": "hbm_phy_abstract", "edge": "east/west",
            "change": "turned footprint (depth x shoreline), M4 pins on the west edge on track, H and W = 0.024 "
                      "mod 0.048; compare against the v1 footprint turned", "requested_by": "Qwen ROM near-HBM "
                      "B2-EW frame (claude/qwen-rom-floorplan-nearhbm-20261003 @ b4593fb82)"})}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=V2_DIR)
    ap.add_argument("--pdie-out", type=Path, default=PDIE_V2_DIR)
    ap.add_argument("--ew-out", type=Path, default=EW_V2_DIR)
    ap.add_argument("--check-only", action="store_true", help="build into a temporary directory and compare "
                    "with the committed v2 sets byte for byte")
    a = ap.parse_args(argv)
    if a.check_only:
        with tempfile.TemporaryDirectory() as t:
            rc = main(["--out", f"{t}/m", "--pdie-out", f"{t}/p", "--ew-out", f"{t}/e"])
            bad = []
            for got, ref in ((Path(t) / "m", a.out), (Path(t) / "p", a.pdie_out), (Path(t) / "e", a.ew_out)):
                for f in sorted(got.rglob("*")):
                    if f.is_file():
                        r = ref / f.relative_to(got)
                        if not r.exists() or r.read_bytes() != f.read_bytes():
                            bad.append(str(r.relative_to(ROOT)))
            print("CHECK", "PASS" if not bad else f"FAIL {bad[:10]}")
            return rc or (1 if bad else 0)
    for d in (a.out, a.pdie_out, a.ew_out):
        if d.exists() and any(d.iterdir()):
            raise SystemExit(f"{d} exists: v2 sets are written once; build elsewhere and compare (--check-only)")
    a.out.mkdir(parents=True, exist_ok=True)
    a.pdie_out.mkdir(parents=True, exist_ok=True)
    a.ew_out.mkdir(parents=True, exist_ok=True)
    cat = build_catalog(a.out)
    pdie = build_pdie(a.pdie_out)
    ew = build_ew(a.ew_out)
    common = {"schema": SCHEMA, "builder": "tools/mem_compiler/build_aligned_v2.py",
              "builder_sha256": asap7.sha256_file(Path(__file__)),
              "checker": "tools/check_macro_track_alignment.py",
              "checker_sha256": asap7.sha256_file(HERE.parent / "check_macro_track_alignment.py"),
              "rule": "every signal pin centre on its preferred-direction track at origin x = y = 0 mod 0.048 um "
                      "in R0, MX, MY and R180; SYMMETRY X Y (rotations dropped)",
              "usage": {"lef": "<name>/<name>.lef", "orfs": "tools/run_abi3_physical.py --macro-view "
                        "<name>=<this dir>/<name>", "hooks": "physical/common/ot_macro_track_snap.tcl"},
              "audit": "results/uarch/macro_pin_access_audit_20261003"}
    gen = {"generators": {"rom": f"tools/mem_compiler/rom_gen.py v{rom_gen.GENERATOR_VERSION}",
                          "sram": f"tools/mem_compiler/sram_gen.py v{sram_gen.GENERATOR_VERSION}",
                          "hbm": "tools/mem_compiler/hbm_phy_gen.py (generate, generate_v41x_legal)"},
           "v1_index": "physical/asap7_memory_macros/index.json",
           "v1_index_sha256": asap7.sha256_file(V1_DIR / "index.json")}
    (a.out / "index.json").write_text(json.dumps(
        {**common, **gen, "macros": cat, "die_pricing": die_pricing(cat)}, indent=1, sort_keys=True) + "\n")
    (a.pdie_out / "index.json").write_text(json.dumps(
        {**common, "generators": {"pdie": "tools/v41x_die_pnr.py pdie_specs + tools/chip_assembly/macros.py"},
         "v1_index": "physical/asap7_v41x_pdie_macros/index.json",
         "v1_index_sha256": asap7.sha256_file(PDIE_V1_DIR / "index.json"), "macros": pdie},
        indent=1, sort_keys=True) + "\n")
    (a.ew_out / "index.json").write_text(json.dumps(
        {**common, "generators": {"hbm_ew": "tools/mem_compiler/hbm_phy_gen.py generate() with "
                                  "build_aligned_v2.hbm_ew_write_lef"},
         "note": "same MACRO name as the catalog PHY (the netlist binds it); this set is the east/west-edge "
                 "footprint, select it with --macro-view ot_hbm3e_phy=<this dir>/ot_hbm3e_phy",
         "macros": ew}, indent=1, sort_keys=True) + "\n")
    for n, e in {**cat, **pdie, **{k + " (ew)": v for k, v in ew.items()}}.items():
        print(f"{n:34s} {e['width_um']:>10.3f} x {e['height_um']:<9.3f} dW {e['delta']['width_nm']:3d} nm "
              f"dH {e['delta']['height_nm']:3d} nm  +{e['delta']['area_um2']:.3f} um2 ({e['delta']['area_pct']:.3f}%)")
    print(json.dumps(die_pricing(cat), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
