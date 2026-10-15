`timescale 1ns/1ps
module tb_fixed_issue_pw;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,pw_v=0;reg[9:0]pw_addr=0;reg[63:0]pw_data=0;
 wire issue,fin,active,done,fault;wire[11:0]pc;wire[1:0]unit;wire[31:0]cycle;
 reg[11:0]candidate_pc;reg[1:0]candidate_unit;
 integer n,got=0,ends=0;
 function is_end(input integer x);begin is_end=(x==5||x==13||x==19);end endfunction
 always @*begin
  candidate_pc=(cycle>=4&&cycle<=23)?cycle-4:0;
  candidate_unit=is_end(candidate_pc)?0:2;
 end
 ot_qwen_fixed_issue_pw #(.OWN(2))dut(.clk(clk),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),
 .start(start),.stage(6'd9),.candidate_v(1'b1),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),
 .available(MUT==2?1'b0:1'b1),.end_ok(1'b1),.issue_v(issue),.end_v(fin),.issue_pc(pc),.issue_unit(unit),
 .active(active),.done(done),.cycle(cycle),.fault(fault));
 task wr(input[9:0]a,input[63:0]d);begin
  @(negedge clk);pw_v=1;pw_addr=a;pw_data=d;
  @(negedge clk);pw_v=0;
 end endtask
 always @(posedge clk)if(rst_n&&(issue||fin))begin
  if(cycle!=got+4||pc!=got||unit!=(is_end(got)?0:2))$fatal(1,"PW ISSUE TIMELINE");
  if(fin)ends=ends+1;
  got=got+1;
 end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  wr(1018,{32'h43414c32,32'd23});
  for(n=0;n<20;n=n+1)if(MUT!=1||n!=7)wr(984+n,{17'd0,1'(n==19),2'(is_end(n)?0:2),12'(n),32'(n+4)});
  wr(1017,{32'h43414c53,4'd0,10'd25,6'd9,6'd20,6'd8});
  @(negedge clk);start=1;@(negedge clk);start=0;
  wait(done);@(negedge clk);
  if(got!=20||ends!=3)$fatal(1,"PW MISSING REAL END/ISSUE");
  if((MUT==0&&fault)||(MUT==2&&!fault))$fatal(1,"PW FAULT");
  $display("FIXED_ISSUE_PW_PASS MUT=%0d total=%0d ENDs=%0d fault=%0d",MUT,got,ends,fault);$finish;
 end
 initial begin #20000;$fatal(1,"PW bench exceeds compiledstage deadline");end
endmodule
