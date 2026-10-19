#!/usr/bin/env python3
"""Audit every native driver with BUF and INV transparent.

Use on the actual ORFS mapped netlist. Constant tie fanout remains part of the reported failure
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
rows=[]
for n in sorted(set(A['loads'])|set(A['driver'])):
 if n in clocks:continue
 d=A['driver'].get(n)
 if d is None:continue
 kind='top_input' if d[0]<0 else A['kind'][d[0]]
 total,ff,example=T.bufinv_fanout(g,A,n,clocks)
 rows.append({'net':g.net_name[n],'loads':total,'ff_terminal_loads':ff,'driver_kind':kind,'driver':'TOP.'+str(d[1]) if d[0]<0 else g.cells[d[0]][1]+'.'+d[1]})
rows.sort(key=lambda r:r['loads'],reverse=True)
classes={k:max((r['loads'] for r in rows if r['driver_kind']==k),default=0) for k in sorted({r['driver_kind'] for r in rows})}
out={'method':'every actual native driver; BUF/INV transparent terminal input pins plus top outputs; explicit macro directions; only clock excluded','netlist_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'max_all_nonclock':rows[0]['loads'],'max_nonconstant':max(r['loads'] for r in rows if r['driver_kind']!='tie'),'max_by_kind':classes,'over32':[r for r in rows if r['loads']>32],'all_drivers':rows,'status':'FAIL' if any(r['loads']>32 for r in rows) else 'PASS'}
Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['all_drivers','over32']}))
