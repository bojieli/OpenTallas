#!/usr/bin/env python3
"""S81 plan event 2026-11-11 (DS85-LLPINS, DIE-S81-85 ruling 11-11): move two plan pins per LL network node onto their
EXISTING outline-face PORT RECT (same form as delta_bfcfg47_1027.py / delta_ninepins_1027.py).

Plan-only: every LEF is byte-identical.  dsfd_node_LLd fo[0] (M5, S) + rst_n[0] (M4, E); dsfd_node_LLfd / LLfu fi[0]
(M5, N) + fo[0] (M5, S).  Each pin has an outline-face PORT RECT of the canonical pin size plus an inset access
extension; the plan centre was the centre of the extension (the largest RECT), up to 1.03 um off the face, so the
routed kit pin_audit reported wrong_place on the rebuilt LL cores (DS85 child rebuild 11-11, kits dsfd_node_LL*_d85).
The new centre is the centre of the face RECT, i.e. the generator's canonical face pin (gen_core_kit_legacy RECT),
wholly inside that PORT RECT and on the same face.  No LEF move, no body/clock/latency change.

Input: delta_llpins_1111.json.  Fail-closed checks: base pin-file sha256, LEF sha256, each pin's old centre + layer,
the selected RECT is a PORT RECT of that pin on that layer in the kit (plan) LEF and touches the outline face, and the
canonical pin shape at the new centre lies inside it and touches the same face.  pinhash recomputed as in
delta_kitsspare2_1025.py; the file's own serialisation is kept.

  python3 physical/die_plan/s81/delta_llpins_1111.py [--check]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from delta_ninepins_1027 import FORMATS, PINS, EPS, lef_port_rects, lef_text  # noqa: E402

DELTA = HERE / "delta_llpins_1111.json"
TAG = "DS85-LLPINS"
SHAPE = {"M3": (0.018, 0.038), "M4": (0.084, 0.024), "M5": (0.024, 0.084)}   # == gen_core_kit_legacy.RECT


def apply(check_only=False):
    delta = json.loads(DELTA.read_text())
    out = []
    for core in delta["cores"]:
        mod = core["module"]
        f = PINS / f"{mod}.json"
        raw = f.read_bytes()
        fmt = next((k for k in FORMATS if FORMATS[k](json.loads(raw)) == raw.decode()), None)
        if fmt is None:
            raise SystemExit(f"{mod}: unknown pin-table serialisation (refusing to reformat)")
        cur = hashlib.sha256(raw).hexdigest()
        d = json.loads(raw)
        lefb = lef_text(d["lef"])
        if hashlib.sha256(lefb).hexdigest() != core["base_lef_sha256"]:
            raise SystemExit(f"{mod}: LEF {d['lef']} differs from the delta base (no LEF move allowed)")
        lef = lefb.decode()
        w, h = core["outline_um"]
        by = {p["name"]: p for p in d["pins"]}
        done = all([by[m["pin"]]["x"], by[m["pin"]]["y"]] == m["new_center_um"] for m in core["pins"])
        if not done and cur != core["base_pins_sha256"]:
            raise SystemExit(f"{mod}: pin table changed since the delta base ({cur[:12]})")
        for m in core["pins"]:
            p = by[m["pin"]]
            if p["layer"] != m["layer"]:
                raise SystemExit(f"{mod}.{m['pin']}: layer {p['layer']} != {m['layer']}")
            r = m["selected_existing_edge_rect_um"]
            if not any(all(abs(a - b) < EPS for a, b in zip(r, q)) for q in lef_port_rects(lef, m["pin"], m["layer"])):
                raise SystemExit(f"{mod}.{m['pin']}: selected RECT {r} is not a {m['layer']} PORT RECT in the LEF")
            faces = {"W": abs(r[0]), "S": abs(r[1]), "E": abs(r[2] - w), "N": abs(r[3] - h)}
            face = min(faces, key=faces.get)
            if faces[face] > EPS:
                raise SystemExit(f"{mod}.{m['pin']}: selected RECT {r} does not touch the outline")
            sw, sh = SHAPE[m["layer"]]
            cx, cy = m["new_center_um"]
            s = [cx - sw / 2, cy - sh / 2, cx + sw / 2, cy + sh / 2]
            inside = s[0] >= r[0] - EPS and s[1] >= r[1] - EPS and s[2] <= r[2] + EPS and s[3] <= r[3] + EPS
            sface = {"W": abs(s[0]), "S": abs(s[1]), "E": abs(s[2] - w), "N": abs(s[3] - h)}[face]
            if not inside or sface > EPS:
                raise SystemExit(f"{mod}.{m['pin']}: canonical pin {s} at the new centre is not on the {face} face "
                                 f"inside the existing edge RECT {r}")
            if not done and [p["x"], p["y"]] != m["old_center_um"]:
                raise SystemExit(f"{mod}.{m['pin']}: old centre {[p['x'], p['y']]} != {m['old_center_um']}")
            p["x"], p["y"] = m["new_center_um"]
        d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
        if TAG not in d["source"]:
            d["source"] += (f"; S81 plan event 2026-11-11 {TAG} (delta_llpins_1111.py): "
                            f"{len(core['pins'])} pin centre(s) -> existing outline-face PORT RECT, LEF unchanged")
        out.append((mod, len(core["pins"]), "already applied" if done else "applied"))
        if not check_only and not done:
            f.write_text(FORMATS[fmt](d))   # same serialisation as the file had
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only, write nothing")
    for row in apply(ap.parse_args().check):
        print(*row)
