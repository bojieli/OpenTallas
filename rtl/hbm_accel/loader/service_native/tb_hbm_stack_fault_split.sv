`timescale 1ns/1ps
module tb_hbm_stack_fault_split;
 parameter integer MUT=0;
 reg hc=0,sc=0;always #4 hc=~hc;always #3 sc=~sc;
 reg hr=0,sr=0;reg [191:0] bits=0;
 reg [31:0]rv=0,pf=0;reg [7:0]svg=0,share=0,del=0;reg cal=0;
 wire [31:0] scalar;wire [1:0] fault;wire [6:0] status[2];
 for(genvar p=0;p<32;p=p+1)begin:fold assign scalar[p]=|bits[p*6+:6];end
 ot_hbm_svc_stack_fault ref_i(.hbm_clk(hc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),.row_v(rv),.pc_fault(pf),.owner_fault(scalar),.svg_fault(svg),.share_fault(share),.del_fault(del),.cal_fault(cal),.fault(fault[0]),.status(status[0]));
 wire [191:0] cbits=(MUT==1)?(bits & ~(192'b1<<5)):bits;
 wire cc=(MUT==2)?1'b0:hc;
 ot_hbm_svc_stack_fault_split dut(.hbm_clk(cc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),.row_v(rv),.pc_fault(pf),.owner_fault_split(cbits),.svg_fault(svg),.share_fault(share),.del_fault(del),.cal_fault(cal),.fault(fault[1]),.status(status[1]));
 integer checks=0,cases=0;
 always @(negedge sc) begin
 #0.1;
 if(sr)begin
  checks=checks+1;
  if(fault[0]!==fault[1] || status[0]!==status[1])$fatal(1,"STACK_FAULT_SPLIT mismatch case%0d status%h/%h",cases,status[0],status[1]);
 end
 end
 task reset;begin
 hr=0;sr=0;bits=0;rv=0;pf=0;svg=0;share=0;del=0;cal=0;
 repeat(3)@(negedge hc);#1;hr=1;sr=1;repeat(4)@(negedge hc);
 end endtask
 initial begin
 for(integer n=0;n<192;n=n+1)begin
 reset();@(negedge hc);#1;bits=192'b1<<n;repeat(2)@(negedge hc);#1;bits=0;repeat(12)@(negedge hc);
 if(status[0]!==7'b0000100 || status[1]!==7'b0000100)$fatal(1,"STACK_FAULT_SPLIT missing owner bit%0d",n);cases=cases+1;
 end
 // Concurrent CA/PC and all stream faults retain their existing domains/edges.
 reset();@(negedge hc);#1;rv=32'h3;pf=32'h80000000;bits=192'b1<<191;svg=8'h40;share=8'h2;del=8'h80;cal=1;
 repeat(16)@(negedge hc);
 if(status[0]!==7'h7f || status[1]!==7'h7f)$fatal(1,"STACK_FAULT_SPLIT mixed flags");cases=cases+1;
 $display("STACK_FAULT_SPLIT PASS cases=%0d checks=%0d owner_pins=192 added_edges=0",cases,checks);$finish;
 end
endmodule
