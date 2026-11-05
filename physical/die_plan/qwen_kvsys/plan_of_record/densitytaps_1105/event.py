#!/usr/bin/env python3
"""DIE-KV-73 11-05: hold-after-CTS class on KV big rows (DIE-KV-72 04:23: tap spread on sparse big taps; plan taps 16-20 on 13k-99k sinks).
Class form of pvpilot_1104 + pvband_1105 on one row list: density taps on the row own placed sinks (clock.sink_bins_file, all_registers -clock clk
centres on the row wave 3_place.odb) and the row landing bands as clock.keepouts_um, so taps and their relays stay off the bands.
No START transport, no raw branches, no core_taps change, 0 data cycles. Collector then by geom93_1031/delta_geom93_coll.py with TYPES_RE on the same rows.
usage (repo root): event.py PLAN_IN PLAN_OUT REPORT.json SINK_DIR ROW[:RADIUS_UM] ...   (SINK_DIR/<ROW>.tsv; radius default 200. A row needs more when core and band keepouts leave its 17-um ring corner sinks no nearer legal tap: smallest passing step per row)"""
import collections, copy, json, os, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))
import schema as S, taps as TP, plan_geom as PG
REL = "physical/die_plan/qwen_kvsys/plan_of_record/sink_bins"
BIN = 10.8
a, b, c_, sd, *specs = sys.argv[1:]
spec = [x.split(":") for x in specs]
FAR = {x[0]: [float(v) for v in x[2].split(",")] for x in spec if len(x) > 2}
spec = [x[:2] for x in spec]
rows = [x[0] for x in spec]
RAD = {x[0]: float(x[1]) if len(x) > 1 else 200.0 for x in spec}
text = open(a).read()
raw = json.loads(text)
orig = copy.deepcopy(raw)
rep = {}
for TN in rows:
    c = collections.Counter()
    for line in open(Path(sd) / f"{TN}.tsv"):
        x, y, *_ = line.split("\t")
        c[(int(float(x) // BIN), int(float(y) // BIN))] += 1
    doc = dict(bin_um=BIN, n=sum(c.values()), source=f"DIE-KV-73 11-05 kv-wave-1104 {TN} 3_place.odb all_registers -clock clk (edge-clock ring flops excluded)",
               bins=[[round((i + .5) * BIN, 2), round((j + .5) * BIN, 2), n] for (i, j), n in sorted(c.items())], type=TN, placed_kit=TN)
    Path(REL).mkdir(exist_ok=True)
    Path(REL, TN + ".json").write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    ck = raw["partition_types"][TN]["clock"]
    assert ck.get("tap_mode") is None and not ck.get("keepouts_um"), TN
    ck.update(tap_mode="density", tap_max_sinks=1200, tap_target_sinks=960, tap_radius_um=RAD[TN], sink_bins_file=f"{REL}/{TN}.json",
              keepouts_um=[v["rect_um"] for v in ck["landing_contract"]["bands"].values()])
    if FAR.get(TN): ck["keepouts_um"].append(FAR[TN])   # far-corner rect: keeps the farthest tap inside the old reset hop count, so the wavefront parents stay
    P1 = S.Plan(copy.deepcopy(raw), Path(a).resolve())
    fin = TP.density_taps(P1, TN)
    load = sorted(x[3] for x in fin)
    m = PG.type_metrics(P1, TN)
    rep[TN] = dict(sinks=doc["n"], bins=len(doc["bins"]), taps=len(fin), max_load=load[-1], median_load=load[len(load) // 2], empty=sum(1 for v in load if v == 0),
                   max_radius=round(max(x[4] for x in fin), 1), clock_reach=m["clock_reach_max"], bands=len(ck["keepouts_um"]))
    print(TN, rep[TN], flush=True)
for k in raw:
    if k != "partition_types":
        assert raw[k] == orig[k], k
for t in raw["partition_types"]:
    if t not in rows:
        assert raw["partition_types"][t] == orig["partition_types"][t], t
for TN in rows:
    mm = re.search(r"^  \"" + TN + r"\": ", text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, mm.end())
    text = text[:mm.end()] + json.dumps(raw["partition_types"][TN], indent=1).replace("\n", "\n  ") + text[j:]
assert json.loads(text) == raw
open(b, "w").write(text)
json.dump(rep, open(c_, "w"), indent=1)
