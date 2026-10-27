#!/usr/bin/env python3
"""S81 plan event 2026-10-27 (S81-CORES-R22, COORD ruling 10-27 15:1x): adopt the EXISTING .084 um edge PORT
RECT centres for the eight dsdv_gunit_l2 data/control pins and the ot_s81_cfg7_seq_bfp rst_n[0] reset pin.

Plan-only: the LEFs are byte-identical (each pin already has an edge RECT at the outline face plus an inset
access extension; the plan centre pointed at the inset extension's centre).  The die plan pin table now names
the centre of the existing edge RECT, so the parent route lands on the face rectangle, not inside the core.
No LEF move, no body/clock/latency change; H0 (dsdv_eng_rr_h0) untouched.  The graded-mesh rails of the same
COORD ruling are NOT part of this event (their encoder does not yet preserve the real rail topology / PG spacing
with a full-metal review; see lanes/S81-CORES.md R22).

Input: delta_ninepins_1027.json (typed candidate from the r20_models child: base pin/LEF hashes, old/new centres,
existing RECTs).  Fail-closed checks: base pin-file sha256, LEF sha256 (git HEAD content), each pin's old centre +
layer, and the selected edge RECT is a PORT RECT of that pin on that layer in the LEF and touches the outline face
with the new centre at its centre.  pinhash recomputed as in delta_kitsspare2_1025.py.

  python3 physical/die_plan/s81/delta_ninepins_1027.py [--check]
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DELTA = HERE / "delta_ninepins_1027.json"
PINS = HERE / "inputs" / "core_pins"
EPS = 1e-6
FORMATS = {  # existing pin tables use one of these byte forms; keep each file's own form (minimal diff)
    "indent0": lambda d: json.dumps(d, indent=0),
    "indent0_nl": lambda d: json.dumps(d, indent=0) + "\n",
    "compact": lambda d: json.dumps(d),
    "compact_nl": lambda d: json.dumps(d) + "\n",
    "indent2_nl": lambda d: json.dumps(d, indent=2) + "\n",
}


def lef_port_rects(lef_text, pin, layer):
    m = re.search(r"^\s*PIN\s+" + re.escape(pin) + r"\s*$(.*?)^\s*END\s+" + re.escape(pin) + r"\s*$",
                  lef_text, re.S | re.M)
    if not m:
        raise SystemExit(f"LEF has no PIN {pin}")
    rects, cur = [], None
    for ln in m.group(1).splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == "LAYER":
            cur = t[1]
        elif t[0] == "RECT" and cur == layer:
            rects.append([float(v) for v in t[1:5]])
    return rects


def lef_text(path):
    p = REPO / path
    if p.exists():
        return p.read_bytes()
    return subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{path}"], check=True, capture_output=True).stdout


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
            on_face = min(abs(r[0]), abs(r[1]), abs(r[2] - w), abs(r[3] - h)) < EPS
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            if not on_face or abs(cx - m["new_center_um"][0]) > EPS or abs(cy - m["new_center_um"][1]) > EPS:
                raise SystemExit(f"{mod}.{m['pin']}: new centre is not the centre of an outline-face RECT")
            if not done and [p["x"], p["y"]] != m["old_center_um"]:
                raise SystemExit(f"{mod}.{m['pin']}: old centre {[p['x'], p['y']]} != {m['old_center_um']}")
            p["x"], p["y"] = m["new_center_um"]
        d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
        if "S81-CORES-R22" not in d["source"]:
            d["source"] += ("; S81 plan event 2026-10-27 S81-CORES-R22 (delta_ninepins_1027.py): "
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
