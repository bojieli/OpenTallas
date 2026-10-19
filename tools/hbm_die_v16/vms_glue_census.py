#!/usr/bin/env python3
"""Complete non-clock mapped census (copy of tools/hbm_static/pgstream_safe/census.py for the VM glue g6, L2H-PGVM). Run on fleet on the gate synthesis netlist (1_2_yosys.raw.v); a component audit, not STA."""
import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import textbook_lint as tl

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("netlist", type=pathlib.Path)
p.add_argument("output", type=pathlib.Path)
p.add_argument("--top")
a = p.parse_args()
g, top = tl.flatten(tl.parse_verilog(a.netlist.read_text()), a.top)
index = tl.build(g, None)
clocks, _ = tl.clock_nets(g, index)
rows = []
aliases = {}
for name, net in g.net_id.items():
    aliases.setdefault(g.find(net), []).append(name)
for net, driver in index["driver"].items():
    if net <= 3 or net in clocks:
        continue
    cell = driver[0]
    kind = "port" if cell < 0 else index["kind"][cell]
    if kind in ("buf", "tie"):
        continue
    loads, flop_loads, example = tl.bufinv_fanout(g, index, net, clocks)
    row=dict(net=tl.net_label(g, index, net), kind=kind,
             loads=loads, flop_loads=flop_loads, example=example)
    if loads > 32:
        seen={net}; stack=[net]
        while stack:
            current=stack.pop()
            for ci,_,_ in index['loads'].get(current,()):
                if index['kind'][ci]=='buf':
                    for child in tl._out_nets(g,index,ci):
                        if child not in seen:
                            seen.add(child);stack.append(child)
        row['source_aliases']=sorted({name for child in seen for name in aliases.get(child,[]) if not name.startswith('_')})
    rows.append(row)
rows.sort(key=lambda row: (-row["loads"], row["net"]))
out = dict(top=top, netlist_sha256=hashlib.sha256(a.netlist.read_bytes()).hexdigest(),
           census_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
           textbook_sha256=hashlib.sha256(pathlib.Path(tl.__file__).read_bytes()).hexdigest(),
           scope="all non-clock nonconstant drivers, including ports, reset, combinational and FF; BUF/INV transparent",
           cells=len(g.cells), ff_cells=index["kind"].count("ff"), roots=len(rows),
           over32=[row for row in rows if row["loads"] > 32],
           maximum=rows[0]["loads"] if rows else 0, all_roots=rows,
           native_timing_qualified=False, physical_qualified=False)
a.output.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({key: value for key, value in out.items() if key not in ("over32", "all_roots")}, indent=2))
print("over32", len(out["over32"]))
