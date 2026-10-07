#!/usr/bin/env python3
"""Composition gate: real native north front + protected owner + consumed-ACK descriptor flight."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile
from hbm_sm_native_front_gate import bench,SOURCES,FIXTURE,ROOT
from hbm_sm_native_owner_join_model import model
B='rtl/hbm_accel/control_20261007/'
JOIN=B+'native_join/ot_hbm_sm_native_owner_join.sv'
DESC=B+'descriptor/ot_hbm_sm_descriptor_bridge.sv'

def main():
 join=(ROOT/JOIN).read_text();sm=(ROOT/'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv').read_text()
 header=re.sub(r'//[^\n]*','',sm).split('module ot_hbm_accel_smh #(',1)[1].split(');',1)[0]
 smports=set(re.findall(r'\b(?:input|output)\s+wire\s*(?:\[[^\]]+\])?\s*(\w+)',header))
 actual=dict(re.findall(r'\.(\w+)\((\w+)\)',join.split('ot_hbm_accel_smh sm(',1)[1].split(');',1)[0]))
 assert set(actual)==smports,'native production join has missing/extra/tied SM ports'
 assert actual['op_xb']=='op_xb' and actual['start_ready']=='start_ready'
 assert actual['d_ready']=='south_d_ready' and actual['release_in']=='release_in'
 runs=[]
 with tempfile.TemporaryDirectory(prefix='sm-native-joined-')as d:
  for hops in [0,16,31]:
   tb=bench().replace('reg d_ready;', 'wire d_ready;\n reg south_ready=0;')
   tb=tb.replace('reg sm_fault;', 'wire sm_fault;')
   tb=tb.replace('d_ready=(cyc%7!=0);','south_ready=(cyc%7!=0);').replace('d_ready=0;','south_ready=0;').replace('sm_fault=0;','')
   extra=f'''
 wire south_d_valid;wire[31:0]south_d_base;wire[23:0]south_d_lines;
 integer descriptors_seen=0;
 ot_hbm_sm_descriptor_bridge #(.ENABLE(1),.HOPS({hops}),.DEPTH(2)) descriptor(
  .clk(clk),.rst_n(rst_n),.s_valid(d_valid),.s_ready(d_ready),.s_base(d_base),.s_lines(d_lines),
  .d_valid(south_d_valid),.d_ready(south_ready),.d_base(south_d_base),.d_lines(south_d_lines),
  .south_fault(1'b0),.north_fault(sm_fault),.fault());
 always @(posedge clk)begin
  if(south_d_valid && south_ready)begin
   if(south_d_base!=32'h80000000+descriptors_seen*4096 || south_d_lines!=words[descriptors_seen*10+4])$fatal(1,"south descriptor native join mismatch");
   descriptors_seen=descriptors_seen+1;
  end
  if(d_valid && d_ready && descriptors_seen!=ops+1)$fatal(1,"owner ACK before real south acceptance");
 end
'''
   tb=tb.replace('endmodule',extra+'\nendmodule')
   p=Path(d)/'tb.sv';p.write_text(tb);exe=Path(d)/'sim'
   subprocess.run(['iverilog','-g2012','-s','tb_sm_serial_owner','-o',str(exe),str(p),str(ROOT/DESC),*[str(ROOT/x)for x in SOURCES]],check=True)
   r=subprocess.run(['vvp',str(exe),'+SEQ='+str(ROOT/FIXTURE)],capture_output=True,text=True)
   if r.returncode:raise RuntimeError(r.stdout)
   runs.append(dict(descriptor_hops=hops,returncode=0,output=r.stdout.strip()))
 return dict(scope='literal complete SMH port binding plus smallest native owner/north-front/descriptor transport composition. Full arithmetic, weight service, real program/allocator/result-publication providers are not simulated or physically bound.',
  model=model(),native_SM_ports_bound=len(actual),op_xb_and_start_ready_native=True,release_external=True,runs=runs,
  sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in [JOIN,DESC,*SOURCES,FIXTURE,'tools/hbm_sm_native_owner_join_model.py','tools/hbm_sm_native_owner_join_build.py','tools/hbm_sm_native_front_gate.py','tools/hbm_sm_native_join_gate.py','tools/hbm_sm_descriptor_bridge_model.py','tools/hbm_sm_serial_protection_model.py','tools/hbm_sm_serial_owner_model.py','results/physical/hbm_smh_actual_pin_readback_20261007/actual_top_pin_boxes.json']},passed=True,selected=False)
if __name__=='__main__':print(json.dumps(main(),indent=2))
