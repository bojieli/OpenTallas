#!/usr/bin/env python3
"""HBM-CORES: fold CTS-probe measurements (cts_gather.sh output: kit|host|OT_TAP_BALANCE it0 ...|...) into
results/core_insertion_b2l.json (same rule as the table: I = max over flop-bearing clock ports (sinks >= 2) of the
mean sink insertion, TT placement RC, tap_balance it0 = natural trees).  Only views whose kit in the gather is the
view's current kit dir are updated; existing MEASURED rows are re-measured when the gather has their kit.
    update_insertion.py GATHER.txt [--kits /srv/opentallas-scratch/claude/elem-hbm/kits_b2l]"""
import argparse, json, re, collections
from pathlib import Path
H = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("gather")
ap.add_argument("--kits", default="/srv/opentallas-scratch/claude/elem-hbm/kits_b2l")
ap.add_argument("--views", default=None, help="HBM-CORES3 10-25: views file (e.g. views_b2n.json) whose views missing "
                "from the table are added as NOT MEASURED rows first (B2n re-placed cores)")
a = ap.parse_args()
T = H / "results" / "core_insertion_b2l.json"; d = json.load(open(T))
if a.views:
    have = {v["view"] for v in d["views"]}
    for x in json.load(open(a.views))["view_list"]:
        if x["view"] not in have:
            d["views"].append(dict(view=x["view"], module=x["module"], family=x.get("family"), placed=x.get("placed"),
                                   instances=x.get("instances"), outline_um=x["outline_um"], status="NOT MEASURED",
                                   views_file=Path(a.views).name))
com = d["common_latency_ps"]
meas = {}
for l in open(a.gather):
    f = l.rstrip("\n").split("|")
    if len(f) < 3 or "OT_TAP_BALANCE it0" not in f[2]: continue
    ports = {}
    for m in re.finditer(r"(\S+?)=(\d+)\((\d+)-(\d+),(\d+)\)", f[2].split(":", 1)[1]):
        ports[m.group(1)] = dict(mean_ps=int(m.group(2)), min_ps=int(m.group(3)), max_ps=int(m.group(4)), sinks=int(m.group(5)))
    meas[f[0]] = (f[1], ports)
n = collections.Counter()
for v in d["views"]:
    k = v["view"].replace("@", "_")
    if k not in meas: continue
    fz = next((Path(kk) / k / "freeze.json" for kk in a.kits.split(",") if (Path(kk) / k / "freeze.json").is_file()),
              Path(a.kits.split(",")[0]) / k / "freeze.json")   # HBM-CORES3: --kits DIR1,DIR2
    host, ports = meas[k]
    big = {p: x for p, x in ports.items() if x["sinks"] >= 2}
    if not big: n["no flop port"] += 1; continue
    I = max(x["mean_ps"] for x in big.values())
    w = sum(x["mean_ps"] * x["sinks"] for x in big.values()) / sum(x["sinks"] for x in big.values())
    v.update(kit=k, kit_hash=(json.load(open(fz))["kit_hash"] if fz.is_file() else None), host=host, status="MEASURED",
             ports=ports, insertion_mean_ps=I, insertion_sink_weighted_mean_ps=round(w, 1),
             insertion_max_ps=max(x["max_ps"] for x in big.values()), early_tap_ps=max(0, I - int(com)),
             contract_vclk_latency_ps=max(I, int(com)))
    v.pop("note", None); n["updated"] += 1
c = collections.Counter()
for v in d["views"]:
    if v["status"] == "NO KIT": c["no kit"] += 1
    elif v["status"] != "MEASURED": c["not measured"] += 1
    elif v["early_tap_ps"] > 40: c["early tap > 40 (over tol)"] += 1; c["measured, early tap > 0"] += 1
    elif v["early_tap_ps"] > 0: c["measured, early tap > 0"] += 1
    else: c["measured, I <= 250"] += 1
d["counts"] = dict(c)
T.write_text(json.dumps(d, indent=1) + "\n")
print(dict(n), dict(c))
