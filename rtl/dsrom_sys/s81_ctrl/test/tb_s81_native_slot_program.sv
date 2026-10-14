`timescale 1ns/1ps
module tb_s81_native_slot_program #(parameter integer MUT=0);
 reg clk=0,rst=0;always #0.4166 clk=~clk;
 reg pw=0;reg[6:0] pa=0;reg[27:0] pd=0;
 reg jv=0;wire jr,jdone;wire[11:0] cv;wire[12*84-1:0] cd;
 wire[11:0] dn;wire[12*8-1:0] dt;wire sf;wire[3:0] fc;wire[31:0] jobs,cmds,stalls;
 wire ev,hv,ha,af,onl;wire[83:0] ed,hd;reg edone=0;reg[7:0] etag=0;wire adone;wire[7:0] atag;
 assign dn={9'd0,adone,2'd0};assign dt={72'd0,atag,16'd0};
 ot_s81_stage_seq #(.QD(8),.HC_SLOT_REBASE(MUT==0)) seq(.clk(clk),.rst_n(rst),
 .pw_v(pw),.pw_a(pa),.pw_d(pd),.prog_len(8'd2),.job_v(jv),.job_rdy(jr),
 .job_user(10'd19),.job_pos(21'd1048575),.job_tok(21'd27),.job_done(jdone),
 .cmd_v(cv),.cmd_d(cd),.dn_v(dn),.dn_tag(dt),.busy(),.fault(sf),.fault_code(fc),
 .st_jobs(jobs),.st_cmds(cmds),.st_credit_stall(stalls));
 ot_s81_engine_adapter ad(.c_clk(clk),.c_rst_n(rst),.c_cmd_v(cv[2]),.c_cmd_d(cd[168+:84]),
 .c_done_v(adone),.c_done_tag(atag),.fault(af),.online(onl),.e_clk(clk),.e_rst_n(rst),
 .e_cmd_v(ev),.e_cmd_d(ed),.e_cmd_ready(1'b1),.e_inputs_present(1'b1),.e_done_v(edone),.e_done_tag(etag),
 .e_head_valid(hv),.e_head_d(hd),.e_head_accept(ha));
 integer n=0,loads=0,stores=0,errors=0,finished=0;reg pending=0;reg[7:0] ptag;
 always @(posedge clk)if(rst)begin
  if(ha)begin
   if(ed[83]!==1'(n/2)||ed[6:0]!==7'(n%2)||ed[82:73]!=19||ed[72:52]!=1048575||ed[51:31]!=27)errors=errors+1;
   if(ed[30:7]!==24'(((n%2)<<20)+(n%2?2048:0)+(n/2?640:0)))errors=errors+1;
   if(n%2)stores=stores+1;else loads=loads+1;
   n=n+1;pending=1;ptag={ed[83],ed[6:0]};
  end
  if(jdone)finished=finished+1;
 end
 always @(negedge clk)begin
  edone=pending;etag=ptag;pending=0;
 end
 initial begin
  repeat(6)@(negedge clk);rst=1;wait(onl);
  @(negedge clk);pw=1;pa=0;pd=28'h2800000;
  @(negedge clk);pa=1;pd=28'h2900800;
  @(negedge clk);pw=0;repeat(6)@(negedge clk);
  wait(jr);jv=1;@(negedge clk);jv=0;repeat(4)@(negedge clk);
  wait(jr);jv=1;@(negedge clk);jv=0;
  repeat(240)@(negedge clk);
  if(n!=4||loads!=2||stores!=2||finished!=2||af||sf)errors=errors+1;
  $display("TB_S81_NATIVE_SLOT_PROGRAM mut=%0d accepted_loads=%0d accepted_stores=%0d jobs_done=%0d errors=%0d faults=%b%b %s",MUT,loads,stores,finished,errors,af,sf,errors==0?"PASS":"FAIL");$finish;
 end
endmodule
