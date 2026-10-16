#!/usr/bin/env python3
"""H-SM 2026-10-15 22:40 (OWNER 22:30: v8 SM column 1036.8 um wide trial): re-harden the four CLOSED SM leaf masters at a
denser outline (same RTL, same ports/faces, same latency) to measure the fill an SM leaf closes at.  The column height is
set by leaf density: SM content 2.21 mm2 -> 1036.8 x 2,750 needs 77.5 % fill; today's leaves close at util 0.51-0.55.
Each d62 kit targets ~62 % std+macro fill (pd 0.60).  These replace (not add to) the leaf masters if they close.
"""
import copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "physical/ref_tile_specs/smh"
# name: (closed kit, new outline (w, h), macro positions or None, closed util, note)
LEAVES = {
    "smh_xs_d62": ("smh_xs_ref_p45m", (259.2, 155.544), [[23.76, 30.24], [139.968, 30.24], [23.76, 92.88], [139.968, 92.88]], 0.533,
                   "302.4 x 155.544 -> 259.2 x 155.544 (-14.3 %): two macro columns 23.76 um from the W edge, 21.384-um macro channel kept"),
    "smh_tcl_gu_d62": ("smh_tcl_gu_ref", (86.4, 108.0), None, 0.5545, "86.4 x 120.024 -> 86.4 x 108.0 (-10.0 %)"),
    "smh_bdc_d62": ("smh_bdc_ref_p50", (112.32, 116.64), None, 0.506, "112.32 x 142.56 -> 112.32 x 116.64 (-18.2 %)"),
    "smh_tct_d62": ("smh_tct_ref_p45", (194.4, 64.8), None, 0.508, "194.4 x 69.144 -> 194.4 x 64.8 (-6.3 %; 56.16 gated at 79 % synth util)"),
}


def main(names):
    for name in names or LEAVES:
        src, (w, h), macros, util, note = LEAVES[name]
        s = json.load(open(ROOT / "physical/ref_tile" / src / "spec.json"))
        s = copy.deepcopy(s)
        old = s["outline"]
        s["name"] = name
        s["outline"] = {"w": w, "h": h}
        s["recipe"] = 2
        s.setdefault("route", {})["pd"] = 0.6
        if macros:
            for m, at in zip(s["macros"], macros):
                m["at"] = at
        s["pin_regs"] = {"enable": False, "reason": (
            f"density re-harden of the CLOSED master {src} (same RTL, ports, faces and latency; recipe 2 as closed): a "
            "recipe-3 wrapper would add +1 cycle on every leaf port inside the SM tile, whose pins are already registered "
            "(OT_SMH_PINREG); leaf ports are internal SM tile seams")}
        j = s.setdefault("job", {})
        j.update({"owner": "Claude H-SM", "branch": "claude/hbm-sm-repack-1015", "tag": "d62",
                  "structural_change": (f"[H-SM v8 SM column, OWNER 22:30] density re-harden of {src} "
                                        f"({old['w']} x {old['h']}, synth util {util}) at ~62 % fill: {note}; pd 0.60. "
                                        "Measures the leaf fill that closes; the 1036.8-um SM column height follows it."),
                  "purpose": f"[H-SM d62] {src} re-hardened denser for the v8 SM column (1036.8 um wide): {note}"})
        p = SPECS / f"{name}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print(p.relative_to(ROOT), round(old["w"] * old["h"]), "->", round(w * h), "um2")


if __name__ == "__main__":
    main(sys.argv[1:])
