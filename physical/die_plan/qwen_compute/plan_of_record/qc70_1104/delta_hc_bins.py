#!/usr/bin/env python3
"""DIE-QC-70 11-04: hc1/hc2/hc3 die-clock taps on the real sink inventory (clock.sink_bins_file). sle_hc1 a7 post-CTS: clk net kept
49455 sinks, 437 ps against 250, FF -365; slw_hc3 4 taps on 69.5k sinks, FF -252. Plan taps counted only plan pins and ft sinks; the
rows hold 70-83k. Bins = all_registers -clock clk centres on the row's own wave 3_place.odb (edge-clock ring flops excluded), same
format as the stm rows (plan_qc51). hc0 stays: 15 taps, FF -130 passes the gate. usage (repo root): delta_hc_bins.py PLAN SINK_TSV_DIR"""
import collections
import json
import sys
from pathlib import Path

P, D = sys.argv[1], Path(sys.argv[2])
REL = "physical/die_plan/qwen_compute/plan_of_record/sink_bins"
SIB = {"slw_hc1__cl68f9248e__cle683a076": "slw_hc1__cl68f9248e__cl144ee7b3"}  # no placed odb yet: sibling, same module
SRC = dict(l.split() for l in open(D / "rows.txt"))
BIN = 10.8
t = Path(P).read_text()
p = json.loads(t)
sp = next(s for s in ((", ", ": "), (",", ":")) if json.dumps(p, separators=s) + "\n" == t)
for k in sorted(p["partition_types"]):
    if not k.startswith(("sle_hc1", "slw_hc1", "sle_hc2", "slw_hc2", "slw_hc3")):
        continue
    s = SIB.get(k, k)
    c = collections.Counter()
    for line in open(D / (s + ".tsv")):
        x, y, *_ = line.split("\t")
        c[(int(float(x) // BIN), int(float(y) // BIN))] += 1
    bins = [[round((i + .5) * BIN, 2), round((j + .5) * BIN, 2), n] for (i, j), n in sorted(c.items())]
    doc = dict(bin_um=BIN, n=sum(c.values()), source=f"DIE-QC-70 11-04 wave {s} {SRC[s]} 3_place.odb all_registers -clock clk "
               "(edge-clock ring flops excluded)", bins=bins, type=k, placed_kit=s)
    Path(REL, k + ".json").write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    p["partition_types"][k]["clock"]["sink_bins_file"] = f"{REL}/{k}.json"
    print(k, doc["n"], len(bins))
Path(P).write_text(json.dumps(p, separators=sp) + "\n")
