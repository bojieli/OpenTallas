#!/usr/bin/env python3
"""Native compact 53x33-bit payload leaf; four roots replace one empty wide strip."""
import pathlib,json,subprocess,hashlib
from build_a2f_parent_kits import sites
import die_port_bind as D
R=pathlib.Path(__file__).resolve().parents[2]
assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
s=json.load(open(R/'tools/ref_tile/specs_s81vm_a2f_parent_0310/payload_r2.json'))
s['top']='s81_a2_w0_payload33';s['name']='s81_a2_w0_payload33_native_0330_r1'
s['sources']=['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_a2f_payload33.sv']
s['outline']=dict(w=291.6,h=32.4,exact=True);s['pins']={'N':['i_data','ck','o_epoch'],'S':['o_data'],'W':['i_mask','o_mask','rst_n']}
s['structural_change']='Actual r2 wide payload: R1031.1ps/spread100.7ps, TT-38.3/FF-50.3; 1166um empty strip persists after coface mask and centre clock. Split into FOUR independent53source x (32data+1mask) physical leaves per old payload, 16 total roots. Actual 1749 data/mask FF per leaf preserves6996 per old payload; local reset/epoch replicas add18FF per old payload. Max half-span146um; unchanged one-edge data/mask/epoch calendar. Existing controller per slice observes all four LOCAL epochs, preserving its closed RTL; global OR proof required.'
s['slot_change_request']=dict(contract='S81 VM actual payload root partition',version='payload33-0330',why='Four291.6x32.4 leaves replace each1166.4x75.6 strip, actual new pin graph/clockreset4->16 rebind owed; no parent adoption until proof and native closure.')
s['route']['peak_ram_gb']=12
src=R/s['sources'][0];m=next(x for x in D.parse_modules(src.read_text(),str(src)) if x.name==s['top']);e=m.env({});ww={n:m.width(n,e) for n in m.ports}
pins=[];t=[];w,h=291.6,32.4
for f,names in s['pins'].items():
 b=[(n,i) for n in names for i in range(ww[n])]
 if f=='W':b=[(n,i) for i in range(53) for n in ['i_mask','o_mask']]+[('rst_n',0)]
 layer='M5' if f in'NS'else'M4';ss=sites(w if f in'NS'else h,layer)
 central=[x for x in b if x[0]in('ck','o_epoch')];b=[x for x in b if x[0]not in('ck','o_epoch')];b[len(b)//2:len(b)//2]=central
 assert len(b)<=len(ss),(f,len(b),len(ss))
 for j,(n,i) in enumerate(b):
  q=ss[int((j+.5)*len(ss)/len(b))];x,y=(q,h if f=='N'else 0) if f in'NS'else(w if f=='E'else 0,q)
  p=n if ww[n]==1 else f'{n}[{i}]';sz='.024 .192' if layer=='M5'else'.192 .024'
  pins.append(dict(port=p,face=f,layer=layer,x_um=x,y_um=y));t.append(f'place_pin -pin_name {{{p}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{sz}}} -force_to_die_boundary')
d=R/'physical/s81_vm_a2f_parent_0310/payload33';d.mkdir(exist_ok=True);io=d/(s['top']+'.tcl');io.write_text('\n'.join(t)+'\n');s['io_tcl']=str(io.relative_to(R))
(d/(s['top']+'.pins.json')).write_text(json.dumps(dict(master=s['top'],outline_um=[w,h],source=s['sources'][0],source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),data_mask_ff=1749,total_ff=1755,pins=pins),indent=1)+'\n')
deps=s['sources']+['tools/s81_vm/area_a2_controlled.sv','tools/s81_vm/a2f_payload33_gate.py','tools/s81_vm/payload33_epoch_or_gate.py','tools/s81_vm/payload33_epoch_or_bench.sv','tools/s81_vm/area_a2f.sv','tools/s81_vm/area_a2f_control_resetlocal.sv',s['io_tcl']]
benches=[dict(name='payload33_gold',cmd='python3 tools/s81_vm/a2f_payload33_gate.py',expect='pass',threads=1,peak_ram_gb=2,needs=['iverilog'],pass_regex='PAY33 PASS')]
for v in ['DATA','MASK','EPOCH','RESET']:benches.append(dict(name='payload33_mut_'+v,cmd='python3 tools/s81_vm/a2f_payload33_gate.py --mutant '+v,expect='fail',threads=1,peak_ram_gb=2,needs=['iverilog'],fail_regex='PAY33 FAIL'))
for mutant in [False,True]:benches.append(dict(name='payload33_global_or_'+str(mutant),cmd='python3 tools/s81_vm/payload33_epoch_or_gate.py'+(' --mutant' if mutant else ''),expect='fail'if mutant else'pass',threads=1,peak_ram_gb=4,needs=['iverilog'],**({'fail_regex':'PAY33_OR FAIL'}if mutant else{'pass_regex':'PAY33_OR PASS'})))
s['job']=dict(owner='codex:S81 parent payload root partition',branch='claude/s81-vm-a2f-parent-0200',tag='split33',extra_paths=deps,purpose='Exact payload33 and16-root scheduled global OR proof with observed data/mask/epoch/reset/omission mutants; actual compact native hard master.',cycles_added=0,benches=benches)
p=R/'tools/ref_tile/specs_s81vm_a2f_parent_0310/payload33.json';p.write_text(json.dumps(s,indent=1)+'\n');subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(p)],cwd=R,check=True)
