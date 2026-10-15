`timescale 1ns/1ps
module tb_vms_host_disable124;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,aw=0,wv=0;reg[11:0]addr=0;reg[31:0]data=0;
 wire fault,dv;wire[7:0]target;wire[11:0]base;wire[12:0]limit;wire[15:0]loops;
 ot_vms_calendar_host_static dut(.clk(clk),.rst_n(rst_n),
 .s_awvalid(aw),.s_awaddr(addr),.s_wvalid(wv),.s_wdata(data),.s_wstrb(4'hf),.s_bready(1'b1),
 .s_arvalid(1'b0),.s_araddr(12'b0),.s_rready(1'b1),
 .c_awready(1'b1),.c_wready(1'b1),.c_bvalid(1'b0),.c_arready(1'b1),.c_rvalid(1'b0),.c_rdata(32'b0),
 .lcp_doorbell(1'b0),.program_active(4'b0),.program_done(4'b0),.program_fault(4'b0),
 .ext_desc_v(dv),.ext_target(target),.ext_base(base),.ext_limit(limit),.ext_loops(loops),.fault(fault));
 task wr(input[11:0]a,input[31:0]d);
 begin @(negedge clk);aw=1;wv=1;addr=a;data=d;@(posedge clk);#1;end endtask
 task finishwr;begin @(negedge clk);aw=0;wv=0;@(posedge clk);#1;end endtask
 integer checks=0;
 task check(input[7:0]t,input[11:0]b,input[12:0]l,input[31:0]lp,input bit good);
 begin
  @(negedge clk);rst_n=0;aw=0;wv=0;repeat(2)@(posedge clk);@(negedge clk);rst_n=1;
  wr(12'hf20,{24'b0,t});finishwr();wr(12'hf28,{7'b0,l,b});finishwr();wr(12'hf2c,lp);
  if(fault!==!good || dv!==good)$fatal(1,"descriptor check target%0d base%0d limit%0d loops%h good%0d fault%0d desc%0d",t,b,l,lp,good,fault,dv);
  if(good && (target!==t || base!==b || limit!==l || loops!==lp[15:0]))$fatal(1,"descriptor payload changed");
  checks=checks+1;finishwr();
 end endtask
 initial begin
  check(124,0,0,0,1);check(123,0,0,0,0);check(125,0,0,0,0);
  check(124,1,0,0,0);check(124,0,1,0,0);check(124,0,0,1,0);check(124,0,0,32'h10000,0);
  check(120,0,2091,1,1);check(80,0,2048,1,1);check(124,0,42,1,1);
  $display("HOST_DISABLE124_GUARD PASS %0d exact/partial/other/normal descriptors",checks);$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
