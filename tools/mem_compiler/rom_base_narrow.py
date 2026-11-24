#!/usr/bin/env python3
"""Derive a narrower-word ROM base GDS + VIA1 grid from a released, seam-fixed base.

The 11-23 delete took the trial array generator with it (it lived only in the
lane bin/ and was never committed). The released HEAD 4096x274 base,
physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/*.base_head_driver.gds.gz,
is seam-fixed (rom_seam_gate, deck-clean prog_seam 0d03bbe5) and carries the
same 4096-word, mux-8 native array, wordline driver band and PG as any
narrower 4096xN_m8 macro of the same height.  The signed ot_rom_4096x266_m8
LEF differs from the 274 LEF only in SIZE x (121.848 vs 125.304) and in the
M4 VDD/VSS stripe right ends (121.548 vs 125.004); the 266 LEF's q pins are
abstract 24 nm stubs and are not drawn in either base.

This tool:
  * rewrites the M4 stripes whose right end sits at the source outline - margin
    to end at the destination outline - margin (BOUNDARY XY only),
  * refuses if any other drawn shape or placed cell would cross the
    destination outline,
  * renames the array/top structures (STRNAME/SNAME records),
  * copies every other record byte for byte (per-layer digests in the report),
  * writes a VIA1 grid for N = cols/mux bits. The 'drop' outer columns of each
    bank side become unprogrammed edge-dummy bitlines. Their drains stay in the
    base, and no logical bit maps to them.  Edge columns nearest the macro
    boundary are dropped, so the driver band seam and all interior geometry
    are unchanged.

Pure stream rewrite, no KLayout.

  rom_base_narrow.py --base-gds 274.gds[.gz] --src-grid 274.via_grid.json --src-lef 274.lef \
      --dst-macro 266.json --out-gds 266.base.gds --out-grid 266.via_grid.json \
      --src-array head_274_array_center --dst-array qc_266_array_center \
      --src-top ot_rom_head_driver_trial --dst-top ot_rom_qc266_driver_trial [--report r.json]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rom_viamap_gds import (  # noqa: E402
    BOUNDARY, ENDEL, ENDSTR, LAYER, DATATYPE, SNAME, SREF, STRNAME, UNITS, XY, read_records, real8_dec, rec,
)

AREF = 0x0B
M4 = (40, 0)


def lef_size(text: str) -> tuple[float, float]:
    m = re.search(r"^\s*SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;", text, re.M)
    if not m:
        raise SystemExit("LEF has no SIZE")
    return float(m.group(1)), float(m.group(2))


def lef_pg_right(text: str) -> set[float]:
    """right x of every M4 RECT in the VDD/VSS pins"""
    out = set()
    for pin in ("VDD", "VSS"):
        m = re.search(rf"PIN {pin}\b(.*?)END {pin}\b", text, re.S)
        if not m:
            raise SystemExit(f"LEF has no PIN {pin}")
        for r in re.finditer(r"RECT\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", m.group(1)):
            out.add(float(r.group(3)))
    return out


def open_in(p: Path):
    return gzip.open(p, "rb") if p.suffix == ".gz" else p.open("rb")


def derive(a) -> dict:
    src_lef = Path(a.src_lef).read_text()
    dst_sheet = json.loads(Path(a.dst_macro).read_text())
    dst_lef_path = Path(a.dst_macro).with_name(dst_sheet["spec"]["name"] + ".lef")
    dst_lef_bytes = dst_lef_path.read_bytes()
    dst_lef = dst_lef_bytes.decode()
    dst_lef_sha = hashlib.sha256(dst_lef_bytes).hexdigest()
    if dst_sheet["views"].get(dst_lef_path.name) != dst_lef_sha:
        raise SystemExit(f"{dst_lef_path}: LEF SHA-256 differs from the datasheet")
    (sw, sh), (dw, dh) = lef_size(src_lef), lef_size(dst_lef)
    if abs(sh - dh) > 1e-9 or dw > sw:
        raise SystemExit("destination must have the same height and be no wider")
    src_r, dst_r = lef_pg_right(src_lef), lef_pg_right(dst_lef)
    if len(src_r) != 1 or len(dst_r) != 1:
        raise SystemExit("expected one common M4 PG right end per LEF")
    src_r, dst_r = src_r.pop(), dst_r.pop()
    margin = round(sw - src_r, 6)
    if abs((dw - dst_r) - margin) > 1e-9:
        raise SystemExit("PG margin differs between LEFs")
    grid = json.loads(Path(a.src_grid).read_text())
    dbu = grid["dbu_per_um"]
    src_x, dst_x, dst_lim = round(src_r * dbu), round(dst_r * dbu), round(dw * dbu)

    rename = {a.src_array: a.dst_array, a.src_top: a.dst_top}
    out_gds = Path(a.out_gds)
    tmp = out_gds.with_name(out_gds.name + ".part")
    digests: dict[str, "hashlib._Hash"] = defaultdict(hashlib.sha256)
    clipped = 0
    max_x = 0
    cell_bbox: dict[str, list[int]] = {}
    refs: list[tuple[str, str, int, int]] = []
    cur = None
    el = None
    buf: list[tuple[int, int, bytes]] = []
    with open_in(Path(a.base_gds)) as f, tmp.open("wb") as o:
        for rt, dt, p in read_records(f):
            if rt == UNITS and abs(real8_dec(p[8:16]) - 1e-6 / dbu) > 1e-18:
                raise SystemExit("GDS database unit differs from the grid")
            if rt == STRNAME:
                cur = p.rstrip(b"\0").decode()
                cell_bbox.setdefault(cur, [10**12, 10**12, -10**12, -10**12])
                if cur in rename:
                    p = rename[cur].encode()
                o.write(rec(rt, dt, p))
                continue
            if rt == ENDSTR:
                cur = None
            if rt in (BOUNDARY, SREF, AREF) and cur is not None:
                el = {"k": rt}
                buf = [(rt, dt, p)]
                continue
            if el is not None:
                if rt == LAYER:
                    el["layer"] = struct.unpack(">h", p)[0]
                elif rt == DATATYPE:
                    el["dt"] = struct.unpack(">h", p)[0]
                elif rt == SNAME:
                    el["sname"] = p.rstrip(b"\0").decode()
                    if el["sname"] in rename:
                        p = rename[el["sname"]].encode()
                elif rt == XY:
                    xy = list(struct.unpack(f">{len(p) // 4}i", p))
                    if el["k"] == BOUNDARY:
                        key = f"{el.get('layer')}/{el.get('dt')}"
                        if (el.get("layer"), el.get("dt")) == M4 and src_x in xy[0::2]:
                            xs = xy[0::2]
                            if len(xy) != 10 or len(set(xs[:4])) != 2 or max(xs) != src_x:
                                raise SystemExit("M4 stripe at the PG end is not a rectangle ending there")
                            xy = [dst_x if (i % 2 == 0 and v == src_x) else v for i, v in enumerate(xy)]
                            p = struct.pack(f">{len(xy)}i", *xy)
                            clipped += 1
                            key = "40/0:clipped"
                        el["key"] = key
                        b = cell_bbox[cur]
                        b[0] = min(b[0], *xy[0::2]); b[2] = max(b[2], *xy[0::2])
                        b[1] = min(b[1], *xy[1::2]); b[3] = max(b[3], *xy[1::2])
                    else:
                        el["xy"] = xy
                buf.append((rt, dt, p))
                if rt == ENDEL:
                    blob = b"".join(rec(*r) for r in buf)
                    if el["k"] == BOUNDARY:
                        digests[el["key"]].update(blob)
                    else:
                        digests["refs"].update(blob)
                        refs.append((cur, el["sname"], el["xy"][0], el["xy"][1]))
                        if el["k"] == AREF:
                            refs.append((cur, el["sname"], max(el["xy"][0::2]), max(el["xy"][1::2])))
                    o.write(blob)
                    el = None
                continue
            o.write(rec(rt, dt, p))
    # outline check: every top-level/array shape and every placed child bbox inside [0, dw]
    for parent, child, x, y in refs:
        cb = cell_bbox.get(child)
        if cb and cb[2] > -10**12:
            max_x = max(max_x, x + cb[2])
    for cell in (a.src_array, a.src_top):
        max_x = max(max_x, cell_bbox[cell][2])
    if max_x > dst_lim:
        tmp.unlink()
        raise SystemExit(f"geometry reaches x={max_x / dbu} um beyond the {dw} um outline")
    if clipped == 0:
        tmp.unlink()
        raise SystemExit("no M4 stripe ends at the source PG end")
    tmp.replace(out_gds)
    out_sha = hashlib.sha256(out_gds.read_bytes()).hexdigest()

    # VIA1 grid: banks that share one row axis form a half of the array; each half drops the
    # same number of columns, split evenly over its banks, taken at each bank's macro-edge end
    # (farthest from the driver band). Those columns stay in the base as unprogrammed edge dummies.
    sp = dst_sheet["spec"]
    rows, cols = sp["words"] // sp["mux"], sp["bits"] * sp["mux"]
    order = sorted(grid["banks"], key=lambda b: b["col_start"])
    groups = defaultdict(list)
    for b in order:
        groups[tuple(b["rows_dbu"])].append(b)
    src_cols = sum(len(b["cols_dbu"]) for b in order)
    if cols % len(groups) or src_cols % len(groups):
        raise SystemExit("columns do not split over the array halves")
    dropped = {}
    new = {}
    for key, hb in groups.items():
        drop = sum(len(b["cols_dbu"]) for b in hb) - cols // len(groups)
        if drop < 0 or drop % len(hb):
            raise SystemExit("destination columns do not split evenly over the source banks")
        k = drop // len(hb)
        lo = min(min(b["cols_dbu"]) for b in hb)
        hi = max(max(b["cols_dbu"]) for b in hb)
        mid = (lo + hi) / 2
        for b in hb:
            c = b["cols_dbu"]
            outer_first = abs(c[0] - mid) > abs(c[-1] - mid)
            keep = c[k:] if outer_first else c[:len(c) - k]
            dropped[b["col_start"]] = (c[:k] if outer_first else c[len(c) - k:])
            new[b["col_start"]] = dict(b, cols_dbu=keep)
    out_banks = []
    nxt = 0
    for b in order:
        nb = new[b["col_start"]]
        nb["col_start"] = nxt
        nxt += len(nb["cols_dbu"])
        out_banks.append(nb)
    if nxt != cols or any(b["row_start"] + len(b["rows_dbu"]) > rows for b in out_banks):
        raise SystemExit(f"grid covers {nxt} columns, macro needs {cols}")
    out = {"schema": "opentallas.rom-via-grid.v1", "dbu_per_um": dbu, "lef_sha256": dst_lef_sha,
           "banks": out_banks, "base_gds_sha256": out_sha, "seam_array_cell": a.dst_array}
    Path(a.out_grid).write_text(json.dumps(out, indent=1) + "\n")
    rep = {"schema": "opentallas.rom-base-narrow.v1", "in": str(a.base_gds), "out": str(out_gds), "out_sha256": out_sha,
           "src_outline_um": [sw, sh], "dst_outline_um": [dw, dh], "pg_right_um": [src_r, dst_r],
           "m4_stripes_clipped": clipped, "max_drawn_x_um": max_x / dbu, "rename": rename,
           "grid_rows_cols": [rows, cols],
           "edge_dummy_columns": {str(k): [v / dbu for v in vs] for k, vs in sorted(dropped.items())},
           "record_digests": {k: v.hexdigest() for k, v in sorted(digests.items())}}
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k in ("base-gds", "src-grid", "src-lef", "dst-macro", "out-gds", "out-grid", "src-array", "dst-array", "src-top", "dst-top"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--report")
    a = ap.parse_args()
    rep = derive(a)
    print(json.dumps({k: rep[k] for k in ("out_sha256", "m4_stripes_clipped", "max_drawn_x_um", "grid_rows_cols")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
