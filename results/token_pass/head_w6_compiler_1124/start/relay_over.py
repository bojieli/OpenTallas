#!/usr/bin/env python3
"""HEAD-START-R16: close the provider START-stage raw reset hops over 405 um with one registered die-level relay
(ot_dp_rrelay, same cell as the type raw relays) per over-reach stage, sited on the hop midpoint, clocked from the
stage clock tap port.  +1 raw release cycle on those stages (inside the root settle guard; checked).
usage: relay_over.py IN_PROVIDER OUT_PROVIDER EXPORTS.json"""
import json, sys, re
from pathlib import Path
I, O, E = sys.argv[1:4]
doc = json.load(open(I + "/start_stages.json")); sv = open(I + "/start_stages.sv").read(); ex = json.load(open(E))
over = {sid for sid, _ in ex["summary"].get("over_hop_open", [])}; rows = {r["stage"]: r for r in ex["stages"]}
relays = []
for s in doc["stages"]:
    if s["id"] not in over:
        continue
    port = s["reset_port"]; w = "rrly_" + s["id"]; clk = s["clock_port"]
    pat = r"(\.clk\(" + re.escape(clk) + r"\), \.rst_raw_n\()" + re.escape(port) + r"(\))"
    sv, n = re.subn(pat, lambda m: m[1] + w + m[2], sv)
    if n != 1:
        raise SystemExit(f"{s['id']}: expected one raw reset binding, found {n}")
    inst = re.search(r"(?m)^    ot_dp_landing_(?:origin|root)\b[^\n]*\(\.clk\(" + re.escape(clk) + r"\)", sv)
    sv = (sv[:inst.start()] + f"    wire {w};\n    ot_dp_rrelay u_rrly_{s['id']} (.clk({clk}), .d({port}), .q({w}));"
          f"  // R16 START reset relay, hop midpoint\n" + sv[inst.start():])
    a = rows[s["id"]]["source"]["xy_um"]; b = s["clock_pin_xy_um"]
    mid = [round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3)]
    hop = rows[s["id"]]["hop_um"]
    s["reset_relay"] = dict(instance="u_rrly_" + s["id"], net=w, xy_um=mid, hops_um=[round(hop / 2, 1)] * 2,
                            added_raw_release=1)
    relays.append((s["id"], hop, mid))
rootid = next(s["id"] for s in doc["stages"] if s["root"]); rr = rows[rootid]["source"]["raw_release"]
span = max(rows[s["id"]]["source"]["raw_release"] + (1 if s["id"] in over else 0) - rr for s in doc["stages"])
assert span + 4 <= doc["root_settle"], (span, doc["root_settle"])
doc["root_settle_guard"]["raw_relative_span_with_relays"] = span; doc["reset_relays"] = len(relays)
Path(O).mkdir(exist_ok=False)
json.dump(doc, open(O + "/start_stages.json", "w"), indent=1); open(O + "/start_stages.sv", "w").write(sv)
for n in ("ctree.v", "ctree.tcl"):
    if Path(I + "/" + n).exists():
        Path(O + "/" + n).write_bytes(Path(I + "/" + n).read_bytes())
print(json.dumps(dict(relays=len(relays), max_half_hop_um=max(h / 2 for _, h, _ in relays), span=span,
                      settle=doc["root_settle"])))
