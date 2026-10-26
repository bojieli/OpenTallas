#!/usr/bin/env python3
"""Physical candidate for serial-only capture diagnostics; original data leaves stand."""
import json,pathlib,sys,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_vm'))
from build_a2f_parent_kits import sites
s=json.loads((ROOT/'tools/ref_tile/specs_s81vm_a2f_parent_0310/fault.json').read_text())
s.update(top='dsfd_vm_capture_fault_serial',sources=['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_capture_fault_serial.sv'],name='dsfd_vm_capture_fault_serial_native_0415_r1',outline=dict(w=16.2,h=16.2,exact=True),pins={'W':['i_lo'],'E':['i_hi','i_status'],'N':['ck','rst_n'],'S':['fault']})
s['route'].update(period_ps=833.333,peak_ram_gb=8)
s['structural_change']='Actual81 serial-domain capture faults captured and reduced in a dedicated leaf; +2serial diagnostic edges only; source-current final seq-receiver phase proof required.'
s['slot_change_request']['why']='New serial diagnostic root requires exact connected source/seq home and per-root phase-R delivery; no fit or die timing claim.'
out=ROOT/'physical/s81_vm_capture_fault_0415';out.mkdir(exist_ok=True)
tcl=[];pins=[]
width={'i_lo':40,'i_hi':40,'i_status':1,'ck':1,'rst_n':1,'fault':1}
for face,names in s['pins'].items():
 ports=[n if width[n]==1 else f'{n}[{i}]' for n in names for i in range(width[n])]
 layer='M5' if face in 'NS' else 'M4';ss=sites(16.2,layer)
 assert len(ss)>=len(ports)
 for j,port in enumerate(ports):
  q=ss[int((j+.5)*len(ss)/len(ports))]
  x,y=(q,16.2 if face=='N' else 0) if face in 'NS' else (0 if face=='W' else 16.2,q)
  # Clock at face centre; reset on its adjacent signal track.
  if port=='ck':x=ss[len(ss)//2]
  elif port=='rst_n':x=ss[len(ss)//2+2]
  size='.024 .192' if layer=='M5' else '.192 .024'
  tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{size}}} -force_to_die_boundary')
  pins.append(dict(port=port,face=face,layer=layer,x_um=x,y_um=y))
pin='physical/s81_vm_capture_fault_0415/dsfd_vm_capture_fault_serial.tcl';(ROOT/pin).write_text('\n'.join(tcl)+'\n')
(out/'pins.json').write_text(json.dumps(pins,indent=1)+'\n');s['io_tcl']=pin
s['job'].update(owner='codex:S81 VM',branch='claude/s81-vm-widehub-2210',tag='capfault1',extra_paths=s['sources']+[pin,'tools/s81_vm/capture_fault_split_bench.sv','tools/s81_vm/capture_fault_split_gate.sh','rtl/dsrom_sys/s81_ph/vm/dsfd_vm_native_valid_diag.sv','rtl/dsrom_sys/s81_ph/vm/dsfd_vm_seq_tile.sv','rtl/dsrom_sys/s81_ph/vm/dsfd_vm_seq_static.sv'],purpose=s['structural_change'],cycles_added=0)
s['job']['benches']=[dict(name='capture_fault_'+m,cmd=f'bash tools/s81_vm/capture_fault_split_gate.sh /tmp/s81-capture-fault-{m} {m}',expect='pass' if m=='gold' else 'fail',threads=1,peak_ram_gb=2,needs=['iverilog'],**({'pass_regex':'CAPTURE_FAULT_SPLIT PASS'} if m=='gold' else {'fail_regex':'CAPTURE_FAULT_SPLIT FAIL'})) for m in ['gold','serial','core','early']]
p=ROOT/'tools/ref_tile/specs_s81vm_capture_fault_0415';p.mkdir(exist_ok=True);p=p/'serial.json';p.write_text(json.dumps(s,indent=1)+'\n')
subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(p)],cwd=ROOT,check=True)
