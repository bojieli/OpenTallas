#!/usr/bin/env python3
"""DIE-KV-66 11-04: qkd_kvs_pc r27 rows move to the fMX table with the orient flipped, at the same origin.

One module, one LEF per kit: r27 and fMX rows cannot both be served, and kv3_pc_v1__cl* uses both. The fMX table is an exact
y-mirror of the r27 table (checked here), so r27@O and fMX@(O*MX) put every pin at the same parent point. Zero geometry
change in the parent; the r27 PC design leaves the plan. Replaces the R270 ECO path (eco5 not signed, COORD RE-FORM).

    pc_collapse.py PLAN_IN PLAN_OUT
"""
import json
import sys
from pathlib import Path

R27, FMX = "pins/qkd_kvs_pc_pins_r27.json", "pins/qkd_kvs_pc_pins_fMX_r27.json"
FLIP = {"R0": "MX", "MX": "R0", "MY": "R180", "R180": "MY"}


def main(src, dst):
    raw = json.loads(Path(src).read_text())
    pdir = Path(src).parent
    a = {p["name"]: p for p in json.loads((pdir / R27).read_text())["pins"]}
    b = {p["name"]: p for p in json.loads((pdir / FMX).read_text())["pins"]}
    if set(a) != set(b):
        raise SystemExit("tables differ in pin names")
    n, types = 0, set()
    for tn, t in raw["partition_types"].items():
        for h in t.get("hard_cores", []):
            if h.get("module") != "qkd_kvs_pc" or h.get("pins_file") != R27:
                continue
            H = h["outline_um"][1]
            for k, p in a.items():
                q = b[k]
                if abs(p["x"] - q["x"]) > 1e-3 or abs((H - p["y"]) - q["y"]) > 1e-3 or p["layer"] != q["layer"]:
                    raise SystemExit(f"{tn}.{h['inst']}.{k}: not a mirror")
            h["pins_file"], h["orient"] = FMX, FLIP[h["orient"]]
            n += 1
            types.add(tn)
    Path(dst).write_text(json.dumps(raw, indent=1) + "\n")
    print(f"{n} rows, {len(types)} types moved to fMX table")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
