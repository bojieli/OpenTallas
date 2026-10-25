#!/usr/bin/env python3
"""S81/PORTBIND 10-25: port-bind gap audit of the S81 die plan against the as-built die (tools/die_plan/bind.py).

Runs the Binder of tools/die_plan/bind.py (map + analyse + buses, no emit) on PLAN with the as-built binding section
ASBUILT and the cached as-built elaboration OUT/asbuilt.json, then lists EVERY leaf port bit the plan does not carry:

  die_io    leaf input driven by / leaf output driving an as-built die-top port (non-PHY ports = no plan lane)
  tied      leaf input bit driven by a literal (not a declared strap)
  open_out  leaf output with no load in the as-built die (unconnected output)
  unused    plan lane with no as-built driver/sink (a plan port with no RTL endpoint)
  empty     plan partition with no as-built leaf and no lane

    python3 portbind_audit.py PLAN.json ASBUILT.json OUT_DIR  -> OUT_DIR/portbind_raw.json
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

plan, abf, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
TOOLS = Path(plan).resolve().parents[3] / "tools" / "die_plan"
sys.path.insert(0, str(TOOLS))
import bind as BD  # noqa: E402

BD._AB_OVERRIDE["path"] = abf
raw = BD.load_plan(plan)
yjs = json.loads((out / "asbuilt.json").read_text())
B = BD.Binder(raw, yjs, Path(plan).parent, BD.plan_base(plan, raw))
B.map_cells()
B.analyse()
B.build_buses()
B.align_landings()
B.regen_params()
B.check_types()
F, G = B.F, B.G


def ranges(bits):
    bits = sorted(bits)
    r, s, p = [], None, None
    for b in bits:
        if s is None:
            s = p = b
        elif b == p + 1:
            p = b
        else:
            r.append([s, p])
            s = p = b
    if s is not None:
        r.append([s, p])
    return r


ptype = {p["name"]: p["type"] for p in raw["partitions"]}
rows = defaultdict(lambda: dict(bits=set(), src=set()))
for (ci, pn, i), d in B.sinks.items():
    k = d[0]
    if k not in ("top", "tied"):
        continue
    c = F.cells[ci]
    key = (k, c.path, c.module, pn, B.cpart.get(ci))
    rows[key]["bits"].add(i)
    rows[key]["src"].add(str(d[1]) if k == "top" else str(d[1:3]))
inputs = []
for (k, path, mod, pn, part), v in sorted(rows.items()):
    inputs.append(dict(kind=k, pin=f"{path}.{pn}", module=mod, port=pn, part=part, type=ptype.get(part),
                       bits=len(v["bits"]), ranges=ranges(v["bits"]), src=sorted(v["src"])[:8]))
used = set(G.loads)
top_out = defaultdict(list)
for n, (d, bits) in F.top_ports.items():
    if d == "output":
        for i, b in enumerate(bits):
            top_out[b].append(f"{n}[{i}]")
outs = []
for ci in B.cpart:
    c = F.cells[ci]
    for pn, bits in c.ports.items():
        if G.dirs[ci].get(pn) != "output":
            continue
        tops = sorted({t.split("[")[0] for b in bits if not isinstance(b, str) for t in top_out.get(b, [])})
        dead = all(isinstance(b, str) or b not in used for b in bits)
        if dead or tops:
            outs.append(dict(kind="die_io_out" if tops else "open_out", pin=f"{c.path}.{pn}", module=c.module,
                             port=pn, part=B.cpart.get(ci), type=ptype.get(B.cpart.get(ci)), bits=len(bits),
                             top=tops, all_unloaded=dead))
rep = B.report()[0]
res = dict(note=__doc__.splitlines()[0], plan=plan, asbuilt=abf, proof=rep["proof"], load_bits=rep["load_bits"],
           inputs=inputs, outputs=outs, unused_lanes=B.lanes_unused,
           empty=[e for e in B.errors if e.startswith("EMPTY_PARTITION")],
           top_ports={n: [d, len(b)] for n, (d, b) in F.top_ports.items()})
(out / "portbind_raw.json").write_text(json.dumps(res, indent=1))
print(len(inputs), len(outs), len(B.lanes_unused))
