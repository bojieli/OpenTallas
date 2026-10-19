#!/usr/bin/env python3
"""KV D2D slot-store SRAM family (KV-SRAM-D2D 2026-10-19, SAFE-DESIGN item 6): truthful right-sized macros.

Why: the KV D2D link end (qkd_d2d_static_sf / _ovl_sf, kits r7w_sf / ovl_sf) stores its 548-b slot payload in four
banks of the catalog macro ot_sram_1r1w_64x512_m1_r2c2 (171.288 x 77.784 um, LEF ec986c5e) and uses 137 of its
512 columns; the macro's W / E faces carry 793 / 792 signal pins at 0.096 um = 10.195 / 10.182 pins/um (> 6, Codex
HOLD 12:48).  The logic needs exactly 4 banks x 64 slots x 137 b (FW 548 = 4 x 137; slot lifetime = 64 slots, 6-b
slot address; 1R1W on one clock; same-cycle and one-cycle-old write ages bypassed in the leaf).  This builder runs
the SAME sram_gen generator and the SAME v2 alignment (build_aligned_v2: H, W = 0.024 mod 0.048, SYMMETRY X Y,
on track in R0/MX/MY/R180) for exactly that shape, with ONE change, the signal-pin pitch:

  d2d_sram_1r1w_64x137_m1_r2c2_p192   pitch 0.192 um (every 4th M4 track)  PRIMARY
  d2d_sram_1r1w_64x137_m1_r2c2_p288   pitch 0.288 um (every 6th M4 track)  PARALLEL FALLBACK, taller pin face

Capacity, word width, ports, spare rows / columns, read / write timing semantics and the behavioural model come
from the generator unchanged (only the outline grows when the pin block needs more face).  Macro names carry the
d2d_ prefix so they never collide with the Qwen compute-die candidate (ot_sram_1r1w_64x137_m1_r2c2_p192) or the
KV CTL family (lane KV-SRAM-CTL).  Every view goes to its own new directory; no existing view is touched.

    python3 tools/mem_compiler/build_d2d_sram_1019.py [--out physical/asap7_memory_macros_v2] [--check-only]
"""
from __future__ import annotations

import argparse
import contextlib
import json
import re
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

BASE = {"words": 64, "bits": 137, "mux": 1, "ports": "1r1w", "spare_rows": 2, "spare_cols": 2}
SPECS = [
    ({"name": "d2d_sram_1r1w_64x137_m1_r2c2_p192", **BASE}, 0.192),
    ({"name": "d2d_sram_1r1w_64x137_m1_r2c2_p288", **BASE}, 0.288),
]
LIMIT_PINS_PER_UM = 6.0


@contextlib.contextmanager
def pitch(p: float):
    old = asap7.METAL["pin_pitch_um"]
    asap7.METAL["pin_pitch_um"] = p
    try:
        yield
    finally:
        asap7.METAL["pin_pitch_um"] = old


def face_density(lef: str) -> dict:
    W = float(re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", lef).group(1))
    faces: dict[str, list[float]] = {"W": [], "E": []}
    for m in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1", lef, re.S):
        body = m.group(2)
        if "USE POWER" in body or "USE GROUND" in body:
            continue
        x1, y1, x2, y2 = map(float, re.search(r"RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)", body).groups())
        faces["W" if x1 < W / 2 else "E"].append((y1 + y2) / 2)
    res = {}
    for f, ys in faces.items():
        ys.sort()
        span = ys[-1] - ys[0]
        win = max(sum(1 for y in ys if a <= y < a + 1.0) for a in ys)  # densest 1-um window
        res[f] = {"pins": len(ys), "span_um": round(span, 3), "pins_per_um": round(len(ys) / span, 3),
                  "min_pitch_um": round(min(b - a for a, b in zip(ys, ys[1:])), 3), "max_in_1um": win}
    return res


def build(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    assert views.METAL is asap7.METAL
    ents = {}
    for s, p in SPECS:
        with pitch(p), v2.patched(sram_gen, macro_outline=v2.aligned_outline, write_lef=v2.aligned_write_lef,
                                  GENERATOR_VERSION=f"{sram_gen.GENERATOR_VERSION}+{v2.ALIGN_VERSION}+p{int(p*1000)}"):
            sheet = sram_gen.compile_macro(sram_gen.SramSpec(**s), out)
            a = sheet["area"]
            e = v2.finish(out, s["name"], None, (a["macro_width_um"], a["macro_height_um"]),
                          {"kind": "sram", "spec": s, "pin_pitch_um": p,
                           "builder_d2d": "tools/mem_compiler/build_d2d_sram_1019.py"})
        faces = face_density((out / s["name"] / f"{s['name']}.lef").read_text())
        e["pin_faces"] = faces
        e["face_rule_pass"] = all(f["pins_per_um"] <= LIMIT_PINS_PER_UM and f["max_in_1um"] <= LIMIT_PINS_PER_UM
                                  for f in faces.values())
        assert e["face_rule_pass"], (s["name"], faces)
        ents[s["name"]] = e
    return ents


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=v2.V2_DIR)
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args(argv)
    if a.check_only:
        with tempfile.TemporaryDirectory() as t:
            build(Path(t))
            bad = [s["name"] + "/" + f.name for s, _ in SPECS for f in (Path(t) / s["name"]).iterdir()
                   if (a.out / s["name"] / f.name).read_bytes() != f.read_bytes()]
            print("CHECK", "PASS" if not bad else f"FAIL {bad}")
            return 1 if bad else 0
    for s, _ in SPECS:
        if (a.out / s["name"]).exists():
            shutil.rmtree(a.out / s["name"])
    ents = build(a.out)
    (a.out / "d2d_sram_index_1019.json").write_text(json.dumps(
        {"builder": "tools/mem_compiler/build_d2d_sram_1019.py", "builder_sha256": asap7.sha256_file(Path(__file__)),
         "limit_pins_per_um": LIMIT_PINS_PER_UM, "replaces": "ot_sram_1r1w_64x512_m1_r2c2 (137/512 columns used, W/E "
         "793/792 pins = 10.195/10.182 per um)", "macros": ents}, indent=1, sort_keys=True) + "\n")
    for n, e in ents.items():
        print(n, e["width_um"], "x", e["height_um"], json.dumps(e["pin_faces"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
