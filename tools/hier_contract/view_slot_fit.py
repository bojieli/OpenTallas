#!/usr/bin/env python3
"""Slot fit of a CLOSED VIEW (s81-qelem 2026-10-13): slot_fit.py compares a ref_tile KIT with its contract slot; a master
closed outside the ref_tile flow (the DeepSeek ROM q-element) has no kit, so this reads the same facts from the routed
abstract and its TT liberty and applies slot_fit.compare unchanged:

    view_slot_fit.py VIEW.lef --contract DIE.json --slot NAME [--libs DIR] [--clock clk] [--resets rst_n] [--json]

  outline     LEF SIZE vs slot outline
  pins        every signal pin's face from its LEF rect (child_lint.face_of) vs the slot pins (when the slot lists pins)
  pin_layer   the layers the view's pins use on each face vs the slot pin layers
  layer_cap   the view's top signal/OBS layer vs the slot layer_cap, or (a closed view) its view_cap
  insertion   TT lib max_clock_tree_path vs slot target_insertion_ps (+-100 ps)
exit 0 fit, 1 mismatch, 2 usage.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import child_lint as CL  # noqa: E402
import slot_fit as SF  # noqa: E402


def view_facts(lef: Path, libs: Path | None, clock: str, resets: list[str]) -> dict:
    m = CL.parse_lef(lef.read_text(errors="replace"))
    W, H = m["W"], m["H"]
    faces: dict[str, set] = {}
    layers: dict[str, set] = {"N": set(), "S": set(), "E": set(), "W": set()}
    interior, top = [], 0
    for n, p in m["pins"].items():
        if CL.is_pg(n, p):
            continue
        fs = {CL.face_of(r, W, H) for r in p["rects"]} - {None}
        if not fs:
            interior.append(n)
            continue
        f = sorted(fs)[0]
        faces.setdefault(f, set()).add(SF.base(n))
        for r in p["rects"]:
            layers[f].add(r[0])
            top = max(top, CL.metal(r[0]) or 0)
    obs_top = max([CL.metal(r[0]) or 0 for r in m["obs"]] or [0])
    est, basis = None, None
    lib = (libs or lef.parent) / f"{m['name']}_tt.lib"
    if lib.exists():
        ins = [v["max_ps"] for v in CL.clock_insertion(lib.read_text(errors="replace")).values() if v]
        if ins:
            est, basis = max(ins), f"{lib.name} max_clock_tree_path"
    split = sorted(n for n in {x for v in faces.values() for x in v} if sum(n in v for v in faces.values()) > 1)
    return {"name": lef.stem, "top": m["name"], "kind": "closed_view", "contract": None, "outline": [W, H],
            "pins": {f: sorted(v) for f, v in faces.items()}, "clock_port": clock, "reset_ports": resets,
            "pin_layers": {f: sorted(v) for f, v in layers.items()}, "cap": f"M{max(top, obs_top)}",
            "signal_pin_top": f"M{top}", "obs_top": f"M{obs_top}", "est_insertion_ps": est, "est_basis": basis,
            "slot_change_request": None, "interior_pins": interior, "ports_on_two_faces": split,
            "pin_bits": sum(1 for n, p in m["pins"].items() if not CL.is_pg(n, p))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lef", type=Path)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--slot", required=True)
    ap.add_argument("--libs", type=Path)
    ap.add_argument("--clock", default="clk")
    ap.add_argument("--resets", default="rst_n")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    k = view_facts(a.lef, a.libs, a.clock, [x for x in a.resets.split(",") if x])
    c = json.loads(Path(a.contract).read_text())
    s = next((x for x in c["slots"] if x.get("name") == a.slot), None)
    if s is None:
        print(f"view_slot_fit: no slot {a.slot} in {a.contract}", file=sys.stderr)
        return 2
    bad, notes = [], []
    if s.get("cell") not in (k["top"], None) and not str(s.get("cell", "")).endswith("*"):
        bad.append(f"slot cell {s.get('cell')} != view {k['top']}")
    # a closed view is judged at the cap the contract records for it (view_cap) when it has one, as child_lint (c)
    s_cmp = dict(s)
    vcap = CL.cap_str(s.get("view_cap"))
    if vcap and (CL.metal(k["cap"]) or 0) > (CL.metal(CL.cap_str(s.get("layer_cap")) or "M0") or 0):
        s_cmp["layer_cap"] = vcap
        notes.append(f"routing cap {k['cap']} judged against the slot view_cap {vcap} (closed view; slot layer_cap "
                     f"{CL.cap_str(s.get('layer_cap'))} is for new routes)")
    b, n = SF.compare(k, s_cmp)
    bad += b
    notes += n
    if not s.get("pins"):
        notes.append("slot lists no pins: faces and pin layers not checked against the contract (reported only)")
    if s.get("target_insertion_ps") is None:
        notes.append(f"slot has no target_insertion_ps: view insertion {k['est_insertion_ps']} ps ({k['est_basis']}) reported only")
    ce = s.get("clock_entry") or {}
    ckf = next((f for f, v in k["pins"].items() if k["clock_port"] in v), None)
    if ce and (ce.get("pin") != k["clock_port"] or ce.get("face") != ckf):
        notes.append(f"slot clock_entry {ce.get('pin')}/{ce.get('face')}/{ce.get('layer')} vs view clock pin "
                     f"{k['clock_port']} on {ckf} ({'/'.join(k['pin_layers'].get(ckf, []))}): the die lead must fix the entry")
    out = dict(schema="opentallas.hier_contract.view_slot_fit.v1", view=str(a.lef), top=k["top"], contract=a.contract,
               contract_version=c.get("version"), slot=a.slot, status="mismatch" if bad else "fit", mismatches=bad,
               notes=notes, outline=k["outline"], slot_outline=s.get("outline"), pin_bits=k["pin_bits"],
               ports_by_face=k["pins"], pin_layers_by_face=k["pin_layers"], routing_cap=k["cap"],
               signal_pin_top=k["signal_pin_top"], clock_face=ckf, est_insertion_ps=k["est_insertion_ps"],
               est_basis=k["est_basis"], interior_pins=k["interior_pins"], ports_on_two_faces=k["ports_on_two_faces"])
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"view_slot_fit {out['status'].upper()}: {k['top']} {k['outline'][0]:g} x {k['outline'][1]:g} vs {a.slot} "
              f"(contract v{c.get('version')}); cap {k['cap']}; insertion {k['est_insertion_ps']} ps")
        for x in bad:
            print("  MISMATCH", x)
        for x in notes:
            print("  note", x)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
