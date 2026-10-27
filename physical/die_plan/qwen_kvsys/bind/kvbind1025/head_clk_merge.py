#!/usr/bin/env python3
"""PATH-KV-BIND 10-25 (GEOM-REVIEW m6 e2/e6 cond (3), KV pin delta): one clock pin per head-eighth core.

Every member leaf of a head eighth (u_front / u_l8 / u_stin / u_stk / u_kt) is clocked by the SAME native net
(n_clk_core_<Q>[0], checked here on the bound native netlist for every composite), and the head-eighth kit already
clocks all of its flops from the FIRST clock pin of its pin table; the other per-member __clk pins (6 on e2/e4/e6,
7 on e0 (+u_kt), 5 on e1/e3/e5/e7) are port declarations only -- unloaded pins the parent must not route the die clock
to.  This tool removes them structurally:
  * cores/kv3_head_eighth_e*_pins.json: keep the first `*__clk[0]` pin, drop the others (no other pin moves);
  * the composition spec: every `*__clk` composite port of a head-eighth core is merged into that one kept port (one
    bit, all member clk endpoints -- bind_compose requires identical original nets, so a wrong merge fails the bind).
usage: head_clk_merge.py CORES_DIR SPEC_IN(.json[.gz]) SPEC_OUT.json.gz NATIVE_NETLIST.v.gz REPORT.json"""
import gzip
import json
import re
import sys
from pathlib import Path

cores_dir, spec_in, spec_out, netlist, rep_p = sys.argv[1:]
keep, removed = {}, {}
for f in sorted(Path(cores_dir).glob("kv3_head_eighth_e*_pins.json")):
    text = f.read_text()
    d = json.loads(text)
    nl = "\n" if text.endswith("\n") else ""
    ind = next(i for i in (0, 1, 2, None) if json.dumps(d, indent=i) + nl == text)   # keep the file format
    ck = [p["name"] for p in d["pins"] if re.fullmatch(r"\w+__clk\[0\]", p["name"])]
    if not ck:
        continue
    keep[d["core"]] = ck[0][:-3]
    removed[d["core"]] = [x[:-3] for x in ck[1:]]
    d["pins"] = [p for p in d["pins"] if p["name"] not in ck[1:]]
    d["source"] += (" | PATH-KV-BIND 10-25 head_clk_merge.py: one clock pin per core (kit clocks every flop from it); "
                    f"dropped unloaded per-member clock pins {removed[d['core']]}")
    f.write_text(json.dumps(d, indent=ind) + nl)
raw = Path(spec_in).read_bytes()
spec = json.loads(gzip.decompress(raw) if spec_in.endswith(".gz") else raw)
# native clock net of every member leaf instance
clk = {}
with gzip.open(netlist, "rt") as fh:
    for line in fh:
        m = re.match(r"\s*\w+\s+(?:#\(.*?\)\s+)?(head_\w+)\s+\(.*?\.clk\(([^)]+)\)", line)
        if m:
            clk[m.group(1)] = m.group(2)
merged = 0
for core in spec["cores"]:
    k = keep.get(core["module"])
    if not k:
        continue
    names = [n for n in core["ports"] if n.endswith("__clk")]
    eps = [e for n in names for grp in core["ports"][n]["bits"] for e in grp]
    nets = {clk.get(e["member"]) for e in eps}
    if len(nets) != 1 or None in nets:
        raise SystemExit(f"{core['inst']}: member clocks are not one native net: {nets}")
    if k not in names:
        raise SystemExit(f"{core['inst']}: kept clock {k} is not a composite port")
    for n in names:
        del core["ports"][n]
    core["ports"][k] = dict(dir="input", bits=[eps], indices=[0])
    merged += 1
Path(spec_out).write_bytes(gzip.compress(json.dumps(spec, indent=1).encode(), 9, mtime=0))
Path(rep_p).write_text(json.dumps(dict(schema="opentallas.kv.head_clk_merge.v1", kept=keep, removed=removed,
                                       composites_merged=merged), indent=1) + "\n")
print(json.dumps(dict(merged=merged, removed={k: len(v) for k, v in removed.items()})))
