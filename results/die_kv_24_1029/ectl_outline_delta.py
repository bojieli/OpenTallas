#!/usr/bin/env python3
"""Unsigned ECTL q1/q2 four-SRAM floorplan proposal; zero RTL/cycle changes."""
import argparse
import copy
import json
import os
import re
from collections import Counter
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("out")
    a = ap.parse_args()
    src = Path(a.plan).resolve()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    d = json.load(open(src))
    p = copy.deepcopy(d)
    targets = {"qkd_ectlk_q1", "qkd_ectlk_q2"}
    docs = {}
    n = Counter()
    for tn, t in p["partition_types"].items():
        for c in t.get("hard_cores", []):
            pf = (src.parent / c["pins_file"]).resolve() if c.get("pins_file") else None
            if c["module"] in targets:
                assert c["outline_um"] == [216.0, 172.8], c
                key = c["module"]
                if key not in docs:
                    q = json.load(open(pf))
                    moved = 0
                    for pin in q["pins"]:
                        if 215.8 <= float(pin["x"]) <= 216.0:
                            pin["x"] = round(float(pin["x"]) + 17.28, 6)
                            moved += 1
                    q["frame"], changes = re.subn(r"outline\s+216(?:\.0)?\s+x\s+172\.8",
                                                   "outline 233.28 x 172.8", q["frame"])
                    assert changes == 1, q["frame"]
                    q["source"] = q.get("source", "") + " | CODEX ECTL233: four real SRAMs, E face +17.28 um, other pins and clock unchanged, 0 cycles"
                    fn = key + "_pins_233.json"
                    (out / fn).write_text(json.dumps(q, indent=1) + "\n")
                    docs[key] = dict(path=fn, moved=moved)
                c["pins_file"] = docs[key]["path"]
                c["outline_um"] = [233.28, 172.8]
                c["note"] = c.get("note", "") + " | CODEX ECTL233 four-SRAM channel fit, 0 cycles"
                n[tn] += 1
            elif pf:
                c["pins_file"] = os.path.relpath(pf, out)
    instances = Counter(x["type"] for x in p["partitions"])
    count = sum(instances[t] * k for t, k in n.items())
    rep = dict(status="PROPOSAL", changed_types=dict(n), core_instances=count,
               outline_old_um=[216, 172.8], outline_new_um=[233.28, 172.8],
               area_delta_mm2=round(count * 17.28 * 172.8 / 1e6, 6),
               added_cycles=0, clock_pins="unchanged", pins=docs,
               macros=dict(master="ot_sram_1r1w_128x256_m1_r2c2", count=4,
                           sites=[[15.552, 13.26, "MX"], [15.552, 127.404, "R0"],
                                  [123.12, 13.26, "MX"], [123.12, 127.404, "R0"]]),
               channels_um=dict(west_core=11.232, east_core=11.016, middle=12.744,
                                south_halo_end=8.94, clock_ft_island_top=8.91),
               dependencies="parent pin reach check, new kit geometry review, placement, CTS, sign-off")
    (out / "plan.json").write_text(json.dumps(p, indent=1) + "\n")
    (out / "impact.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
