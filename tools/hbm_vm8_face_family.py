#!/usr/bin/env python3
"""Size and optionally emit additive native face hierarchy for all eight halves.

Default preserves the selected source's per-bit depths. Explicit --f3 changes
oreg1 launches to D3, requiring a new inter-half alignment gate. Never edits
the original split8 source or runs a compiler/physical build.
"""
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HALVES=[f'{q}_{h}' for q in ('se','ne','nw','sw') for h in ('n','s')]
CAP=re.compile(r'reg \[(\d+):0\] (x_\w+); always @\(posedge clk\) \2 <= (\w+);')
OUT=re.compile(r'for \(genvar k = 0; k < (\d+); k = k \+ 1\) begin : (g_\w+)\s*ot_hfd_oreg([13]) u \(\.clk\(clk\), \.d\((\w+)\[k\]\), \.q\((\w+)\[k\]\)\);\s*end')
INGRESS=re.compile(r'reg \[(\d+):0\] i0_(\w+); always @\(posedge clk\) i0_\2 <= \2;\s*reg \[\1:0\] i1_\2; always @\(posedge clk\) i1_\2 <= i0_\2;\s*reg \[\1:0\] i_\2; always @\(posedge clk\) i_\2 <= i1_\2;')
def render(half,f3=False):
 p=ROOT/f'physical/hbm_accel_die_views/vm/split8/hfd_vm_{half}.sv'
 original=p.read_text();inventory=[]
 def cap(m):
  w=int(m[1])+1;inventory.append(dict(role='capture',width=w,depth=1,banks=(w+127)//128))
  return f'wire [{w-1}:0] {m[2]};\n    ot_hbm_vm8_face_bus #(.W({w}),.D(1)) u_{m[2]}(.clk(clk),.d({m[3]}),.q({m[2]}));'
 def ingress(m):
  w=int(m[1])+1;inventory.append(dict(role='ingress',width=w,depth=3,banks=(w+127)//128))
  return f'wire [{w-1}:0] i_{m[2]};\n    ot_hbm_vm8_face_bus #(.W({w}),.D(3)) u_i_{m[2]}(.clk(clk),.d({m[2]}),.q(i_{m[2]}));'
 def out(m):
  w=int(m[1]);d=3 if f3 else int(m[3]);inventory.append(dict(role='launch',width=w,depth=d,banks=(w+127)//128))
  return f'ot_hbm_vm8_face_bus #(.W({w}),.D({d})) {m[2]}(.clk(clk),.d({m[4]}),.q({m[5]}));'
 source=OUT.sub(out,INGRESS.sub(ingress,CAP.sub(cap,original)))
 assert inventory and 'ot_hfd_oreg' not in source
 source=source.replace(f'module hfd_vm_{half} (',f'module hfd_vm_{half}_face_hier (',1)
 macros=sum(2*int(n) for n in re.findall(r'ot_hfd_vm_slice #\(\.NM\((\d+)\)\)',original))
 model=dict(half=half,source=str(p.relative_to(ROOT)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
  mode='f3' if f3 else 'preserve',inventory=inventory,
  register_bits=sum(x['banks']*128*x['depth'] for x in inventory),
  relay_leaves=sum(x['banks'] for x in inventory),storage_macro_count=macros,
  parent_geometry_um=[1600,1000],actual_parent_pin_clock_binding=False,
  arithmetic_or_control_change=False,exactness_qualified=False,physical_qualified=False)
 return source,model
def model(f3=False):
 return dict(schema='opentallas.hbm.vm8.face_family.v1',halves=[render(h,f3)[1] for h in HALVES],
  default_enabled=False,MACs_per_cycle=0,
  memory_bytes_per_cycle='actual128x256 macros remain in each unchanged half',
  boundary_bits_per_cycle='literal original fullface widths; perhalf inventory below',
  routing_tracks_per_leaf=256,channel_capacity_tracks=None,
  mux_demux_cost='static128bit slicing including priced tailpadding',
  fanout_cost='real D1/D3 kept leaves; actual clockroot binding pending',
  latency='preserve every original perbit depth bydefault; explicitf3 requires freshalignment gate',
  dependencies=['One actual D1 andoneactual D3 viaClaudeexclusiveintake before replication',
   'Actual1600x1000 parentpin/clockbinding andslotfit',
   'All8halves fullface/nativecontrol alignment gate beforeassembly'],headline_credit=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--halves',nargs='+',choices=HALVES,default=HALVES)
 p.add_argument('--f3',action='store_true');p.add_argument('--out',type=Path)
 a=p.parse_args();m=model(a.f3)
 if a.out:
  a.out.mkdir(parents=True,exist_ok=False)
  (a.out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
  for h in a.halves:(a.out/f'hfd_vm_{h}_face_hier.sv').write_text(render(h,a.f3)[0])
 else:print(json.dumps(m,indent=2))
if __name__=='__main__':main()
