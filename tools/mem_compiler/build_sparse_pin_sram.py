#!/usr/bin/env python3
"""Track-aligned (v2) SRAM abstracts with a SPARSE signal-pin pitch (QW-D2D 2026-10-19, SAFE-DESIGN item 6).

Why: every catalog abstract puts its signal pins at METAL['pin_pitch_um'] = 0.096 um (every other 48 nm M4 track,
10.4 pins/um on each vertical face).  The owner's safe-design rule caps macro-face pin density at 6 pins/um so the
channel beside the face can escape every pin; a dense face is the documented cause of the bksel / bk_g route
failures and of the compute D2D (qfd_d2d_static) SRAM-escape blocker, whose 64x512 macro used only 137 of its 512
columns.  This builder re-runs the SAME sram_gen generator and the SAME v2 alignment rules (build_aligned_v2:
H and W = 0.024 mod 0.048, SYMMETRY X Y, verified on track in R0/MX/MY/R180) with ONE change: the signal-pin
pitch of the listed specs is 0.192 um (every 4th M4 track, 5.21 pins/um).  The macro grows in height only if
its pin block no longer fits (reported as pin_stretch_um).  Every existing view is untouched: the pitch is
patched only inside this script, for the specs listed below, and each output goes to its own new directory.

    python3 tools/mem_compiler/build_sparse_pin_sram.py [--out physical/asap7_memory_macros_v2] [--check-only]
"""
from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import asap7  # noqa: E402
import build_aligned_v2 as v2  # noqa: E402
import sram_gen  # noqa: E402
import views  # noqa: E402

PITCH_UM = 0.192
SPECS = [
    # compute D2D slot store: 4 banks x 64 slots x 137 b (548-b payload); the 64x512 used 137 of 512 columns
    {"name": "ot_sram_1r1w_64x137_m1_r2c2_p192", "words": 64, "bits": 137, "mux": 1, "ports": "1r1w",
     "spare_rows": 2, "spare_cols": 2},
]


@contextlib.contextmanager
def sparse_pitch(pitch: float):
    old = asap7.METAL["pin_pitch_um"]
    asap7.METAL["pin_pitch_um"] = pitch
    try:
        yield
    finally:
        asap7.METAL["pin_pitch_um"] = old


def build(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    entries = {}
    assert views.METAL is asap7.METAL, "views must share asap7.METAL for the pitch patch to apply"
    with sparse_pitch(PITCH_UM), \
         v2.patched(sram_gen, macro_outline=v2.aligned_outline, write_lef=v2.aligned_write_lef,
                    GENERATOR_VERSION=f"{sram_gen.GENERATOR_VERSION}+{v2.ALIGN_VERSION}+p192"):
        for s in SPECS:
            sheet = sram_gen.compile_macro(sram_gen.SramSpec(**s), out)
            a = sheet["area"]
            e = v2.finish(out, s["name"], None, (a["macro_width_um"], a["macro_height_um"]),
                          {"kind": "sram", "spec": s, "pin_pitch_um": PITCH_UM,
                           "builder_sparse": "tools/mem_compiler/build_sparse_pin_sram.py"})
            lef = (out / s["name"] / f"{s['name']}.lef").read_text()
            faces = face_density(lef)
            e["pin_faces"] = faces
            entries[s["name"]] = e
    return entries


def face_density(lef: str) -> dict:
    import re
    sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", lef)
    W = float(sz.group(1))
    faces: dict[str, list[float]] = {"W": [], "E": []}
    for m in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1", lef, re.S):
        body = m.group(2)
        if "USE POWER" in body or "USE GROUND" in body:
            continue
        r = re.search(r"RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)", body)
        x1, y1, x2, y2 = map(float, r.groups())
        faces["W" if x1 < W / 2 else "E"].append((y1 + y2) / 2)
    res = {}
    for f, ys in faces.items():
        ys.sort()
        span = ys[-1] - ys[0]
        res[f] = {"pins": len(ys), "span_um": round(span, 3), "pins_per_um": round(len(ys) / span, 3),
                  "min_pitch_um": round(min(b - a for a, b in zip(ys, ys[1:])), 3)}
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=v2.V2_DIR)
    ap.add_argument("--check-only", action="store_true", help="rebuild in a temporary directory and compare")
    a = ap.parse_args(argv)
    if a.check_only:
        with tempfile.TemporaryDirectory() as t:
            build(Path(t))
            bad = [s["name"] for s in SPECS for f in (Path(t) / s["name"]).iterdir()
                   if (a.out / s["name"] / f.name).read_bytes() != f.read_bytes()]
            print("CHECK", "PASS" if not bad else f"FAIL {bad}")
            return 1 if bad else 0
    for s in SPECS:
        if (a.out / s["name"]).exists():
            shutil.rmtree(a.out / s["name"])
    ents = build(a.out)
    (a.out / "sparse_pin_index.json").write_text(json.dumps(
        {"builder": "tools/mem_compiler/build_sparse_pin_sram.py", "pin_pitch_um": PITCH_UM,
         "builder_sha256": asap7.sha256_file(Path(__file__)), "macros": ents}, indent=1, sort_keys=True) + "\n")
    for n, e in ents.items():
        print(n, e["width_um"], "x", e["height_um"], json.dumps(e["pin_faces"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
