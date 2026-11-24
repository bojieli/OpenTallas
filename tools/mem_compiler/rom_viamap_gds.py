#!/usr/bin/env python3
"""Apply a ROM instance's via map (<INSTANCE>.viamap.hex) to the die GDS.

rom_gen.py writes LEF, Liberty and a model per ROM macro plus one
``<INSTANCE>.viamap.hex`` per placed instance, but no layout.  The ROM's only
content-dependent mask is the programming VIA1 (drain -> bitline, see
tools/asap7_bitcell_density.py build_rom: V0/M1/M2/active are identical in
every cell, V1 is present exactly where the stored bit is 1).  This tool turns
a via map into a GDS "overlay" structure holding only those V1 rectangles, and
merges one overlay per UNIQUE image into the die stream, with one SREF per
placed instance at the DEF location and orientation.  Siblings that differ
only in ROM image therefore share every other mask and differ in the overlay.

Subcommands (pure Python, no KLayout needed; GDSII is streamed, the die file is
never held in memory):

  overlay  --macro M.json --viamap I.viamap.hex --out I.gds [--dbu-per-um N]
  merge    --die-gds in.gds --top TOP --def placed.def --macro M.json
           --manifest P.personalisation.json --viamap-dir D --out out.gds
  verify   --die-gds out.gds --top TOP --def placed.def --macro M.json
           --manifest ... --viamap-dir D        (reads the vias back, compares)
  readback --gds I.gds --macro M.json --viamap I.viamap.hex
  merge-map  --rommap R.json --macro M.json --viamap-dir D --top TOP --out out.gds [--die-gds in.gds] [--parts P ...] [--allow-missing]
  verify-map --rommap R.json --macro M.json --viamap-dir D --top TOP --die-gds out.gds [--parts P ...] [--allow-missing]
           TYPE-TEMPLATE die assembly (tools/fleet/type_template.py rommap): the die stream instantiates ONE representative
           layout per template group, so no DEF names the ROMs of a position.  The map gives, per die position, every ROM
           macro's die-frame lower-left corner, orientation and the position's own image; merge-map stamps that image's
           overlay there, verify-map reads every one back.  Without --die-gds the output is an overlay-only stream (TOP holds
           only the SREFs) for a later stream merge.  Rows of another macro (element cores) are counted, not stamped: their
           ROMs sit inside the core layout. A .gds.gz output is compressed as it is written and can be read by verify-map.
           Use a fresh output path for each attempt. merge-map reserves that path and publishes only the complete stream.

Pass --via-grid to use explicit, signed-LEF-bound drain coordinates from the
base layout. The "opentallas.rom-via-grid.v1" JSON contains "lef_sha256",
integer "dbu_per_um" and a "banks" array. Each bank defines "row_start",
"col_start", "row_axis" ("x" or "y") and "rows_dbu"/"cols_dbu" coordinate
lists in logical address and column order. For full macro assembly, include
"base_gds_sha256" for the unprogrammed layout. Axis lists may descend or have
unequal spacing to represent mirrored arrays and access bands. The grid
covers every logical bit, and all bank geometry is macro-local.

Preview geometry (macro-local, rom_gen orientation: physical column c at x, row r at y):
V1 centre = origin + (c*col_pitch + col_pitch/2, r*row_pitch + row_pitch/2),
18 nm square on GDS layer 21/0.  The array origin inside the macro is not fixed
by the abstract (LEF has no array); it defaults to (decoder_width, 0) of the
datasheet and is recorded in every output.  CLAIM BOUNDARY: this places the
programming layer on the compiler's cell grid; the base macro layout
(array, decoder, sense) is still not generated, and the V1 offset inside a
cell is the cell centre, not the drawn drain position.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import struct
import sys
import tempfile
from contextlib import ExitStack, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterator

V1_LAYER, V1_DT = 21, 0
V_SZ_NM = 18.0

# record types
HEADER, BGNLIB, LIBNAME, UNITS, ENDLIB = 0x00, 0x01, 0x02, 0x03, 0x04
BGNSTR, STRNAME, ENDSTR, BOUNDARY, SREF = 0x05, 0x06, 0x07, 0x08, 0x0A
LAYER, DATATYPE, XY, ENDEL, SNAME, STRANS, ANGLE = 0x0D, 0x0E, 0x10, 0x11, 0x12, 0x1A, 0x1C


def real8_enc(v: float) -> bytes:
    if v == 0:
        return b"\0" * 8
    sign = 0x80 if v < 0 else 0
    v = abs(v)
    e = 64
    while v >= 1:
        v /= 16
        e += 1
    while v < 1 / 16:
        v *= 16
        e -= 1
    return bytes([sign | e]) + int(round(v * (1 << 56))).to_bytes(7, "big")


def real8_dec(b: bytes) -> float:
    m = int.from_bytes(b[1:8], "big") / (1 << 56)
    v = m * 16.0 ** ((b[0] & 0x7F) - 64)
    return -v if b[0] & 0x80 else v


def rec(rt: int, dt: int, payload: bytes = b"") -> bytes:
    if len(payload) % 2:
        payload += b"\0"
    return struct.pack(">HBB", len(payload) + 4, rt, dt) + payload


def i2(*v: int) -> bytes:
    return struct.pack(f">{len(v)}h", *v)


def i4(*v: int) -> bytes:
    return struct.pack(f">{len(v)}i", *v)


def read_records(f: BinaryIO) -> Iterator[tuple[int, int, bytes]]:
    while True:
        h = f.read(4)
        if not h:
            return
        n, rt, dt = struct.unpack(">HBB", h)
        yield rt, dt, f.read(n - 4)


def strname(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode()


# ---------------------------------------------------------------------------
# macro geometry and via map
# ---------------------------------------------------------------------------

@dataclass
class ViaBank:
    row_start: int
    col_start: int
    row_x: bool
    rows: list[int]
    cols: list[int]
    row_indices: dict[int, int]
    col_indices: dict[int, int]

    @property
    def row_stop(self) -> int:
        return self.row_start + len(self.rows)

    @property
    def col_stop(self) -> int:
        return self.col_start + len(self.cols)


class ViaGrid:
    def __init__(self, path: Path, lef_sha: str, shape: tuple[int, int], outline_um: tuple[float, float]) -> None:
        raw = path.read_bytes()
        grid = json.loads(raw)
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.lef_sha256 = lef_sha
        self.base_gds_sha256 = grid.get("base_gds_sha256")
        if self.base_gds_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", self.base_gds_sha256):
            raise ValueError(f"{path}: invalid base GDS SHA-256")
        # A grid may name the base macro's array cell: program-macro then refuses a base whose array
        # gates still end short of a neighbouring cell's poly (rom_seam_gate; HEAD GATE.S.1 band 11-24).
        self.seam_array_cell = grid.get("seam_array_cell")
        if self.seam_array_cell is not None and (not isinstance(self.seam_array_cell, str) or not self.seam_array_cell):
            raise ValueError(f"{path}: seam_array_cell must be a cell name")
        if grid["schema"] != "opentallas.rom-via-grid.v1" or grid["lef_sha256"] != lef_sha:
            raise ValueError(f"{path}: VIA1 grid schema or LEF SHA-256 differs")
        self.dbu = grid["dbu_per_um"]
        if type(self.dbu) is not int or self.dbu <= 0 or self.dbu % 1000:
            raise ValueError(f"{path}: VIA1 grid DBU per micron must be a positive multiple of 1000")
        half = 9 * (self.dbu // 1000)
        self.banks: list[ViaBank] = []
        boxes = []
        rows, cols = shape
        for entry in grid["banks"]:
            row_axis = entry["row_axis"]
            starts = (entry["row_start"], entry["col_start"])
            axes = (entry["rows_dbu"], entry["cols_dbu"])
            if row_axis not in ("x", "y") or any(type(v) is not int or v < 0 for v in starts):
                raise ValueError(f"{path}: invalid VIA1 bank axes or first logical indices")
            for axis in axes:
                if not axis or any(type(v) is not int for v in axis):
                    raise ValueError(f"{path}: VIA1 grid coordinates must be nonempty integer lists")
                steps = [b - a for a, b in zip(axis, axis[1:])]
                if not (all(step >= 2 * half for step in steps) or all(step <= -2 * half for step in steps)):
                    raise ValueError(f"{path}: VIA1 grid axis must be strictly ordered with room for each cut")
            bank = ViaBank(*starts, row_axis == "x", *axes,
                           *({v: i + start for i, v in enumerate(axis)} for start, axis in zip(starts, axes)))
            if bank.row_stop > rows or bank.col_stop > cols:
                raise ValueError(f"{path}: VIA1 bank exceeds the logical shape")
            xs, ys = axes if bank.row_x else axes[::-1]
            box = (min(xs) - half, min(ys) - half, max(xs) + half, max(ys) + half)
            if min(box[:2]) < 0 or any(v > length * self.dbu for v, length in zip(box[2:], outline_um)):
                raise ValueError(f"{path}: VIA1 bank exceeds the macro outline")
            if any(box[0] < x1 and x0 < box[2] and box[1] < y1 and y0 < box[3] for x0, y0, x1, y1 in boxes):
                raise ValueError(f"{path}: VIA1 bank boxes overlap")
            boxes.append(box)
            self.banks.append(bank)
        self.by_row = [[b for b in self.banks if b.row_start <= r < b.row_stop] for r in range(rows)]
        for banks in self.by_row:
            stop = 0
            banks.sort(key=lambda b: b.col_start)
            for bank in banks:
                if bank.col_start != stop:
                    break
                stop = bank.col_stop
            else:
                if stop == cols:
                    continue
            raise ValueError(f"{path}: VIA1 banks must cover every logical cell exactly once")

    def centre(self, row: int, col: int) -> tuple[float, float]:
        bank = next(b for b in self.by_row[row] if b.col_start <= col < b.col_stop)
        r, c = bank.rows[row - bank.row_start] / self.dbu, bank.cols[col - bank.col_start] / self.dbu
        return (r, c) if bank.row_x else (c, r)

    def cell(self, x_um: float, y_um: float) -> tuple[int, int]:
        x, y = round(x_um * self.dbu), round(y_um * self.dbu)
        if abs(x - x_um * self.dbu) < 1e-5 and abs(y - y_um * self.dbu) < 1e-5:
            for bank in self.banks:
                r, c = (x, y) if bank.row_x else (y, x)
                row, col = bank.row_indices.get(r), bank.col_indices.get(c)
                if row is not None and col is not None:
                    return row, col
        raise ValueError(f"via at ({x_um},{y_um}) um is not on a programming drain")


class Macro:
    def __init__(self, sheet_path: Path, array_origin_um: tuple[float, float] | None = None,
                 via_grid: Path | None = None) -> None:
        s = json.loads(sheet_path.read_text())
        sp, a = s["spec"], s["area"]
        self.name, self.words, self.bits, self.mux = sp["name"], sp["words"], sp["bits"], sp["mux"]
        self.rows, self.cols = self.words // self.mux, self.bits * self.mux
        self.col_pitch, self.row_pitch = a["cell_col_pitch_um"], a["cell_row_pitch_um"]
        self.w, self.h = a["macro_width_um"], a["macro_height_um"]
        self.origin = array_origin_um or (a["decoder_width_um"], 0.0)
        self.origin_assumed = array_origin_um is None
        self.grid = None
        if via_grid is not None:
            if array_origin_um is not None:
                raise ValueError("specify VIA1 grid coordinates or an array origin")
            lef = sheet_path.with_name(self.name + ".lef")
            lef_sha = hashlib.sha256(lef.read_bytes()).hexdigest()
            if s["views"].get(lef.name) != lef_sha:
                raise ValueError(f"{lef}: LEF SHA-256 differs from the datasheet")
            self.grid = ViaGrid(via_grid, lef_sha, (self.rows, self.cols), (self.w, self.h))
            self.origin_assumed = False

    def geometry_info(self) -> dict[str, Any]:
        if self.grid is not None:
            return {"array_origin_um": None, "array_origin_assumed": False, "via_grid_sha256": self.grid.sha256,
                    "via_grid_lef_sha256": self.grid.lef_sha256}
        return {"array_origin_um": list(self.origin), "array_origin_assumed": self.origin_assumed}

    def grid_dbu(self, dbu: float | None) -> float:
        if self.grid is None:
            return 1000.0 if dbu is None else dbu
        if dbu is not None and not math.isclose(dbu, self.grid.dbu, rel_tol=0, abs_tol=1e-8):
            raise ValueError(f"GDS DBU per micron {dbu} differs from VIA1 grid {self.grid.dbu}")
        return self.grid.dbu

    def centre_um(self, row: int, col: int) -> tuple[float, float]:
        if self.grid is not None:
            return self.grid.centre(row, col)
        return (self.origin[0] + col * self.col_pitch + self.col_pitch / 2,
                self.origin[1] + row * self.row_pitch + self.row_pitch / 2)

    def cell_of(self, x_um: float, y_um: float) -> tuple[int, int]:
        if self.grid is not None:
            return self.grid.cell(x_um, y_um)
        c = (x_um - self.origin[0]) / self.col_pitch - 0.5
        r = (y_um - self.origin[1]) / self.row_pitch - 0.5
        if abs(c - round(c)) > 0.01 or abs(r - round(r)) > 0.01:
            raise ValueError(f"via at ({x_um},{y_um}) um is not on the cell grid")
        return int(round(r)), int(round(c))


def read_viamap(path: Path, m: Macro) -> list[int]:
    rows = [int(t, 16) for t in path.read_text().split()]
    if len(rows) != m.rows:
        raise ValueError(f"{path.name}: {len(rows)} rows, macro {m.name} has {m.rows}")
    if any(r >> m.cols for r in rows):
        raise ValueError(f"{path.name}: bits beyond {m.cols} columns")
    return rows


def via_cells(rows: list[int]) -> Iterator[tuple[int, int]]:
    for r, v in enumerate(rows):
        while v:
            low = v & -v
            yield r, low.bit_length() - 1
            v ^= low


def structure_bytes(name: str, m: Macro, rows: list[int], dbu_per_um: float) -> bytes:
    dbu_per_um = m.grid_dbu(dbu_per_um)
    half = V_SZ_NM / 2000.0
    out = [rec(BGNSTR, 2, i2(*([1970, 1, 1, 0, 0, 0] * 2))), rec(STRNAME, 6, name.encode())]
    for r, c in via_cells(rows):
        x, y = m.centre_um(r, c)
        x0, x1, y0, y1 = (round((x - half) * dbu_per_um), round((x + half) * dbu_per_um),
                          round((y - half) * dbu_per_um), round((y + half) * dbu_per_um))
        out += [rec(BOUNDARY, 0), rec(LAYER, 2, i2(V1_LAYER)), rec(DATATYPE, 2, i2(V1_DT)),
                rec(XY, 3, i4(x0, y0, x1, y0, x1, y1, x0, y1, x0, y0)), rec(ENDEL, 0)]
    out.append(rec(ENDSTR, 0))
    return b"".join(out)


def lib_header(dbu_per_um: float, libname: str) -> bytes:
    return b"".join([rec(HEADER, 2, i2(600)), rec(BGNLIB, 2, i2(*([1970, 1, 1, 0, 0, 0] * 2))),
                     rec(LIBNAME, 6, libname.encode()),
                     rec(UNITS, 5, real8_enc(1.0 / dbu_per_um) + real8_enc(1e-6 / dbu_per_um))])


def overlay_name(m: Macro, rows: list[int]) -> str:
    h = hashlib.sha256("".join(f"{r:x}\n" for r in rows).encode()).hexdigest()[:12]
    return f"{m.name}__VIA1_{h}"


def write_overlay(m: Macro, viamap: Path, out: Path, dbu_per_um: float | None = None) -> str:
    dbu_per_um = m.grid_dbu(dbu_per_um)
    rows = read_viamap(viamap, m)
    name = overlay_name(m, rows)
    out.write_bytes(lib_header(dbu_per_um, name) + structure_bytes(name, m, rows, dbu_per_um) + rec(ENDLIB, 0))
    return name


# ---------------------------------------------------------------------------
# read back
# ---------------------------------------------------------------------------

def iter_structures(path: Path, collect_rects: Callable[[str], bool], top: str | None = None):
    """Yield each selected structure's VIA1 rectangles or the top's SREFs, then release its geometry."""
    dbu = 0.0
    name = None
    want_rects = False
    rects = []
    refs = []
    element = None
    with open_gds(path) as f:
        for rt, _dt, payload in read_records(f):
            if rt == UNITS:
                dbu = 1.0 / real8_dec(payload[:8])
            elif rt == STRNAME:
                name = strname(payload)
                want_rects = collect_rects(name)
                rects, refs = [], []
            elif rt == ENDSTR:
                if want_rects or name == top:
                    yield name, dbu, rects, refs
                name = None
                want_rects = False
            elif rt in (BOUNDARY, SREF):
                selected = (rt == BOUNDARY and want_rects) or (rt == SREF and top is not None and name == top)
                element = {"kind": rt, "refl": False, "angle": 0.0} if selected else None
            elif element is not None:
                if rt == LAYER:
                    element["layer"] = struct.unpack(">h", payload)[0]
                elif rt == DATATYPE:
                    element["dt"] = struct.unpack(">h", payload)[0]
                elif rt == SNAME:
                    element["sname"] = strname(payload)
                elif rt == STRANS:
                    element["refl"] = bool(struct.unpack(">H", payload[:2])[0] & 0x8000)
                elif rt == ANGLE:
                    element["angle"] = real8_dec(payload[:8])
                elif rt == XY:
                    element["xy"] = struct.unpack(f">{len(payload) // 4}i", payload)
                elif rt == ENDEL:
                    if element["kind"] == BOUNDARY and (element.get("layer"), element.get("dt")) == (V1_LAYER, V1_DT):
                        xs, ys = element["xy"][0::2], element["xy"][1::2]
                        rects.append((min(xs), min(ys), max(xs), max(ys)))
                    elif element["kind"] == SREF:
                        x, y = element["xy"]
                        refs.append((element["sname"], x, y, element["refl"], element["angle"]))
                    element = None


def decode_rects(m: Macro, rects: list[tuple[int, int, int, int]], dbu: float) -> list[int]:
    dbu = m.grid_dbu(dbu)
    rows = [0] * m.rows
    size = V_SZ_NM / 1000.0
    tolerance = (0.5 if m.grid is not None else 2.0) / dbu
    for x0, y0, x1, y1 in rects:
        if any(abs(side / dbu - size) > tolerance for side in (x1 - x0, y1 - y0)):
            raise ValueError("via rectangle has the wrong size")
        x, y = (x0 + x1) / 2 / dbu, (y0 + y1) / 2 / dbu
        r, c = m.cell_of(x, y)
        if not (0 <= r < m.rows and 0 <= c < m.cols) or (rows[r] >> c) & 1:
            raise ValueError(f"via at row {r} col {c} out of range or duplicated")
        rows[r] |= 1 << c
    return rows


def readback_overlay(m: Macro, gds: Path) -> list[int]:
    result = None
    for name, dbu, rects, _ in iter_structures(gds, lambda _: True):
        if rects or name.startswith(m.name + "__VIA1_"):
            if result is not None:
                raise ValueError("expected one overlay structure, found multiple")
            result = decode_rects(m, rects, dbu)
        del rects
    if result is None:
        raise ValueError("expected one overlay structure, found none")
    return result


# ---------------------------------------------------------------------------
# placement (DEF) and orientation
# ---------------------------------------------------------------------------

# DEF orient -> (reflect about the x axis first (y -> -y), then rotate CCW degrees)
ORIENT = {"N": (False, 0), "W": (False, 90), "S": (False, 180), "E": (False, 270),
          "FS": (True, 0), "FN": (True, 180)}
# FN (mirror about the y axis) = reflect about the x axis, then rotate 180; FS = reflect about the x axis.
# FW/FE are refused (ambiguous composition in DEF); the die-level readback proves each orientation used.


def apply(refl: bool, angle: int, x: float, y: float) -> tuple[float, float]:
    if refl:
        y = -y
    a = math.radians(angle)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def parse_def(path: Path, macro: str) -> tuple[float, dict[str, tuple[float, float, str]]]:
    """DEF units per um and {instance: (x_um, y_um, orient)} of the PLACED/FIXED/COVER components of ``macro``."""
    text = path.read_text()
    u = float(re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", text).group(1))
    sec = re.search(r"COMPONENTS\s+\d+\s*;(.*?)END\s+COMPONENTS", text, re.S)
    out: dict[str, tuple[float, float, str]] = {}
    for stmt in (sec.group(1) if sec else "").split(";"):
        t = stmt.split()
        if len(t) < 2 or t[0] != "-" or t[2] != macro:
            continue
        mm = re.search(r"\+\s*(?:PLACED|FIXED|COVER)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*(\w+)", stmt)
        if not mm:
            raise ValueError(f"{t[1]}: macro instance is not placed")
        if mm.group(3) not in ORIENT:
            raise ValueError(f"{t[1]}: orientation {mm.group(3)} unsupported (N W S E FN FS)")
        out[t[1].replace("\\", "")] = (int(mm.group(1)) / u, int(mm.group(2)) / u, mm.group(3))
    return u, out


def sref_origin(m: Macro, x: float, y: float, orient: str) -> tuple[float, float, bool, int]:
    refl, ang = ORIENT[orient]
    pts = [apply(refl, ang, px, py) for px, py in ((0, 0), (m.w, 0), (m.w, m.h), (0, m.h))]
    return x - min(p[0] for p in pts), y - min(p[1] for p in pts), refl, ang


def instance_rows(manifest: Path, viamap_dir: Path, m: Macro) -> dict[str, list[int]]:
    man = json.loads(manifest.read_text())
    if man["macro"] != m.name:
        raise ValueError(f"manifest macro {man['macro']} != {m.name}")
    out = {}
    for r in man["instances"]:
        vm = viamap_dir / r["viamap"]
        text = vm.read_text()
        if hashlib.sha256(text.encode()).hexdigest() != r["viamap_sha256"]:
            raise ValueError(f"{vm}: SHA-256 differs from the manifest")
        out[r["instance"]] = read_viamap(vm, m)
    return out


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

MAP_ORIENT = {"R0": "N", "MX": "FS", "MY": "FN", "R180": "S"}


def image_file(viamap_dir: Path, image: str) -> Path | None:
    """<image>.viamap.hex, else the flattened frame form of the 10-20 S81 exports ('u_f_0L01.u_r0.u_c1_5' -> u_f_0L01_c1_5)"""
    for name in (image, re.sub(r"\.u_r\d+\.u_", "_", image)):
        f = viamap_dir / f"{name}.viamap.hex"
        if f.is_file():
            return f
    return None


def map_inputs(rommap: Path, viamap_dir: Path, m: Macro, parts: list[str] | None = None,
               allow_missing: bool = False) -> tuple[dict[str, list[int]], dict[str, tuple[float, float, str]], dict[str, Any]]:
    """type_template rommap -> (imgs {key: rows}, placed {key: (x_um, y_um, DEF orient)}, info); key = '<part>/<bound instance>'.
    A map with errors is refused.  A ROM of this macro with no via map file is an error unless allow_missing (then counted)."""
    r = json.loads(rommap.read_text())
    if r.get("errors"):
        raise ValueError(f"{rommap.name}: the map has {len(r['errors'])} error(s), e.g. {r['errors'][0]}")
    imgs: dict[str, list[int]] = {}
    placed: dict[str, tuple[float, float, str]] = {}
    other, missing, files = 0, [], {}
    for pos in r["positions"]:
        if parts and pos["part"] not in parts:
            continue
        for x in pos["roms"]:
            if x["module"] != m.name:
                other += 1
                continue
            key = f"{pos['part']}/{x['bound']}"
            f = image_file(viamap_dir, x["image"])
            if f is None:
                missing.append(f"{key} ({x['image']})")
                continue
            if x.get("die_orient") not in MAP_ORIENT or not x.get("die_xy_um"):
                raise ValueError(f"{key}: no die rectangle / orientation {x.get('die_orient')}")
            if x.get("viamap") and x["viamap"][0].get("sha256") and f.name == x["viamap"][0]["name"] \
                    and hashlib.sha256(f.read_bytes()).hexdigest() != x["viamap"][0]["sha256"]:
                raise ValueError(f"{f}: SHA-256 differs from the map")
            imgs[key] = read_viamap(f, m)
            files[key] = f.name
            placed[key] = (float(x["die_xy_um"][0]), float(x["die_xy_um"][1]), MAP_ORIENT[x["die_orient"]])
    if missing and not allow_missing:
        raise ValueError(f"{len(missing)} {m.name} position(s) have no via map in {viamap_dir}, e.g. {missing[:3]}")
    if not placed:
        raise ValueError("no ROM position selected")
    return imgs, placed, {"positions_selected": len({k.split('/')[0] for k in placed}), "other_macro_rows": other,
                          "missing_viamap": len(missing), "image_files": len(set(files.values()))}


def empty_stream(out: Path, top: str, dbu_per_um: float = 1000.0) -> None:
    out.write_bytes(lib_header(dbu_per_um, top) + rec(BGNSTR, 2, i2(*([1970, 1, 1, 0, 0, 0] * 2))) + rec(STRNAME, 6, top.encode())
                    + rec(ENDSTR, 0) + rec(ENDLIB, 0))


def open_gds(path: Path) -> BinaryIO:
    return gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")


def merge_map(die: Path | None, top: str, rommap: Path, m: Macro, viamap_dir: Path, out: Path, parts: list[str] | None = None,
              allow_missing: bool = False, dbu_per_um: float | None = None) -> dict[str, Any]:
    lock = out.with_name(out.name + ".writer")
    partial = out.with_name(out.name + ".part")
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise FileExistsError(f"{out}: writer reservation exists at {lock}") from exc
    try:
        for path in (out, partial):
            if os.path.lexists(path):
                raise FileExistsError(f"{out}: refusing to overwrite {path}")
        imgs, placed, info = map_inputs(rommap, viamap_dir, m, parts, allow_missing)
        dbu_per_um = m.grid_dbu(dbu_per_um)
        with ExitStack() as stack:
            src = die
            if src is None:
                tmp = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=out.parent)))
                src = tmp / "empty.gds"
                empty_stream(src, top, dbu_per_um)
            raw = stack.enter_context(partial.open("xb"))
            stream = raw
            if out.suffix == ".gz":
                stream = stack.enter_context(gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=1, mtime=0))
            res = merge_placed(src, top, m, imgs, placed, stream)
        # Publish without replacing a file created by a process outside this reservation.
        os.link(partial, out)
        partial.unlink()
    finally:
        lock.rmdir()
    return dict(res, **info, overlay_only=die is None)


def verify_map(die: Path, top: str, rommap: Path, m: Macro, viamap_dir: Path, parts: list[str] | None = None,
               allow_missing: bool = False) -> dict[str, Any]:
    imgs, placed, info = map_inputs(rommap, viamap_dir, m, parts, allow_missing)
    return dict(verify_placed(die, top, m, imgs, placed), **info)


def merge(die: Path, top: str, def_path: Path, m: Macro, manifest: Path, viamap_dir: Path, out: Path) -> dict[str, Any]:
    imgs = instance_rows(manifest, viamap_dir, m)
    _u, placed = parse_def(def_path, m.name)
    return merge_placed(die, top, m, imgs, placed, out)


def merge_placed(die: Path, top: str, m: Macro, imgs: dict[str, list[int]], placed: dict[str, tuple[float, float, str]],
                 out: Path | BinaryIO) -> dict[str, Any]:
    """one overlay structure per unique image appended to the stream, one SREF per placed instance inside ``top``"""
    missing = sorted(set(placed) - set(imgs))
    if missing:
        raise ValueError(f"{len(missing)} placed {m.name} instance(s) have no via map, e.g. {missing[:3]}")
    unused = sorted(set(imgs) - set(placed))
    names = {i: overlay_name(m, rows) for i, rows in imgs.items() if i in placed}
    uniq = {names[i]: imgs[i] for i in names}
    dbu = 0.0
    seen: set[str] = set()
    cur = None
    top_seen = False
    if m.grid is not None:
        with open_gds(die) as src:
            for rt, _, payload in read_records(src):
                if rt == UNITS:
                    m.grid_dbu(1.0 / real8_dec(payload[:8]))
                    break
            else:
                raise ValueError(f"{die}: no GDS UNITS record")
    with open_gds(die) as f, (out.open("wb") if isinstance(out, Path) else nullcontext(out)) as o:
        for rt, dt, p in read_records(f):
            if rt == UNITS:
                dbu = m.grid_dbu(1.0 / real8_dec(p[:8]))
            if rt == STRNAME:
                cur = strname(p)
                seen.add(cur)
                top_seen |= cur == top
            if rt == ENDSTR and cur == top:
                for inst, nm in sorted(names.items()):
                    x, y, orient = placed[inst]
                    ox, oy, refl, ang = sref_origin(m, x, y, orient)
                    o.write(rec(SREF, 0) + rec(SNAME, 6, nm.encode()))
                    if refl or ang:
                        o.write(rec(STRANS, 1, struct.pack(">H", 0x8000 if refl else 0)))
                        if ang:
                            o.write(rec(ANGLE, 5, real8_enc(float(ang))))
                    o.write(rec(XY, 3, i4(round(ox * dbu), round(oy * dbu))) + rec(ENDEL, 0))
            if rt == ENDLIB:
                clash = sorted(set(uniq) & seen)
                if clash:
                    raise ValueError(f"overlay structure(s) already in the die GDS: {clash}")
                for nm, rows in sorted(uniq.items()):
                    o.write(structure_bytes(nm, m, rows, dbu))
            o.write(rec(rt, dt, p))
    if not top_seen:
        raise ValueError(f"top structure {top} not in {die}")
    return {"instances_merged": len(names), "unique_images": len(uniq), "def_instances_unused_in_manifest": len(unused),
            "dbu_per_um": dbu, **m.geometry_info()}


def program_macro(base: Path, top: str, m: Macro, viamap: Path, out: Path) -> dict[str, Any]:
    """Apply one mask to the exact unprogrammed top and publish after readback."""
    if m.grid is None or m.grid.base_gds_sha256 is None:
        raise ValueError("full macro assembly needs a VIA1 grid with base_gds_sha256")
    if base.resolve() == out.resolve():
        raise ValueError("the programmed GDS path must differ from the base GDS path")
    digest = hashlib.sha256()
    with base.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != m.grid.base_gds_sha256:
        raise ValueError(f"{base}: SHA-256 differs from the VIA1 grid's unprogrammed GDS")
    seam = None
    if getattr(m.grid, "seam_array_cell", None):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import rom_seam_gate
        seam = rom_seam_gate.residual(base, m.grid.seam_array_cell, top=top)
        if seam["short_seams"]:
            raise ValueError(f"{base}: {seam['short_seams']} gate seam(s) of {m.grid.seam_array_cell} under 100 nm; "
                             "run rom_seam_gate.py fix on the base and bind the grid to the fixed base")
    overlay_prefix = m.name + "__VIA1_"
    for name, _, _, refs in iter_structures(base, lambda n: n.startswith(overlay_prefix), top):
        if name != top or any(ref[0].startswith(overlay_prefix) for ref in refs):
            raise ValueError(f"{base}: found existing programming structures")
    rows = read_viamap(viamap, m)
    images = {m.name: rows}
    placements = {m.name: (0.0, 0.0, "N")}
    with tempfile.TemporaryDirectory(dir=out.parent) as work:
        gds = Path(work) / out.name
        info = merge_placed(base, top, m, images, placements, gds)
        verify = verify_placed(gds, top, m, images, placements)
        if verify["verdict"] != "PASS":
            raise ValueError(f"programmed macro readback failed: {verify['failures']}")
        gds.replace(out)
    return dict(info, structure=overlay_name(m, rows), top=top, readback="PASS", seam_check=seam,
                base_gds_sha256=m.grid.base_gds_sha256, programmed_vias=sum(row.bit_count() for row in rows))


def verify(die: Path, top: str, def_path: Path, m: Macro, manifest: Path, viamap_dir: Path) -> dict[str, Any]:
    """Read every placed instance's vias back out of the die GDS (un-transforming the SREF) and compare with the hex."""
    imgs = instance_rows(manifest, viamap_dir, m)
    _u, placed = parse_def(def_path, m.name)
    return verify_placed(die, top, m, imgs, placed)


def verify_placed(die: Path, top: str, m: Macro, imgs: dict[str, list[int]], placed: dict[str, tuple[float, float, str]]) -> dict[str, Any]:
    overlay_prefix = m.name + "__VIA1_"
    def is_overlay(name: str) -> bool:
        return name.startswith(overlay_prefix)

    masks: dict[str, list[int] | str] = {}
    placements = None
    by_pos = {}
    for name, dbu, rects, refs in iter_structures(die, is_overlay, top):
        if name == top:
            dbu = m.grid_dbu(dbu)
            placements = {}
            for inst, (x, y, orient) in placed.items():
                ox, oy, refl, ang = sref_origin(m, x, y, orient)
                placements[inst] = ((round(ox * dbu), round(oy * dbu)), refl, ang)
            for nm, x, y, refl, angle in refs:
                if is_overlay(nm):
                    by_pos.setdefault((x, y), []).append((nm, refl, angle))
        if is_overlay(name):
            if name in masks:
                raise ValueError(f"duplicate overlay structure {name}")
            try:
                masks[name] = decode_rects(m, rects, dbu)
            except ValueError as exc:
                masks[name] = str(exc)
        # Drop this rectangle list before the iterator reads the next structure.
        del rects
    if placements is None:
        raise ValueError(f"top {top} not in {die}")
    bad, checked = [], 0
    for inst, (xy, refl, ang) in sorted(placements.items()):
        refs = by_pos.get(xy, [])
        if len(refs) != 1 or refs[0][1] != refl or not math.isclose(refs[0][2], ang, abs_tol=1e-9):
            bad.append((inst, "expected exactly one SREF with the correct origin/orientation"))
            continue
        decoded = masks.get(refs[0][0])
        if decoded is None:
            bad.append((inst, "referenced overlay structure is missing"))
            continue
        if isinstance(decoded, str):
            bad.append((inst, decoded))
            continue
        checked += 1
        if decoded != imgs[inst]:
            diff = sum((a ^ b).bit_count() for a, b in zip(decoded, imgs[inst]))
            bad.append((inst, f"{diff} via(s) differ from the hex"))
    return {"verdict": "PASS" if not bad and checked == len(placed) and placed else "FAIL",
            "instances_checked": checked, "instances_placed": len(placed), "failures": bad[:10]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("overlay", "merge", "verify", "readback", "merge-map", "verify-map"):
        s = sub.add_parser(n)
        s.add_argument("--macro", type=Path, required=True, help="macro datasheet JSON from rom_gen compile")
        geometry = s.add_mutually_exclusive_group()
        geometry.add_argument("--array-origin-um", type=float, nargs=2)
        geometry.add_argument("--via-grid", type=Path, help="explicit programming drain coordinates bound to the macro LEF")
        if n in ("overlay", "readback"):
            s.add_argument("--viamap", type=Path, required=True)
        if n == "overlay":
            s.add_argument("--out", type=Path, required=True)
            s.add_argument("--dbu-per-um", type=float)
        if n == "readback":
            s.add_argument("--gds", type=Path, required=True)
        if n in ("merge", "verify"):
            s.add_argument("--die-gds", type=Path, required=True)
            s.add_argument("--top", required=True)
            s.add_argument("--def", dest="def_path", type=Path, required=True)
            s.add_argument("--manifest", type=Path, required=True)
            s.add_argument("--viamap-dir", type=Path, required=True)
        if n == "merge":
            s.add_argument("--out", type=Path, required=True)
        if n in ("merge-map", "verify-map"):
            s.add_argument("--rommap", type=Path, required=True, help="tools/fleet/type_template.py rommap output")
            s.add_argument("--viamap-dir", type=Path, required=True)
            s.add_argument("--top", required=True)
            s.add_argument("--die-gds", type=Path, required=n == "verify-map")
            s.add_argument("--parts", nargs="*", default=None, help="die positions (default: all of the map)")
            s.add_argument("--allow-missing", action="store_true", help="skip (and count) ROMs with no via map file")
        if n == "merge-map":
            s.add_argument("--out", type=Path, required=True, help="fresh output path ending in .gds or .gds.gz")
            s.add_argument("--dbu-per-um", type=float)
    a = ap.parse_args()
    m = Macro(a.macro, tuple(a.array_origin_um) if a.array_origin_um else None, a.via_grid)
    if a.cmd == "overlay":
        print(write_overlay(m, a.viamap, a.out, a.dbu_per_um))
        return 0
    if a.cmd == "readback":
        ok = readback_overlay(m, a.gds) == read_viamap(a.viamap, m)
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    if a.cmd == "merge-map":
        print(json.dumps(merge_map(a.die_gds, a.top, a.rommap, m, a.viamap_dir, a.out, a.parts, a.allow_missing, a.dbu_per_um), indent=1))
        return 0
    if a.cmd == "verify-map":
        res = verify_map(a.die_gds, a.top, a.rommap, m, a.viamap_dir, a.parts, a.allow_missing)
        print(json.dumps(res, indent=1))
        return 0 if res["verdict"] == "PASS" else 1
    if a.cmd == "merge":
        print(json.dumps(merge(a.die_gds, a.top, a.def_path, m, a.manifest, a.viamap_dir, a.out), indent=1))
        return 0
    res = verify(a.die_gds, a.top, a.def_path, m, a.manifest, a.viamap_dir)
    print(json.dumps(res, indent=1))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
