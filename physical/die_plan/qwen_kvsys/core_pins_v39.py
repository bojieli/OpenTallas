#!/usr/bin/env python3
"""KV-405 10-24: plan v3.9 core pin moves (COORD rulings on KV-CORES OWNER? 4/5, 2026-10-24 22:43; run BEFORE run_v39.sh,
like core_pins_resize_v38x.py before run_v38x.sh; idempotent).

  * qkd_ahub r2 (KV-CORES ahub_fp_proposal.py r2 @666f376ad; GEOM-REVIEW 21:45 / 22:36 PASS-COND for the plan, kit +
    place + CTS OK): outline 734.4 x 540 -> 604.8 x 440.64 with the core's S-E corner fixed in hub_C (post_v39.py moves
    the origin); pins re-spread onto the new outline with the same faces / order / rule (core_pins_resize_v38x.main),
    then ck / rst_n leave the E-face corner for the S face at x 185.76 (under the macro-array centre / zh column gap,
    the r2 centre-feed spine foot), on M7 (the S face's M5 tracks carry the 482 data pins).
  * qkd_ectlk (COORD ruling 4: clock entry to a face centre / centre-feed): ck[0..2] + rst_n leave the E-face bottom
    corner (881.184, 2.3..12.4) for the N face centre (x ~440.6; the N face carries no other pin), on M5 x-tracks.
Core pins only move on their own core's faces; no partition pin, bus or lane changes.  Heads e0-e7 / pv_pair / astk pins
are NOT touched (e1/e5/e7 SIGNED views stand).
    core_pins_v39.py PLAN_DIR"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_pins_resize_v38x as RS   # noqa: E402

AHUB = (604.8, 440.64)
AHUB_CLK_X = 185.76          # r2: S face under the zh column gap (ahub_fp_proposal.py r2)


def frame(d):
    import re
    m = re.search(r"outline ([0-9.]+) x ([0-9.]+)", d["frame"])
    return float(m.group(1)), float(m.group(2))


def track(c, layer):
    p, o = RS.PITCH[layer], RS.OFFS[layer]
    return round(o + round((c - o) / p) * p, 6)


def place(d, names, face, centre, layer, step_tracks=4):
    """put pins `names` on `face` at consecutive tracks (step_tracks apart) centred on `centre` (core frame)."""
    w, h = frame(d)
    by = {p["name"]: p for p in d["pins"]}
    p_ = RS.PITCH[layer] * step_tracks
    n = len(names)
    for j, nm in enumerate(names):
        c = track(centre + (j - (n - 1) / 2) * p_, layer)
        q = by[nm]
        q["layer"] = layer
        if face == "N":
            q["x"], q["y"] = c, round(h - 0.096, 6)
        elif face == "S":
            q["x"], q["y"] = c, 0.096
        elif face == "E":
            q["x"], q["y"] = round(w - 0.096, 6), c
        else:
            q["x"], q["y"] = 0.096, c
    cnt = {}
    for p in d["pins"]:
        fc = ("N" if abs(p["y"] - (h - 0.096)) < 1e-6 else "S" if abs(p["y"] - 0.096) < 1e-6 else
              "E" if abs(p["x"] - (w - 0.096)) < 1e-6 else "W")
        c_ = cnt.setdefault(fc, dict(pins=0, layers=set()))
        c_["pins"] += 1
        c_["layers"].add(p["layer"])
    d["faces"] = {k: dict(pins=v["pins"], layers=sorted(v["layers"])) for k, v in sorted(cnt.items())}
    # no other pin on the same layer within one pitch of a moved pin on that face
    moved = {(by[nm]["layer"], by[nm]["x"], by[nm]["y"]) for nm in names}
    for p in d["pins"]:
        if p["name"] in names:
            continue
        for (ly, x, y) in moved:
            assert not (p["layer"] == ly and abs(p["x"] - x) < RS.PITCH[ly] and abs(p["y"] - y) < RS.PITCH[ly]), p


def main(plan_dir):
    cd = Path(plan_dir) / "cores"
    f = cd / "qkd_ahub_pins.json"
    d = json.loads(f.read_text())
    if frame(d) != AHUB:
        RS.main(str(f), str(f), *AHUB)
        d = json.loads(f.read_text())
        d["source"] += " | v3.9 KV-405: qkd_ahub r2 outline (KV-CORES ahub_fp_proposal r2), same faces / order / rule"
    place(d, ["ck[0]", "rst_n[0]"], "S", AHUB_CLK_X, "M7")
    if "v3.9 ck/rst_n" not in d["source"]:
        d["source"] += f" | v3.9 ck/rst_n -> S face x {AHUB_CLK_X:g} on M7 (r2 centre-fed spine foot)"
    f.write_text(json.dumps(d, indent=0))
    f = cd / "qkd_ectlk_pins.json"
    d = json.loads(f.read_text())
    w, _ = frame(d)
    place(d, ["ck[0]", "ck[1]", "ck[2]", "rst_n[0]"], "N", w / 2, "M5")
    if "v3.9 clock entry" not in d["source"]:
        d["source"] += " | v3.9 clock entry ck[0..2] + rst_n -> N face centre on M5 (COORD ruling 4, centre-feed)"
    f.write_text(json.dumps(d, indent=0))
    print("core_pins_v39: qkd_ahub 604.8 x 440.64, ck/rst_n S x 185.76 M7; qkd_ectlk ck/rst_n N centre M5")


if __name__ == "__main__":
    main(sys.argv[1])
