#!/usr/bin/env python3
"""QC NK pin-face plan event (DIE-QC-97, 2026-11-11; COORD go on the NK pin-face re-assignment, new NK form).

    python3 -I physical/die_plan/qwen_compute/delta_nk_pinface_1111.py BASE_PLAN OUT_PLAN EVENT_JSON   (repo root)
    python3 -I physical/die_plan/qwen_compute/delta_nk_pinface_1111.py --pins-only      (writes the two pin files)

MEASURED (forward cone of every NK output bus to NK input buses / ports, 1_synth.odb of one wave row per type, all 16
cb* types; GRT guides of cbn_q00__cl622f65d2 attempt_20 5_1_grt-failed.odb): the signed NK master has n_a, n_b, n_y
and t_out on its W face, so with the R0 / MY column pairs every bus faces the outer die edge and the cross-column
links (t_out -> n_a, n_y -> n_b, t_out -> n_b of the neighbour column) cross both NK cores: 72 % of the parent guide
area inside the NK footprints is that W<->E through traffic (2,182 nets over the full 457.9-um width).
Tile crossings (x 514 bits) over the 16 types, L-path estimate: today 108, {n_b, t_out} on E 64, {n_a, n_b, t_out}
on E 37; {n_a, n_b, t_out} is <= {n_b, t_out} on every type (COORD 11-11: build {n_a, n_b, t_out}).

FORM: n_a, n_b and t_out (514 bits each, M4) move from the master W face to the master E face at the SAME y track
and layer (E face y 699-1001 is free: E holds tap 561-660 and rst_n / tile_id / tie 665-674).  n_y, ck and the E-face
pins are unchanged.  No RTL change (rtl_change false), no data or pin cycles, pin positions only.  The parent plan
changes only in hard_cores[].pins_file (cores/a0_nk_pins_ck1109.json -> cores/a0_nk_pins_pf1111.json) of the 62
qfd_tile_nk_a0c cores in the 16 cb* types, and every NK hard core drops the 11-10 u_t21 route_channels key (form (c):
the NK keeps no parent channel; the channel event delta_nk_hchan_1110 is withdrawn).  The NK kit pin source
cores/a0/parent/a0_nk_pins_dir.json moves the same pins (face centre x 0.042 -> 457.878).  The NK must be rebuilt
(new pins) before the cb* rows count; the rebuild also snaps the off-track rawfault_m3 macros (KW-FIX-44).

Idempotent guard: refuses a plan whose NK cores do not all carry the ck1109 pins file.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MODULE = "qfd_tile_nk_a0c"
OLD_PINS = "cores/a0_nk_pins_ck1109.json"
NEW_PINS = "cores/a0_nk_pins_pf1111.json"
BUSES = ("n_a", "n_b", "t_out")
W_UM = 457.92
POR = Path(__file__).resolve().parent / "plan_of_record"
DIR_PINS = Path(__file__).resolve().parent / "cores" / "a0" / "parent" / "a0_nk_pins_dir.json"


def _bus(name):
    return name.split("[", 1)[0]


def move_pins(doc, w_x, e_x, source):
    """pin doc with BUSES moved from the W face (x == w_x) to the E face (x == e_x), same layer and y; ValueError when a
    moved pin is not on the W face or lands on an E-face (layer, y) already in use."""
    d = json.loads(json.dumps(doc))
    east = {(p["layer"], round(p["y"], 4)) for p in d["pins"] if abs(p["x"] - e_x) < 1e-6}
    n = 0
    for p in d["pins"]:
        if _bus(p["name"]) not in BUSES:
            continue
        if abs(p["x"] - w_x) > 1e-6:
            raise ValueError(f"{p['name']}: x {p['x']} is not on the W face ({w_x})")
        if (p["layer"], round(p["y"], 4)) in east:
            raise ValueError(f"{p['name']}: E face {p['layer']} y {p['y']} already in use")
        p["x"] = e_x
        n += 1
    if n != 514 * len(BUSES):
        raise ValueError(f"moved {n} pins, expected {514 * len(BUSES)}")
    d["source"] = source
    return d, n


def apply(plan):
    """plan with the NK cores on the pf1111 pins file and no route_channels; (plan, report)."""
    p = json.loads(json.dumps(plan))
    hit, dropped = [], 0
    for tn, t in sorted(p["partition_types"].items()):
        for h in t.get("hard_cores", []) or []:
            if h.get("module") != MODULE:
                continue
            if h.get("pins_file") != OLD_PINS:
                raise SystemExit(f"{tn}/{h['inst']}: pins_file {h.get('pins_file')} != {OLD_PINS} (event applied?)")
            h["pins_file"] = NEW_PINS
            if "route_channels" in h:
                del h["route_channels"]
                dropped += 1
            hit.append(f"{tn}/{h['inst']}")
    if not hit:
        raise SystemExit(f"no {MODULE} hard core in the plan")
    rep = dict(module=MODULE, pins_file_old=OLD_PINS, pins_file_new=NEW_PINS, moved_buses=list(BUSES),
               cores=len(hit), types=sorted({x.split("/")[0] for x in hit}), route_channels_removed=dropped,
               instances=sorted(hit))
    return p, rep


def dumps_like(P, text):
    """re-serialise P in the style the input file used (compact / spaced / indent=1 / indent=2)"""
    R = json.loads(text)
    for kw in (dict(separators=(",", ":")), dict(separators=(", ", ": ")), dict(indent=1), dict(indent=2)):
        s = json.dumps(R, **kw)
        if text in (s, s + "\n"):
            out = json.dumps(P, **kw)
            return out + "\n" if text.endswith("\n") else out
    return json.dumps(P, indent=1) + "\n"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_pins():
    """write cores/a0_nk_pins_pf1111.json (parent pin file) and move the same pins in a0_nk_pins_dir.json"""
    old = POR / OLD_PINS
    new, n = move_pins(json.loads(old.read_text()), 0.096, 457.824,
                       f"{OLD_PINS} (sha256 {_sha(old)}) with n_a, n_b, t_out moved W -> E face, same y and layer "
                       f"(DIE-QC-97 11-11 NK pin-face event, delta_nk_pinface_1111.py)")
    (POR / NEW_PINS).write_text(json.dumps(new, indent=1) + "\n")
    dtext = DIR_PINS.read_text()
    dd, n2 = move_pins(json.loads(dtext), 0.042, 457.878, json.loads(dtext)["source"]
                       + "; DIE-QC-97 11-11 NK pin-face event: n_a, n_b, t_out on the E face (same y and layer)")
    DIR_PINS.write_text(dumps_like(dd, dtext))
    return n, n2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("base", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("event", nargs="?")
    ap.add_argument("--pins-only", action="store_true", help="write the two pin files and stop")
    a = ap.parse_args(argv)
    if a.pins_only:
        print(json.dumps(dict(zip(("parent_pins_moved", "dir_pins_moved"), write_pins()))))
        return 0
    if not (a.base and a.out and a.event):
        ap.error("BASE_PLAN OUT_PLAN EVENT_JSON required")
    text = Path(a.base).read_text()
    P, rep = apply(json.loads(text))
    Path(a.out).write_text(dumps_like(P, text))
    new_pins = POR / NEW_PINS
    ev = dict(schema="opentallas.qc_por_event.v1",
              event="QC NK pin-face re-assignment: n_a, n_b, t_out on the master E face (DIE-QC-97 11-11)",
              base_plan=str(a.base), base_plan_sha256=_sha(a.base), plan_output=str(a.out),
              plan_output_sha256=_sha(a.out), rtl_change=False, data_cycles=0, pin_cycles=0,
              pins_file_new_sha256=_sha(new_pins) if new_pins.is_file() else None, **rep,
              preservation="every other partition type and top-level key byte-identical; in the 16 cb* types only "
                           "hard_cores[].pins_file and hard_cores[].route_channels of qfd_tile_nk_a0c differ")
    Path(a.event).write_text(json.dumps(ev, indent=1) + "\n")
    print(json.dumps(dict(cores=rep["cores"], types=len(rep["types"]),
                          route_channels_removed=rep["route_channels_removed"], out_sha256=ev["plan_output_sha256"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
