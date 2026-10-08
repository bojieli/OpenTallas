#!/usr/bin/env python3
"""Directed faults in finite descriptor control; verifies side-effect containment."""
from pathlib import Path
import json,subprocess,tempfile,hashlib
from hbm_sm_descriptor_bridge_gate import ROOT,RTL,TB,DEPS

def main():
 runs=[]
 with tempfile.TemporaryDirectory(prefix='sm-desc-fault-')as d:
  for name,path,width,bypass in [('pending','dut.pending',1,False),('pending_complement','dut.pending_n',1,False),('queue_a_count','dut.a.cnt',2,False),('queue_b_count','dut.b.cnt',2,False),('checker_bypass','dut.pending',1,True)]:
   src=(ROOT/RTL).read_text();tb=(ROOT/TB).read_text().replace('if(fault)$fatal(1,"bridge fault");','')
   if bypass:src=src.replace('wire mismatch=',"wire mismatch=1'b0 && (").replace('(a_fault!=b_fault);','(a_fault!=b_fault));')
   inj=f'''
 reg[{width-1}:0] bad_value;
 initial begin
  wait(rst_n);wait(dut.pending && dut.a_valid);@(negedge clk);
  bad_value={path} ^ 1'b1;force {path}=bad_value;#1;
  if(fault!==1'b1 || d_valid!==1'b0 || s_ready!==1'b0)$fatal(1,"descriptor fault escapes: {name}");
  repeat(2)@(negedge clk);release {path};#1;
  if(fault!==1'b1 || d_valid!==1'b0 || s_ready!==1'b0)$fatal(1,"descriptor abort lost: {name}");
  $display("PASS descriptor injected {name}; consumption and ACK suppressed");$finish;
 end
'''
   tb=tb.replace('endmodule',inj+'\nendmodule')
   rp=Path(d)/'rtl.sv';rp.write_text(src);bp=Path(d)/'tb.sv';bp.write_text(tb);exe=Path(d)/'sim'
   subprocess.run(['iverilog','-g2012','-s','tb_hbm_sm_descriptor_bridge','-o',str(exe),str(rp),str(bp),*[str(ROOT/p)for p in DEPS]],check=True)
   r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
   if (r.returncode==0)==bypass:raise RuntimeError(r.stdout)
   runs.append(dict(case=name,returncode=r.returncode,output=r.stdout.strip()))
 return dict(scope='component single-control-fault containment; independent physical banks not qualified',runs=runs,sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in [RTL,TB,*DEPS,'tools/hbm_sm_descriptor_fault_gate.py']},passed=True,selected=False)
if __name__=='__main__':print(json.dumps(main(),indent=2))
