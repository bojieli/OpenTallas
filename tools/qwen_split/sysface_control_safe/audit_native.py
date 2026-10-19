#!/usr/bin/env python3
"""Audit direct native leaf pin loads; retained BUF trees are physical loads.

Use on the actual ORFS mapped netlist. Constant tie fanout is reported separately
for physical tie distribution. Clock ownership is audited separately by CTS.
"""
import argparse, hashlib, json, sys, re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import textbook_lint as T
ap=argparse.ArgumentParser();ap.add_argument('netlist');ap.add_argument('--out',required=True);ap.add_argument('--top',default='qfd_sys_face_control_safe');a=ap.parse_args()
p=Path(a.netlist);g,top=T.flatten(T.parse_verilog(p.read_text()),a.top)
# Explicit committed hard-macro port directions; never infer unknown macro pins.
macro_types={}
for master in ['ot_rom_4096x72_m8','ot_sram_1r1w_64x16_m1']:
 bb=Path('physical/asap7_memory_macros')/master/(master+'_bb.v')
 macro_types[master]=T.module_port_dirs(bb.read_text())
macros=[]
for typ,name,pins in g.cells:
 if typ in macro_types:
  dirs=macro_types[typ]
  assert all(T._base(pin) in dirs for pin in pins),(typ,name)
  macros.append({'master':typ,'name':name,'pins':[[pin,0,0,dirs[T._base(pin)].upper()] for pin in pins]})
A=T.build(g,{'macros':macros})
assert all(k!='macro' or typ in macro_types for k,(typ,_,_) in zip(A['kind'],g.cells)), 'untyped native leaf'
clocks={n for n,sinks in A['loads'].items() if any(A['kind'][i] in ('ff','macro') and T.CLKPIN_RE.match(T._base(pin)) for i,pin,_ in sinks)}
rows=[];ties=[]
for n,sinks in A['loads'].items():
 if n in clocks:continue
 driver=A['driver'].get(n)
 row={'net':g.net_name[n],'loads':len(sinks),'driver': None if driver is None else {'cell':g.cells[driver[0]][1] if driver[0]>=0 else 'TOP','pin':driver[1]},'sinks':[[g.cells[i][1],pin] for i,pin,_ in sinks[:3]]}
 (ties if driver and driver[0]>=0 and A['kind'][driver[0]]=='tie' else rows).append(row)
rows.sort(key=lambda x:x['loads'],reverse=True);ties.sort(key=lambda x:x['loads'],reverse=True)
out={'netlist_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'method':'actual direct native leaf input-pin count; native BUF retained; explicit macro BB directions','max_nonclock_nontie_loads':max(r['loads'] for r in rows),'over32':[r for r in rows if r['loads']>32],'top20':rows[:20],'constant_tie_roots':ties,'clock_nets_excluded':len(clocks),'native_source_buffer_instances':sum(name.startswith('u_ot_pr_core.b') for _,name,_ in g.cells),'status':'FAIL' if any(r['loads']>32 for r in rows) else 'PASS'}
Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['over32','top20','constant_tie_roots']}))
