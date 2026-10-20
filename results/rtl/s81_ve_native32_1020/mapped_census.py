#!/usr/bin/env python3
"""Read-only mapped census using the binding textbook parser/BUF-INV semantics.
Does not prove physical reach, pin anchoring, SRAM semantics or tied-port intent.
"""
import argparse,importlib.util,json,hashlib
from pathlib import Path
a=argparse.ArgumentParser();a.add_argument('--tool',required=True);a.add_argument('--netlist',required=True);a.add_argument('--dump');a.add_argument('--top');a.add_argument('--out',required=True);o=a.parse_args()
s=importlib.util.spec_from_file_location('textbook',o.tool);t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
mods=t.parse_verilog(Path(o.netlist).read_text());g,top=t.flatten(mods,o.top);del mods
D=json.loads(Path(o.dump).read_text()) if o.dump else None
A=t.build(g,D);clk,sinks=t.clock_nets(g,A);rows=[]
for n,d in A['driver'].items():
 if n<=3 or n in clk or (d[0]>=0 and A['kind'][d[0]] in ('buf','tie','phys')):continue
 total,ff,example=t.bufinv_fanout(g,A,n,clk)
 label=t.net_label(g,A,n);ci=d[0]
 rows.append(dict(net=label,loads=total,flop_loads=ff,driver_kind='port' if ci<0 else A['kind'][ci],driver=d[1] if ci<0 else g.cells[ci][1]+'/'+d[1],reset=t.is_reset_net(label,g.net_name[n],port=ci<0),example=example))
rows.sort(key=lambda r:-r['loads']);over=[r for r in rows if r['loads']>32]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=dict(schema='opentallas.mapped_native_census.v1',top=top,netlist=o.netlist,netlist_sha256=sha(o.netlist),tool_sha256=sha(o.tool),method='textbook parse/flatten/build; all nonclock nonBUF/INV/TIE/physical roots; BUF+INV-transparent load-pin count including output ports; no reset exclusion',limit=32,root_count=len(rows),max_loads=max((r['loads'] for r in rows),default=0),over32_count=len(over),over32=over,roots=rows,unknown_macro_pin_directions_inferred=D is None,limitations=['physical reach requires placed native census','pin registration/tied functional port intent/storage semantic audit separate'])
Path(o.out).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:r[k] for k in ('schema','top','root_count','max_loads','over32_count')}))
