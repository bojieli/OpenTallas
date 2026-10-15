#!/usr/bin/env python3
"""READ_PIPE 2 native read/valid leaf kits (claude S81 VM F5, 2026-10-15).
Masters dsfd_vm_static_read_{q,v}<g>_p: the read_native_1015 leaves with every input pin-registered (leaf IN_REG=1),
because the r1 routed views fail the native capture audit (S+R > 190 ps: q0 316, q1 321, v0 276, v2 279, v6 226;
inputs crossed the leaf into select / valid / fault logic).  Same source-exact pin candidates, outlines, layers,
833.333 sign-off / 770 route, recipe 2 as the r1 kits (physical/s81_vm_read_native_1015, geometry adoption pending);
only the RTL boundary changes.  +1 stream edge per native read (READ_PIPE 1 -> 2, L13 -> L14)."""
import pathlib,json,hashlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
PIN=ROOT/'physical/s81_vm_read_native_1015'
OUT=ROOT/'physical/s81_vm_read_pinreg_1015';OUT.mkdir(parents=True,exist_ok=True)
SPECS=ROOT/'tools/ref_tile/specs_s81vm_read_pinreg_1015';SPECS.mkdir(parents=True,exist_ok=True)
read=json.loads((PIN/'read_pin_candidates.json').read_text())['types']
model={'schema':'s81.native-read-pinreg-leaves.v1','scope':'READ_PIPE 2 pin-registered read/valid leaves; no physical/throughput qualification',
       'period_ps':833.333,'route_period_ps':770,'added_stream_edges_per_native_read':1,'read_latency_edges':14,'types':{}}
branch=sys.argv[1] if len(sys.argv)>1 else 'claude/s81-vm-read-pinreg-1015'
for kind in 'qv':
 for g in range(8):
  base=f'dsfd_vm_static_read_{kind}{g}';top=base+'_p'
  choice=read[base];w,h=choice['outline_um']
  pins=json.loads((PIN/f'{base}.pins.json').read_text())
  assert pins['outline_um']==[w,h]
  faces={x:[]for x in 'NSEW'}
  for p in pins['pins']:
   b=p['port'].split('[')[0]
   if b not in faces[p['face']]:faces[p['face']].append(b)
  io=PIN/f'{base}.tcl'
  sources=['rtl/dsrom_sys/s81_ph/vm/'+n for n in (['dsfd_vm_static_read_valid.sv','dsfd_vm_static_read_valid_quartets_p.sv']if kind=='v'else['dsfd_vm_static_read_leaf.sv','dsfd_vm_static_read_quartets_p.sv'])]
  cmd=f'python3 tools/s81_vm/native_read_leaf_gate.py {kind} {g}'
  benches=[]
  for mode in ['positive','mutant']:
   b={'name':f'{kind}{g}p_{mode}','cmd':cmd+f' {mode} {{RUN}}/bench/{kind}{g}p_{mode} --pinreg','expect':'pass'if mode=='positive'else'fail','threads':1,'peak_ram_gb':1,'needs':['iverilog']}
   b['pass_regex'if mode=='positive'else'fail_regex']='NATIVE_LEAF '+('PASS'if mode=='positive'else'FAIL')+f' {kind}{g} '
   if mode=='positive':b['min_count_regex']=r'checks (\d+)'
   benches.append(b)
  spec={'name':f'{top}_native_1015_p1','top':top,'kind':'tile','sources':sources,'clock_port':'ck','reset_ports':['rst_n'],
   'outline':{'w':w,'h':h,'exact':True},'pins':faces,'io_tcl':str(io.relative_to(ROOT)),'macros':[],
   'route':{'pd':.4,'threads':8,'peak_ram_gb':16,'period_ps':770,'hold_margin_ns':.03},'recipe':2,
   'structural_change':('Native capture audit of the r1 routed views FAILS (S+R>190: q0 316.1/284 pins, q1 320.7, v0 276.4, v2 279.3, v6 225.8): '
     'inputs crossed the W->E leaf into the 4:1 select, partial-valid and fault logic. Every functional input is now registered at its pin '
     '(leaf IN_REG=1), the select/valid/fault logic runs register-to-register; v leaves pin-register expected/slot and the fault-observed '
     'inputs. +1 stream edge per native read (READ_PIPE 2, L14), WFC keeps one 4:3 epoch (pad 3->2). Same pins/outline/833.333 sign-off/770 route.'),
   'slot_change_request':{'contract':'S81 VM native read/FSR geometry candidate','version':'r1 pins unchanged','why':'new hard master name (_p) for the READ_PIPE 2 leaf; die geometry reservation required before parent adoption'},
   'job':{'owner':'Claude:S81 VM F5 read-capture','branch':branch,'tag':'pinreg1','extra_paths':['tools/s81_vm','rtl/dsrom_sys/s81_ph/vm','rtl/dsrom_sys/s81_ph/test','physical/s81_vm_read_native_1015'],
     'purpose':'READ_PIPE 2 pin-registered read leaf: exact positive oracle at +1 edge + observed mutant, native CTS/pin/reset, one route; parent unqualified.',
     'benches':benches,'cycles_added':1}}
  path=SPECS/f'{top}.json';path.write_text(json.dumps(spec,indent=2)+'\n')
  model['types'][top]={'base':base,'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in sources},'signal_pins':len(pins['pins']),'outline_um':[w,h],'qualification':'UNQUALIFIED_PENDING_NATIVE_CTS_ROUTE_AUDIT'}
  subprocess.run(['python3',str(ROOT/'tools/ref_tile/ref_tile.py'),'gen',str(path)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
(OUT/'model.json').write_text(json.dumps(model,indent=2)+'\n')
print('READ_PINREG_KITS',len(model['types']))
