#!/usr/bin/env python3
"""HBM-CORES3 10-25 (COORD KIT-CENSUS): port-bind preflight of a hard-core kit.  The synthesised top module must expose
exactly the plan pins (pins.json bit names), with no missing and no extra port bits, before floorplan.
    port_bind_core.py NETLIST KITDIR   -> KITDIR/port_bind.json, exit 0 PASS / 1 FAIL"""
import json, re, sys
from pathlib import Path
net, kd = Path(sys.argv[1]), Path(sys.argv[2])
fz = json.load(open(kd / "freeze.json")); top = fz["module"]
plan = {(p["bus"] if p.get("bit") is None else f"{p['bus']}[{p['bit']}]") for p in json.load(open(kd / "pins.json"))}
txt = net.read_text()
m = re.search(r"(?ms)^module\s+\\?" + re.escape(top) + r"\s*\((.*?)^endmodule", txt)
if not m:
    r = dict(verdict="FAIL", reason=f"top {top} not in {net.name}")
else:
    body = m.group(1); bits = set()
    for d, w, names in re.findall(r"^\s*(input|output|inout)\s+(?:wire\s+)?(\[\d+:\d+\]\s+)?([^;]+);", body, re.M):
        for n in names.split(","):
            n = n.strip().lstrip("\\").strip()
            if not n:
                continue
            if w:
                hi, lo = map(int, re.findall(r"\d+", w))
                bits |= {f"{n}[{i}]" for i in range(min(hi, lo), max(hi, lo) + 1)}
            else:
                bits.add(n)
    miss = sorted(b for b in plan - bits if not (b.endswith("[0]") and b[:-3] in bits))
    extra = sorted(b for b in bits - plan if not (b + "[0]" in plan))
    r = dict(verdict="PASS" if not miss and not extra else "FAIL", plan_bits=len(plan), netlist_bits=len(bits),
             missing=len(miss), extra=len(extra), missing_examples=miss[:12], extra_examples=extra[:12])
(kd / "port_bind.json").write_text(json.dumps(r, indent=1) + "\n")
print("port_bind", r["verdict"], {k: v for k, v in r.items() if k in ("missing", "extra", "reason")})
sys.exit(0 if r["verdict"] == "PASS" else 1)
