#!/usr/bin/env python3
"""QC-A0-KITS plan delta D-QC-A0-R3B (core-side slice of the A0 drop-lattice clock form; plan files only).

Inputs (all repo-relative, read-only):
  physical/die_plan/qwen_compute/cores/a0_core.json, a0_nk_pins.json, a0_nl_pins.json   (main)
  physical/die_plan/qwen_compute/inputs/a0_drop_r3b.json  (= QC-CORES-2 R3b a0_clk_r3b.json,
      claude/qc-cores-1027-a0clk-r3@f217587b2 results/qc_cores_1027/a0_split/clk_r3b/a0_clk_r3b.json; GEOM-22 PASS-COND)
Changes:
  (1) E pin block shift -19.344 um (COORD 2026-10-27 07:18 ruling INFRA-FIRST-QC-R25 (b), centred between EF4/EF5):
      every E-face pin y -= 19.344 (403 M4 tracks of 0.048 -> track phase kept).  Audit: 0 E pins within an EF0-5/EN1-2
      island y-window (footprint 8.64 um + 0.5 um clearance, GEOM-25 cond (4)).
  (2) The legacy E clock pin ck (457.824, 668.076) is NOT an entry (12.8a): it is replaced by the 22 R3b island feed ports
      ck_isl_<ISL> on M5 at the island drop point (core frame, face "C" interior = plan island entry, 12.2a1 pushdown),
      x on the M5 plan track U-0.024 (half a track off the M9 lane centre, inside the 0.48 strap),
      identical for every instance (R0 / MX rows: the die drop is y0+V or y0+H-V, the core frame point is the same).
      NL has the same 22 islands (no node leg; the island exists, its node leg is absent).
  (3) a0_core.json clock: entry form = 22 R3b drop islands, die stub 0, child budget B_child 201 TT / 161.5 FF for
      rawleaf/romleaf/node centre pins, children OBS <= M5; legacy one-pin tap description retired.
usage: python3 -I a0_plan_delta_r3b.py REPO   (rewrites the three cores/ files in place, prints the audit)
"""
import json
import sys
from pathlib import Path

SHIFT = -19.344
WIN_HALF = 4.32 + 0.5
M5_HALF = 0.024
CENTRE_PINS = {"rawleaf": [57.672, 70.2], "romleaf": [86.4, 55.08], "node": [23.76, 216.0]}


def main(repo):
    qc = Path(repo) / "physical/die_plan/qwen_compute"
    r3b = json.loads((qc / "inputs/a0_drop_r3b.json").read_text())
    isl = r3b["islands"]
    ewin = {n: i["centre"][1] for n, i in isl.items() if n.startswith(("EF", "EN"))}
    audit = {}
    for var in ("nk", "nl"):
        f = qc / f"cores/a0_{var}_pins.json"
        d = json.loads(f.read_text())
        pins = [p for p in d["pins"] if p["name"] != "ck"]
        assert len(pins) == len(d["pins"]) - 1, f"{var}: exactly one legacy ck pin expected"
        n_e = 0
        for p in pins:
            if p["x"] > 457.0:
                p["y"] = round(p["y"] + SHIFT, 3)
                n_e += 1
        conflicts = {n: sum(1 for p in pins if p["x"] > 457.0 and abs(p["y"] - c) < WIN_HALF) for n, c in ewin.items()}
        ey = sorted(p["y"] for p in pins if p["x"] > 457.0)
        for n in sorted(isl):
            x, y = isl[n]["drop_core_frame"]
            x = round(x - M5_HALF, 3)   # M5 plan track: core x = 0.024 mod 0.048 (U on the 8.64 lane = 0 mod 0.048)
            pins.append({"name": f"ck_isl_{n}", "layer": "M5", "x": x, "y": y, "face": "C",
                         "role": "clock island feed port (R3b drop: die M9 x0+U x M8 y0+V stacked via M9-M5, die stub 0)"})
        d["pins"] = pins
        d["source"] = d["source"] + " | D-QC-A0-R3B 2026-10-27: E pins y-19.344, ck -> 22 ck_isl_* M5 island feed ports"
        f.write_text(json.dumps(d, indent=1) + "\n")
        audit[var] = dict(e_pins=n_e, e_y=[ey[0], ey[-1]], gap_EF4=round(ey[0] - (ewin["EF4"] + 4.32), 3),
                          gap_EF5=round(ewin["EF5"] - 4.32 - ey[-1], 3), island_window_conflicts=sum(conflicts.values()),
                          island_ports=len(isl))
    c = json.loads((qc / "cores/a0_core.json").read_text())
    c["clock"] = {
        "ports": [f"ck_isl_{n}" for n in sorted(isl)],
        "form": "R3b drop islands (QC-CORES-2 claude/qc-cores-1027-a0clk-r3@f217587b2, GEOM-22 PASS-COND; INFRA-FIRST-QC-R25 "
                "form ADOPTED COORD 2026-10-27 07:18): 22 in-core pushdown islands (12.2a1) per instance, identical in R0 and MX; "
                "each island feed port = M5 end of a straight M9-M8-M7-M6-M5 stack at the crossing of die M9 drop strap x0+U "
                "and die M8 drop strap y0+V (MX rows y0+1157.76-V); die stub 0; island wire <= 7.56 um",
        "type_lattice": r3b["type_lattice"],
        "islands": {n: {"centre": i["centre"], "drop_core_frame": i["drop_core_frame"], "where": i["where"]}
                    for n, i in sorted(isl.items())},
        "die_side": "192 M9 + 128 M8 drop straps over the A0 field (qc_clk_mesh3 --a0-mesh inputs/a0_drop_r3b.json); die clock "
                    "owner (INFRA-FIRST-QC) adopts them in the QC plan event, not this delta",
        "children": {"budget_ps": {"TT": 201.0, "FF": 161.5}, "centre_pins_child_frame": CENTRE_PINS,
                     "obs_max_layer": "M5", "note": "B_child = R3 model (UNCHECKED-model); early taps from real views allowed (12.3 v5.0)"},
        "legacy_ck_pin": {"pin_um": [457.824, 668.076], "status": "RETIRED (not an entry, 12.8a)"},
        "insertion_budget_ps": {"target": 250, "at": "core boundary flops, TT (12.3 design target)", "status": "to be measured"},
    }
    c["owner"] = c.get("owner", "") + " | D-QC-A0-R3B QC-A0-KITS 2026-10-27"
    (qc / "cores/a0_core.json").write_text(json.dumps(c, indent=1) + "\n")
    print(json.dumps(audit, indent=1))
    return 0 if all(a["island_window_conflicts"] == 0 for a in audit.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
