`timescale 1ns/1ps
module tb_s81_fixed_issue_base;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,pw_v=0,job_v=0;reg[6:0]pw_a=0;reg[27:0]pw_d=0;
 wire[12:0]cv;wire[1091:0]cd;reg[12:0]dv=0;reg[103:0]dt=0;
 wire done,fault;wire[3:0]code;
 ot_s81_fixed_issue #(.NOPS(2),.OP_BASE(2),.STAGE(7),.ENG_PRESENT(13'h400)) dut(
 .clk(clk),.rst_n(rst_n),.pw_v(pw_v),.pw_a(pw_a),.pw_d(pw_d),.prog_len(8'd2),
 .job_v(job_v),.job_user(10'd37),.job_pos(21'd1000),.job_tok(21'd21946),
 .job_rdy(),.busy(),.job_done(done),.job_kdone(),.done_slot(),.kit_tok(),
 .cmd_v(cv),.cmd_d(cd),.engine_available(13'h400),.dn_v(dv),.dn_tag(dt),
 .fault(fault),.fault_code(code),.st_jobs(),.st_cmds(),.phase());
 reg[34:0]pwmem[0:7];reg[12:0]due[0:1099];reg[103:0]tags[0:1099];
 integer tick=-1,mode=0,i,commands=0,ends=0;
 initial begin
  if(!$value$plusargs("mode=%d",mode))mode=0;
  $readmemh("base_program.hex",pwmem);
  for(i=0;i<1100;i++)begin due[i]=0;tags[i]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(i=0;i<8;i++)begin @(negedge clk);pw_v=1;pw_a=pwmem[i][34:28];pw_d=pwmem[i][27:0];@(negedge clk);pw_v=0;end
 end
 always @(negedge clk)if(rst_n)begin
  dv=due[tick+1];dt=tags[tick+1];if(mode==1)dt[87:80]=0;
  job_v=tick==999;
 end
 always @(posedge clk)if(!rst_n)tick=-1;else begin
  tick++;#1;
  if(cv[10])begin
   commands++;
   if(tick!=1005||cd[840+:84]!={1'b0,10'd37,21'd1000,21'd21946,24'd11880,7'd2})$fatal(1,"physical native op partition identity changed");
   due[tick+3][10]=1;tags[tick+3][80+:8]=8'd2;
  end
  if(done)begin ends++;if(tick!=1011)$fatal(1,"END moved");end
  if(tick==1080)begin
   if(commands!=1||ends!=1||fault!=(mode==1))$fatal(1,"OP_BASE completion verification failed code=%0d",code);
   $display("S81_FIXED_OP_BASE mode=%0d actual_op=2 commands=%0d end=%0d fault=%0d",mode,commands,ends,fault);$finish;
  end
 end
endmodule
