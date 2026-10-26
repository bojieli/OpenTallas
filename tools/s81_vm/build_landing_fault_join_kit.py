#!/usr/bin/env python3
"""Tiny real two-stage fault join; analytical model must exist before generation."""
import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
model=json.loads((ROOT/'tools/s81_vm/landing_fault_join_model.json').read_text())
P=ROOT/'physical/s81_vm_landing_fault_join_1417';P.mkdir(parents=True,exist_ok=True)
side=model['outline_um'][0];pin=P/'pins.tcl';tcl=[]
for i in range(12):
 y=round(4.332+i*.960,3);tcl.append(f'place_pin -pin_name {{i_fault[{i}]}} -layer M4 -location {{0 {y}}} -pin_size {{.192 .024}} -force_to_die_boundary')
for i in range(3):
 y=round(7.212+i*2.88,3);tcl.append(f'place_pin -pin_name {{o_fault[{i}]}} -layer M4 -location {{{side} {y}}} -pin_size {{.192 .024}} -force_to_die_boundary')
tcl.append(f'place_pin -pin_name {{ck}} -layer M5 -location {{10.812 {side}}} -pin_size {{.024 .192}} -force_to_die_boundary')
pin.write_text('\n'.join(tcl)+'\n')
benches=[]
for mode in ['base','drop']:
 b=dict(name='fault_join_'+mode,cmd=f'bash tools/s81_vm/landing_fault_join_gate.sh {{RUN}}/bench/fault_{mode} {mode}',expect='pass' if mode=='base' else 'fail',threads=1,peak_ram_gb=1,needs=['iverilog'])
 b['pass_regex' if mode=='base' else 'fail_regex']='LANDING_FAULT_JOIN '+('PASS' if mode=='base' else 'FAIL');benches.append(b)
benches.append(dict(name='joined_component',cmd='bash tools/s81_vm/landing_joined_gate.sh {RUN}/bench/joined base',expect='pass',threads=1,peak_ram_gb=1,needs=['iverilog'],pass_regex='LANDING_JOINED PASS'))
spec=dict(name='dsfd_vm_static_landing_fault_join_native_1417',top='dsfd_vm_static_landing_fault_join',kind='tile',
 sources=['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_landing_fault_join.sv'],clock_port='ck',reset_ports=[],
 outline=dict(w=side,h=side,exact=True),pins=dict(W=['i_fault'],E=['o_fault'],N=['ck']),io_tcl=str(pin.relative_to(ROOT)),
 macros=[],route=dict(pd=.4,threads=4,peak_ram_gb=4,period_ps=770,hold_margin_ns=.03,cts_sink=dict(size=8,diameter_um=15,extra='-distance_between_buffers 15')),
 recipe=2,io_flop_at_pins=dict(cols=4,allow_none=True),inhold=True,outhold=True,keep_pin_regs=True,pin_reg_split=True,
 hold_pad=dict(cell='HB2xp67_ASAP7_75t_R',out_cell='HB1xp67_ASAP7_75t_R'),io_budget=dict(**{'in':.55,'out':.55}),
 structural_change='Real15FF hard fault join replaces parent combinational OR:12 plain pin captures then3 registered OR4 outputs. Two diagnostic edges, zero data/calendar edges; every parent connection is wire between real hardmasters. No local reset; producer reset zeros propagate exactly through2 stages. Model tools/s81_vm/landing_fault_join_model.json.',
 slot_change_request=dict(contract='S81 five-root landing candidate',version='1417-faultjoin',why='One21.6um square faultjoin plus4x95.04um lanes: .0365969664mm2 perVM vs old.0329204736 (+.0036764928); roots1->5 (+4), data age2 unchanged, diagnostic+2; no parent fit claim'),
 job=dict(owner='codex:S81 VM landing1417',branch='codex/s81-vm-landing-1417',tag='join1',cycles_added=0,
 extra_paths=['tools/s81_vm','rtl/dsrom_sys/s81_ph/vm','physical/s81_vm_landing_fault_join_1417'],
 purpose='Harden fault reduction in its own root; full4096pattern exact bench, observed missing-lane mutant, fulljoined2048bit composition equivalent with diagnostic+2.',benches=benches))
p=P/'spec.json';p.write_text(json.dumps(spec,indent=1)+'\n')
subprocess.run([sys.executable,str(ROOT/'tools/ref_tile/ref_tile.py'),'gen',str(p)],cwd=ROOT,check=True)
