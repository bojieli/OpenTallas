#!/usr/bin/env python3
"""DIE-KV-70 11-04: kv3_pv_v8 pilot on placed sinks, the form of DIE-QC-70 delta_hc_bins.py (clock.sink_bins_file, density taps).
v8 row stopped post-CTS at FF -422.99 on 18642 endpoints, tap spread 302; plan model max 5813 per tap, kit 24129.  Bins = all_registers
-clock clk centres on v8's own wave 3_place.odb (99260; edge-clock ring flops excluded, hard-core pins not in the inventory).
No START transport, no raw branches, no core_taps change.  Then geom93_1031/delta_geom93_coll.py with TYPES_RE=^kv3_pv_v8$.
usage (repo root): event.py PLAN_IN PLAN_OUT REPORT.json SINKS.tsv"""
import collections, copy, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))
import schema as S, taps as TP, plan_geom as PG
TN = "kv3_pv_v8"
REL = "physical/die_plan/qwen_kvsys/plan_of_record/sink_bins"
BIN = 10.8
a, b, c_, tsv = sys.argv[1:5]
text = open(a).read()
raw = json.loads(text)
orig = copy.deepcopy(raw)
c = collections.Counter()
for line in open(tsv):
    x, y, *_ = line.split("\t")
    c[(int(float(x) // BIN), int(float(y) // BIN))] += 1
doc = dict(bin_um=BIN, n=sum(c.values()), source="DIE-KV-70 11-04 kv-wave-1104 kv3_pv_v8 3_place.odb all_registers -clock clk "
           "(edge-clock ring flops excluded)", bins=[[round((i + .5) * BIN, 2), round((j + .5) * BIN, 2), n] for (i, j), n in sorted(c.items())],
           type=TN, placed_kit=TN)
Path(REL).mkdir(exist_ok=True)
Path(REL, TN + ".json").write_text(json.dumps(doc, separators=(",", ":")) + "\n")
ck = raw["partition_types"][TN]["clock"]
assert ck.get("tap_mode") is None, ck.get("tap_mode")
ck.update(tap_mode="density", tap_max_sinks=1200, tap_target_sinks=960, tap_radius_um=200.0, sink_bins_file=f"{REL}/{TN}.json")
P1 = S.Plan(copy.deepcopy(raw), Path(a).resolve())
fin = TP.density_taps(P1, TN)
for k in raw:
    if k != "partition_types":
        assert raw[k] == orig[k], k
for t in raw["partition_types"]:
    if t != TN:
        assert raw["partition_types"][t] == orig["partition_types"][t], t
mm = re.search(r'^  "' + TN + r'": ', text, re.M)
_, j = json.JSONDecoder().raw_decode(text, mm.end())
text = text[:mm.end()] + json.dumps(raw["partition_types"][TN], indent=1).replace("\n", "\n  ") + text[j:]
assert json.loads(text) == raw
open(b, "w").write(text)
load = sorted(x[3] for x in fin)
m = PG.type_metrics(P1, TN)
rep = dict(sinks=doc["n"], bins=len(doc["bins"]), taps=len(fin), max_load=load[-1], median_load=load[len(load) // 2], empty=sum(1 for v in load if v == 0),
           max_radius=round(max(x[4] for x in fin), 1), clock_reach=m["clock_reach_max"], tap_sinks=m.get("grid_tap_sinks_max"))
json.dump(rep, open(c_, "w"), indent=1)
print(rep)
