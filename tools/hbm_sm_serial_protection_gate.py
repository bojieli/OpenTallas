#!/usr/bin/env python3
"""Full-shape normal trace and precise single-state-bit injections into DMR owner."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
from hbm_sm_serial_protection_model import model
ROOT=Path(__file__).resolve().parents[1]
BASE='rtl/hbm_accel/control_20261007/'
CORE=BASE+'protected/ot_hbm_sm_serial_protected_core.sv'
WRAP=BASE+'protected/ot_hbm_sm_serial_protected.sv'
TB=BASE+'tb_sm_serial_owner.sv'
FIXTURE='results/rtl/hbm_sm_command_20261007/stress_seq.hex'
DEPS=[CORE,BASE+'ot_hbm_sm_seq_ingress.sv','rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv']
# State chosen before the affected field can produce a side effect.
FAULTS=[('record',3),('address',1),('limit',1),('index',8),('count',8),('word_index',2),
        ('group',8),('ordinal',8),('weight_base',6),('resident_base',10),('state',8),
        ('arrived',11),('published',11),('xw_data',9)]

def main():
 runs=[]
 with tempfile.TemporaryDirectory(prefix='hbm-sm-protection-') as d:
  cases=[('normal',None,None,False),('protection_off',None,None,False)]
  cases += [(side+'_'+field,side,(field,phase),False) for side in ['a','g_secondary.b'] for field,phase in FAULTS]
  cases += [('checker_bypass','a',('address',1),True)]
  for name,side,inj,bypass in cases:
   tb=(ROOT/TB).read_text().replace('ot_hbm_sm_serial_owner #(.ENABLE(1))','ot_hbm_sm_serial_protected #(.ENABLE(1),.PROTECT('+('0' if name=='protection_off' else '1')+'))')
   tb=tb.replace('dut.state','dut.a.state')
   wrap=(ROOT/WRAP).read_text()
   if bypass:wrap=wrap.replace('assign mismatch=PROTECT &&','assign mismatch=1\'b0 &&')
   if inj:
    field,phase=inj; target='dut.'+side+'.'+field
    # Primary fields are >=2-bit except the two handshake flags.
    bit=target
    width=dict(record=320,address=32,limit=33,index=16,count=16,word_index=4,group=4,ordinal=8,weight_base=32,resident_base=7,state=5,arrived=1,published=1,xw_data=2048)[field]
    injection=f'''
 reg [{width-1}:0] injected_bit;
 initial begin
  wait(rst_n);wait(dut.a.state=={phase});@(negedge clk);
  injected_bit={bit} ^ 1'b1;force {bit}=injected_bit;
  #1;
  if(!fault)$fatal(1,"state fault not detected: {name}");
  if(start || xw_en || mem_req_valid || mem_rsp_ready || alloc_valid || alloc_rsp_ready || d_valid || x_req_valid || x_ready || publication_ready || done || run_ready)
   $fatal(1,"side effect survived detected fault: {name}");
  repeat(2)@(negedge clk);
  release {bit};#1;
  if(!fault || start || xw_en || publication_ready || done)$fatal(1,"fault latch lost: {name}");
  $display("PASS injected {name}; effects suppressed and abort retained");$finish;
 end
'''
    tb=tb.replace('if(fault)$fatal(1,"owner fault op=%0d state=%0d",ops,dut.a.state);','')
    tb=tb.replace('endmodule',injection+'\nendmodule')
   p=Path(d)/'tb.sv';p.write_text(tb);w=Path(d)/'wrap.sv';w.write_text(wrap);exe=Path(d)/'sim'
   subprocess.run(['iverilog','-g2012','-s','tb_sm_serial_owner','-o',str(exe),str(p),str(w),*[str(ROOT/x) for x in DEPS]],check=True)
   r=subprocess.run(['vvp',str(exe),'+SEQ='+str(ROOT/FIXTURE)],text=True,capture_output=True)
   if (r.returncode==0)==bypass:raise RuntimeError(name+' '+r.stdout)
   runs.append(dict(case=name,returncode=r.returncode,output=r.stdout.strip()))
 baseline=json.loads((ROOT/'results/rtl/hbm_sm_command_20261007/serial_owner_component.json').read_text())
 assert runs[0]['output']==baseline['runs'][0]['output'], 'protected normal trace differs from baseline'
 assert runs[1]['output']==baseline['runs'][0]['output'], 'protection-off trace differs from baseline'
 assert baseline['sources'][BASE+'ot_hbm_sm_serial_owner.sv']==hashlib.sha256((ROOT/(BASE+'ot_hbm_sm_serial_owner.sv')).read_bytes()).hexdigest(), 'baseline source changed'
 return dict(baseline_commit='dd2022955', baseline_trace_identical=True, scope='RTL minimum parent; two full-shape owners, external memory/allocation/result peers still modeled',model=model(),runs=runs,
  sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [WRAP,TB,FIXTURE,*DEPS,'tools/hbm_sm_serial_protection_model.py','tools/hbm_sm_serial_protection_build.py','tools/hbm_sm_serial_protection_gate.py']},passed=True,selected=False)
if __name__=='__main__':print(json.dumps(main(),indent=2))
