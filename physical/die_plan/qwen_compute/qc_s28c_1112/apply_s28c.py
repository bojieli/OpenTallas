#!/usr/bin/env python3
"""QC-S28-C (DIE-QC-99 s28 item, 11-12): cbx_q* family structural fix = re-site the y_o21 internal station.

    python3 -I apply_s28c.py BASE_PLAN.json OUT_PLAN.json [--delta delta_s28c.json] [--receipt RECEIPT.json]
                             [--repo ROOT]       (ROOT: repo root holding the plan's pins_file paths; default cwd)

Finding.  The s22 event turned the NK cores of cbx_q10 so that their signal face (n_a/n_b/n_y/t_out: R0 W face)
faces the centre street (u_t20/u_t21 MY, u_t30/u_t31 R0).  The one plan internal station of the type, the 515-bit
u_t21.n_y -> bus y_o21 FIRM station, was not re-sited: to_um still names the pre-s22 R0 W-face pin (77.856, 2356.871)
and its register sits at (34.56, 2522.88), i.e. inside the NW corner that already holds the a22_i landing ring band
[17.28, 2425.152, 69.12, 2514.24] (2,880 padded flops), the 514-bit a22_i W ingress (y 2438-2527) and the three N
out windows a22_o / bc_o21 / y_o21 (x 4.3-272.8).  The real n_y pins are on the E face of u_t21 (x 544.224), so the
kit pulls 515 bits from the centre street west over/around u_t21 into that corner and back east to the window.

Fix (positions only).  For every cbx_q* type of the plan carrying that station: to_um = the real u_t21.n_y pin
centroid (pins_file, orient and track_offset applied), one register at the centre-street / top-band junction
(core E edge + 12.96 um, middle of the top band, on the 4.32 lattice).  Same conn, launch, capture, bits and register
count (1), so no cycle, no RTL and no EQ change (EQ by construction).  Both hops are checked <= reach 405 um.
No core, outline, bus, ft, clock, landing or reset key is touched.  Idempotent: re-applying gives the same plan.
"""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

LAT = 4.32
REACH = 405.0
CONN = "bus:y_o21"
LAUNCH_INST, LAUNCH_PORT = "u_t21", "n_y"
NOTE = ("QC-S28-C 11-12: re-sited for the s22 orient of u_t21 (n_y pins on its centre-street face); was to "
        "(77.856, 2356.871) / reg (34.56, 2522.88) = pre-s22 R0 W-face site in the NW landing corner; 1 FIRM "
        "station, same count, +0 cycles (EQ by construction)")


def snap(v):
    return round(round(v / LAT) * LAT, 3)


def pin_xy(core, pins, port):
    """centroid of core pins <port>[i] in the type frame (orient R0/MY/MX/R180, origin + track_offset)."""
    W, H = core["outline_um"]
    ox, oy = core["origin_um"]
    tx, ty = (core.get("track_offset_um") or [0.0, 0.0])
    o = core.get("orient", "R0")
    pts = [(p["x"], p["y"]) for p in pins["pins"] if re.sub(r"\[\d+\]$", "", p["name"]) == port]
    if not pts:
        raise SystemExit(f"{core['inst']}: no {port} pins in {core['pins_file']}")
    out = []
    for x, y in pts:
        if o in ("MY", "R180"):
            x = W - x
        if o in ("MX", "R180"):
            y = H - y
        out.append((ox + tx + x, oy + ty + y))
    return round(sum(p[0] for p in out) / len(out), 3), round(sum(p[1] for p in out) / len(out), 3), len(out)


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def fix_type(tn, T, repo):
    st = [s for s in T.get("internal_stations", []) if s.get("conn") == CONN and s.get("launch") == f"{LAUNCH_INST}.{LAUNCH_PORT}"]
    if len(st) != 1:
        return None
    s = st[0]
    core = {c["inst"]: c for c in T["hard_cores"]}[LAUNCH_INST]
    pf = Path(repo) / "physical/die_plan/qwen_compute/plan_of_record" / core["pins_file"]
    pins = json.loads(pf.read_text())
    px, py, n = pin_xy(core, pins, LAUNCH_PORT)
    W, H = T["outline_um"]
    bus = {b["name"]: b for b in T["buses"]}[CONN[4:]]
    if bus["face"] != "N":
        raise SystemExit(f"{tn}: {CONN} face {bus['face']} (this fix is written for the N window)")
    win = list(s["from_um"])
    # register: centre-street side of the core's signal face, middle of the top band (cores below it)
    top_band_lo = max(c["origin_um"][1] + c["outline_um"][1] for c in T["hard_cores"])
    ex = core["origin_um"][0] + (core["outline_um"][0] if core.get("orient", "R0") in ("MY", "R180") else 0.0)
    rx = snap(ex + 3 * LAT) if core.get("orient", "R0") in ("MY", "R180") else snap(ex - 3 * LAT)
    ry = snap((top_band_lo + H) / 2.0)
    reg = [rx, ry]
    h1, h2 = man([px, py], reg), man(reg, win)
    if max(h1, h2) > REACH:
        raise SystemExit(f"{tn}: re-sited hops {h1:.1f}/{h2:.1f} > reach {REACH}")
    for c in T["hard_cores"]:
        x0, y0 = c["origin_um"]
        w, h = c["outline_um"]
        if x0 < rx < x0 + w and y0 < ry < y0 + h:
            raise SystemExit(f"{tn}: register {reg} lies over {c['inst']}")
    before = copy.deepcopy(s)
    s["to_um"] = [px, py]
    s["regs_um"] = [reg]
    s["note"] = NOTE + f"; hops {h1:.1f} / {h2:.1f} um <= {REACH:.0f}"
    return {"type": tn, "conn": CONN, "launch_pins": n, "before": {k: before[k] for k in ("to_um", "regs_um")},
            "after": {"to_um": s["to_um"], "regs_um": s["regs_um"]}, "hops_um": [round(h1, 1), round(h2, 1)],
            "hops_before_um": [round(man(before["to_um"], before["regs_um"][0]), 1),
                               round(man(before["regs_um"][0], before["from_um"]), 1)],
            "bits": s.get("bits"), "regs": len(s["regs_um"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--delta")
    ap.add_argument("--receipt")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args()
    raw = Path(a.base).read_bytes()
    P = json.loads(raw)
    rows, delta = [], {"partition_types": {}}
    for tn in sorted(P["partition_types"]):
        if not tn.startswith("cbx_q"):
            continue
        r = fix_type(tn, P["partition_types"][tn], a.repo)
        if r is None:
            print(f"{tn}: no {CONN} station from {LAUNCH_INST}.{LAUNCH_PORT}; unchanged")
            continue
        rows.append(r)
        delta["partition_types"][tn] = {"internal_stations": P["partition_types"][tn]["internal_stations"]}
        print(f"{tn}: {CONN} to {r['before']['to_um']} -> {r['after']['to_um']}, reg {r['before']['regs_um']} -> "
              f"{r['after']['regs_um']}, hops {r['hops_before_um']} -> {r['hops_um']} um")
    if not rows:
        raise SystemExit("no cbx_q* type carries the station")
    txt = json.dumps(P, indent=1) + "\n"
    Path(a.out).write_text(txt)
    rec = {"schema": "opentallas.qc_s28c.receipt.v1", "base": a.base, "base_sha256": hashlib.sha256(raw).hexdigest(),
           "out": a.out, "out_sha256": hashlib.sha256(txt.encode()).hexdigest(), "types": rows,
           "touched_keys": ["partition_types.<cbx_q*>.internal_stations[conn=bus:y_o21].{to_um,regs_um,note}"],
           "eq": "positions only: same station count, bits, launch, capture; +0 cycles; no RTL/core/bus/ft/clock key"}
    if a.delta:
        Path(a.delta).write_text(json.dumps(delta, indent=1) + "\n")
        rec["delta_sha256"] = hashlib.sha256(Path(a.delta).read_bytes()).hexdigest()
    if a.receipt:
        Path(a.receipt).write_text(json.dumps(rec, indent=1) + "\n")
    print(f"out {a.out} sha256 {rec['out_sha256'][:12]} (base {rec['base_sha256'][:12]})")


if __name__ == "__main__":
    sys.exit(main())
