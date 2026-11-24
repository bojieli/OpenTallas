#!/usr/bin/env python3
"""Close ROM array / driver-band gate seams with continuous poly cut by GCUT.

A ROM array cell whose wordline gates end in a stagger (every second gate
carries its gate contact on a 54 nm longer end) leaves those long ends a
short end-to-end gap to the poly of standard cells placed against the array
(the HEAD 4096x274 centre driver band: 56 nm against the 100 nm GATE.S.1
projection limit).  ASAP7 standard cells solve the same seam by running poly
continuously across the cell boundary and cutting it with GCUT.  This tool
does the same for the array cell:

  * every array-cell gate end that faces a non-array gate at an end-to-end
    gap 0 < d < --min-end-space-nm (projection, overlapping x span) is
    extended to touch that gate;
  * the junction must lie strictly inside a GCUT rectangle that covers the
    whole gate width, otherwise the tool refuses (no electrical short);
  * only the array cell's gate BOUNDARY XY records change; every other
    record (vias, programming VIA1 overlay, metals, cells) is copied byte for
    byte, which the report proves with per-layer digests.

Pure stream rewrite, no KLayout needed.  Deterministic, idempotent: a second
run changes nothing.

  rom_seam_gate.py fix --in in.gds --out out.gds --array-cell head_274_array_center \
      [--report report.json]
  rom_seam_gate.py check --in base.gds --array-cell head_274_array_center

A VIA1 grid JSON that names "seam_array_cell" makes rom_viamap_gds
program-macro refuse a base GDS that still has short seams.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rom_viamap_gds import (  # noqa: E402
    ANGLE, BOUNDARY, ENDEL, ENDSTR, LAYER, DATATYPE, SNAME, SREF, STRANS, STRNAME, UNITS, XY,
    read_records, real8_dec, rec, strname,
)

AREF, COLROW, MAG = 0x0B, 0x13, 0x1B
GATE = (7, 0)
GCUT = (10, 0)


def _rect(xy):
    xs, ys = xy[0::2], xy[1::2]
    if len(xy) != 10 or len(set(xs[:4])) != 2 or len(set(ys[:4])) != 2:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def parse(path: Path):
    """Return dbu_um and {cell: {"gate": [(idx, rect)], "gcut": [rect], "refs": [...]}}."""
    cells: dict[str, dict] = {}
    cur = None
    el = None
    dbu_um = None
    with path.open("rb") as f:
        for rt, _dt, p in read_records(f):
            if rt == UNITS:
                dbu_um = real8_dec(p[:8])
            elif rt == STRNAME:
                cur = cells.setdefault(strname(p), {"gate": [], "gcut": [], "refs": [], "nb": 0, "nonrect_gate": 0})
            elif rt == ENDSTR:
                cur = None
            elif rt in (BOUNDARY, SREF, AREF) and cur is not None:
                el = {"k": rt, "refl": False, "angle": 0.0, "mag": 1.0}
                if rt == BOUNDARY:
                    el["idx"] = cur["nb"]
                    cur["nb"] += 1
            elif el is not None:
                if rt == LAYER:
                    el["layer"] = struct.unpack(">h", p)[0]
                elif rt == DATATYPE:
                    el["dt"] = struct.unpack(">h", p)[0]
                elif rt == SNAME:
                    el["sname"] = strname(p)
                elif rt == STRANS:
                    el["refl"] = bool(struct.unpack(">H", p[:2])[0] & 0x8000)
                elif rt == ANGLE:
                    el["angle"] = real8_dec(p[:8])
                elif rt == MAG:
                    el["mag"] = real8_dec(p[:8])
                elif rt == COLROW:
                    el["colrow"] = struct.unpack(">hh", p)
                elif rt == XY:
                    el["xy"] = struct.unpack(f">{len(p) // 4}i", p)
                elif rt == ENDEL:
                    if el["k"] == BOUNDARY:
                        ld = (el.get("layer"), el.get("dt"))
                        if ld in (GATE, GCUT):
                            r = _rect(el["xy"])
                            if ld == GATE:
                                if r is None:
                                    cur["nonrect_gate"] += 1
                                else:
                                    cur["gate"].append((el["idx"], r))
                            elif r is not None:
                                cur["gcut"].append(r)
                    else:
                        if el["mag"] != 1.0:
                            raise SystemExit(f"magnified reference to {el['sname']} not supported")
                        cur["refs"].append(el)
                    el = None
    if dbu_um is None:
        raise SystemExit("no UNITS record")
    return dbu_um, cells


def _xf(refl, angle, ox, oy):
    a = int(round(angle)) % 360
    if a not in (0, 90, 180, 270):
        raise SystemExit(f"non-Manhattan angle {angle}")

    def f(x, y):
        if refl:
            y = -y
        if a == 90:
            x, y = -y, x
        elif a == 180:
            x, y = -x, -y
        elif a == 270:
            x, y = y, -x
        return x + ox, y + oy
    return f


def _xr(f, r):
    x0, y0 = f(r[0], r[1])
    x1, y1 = f(r[2], r[3])
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _placements(el):
    xy = el["xy"]
    if el["k"] == SREF:
        yield xy[0], xy[1]
        return
    nc, nr = el["colrow"]
    (x0, y0), (xc, yc), (xr, yr) = (xy[0], xy[1]), (xy[2], xy[3]), (xy[4], xy[5])
    dcx, dcy = (xc - x0) / nc, (yc - y0) / nc
    drx, dry = (xr - x0) / nr, (yr - y0) / nr
    for i in range(nc):
        for j in range(nr):
            yield int(round(x0 + i * dcx + j * drx)), int(round(y0 + i * dcy + j * dry))


def flatten(cells, top, skip):
    """Flattened (gates, gcuts) of `top` excluding cell `skip`; also the skip cell's placements."""
    has = {}

    def relevant(c):
        if c not in has:
            has[c] = False
            d = cells[c]
            has[c] = bool(d["gate"] or d["gcut"]) or any(relevant(r["sname"]) for r in d["refs"])
        return has[c]

    memo = {}

    def local(c):
        if c in memo:
            return memo[c]
        d = cells[c]
        g = [r for _, r in d["gate"]]
        k = list(d["gcut"])
        for el in d["refs"]:
            s = el["sname"]
            if s == skip or not relevant(s):
                continue
            sg, sk = local(s)
            for ox, oy in _placements(el):
                f = _xf(el["refl"], el["angle"], ox, oy)
                g.extend(_xr(f, r) for r in sg)
                k.extend(_xr(f, r) for r in sk)
        memo[c] = (g, k)
        return memo[c]

    def find(c, f, out):
        for el in cells[c]["refs"]:
            for ox, oy in _placements(el):
                g = _xf(el["refl"], el["angle"], ox, oy)
                h = (lambda g, f: lambda x, y: f(*g(x, y)))(g, f)
                if el["sname"] == skip:
                    out.append((el, h))
                elif relevant(el["sname"]) or skip_reachable(el["sname"]):
                    find(el["sname"], h, out)

    reach = {}

    def skip_reachable(c):
        if c not in reach:
            reach[c] = False
            reach[c] = any(r["sname"] == skip or skip_reachable(r["sname"]) for r in cells[c]["refs"])
        return reach[c]

    gates, gcuts = local(top)
    places = []
    find(top, lambda x, y: (x, y), places)
    return gates, gcuts, places


def plan(cells, top, array_cell, min_space):
    if array_cell not in cells:
        raise SystemExit(f"array cell {array_cell} not in stream")
    if cells[array_cell]["nonrect_gate"]:
        raise SystemExit(f"{array_cell}: {cells[array_cell]['nonrect_gate']} non-rectangular gate shapes")
    others, gcuts, places = flatten(cells, top, array_cell)
    if len(places) != 1:
        raise SystemExit(f"{array_cell} placed {len(places)} times under {top}; in-place edit needs exactly 1")
    el, f = places[0]
    if el["refl"] or int(round(el["angle"])) % 360:
        raise SystemExit("array cell must be placed unrotated/unreflected (R0)")
    ox, oy = f(0, 0)
    gcuts = gcuts + [(k[0] + ox, k[1] + oy, k[2] + ox, k[3] + oy) for k in cells[array_cell]["gcut"]]
    by_lo = defaultdict(list)  # bucket other gates by x span
    for r in others:
        by_lo[r[0]].append(r)
    xs_sorted = sorted(by_lo)
    import bisect

    def overlapping(x0, x1):
        i = bisect.bisect_left(xs_sorted, x0 - 2000)
        while i < len(xs_sorted) and xs_sorted[i] < x1:
            for r in by_lo[xs_sorted[i]]:
                if r[2] > x0 and r[0] < x1:
                    yield r
            i += 1

    def cut_ok(x0, x1, y):
        return any(k[0] <= x0 and k[2] >= x1 and k[1] < y < k[3] for k in gcuts)

    edits = {}
    refused = []
    for idx, r in cells[array_cell]["gate"]:
        x0, y0, x1, y1 = r[0] + ox, r[1] + oy, r[2] + ox, r[3] + oy
        up = [o[1] - y1 for o in overlapping(x0, x1) if o[1] >= y1]
        dn = [y0 - o[3] for o in overlapping(x0, x1) if o[3] <= y0]
        ny0, ny1 = y0, y1
        if up and 0 < min(up) < min_space:
            ny1 = y1 + min(up)
            if not cut_ok(x0, x1, ny1):
                refused.append({"idx": idx, "end": "top", "x0": x0, "y": ny1})
                ny1 = y1
        if dn and 0 < min(dn) < min_space:
            ny0 = y0 - min(dn)
            if not cut_ok(x0, x1, ny0):
                refused.append({"idx": idx, "end": "bottom", "x0": x0, "y": ny0})
                ny0 = y0
        if (ny0, ny1) != (y0, y1):
            edits[idx] = (r[0], ny0 - oy, r[2], ny1 - oy)
    return edits, refused, len(others), len(gcuts)


class _Sink:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def write(self, b):
        return len(b)


def rewrite(src: Path, dst: Path | None, array_cell: str, edits: dict, apply: bool = True):
    digest = defaultdict(hashlib.sha256)
    cur = None
    bidx = -1
    el = None
    buf = []
    changed = 0
    with src.open("rb") as f, (dst.open("wb") if dst else _Sink()) as o:
        for rt, dt, p in read_records(f):
            raw = rec(rt, dt, p)
            if rt == STRNAME:
                cur = strname(p)
                bidx = -1
            elif rt == ENDSTR:
                cur = None
            if rt in (BOUNDARY, SREF, AREF) and cur is not None:
                el = {"k": rt}
                if rt == BOUNDARY:
                    bidx += 1
                    el["idx"] = bidx
                buf = [raw]
                continue
            if el is not None:
                if rt == LAYER:
                    el["layer"] = struct.unpack(">h", p)[0]
                elif rt == DATATYPE:
                    el["dt"] = struct.unpack(">h", p)[0]
                if rt == XY and el["k"] == BOUNDARY and cur == array_cell and el["idx"] in edits \
                        and (el.get("layer"), el.get("dt")) == GATE:
                    el["edited"] = True
                if rt == XY and el.get("edited") and apply:
                    x0, y0, x1, y1 = edits[el["idx"]]
                    raw = rec(XY, dt, struct.pack(">10i", x0, y0, x1, y0, x1, y1, x0, y1, x0, y0))
                    changed += 1
                buf.append(raw)
                if rt == ENDEL:
                    key = f"{el.get('layer')}/{el.get('dt')}" if el["k"] == BOUNDARY else "refs"
                    if not el.get("edited"):
                        digest[key].update(b"".join(buf))
                    o.write(b"".join(buf))
                    el = None
                continue
            digest["frame"].update(raw)
            o.write(raw)
    return changed, {k: v.hexdigest() for k, v in sorted(digest.items())}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def residual(path: Path, array_cell: str, min_end_space_nm: float = 100.0, top: str | None = None) -> dict:
    """Short array/neighbour gate seams left in a stream (0 on a seam-clean macro); used by program_macro."""
    dbu_um, cells = parse(Path(path))
    tops = set(cells) - {r["sname"] for d in cells.values() for r in d["refs"]}
    top = top or (sorted(tops)[0] if len(tops) == 1 else None)
    if top is None:
        raise ValueError(f"several top cells {sorted(tops)}")
    edits, refused, _, _ = plan(cells, top, array_cell, int(round(min_end_space_nm * 1e-3 / dbu_um)))
    return {"top": top, "array_cell": array_cell, "short_seams": len(edits) + len(refused),
            "uncut_junctions": len(refused)}


def fix(args) -> int:
    src, dst = Path(args.inp), Path(args.out)
    dbu_um, cells = parse(src)
    tops = set(cells) - {r["sname"] for d in cells.values() for r in d["refs"]}
    top = args.top or (tops.pop() if len(tops) == 1 else None)
    if top is None:
        raise SystemExit(f"several top cells {sorted(tops)}; pass --top")
    min_space = int(round(args.min_end_space_nm * 1e-3 / dbu_um))
    edits, refused, n_other, n_cut = plan(cells, top, args.array_cell, min_space)
    if refused:
        print(json.dumps({"verdict": "REFUSED", "uncut_junctions": len(refused), "first": refused[:5]}))
        return 2
    _, dig_in = rewrite(src, None, args.array_cell, edits, apply=False)
    changed, _ = rewrite(src, dst, args.array_cell, edits)
    _, dig_out = rewrite(dst, None, args.array_cell, edits, apply=False)
    # recheck: the output has no remaining short seam
    _, cells2 = parse(dst)
    again, refused2, _, _ = plan(cells2, top, args.array_cell, min_space)
    rep = {
        "schema": "opentallas.rom-seam-gate.v1",
        "in": str(src), "in_sha256": sha(src), "out": str(dst), "out_sha256": sha(dst),
        "top": top, "array_cell": args.array_cell, "dbu_um": dbu_um,
        "min_end_space_nm": args.min_end_space_nm,
        "array_gates": len(cells[args.array_cell]["gate"]), "other_gates": n_other, "gcut_rects": n_cut,
        "extended_gates": len(edits), "xy_records_changed": changed,
        "residual_short_seams": len(again) + len(refused2),
        "unchanged_record_digests": dig_out,
        "unchanged_records_identical": dig_in == dig_out,
        "verdict": "PASS" if changed == len(edits) and not again and not refused2 and dig_in == dig_out else "FAIL",
    }
    if args.report:
        Path(args.report).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("verdict", "extended_gates", "residual_short_seams", "out_sha256")}))
    return 0 if rep["verdict"] == "PASS" else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("fix")
    f.add_argument("--in", dest="inp", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--array-cell", required=True)
    f.add_argument("--top")
    f.add_argument("--min-end-space-nm", type=float, default=100.0)
    f.add_argument("--report")
    c = sp.add_parser("check", help="count short seams left (exit 1 if any)")
    c.add_argument("--in", dest="inp", required=True)
    c.add_argument("--array-cell", required=True)
    c.add_argument("--top")
    c.add_argument("--min-end-space-nm", type=float, default=100.0)
    a = ap.parse_args()
    if a.cmd == "check":
        r = residual(Path(a.inp), a.array_cell, a.min_end_space_nm, a.top)
        print(json.dumps(r))
        return 1 if r["short_seams"] else 0
    return fix(a)


if __name__ == "__main__":
    raise SystemExit(main())
