#!/usr/bin/env python3
"""Actual central host fragment -> AXI decoder -> native target124 SRAM scan.
No fictitious four-VM programme is supplied; global launch stays unqualified.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TB=r'''`timescale 1ps/1fs
module tb;
reg clk=0;always #416.667 clk=~clk;reg rst_n=0;
reg av=0,wv=0,doorbell=0;reg[11:0]addr=0;reg[31:0]data=0;wire ar,wr,bv;
wire cfg_v,desc_v,launch_v,host_fault;wire[7:0]target;wire[11:0]cfg_addr,base;wire[12:0]limit;wire[15:0]loops;wire[255:0]cfg_data;
wire configured,busy,done,fault,instruction_v;wire[31:0]instruction;wire[9:0]instruction_pc;
ot_vms_calendar_host_static host(.clk(clk),.rst_n(rst_n),.s_awvalid(av),.s_awready(ar),.s_awaddr(addr),.s_wvalid(wv),.s_wready(wr),.s_wdata(data),.s_wstrb(4'hf),.s_bvalid(bv),.s_bready(1'b1),
 .s_arvalid(1'b0),.s_araddr(12'd0),.s_rready(1'b1),.c_awready(1'b1),.c_wready(1'b1),.c_bvalid(1'b0),.c_arready(1'b1),.c_rvalid(1'b0),.c_rdata(32'd0),
 .lcp_doorbell(doorbell),.program_active(4'd0),.program_done(4'd0),.program_fault(4'd0),
 .ext_cfg_v(cfg_v),.ext_target(target),.ext_cfg_addr(cfg_addr),.ext_cfg_data(cfg_data),.ext_desc_v(desc_v),.ext_base(base),.ext_limit(limit),.ext_loops(loops),.ext_launch_v(launch_v),.fault(host_fault));
ot_hbm_engram_fetch_program fetch(.clk_control(clk),.clk_mem(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(base[9:0]),.desc_limit(limit[9:0]),.desc_loops(loops),.launch_v(launch_v),.token_v(1'b0),.token_cid(17'd0),.token_first(1'b0),.home_done(8'd0),.home_fault(8'd0),
 .configured(configured),.busy(busy),.done(done),.fault(fault),.instruction_v(instruction_v),.instruction(instruction),.instruction_pc(instruction_pc));
integer cycle=0,cfg_count=0,desc_count=0,desc_edge=-1,config_age=-1;reg expect_block=0;
reg[255:0]expected[0:5];
task tick;begin @(posedge clk);#1;cycle++;
 if(cfg_v)begin
  if(target!=124 || cfg_addr!==12'(cfg_count) || cfg_data!==expected[cfg_count])$fatal(1,"actual host124 frame packing/address");cfg_count++;
 end
 if(desc_v)begin
  desc_count++;if(target!=124)$fatal(1,"actual target descriptor collar");
  if(desc_count==1)begin if(base!=0 || limit!=42 || loops!=1)$fatal(1,"active descriptor");desc_edge=cycle;end
  else if(base!=0 || limit!=0 || loops!=0)$fatal(1,"actual disable descriptor");
 end
 if(configured && config_age<0)config_age=cycle-desc_edge;
 if(fault || (!expect_block && host_fault) || instruction_v || launch_v || busy)$fatal(1,"unexpected native fault/launch before whole VM image");
end endtask
task write32(input[11:0]a,input[31:0]d);begin
 @(negedge clk);addr=a;data=d;av=1;wv=1;#1;
 while(!ar || !wr)begin tick;@(negedge clk);#1;end
 tick;@(negedge clk);av=0;wv=0;tick;
end endtask
initial begin
 EXPECTED
 repeat(4)tick;@(negedge clk);rst_n=1;
 ACTIVE
 repeat(140)tick;
 if(!configured || cfg_count!=6 || desc_count!=1 || config_age<0 || config_age>130)$fatal(1,"native SRAM full scan/guard cfg%0d desc%0d age%0d",cfg_count,desc_count,config_age);
 $display("ACTIVE target124 six-word SRAM scan passed age%0d",config_age);
 DISABLED
 repeat(8)tick;
 if(configured || desc_count!=2 || fetch.loaded[5:0]!=6'b111111)$fatal(1,"actual disable preserves programme catalogue");
 // The real host collar must reject global launch without actual four VM descriptors.
 expect_block=1;@(negedge clk);doorbell=1;tick;@(negedge clk);doorbell=0;repeat(3)tick;
 if(!host_fault || launch_v || configured)$fatal(1,"missing actual fourVM configuration boundary");
 $display("PASS actual central CSR fragment→AXI target124→SRAM scan six256words age%0d disable retained; unconfigured fourVM global launch blocked",config_age);$finish;
end
endmodule
'''
def run(out,fragment,host_source):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);fragment=Path(fragment).resolve();host_source=Path(host_source).resolve();binding=json.loads(fragment.read_text());image=binding['actual_image'];text=TB
 expected='\n'.join(f"expected[{w['addr']}]=256'h{w['data']};"for w in image['programme']['configuration_writes']);text=text.replace(' EXPECTED',expected)
 def emit(fr):
  return '\n'.join(f"repeat({w['idle_core_edges']})tick;"if 'idle_core_edges'in w else f"write32(12'h{w['address']:03x},32'h{w['data']:08x});"for w in fr['axi_writes'])
 text=text.replace(' ACTIVE',emit(binding['active'])).replace(' DISABLED',emit(binding['disabled']));tb=out/'tb.sv';tb.write_text(text)
 paths=[ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',host_source,ROOT/'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_fetch_program.sv'];runs=[]
 for name,mut in [('baseline',False),('actual_host_payload_bit4_mutant',True)]:
  src=[str(p)for p in paths]
  if mut:
   old='ext_cfg_data<={s_wdata,engine_assembly[223:0]};';s=host_source.read_text();assert old in s
   variant=out/'host_corrupt.sv';variant.write_text(s.replace(old,"ext_cfg_data<={s_wdata,engine_assembly[223:0]} ^ 256'd16;"));src[1]=str(variant)
  exe=out/name;cp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),*src,str(tb)],capture_output=True,text=True);(out/(name+'.build.log')).write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout+cp.stderr
  rp=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(out/(name+'.run.log')).write_text(rp.stdout+rp.stderr);assert (rp.returncode==0)==(not mut),rp.stdout+rp.stderr;runs.append(dict(name=name,returncode=rp.returncode,output=rp.stdout.strip()))
 result=dict(schema='opentallas.hbm.engram.actual_host_config.v1',status='pass',runs=runs,central_source_sha256=binding['central_source_sha256'],fragment_sha256=hashlib.sha256(fragment.read_bytes()).hexdigest(),actual_host_source_sha256=hashlib.sha256(host_source.read_bytes()).hexdigest(),actual_fetch_source_sha256=hashlib.sha256(paths[-1].read_bytes()).hexdigest(),scope='Actual external host AXI writes and real adapter→native124 SRAM initialization/disable. No invented VM calendars; real host rejects global launch because all four actual VM descriptors are absent. Loader C10 execution/architectural kernel remains open.')
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--fragment',required=True);ap.add_argument('--host-source',required=True);a=ap.parse_args();run(a.out,a.fragment,a.host_source)
