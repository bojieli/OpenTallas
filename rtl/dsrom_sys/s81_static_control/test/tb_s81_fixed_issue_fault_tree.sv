`timescale 1ns/1ps
module tb_s81_fixed_issue_fault_tree;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,pw_v=0,job_v=0;reg[6:0]pw_a=0;reg[27:0]pw_d=0;
 reg[13:0]dv=0;reg[111:0]dt=0;wire[1:0]phase;
 wire fault,busy,ready,done,kdone,slot;wire[20:0]ktok;wire[3:0]code;
 wire[13:0]cv;wire[1175:0]cd;wire[31:0]nj,nc;
 integer mode=0,tick=0,launch=-1,first_local=-1,commands=0;
 ot_s81_fixed_issue #(.NOPS(128),.NENG(14),.STAGE(7),.ENG_PRESENT(14'h2001))dut(
 .clk(clk),.rst_n(rst_n),.pw_v(pw_v),.pw_a(pw_a),.pw_d(pw_d),.prog_len(8'd3),
 .job_v(job_v),.job_user(10'd37),.job_pos(21'd9),.job_tok(21'd8),.job_rdy(ready),.busy(busy),
 .job_done(done),.job_kdone(kdone),.done_slot(slot),.kit_tok(ktok),.cmd_v(cv),.cmd_d(cd),
 .engine_available(14'h3fff),.dn_v(dv),.dn_tag(dt),.fault(fault),.fault_code(code),.st_jobs(nj),.st_cmds(nc),.phase(phase));
 task write(input[6:0]a,input[27:0]d);begin @(negedge clk);pw_v=1;pw_a=a;pw_d=d;@(negedge clk);pw_v=0;end endtask
 task row(input[6:0]a,input[3:0]e,input[23:0]issue,completion);reg[75:0]w;begin
  w={completion,issue,e,24'(a+1)};if(e==15)w[23:0]=0;
  write(a,{2'd0,w[25:0]});write(a,{2'd1,w[51:26]});write(a,{2'd2,2'd0,w[75:52]});
 end endtask
 initial begin
  if(!$value$plusargs("mode=%d",mode))mode=0;
  repeat(3)@(negedge clk);rst_n=1;
  write(0,{2'd3,1'b0,8'd0,8'd3,2'd1,7'd7});
  row(0,0,0,4);
  row(1,mode==1?0:mode==2?12:13,mode==1?0:1,5);
  row(2,15,8,0);
  write(0,{2'd3,1'b1,8'd0,8'd3,2'd1,7'd7});
  repeat(130)@(negedge clk);
  if(mode==2)begin if(!fault||dut.sealed)$fatal(1,"absent-engine boot did not fail closed");$display("FAULT_TREE absent PASS");$finish;end
  while(phase!=0)@(negedge clk);
  job_v=1;@(negedge clk);job_v=0;
  repeat(20)@(negedge clk);
  if(mode==0&&fault)$fatal(1,"valid schedule faulted code%0d",code);
  if(mode!=0&&(!fault||first_local<0))$fatal(1,"fault detector missing mode%0d",mode);
  if(mode==1&&code!=9)$fatal(1,"collision class lost code%0d",code);
  if(mode==3&&code!=6)$fatal(1,"unexpected completion class lost code%0d",code);
  if(mode==4&&code!=8)$fatal(1,"missing completion class lost code%0d",code);
  if(mode!=1&&commands!=2)$fatal(1,"command calendar changed");
  $display("FAULT_TREE mode%0d PASS commands%0d code%0d",mode,commands,code);$finish;
 end
 always @(negedge clk)begin
  dv=0;dt=0;
  if(rst_n&&busy)begin
   if(dut.age[0]==4&&mode!=4)begin dv[0]=1;dt[7:0]=0;end
   if(dut.age[0]==5)begin dv[13]=1;dt[111:104]=1;end
   if(mode==3&&dut.age[0]==1)begin dv[13]=1;dt[111:104]=8'h7f;end
  end
 end
 always @(posedge clk)begin
  tick=tick+1;
  if(job_v)launch=tick;
  #1;
  commands=commands+$countones(cv);
  if(rst_n&&launch>=0)begin
   if((|dut.completion_bad_q)||(|dut.engine_bad_q)||dut.unexpected_q)begin
    if(first_local<0)begin first_local=tick;if(fault)$fatal(1,"diagnostic stage bypassed");end
   end
   if(first_local>=0&&tick==first_local+1&&!fault)$fatal(1,"registered diagnostic did not report on next edge");
   if(cv[0]&&tick!=launch+1)$fatal(1,"engine0 edge moved");
   if(cv[13]&&tick!=launch+2)$fatal(1,"engine13 edge moved");
   if(done&&tick!=launch+9)$fatal(1,"END edge moved");
  end
 end
 initial begin #30000;$fatal(1,"timeout");end
endmodule
