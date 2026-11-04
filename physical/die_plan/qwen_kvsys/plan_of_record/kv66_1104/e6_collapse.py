#!/usr/bin/env python3
"""DIE-KV-66 11-04: kv3_head_eighth_e6 fMX@MX rows move to the R0 table @R0 at the same origin.

gen_phys copies one LEF per module (the R0-table plan LEF) into a kit's macros/, so an fMX-table row placed MX gets the
R0 pins mirrored: up to 215.6 um off the plan table (LEF-SWEEP-2). The fMX table is an exact y-mirror of the R0 table, so
fMX@MX and R0@R0 put every pin at the same parent point; the check below proves it per row before anything is written.
Same form as the pv join collapse (DIE-KV-64 11-03). Parent-frame pins, origins, outlines, straps stay identical.

    e6_collapse.py PLAN_IN PLAN_OUT   (run from the repository root)
"""
import json
import sys
from pathlib import Path

MOD = "kv3_head_eighth_e6"
FMX = "pins/kv3_head_eighth_e6_pins_fMX_r25_r26q4.json"
R0 = "pins/kv3_head_eighth_e6_pins_r25_r26q4.json"


def main(src, dst):
    raw = json.loads(Path(src).read_text())
    pdir = Path(src).parent
    fmx = {p["name"]: p for p in json.loads((pdir / FMX).read_text())["pins"]}
    r0 = {p["name"]: p for p in json.loads((pdir / R0).read_text())["pins"]}
    if set(fmx) != set(r0):
        raise SystemExit("tables differ in pin names")
    n, types = 0, set()
    for tn, t in raw["partition_types"].items():
        for h in t.get("hard_cores", []):
            if h.get("module") != MOD or h.get("pins_file") != FMX:
                continue
            if h.get("orient") != "MX":
                raise SystemExit(f"{tn}.{h['inst']}: fMX row not MX")
            H = h["outline_um"][1]
            for k, a in fmx.items():
                b = r0[k]
                # parent frame y offset: fMX@MX -> H - y; R0@R0 -> y
                if abs(a["x"] - b["x"]) > 1e-3 or abs((H - a["y"]) - b["y"]) > 1e-3 or a["layer"] != b["layer"]:
                    raise SystemExit(f"{tn}.{h['inst']}.{k}: not a mirror")
            h["pins_file"], h["orient"] = R0, "R0"
            n += 1
            types.add(tn)
    Path(dst).write_text(json.dumps(raw, indent=1) + "\n")
    print(f"{n} rows, {len(types)} types moved to R0 table @R0")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
