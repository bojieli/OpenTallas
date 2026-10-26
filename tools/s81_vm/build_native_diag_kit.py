import json,pathlib,sys,hashlib,subprocess
r=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(r/'tools/s81_vm'));from build_a2f_parent_kits import sites
s=json.loads((r/'tools/ref_tile/specs_s81vm_a2f_parent_0310/fault.json').read_text());s.update(top='dsfd_vm_native_valid_diag',sources=['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_native_valid_diag.sv'],name='dsfd_vm_native_valid_diag_native_0400_r2',outline=dict(w=21.6,h=21.6,exact=True),pins={'W':['release_slot'],'N':['expected_v'],'E':['ck','rst_n','i_v','i_fault'],'S':['fault']})
s['route']['period_ps']=833.333;s['route']['peak_ram_gb']=8
s['structural_change']='Five actual captured diagnostic cones replace unplaced combinational valid/slot and write-fault summary logic; +2 diagnostic edges, zero normal data edges; source-current full parent proof pending.'
s['slot_change_request']['why']='New leaf needs coherent exact connected parent home; no fit or die closure claimed.'
out=r/'physical/s81_vm_diag_0400_r2';out.mkdir(exist_ok=True);widths={'ck':1,'rst_n':1,'i_v':32,'expected_v':18,'release_slot':90,'i_fault':16,'fault':1};tcl=[];pins=[]
for face,names in s['pins'].items():
 layer='M5' if face in 'NS' else 'M4';ss=sites(21.6,layer);bits=[(n,i) for n in names for i in range(widths[n])]
 if ('ck',0) in bits:bits.remove(('ck',0));bits.insert(len(bits)//2,('ck',0))
 assert len(ss)>=len(bits),(len(ss),len(bits))
 for j,(n,i) in enumerate(bits):
  q=ss[int((j+.5)*len(ss)/len(bits))];x,y=(q,21.6 if face=='N' else 0) if face in 'NS' else (0 if face=='W' else 21.6,q);port=n if widths[n]==1 else f'{n}[{i}]'
  size='.024 .192' if layer=='M5' else '.192 .024'
  tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{size}}} -force_to_die_boundary');pins.append(dict(port=port,face=face,x_um=x,y_um=y,layer=layer))
pin='physical/s81_vm_diag_0400_r2/dsfd_vm_native_valid_diag.tcl';(r/pin).write_text('\n'.join(tcl)+'\n');s['io_tcl']=pin
(out/'pins.json').write_text(json.dumps(pins,indent=1)+'\n');s['job'].update(owner='codex:S81 VM',branch='claude/s81-vm-widehub-2210',tag='diag2',extra_paths=s['sources']+[pin,'tools/s81_vm/native_valid_diag_bench.sv','tools/s81_vm/native_valid_diag_gate.sh','rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_suhc_return_map.sv'],purpose=s['structural_change'],cycles_added=0)
s['job']['benches']=[dict(name='diag_'+m,cmd=f'bash tools/s81_vm/native_valid_diag_gate.sh /tmp/s81-diag-gate-{m} {m}',expect='pass' if m=='gold' else 'fail',threads=1,peak_ram_gb=2,needs=['iverilog'],**({'pass_regex':'NATIVE_DIAG PASS'} if m=='gold' else {'fail_regex':'NATIVE_DIAG FAIL'})) for m in ['gold','valid','slot','drop','extra']]
p=r/'tools/ref_tile/specs_s81vm_diag_0400';p.mkdir(exist_ok=True);p=p/'diag_r2.json';p.write_text(json.dumps(s,indent=1)+'\n');subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(p)],check=True)
