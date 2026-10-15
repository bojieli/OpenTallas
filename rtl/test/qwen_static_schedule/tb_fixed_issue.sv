`timescale 1ns/1ps
module tb_fixed_issue;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;
 wire re;wire [7:0] addr;reg [46:0]q=0;
 reg [46:0]rom[0:255];
 wire issue,fin,active,done,fault;wire[11:0]pc;wire[1:0]unit;wire[31:0]cycle;
 reg[11:0] candidate_pc;reg[1:0]candidate_unit;
 wire available=(MUT!=2);
 ot_qwen_fixed_issue #(.ROW_AW(8),.OWN(1)) dut(
 .clk(clk),.rst_n(rst_n),.start(start),.stop_cycle(32'd140),
 .slot_re(re),.slot_addr(addr),.slot_q(q),
 .candidate_v(1'b1),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),
 .available(available),.end_ok(1'b1),.issue_v(issue),.end_v(fin),.issue_pc(pc),.issue_unit(unit),
 .active(active),.done(done),.cycle(cycle),.fault(fault));
 reg[46:0]q_late=0;
 always @(posedge clk) if(re)begin q_late<=rom[addr];q<=(MUT==4)?q_late:rom[addr];end
 integer i,count=0;
 always @* begin
   candidate_pc=(cycle>=4 && cycle<132)?cycle-4:128;
   candidate_unit=(cycle==140)?0:1;
   if(MUT==1)candidate_pc=candidate_pc^12'd1;
 end
 always @(posedge clk)if(rst_n)begin
   if(issue)begin
     if(cycle!=count+4 || pc!=count || unit!=1)$fatal(1,"ISSUE TIMELINE/PAYLOAD");
     count=count+1;
   end
   if(fin && (cycle!=140 || pc!=128 || unit!=0))$fatal(1,"END TIMELINE");
 end
 initial begin
   for(i=0;i<128;i=i+1)rom[i]={1'b0,2'd1,12'(i),32'(i+4)};
   rom[128]={1'b1,2'd0,12'd128,32'd140};
   if(MUT==3)rom[31][31:0]=36; // wrong compiled cycle, skipped/late issue
   repeat(3)@(negedge clk);rst_n=1;
   @(negedge clk);start=1;@(negedge clk);start=0;
   wait(done);@(negedge clk);
   if(count!=128)$fatal(1,"DROPPED ISSUE");
   if((MUT==0 && fault) || ((MUT==1 || MUT==2) && !fault))$fatal(1,"FAULT CHECK");
   $display("FIXED_ISSUE_PASS MUT=%0d issues=%0d cycle=%0d fault=%0d",MUT,count,cycle,fault);$finish;
 end
 initial begin #20000;$fatal(1,"bench bounded by compiled 140-edge deadline");end
endmodule
