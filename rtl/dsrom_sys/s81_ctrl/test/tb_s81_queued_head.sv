`timescale 1ns/1ps
// Actual adapter queue: latest submitted slot1 must not open the blocked slot0.
module tb_s81_queued_head #(parameter integer MUT=0);
 reg ck=0,ek=0,rs=0; always #0.4166 ck=~ck;always #0.5555 ek=~ek;
 reg cv=0;reg [83:0] cd=0;wire dv;wire [7:0] dt;wire fault,online;
 wire ev,hv,ha;wire [83:0] ed,hd;reg er=1,normal=0,done=0;reg [7:0] tag=0;
 // MUT1 recreates the circular precondition. MUT2 samples newest-issued input.
 wire ready_head=(MUT==1?ev:hv) && (MUT==2?cd[83]:hd[83]);
 wire go=normal||ready_head;
 ot_s81_engine_adapter a(.c_clk(ck),.c_rst_n(rs),.c_cmd_v(cv),.c_cmd_d(cd),
 .c_done_v(dv),.c_done_tag(dt),.fault(fault),.online(online),.e_clk(ek),.e_rst_n(rs),
 .e_cmd_v(ev),.e_cmd_d(ed),.e_cmd_ready(er),.e_inputs_present(go),.e_done_v(done),.e_done_tag(tag),
 .e_head_valid(hv),.e_head_d(hd),.e_head_accept(ha));
 function automatic [83:0] desc(input bit slot,input [6:0] op);
  desc={slot,10'd5,21'd12,21'd19,24'd0,op};
 endfunction
 integer errors=0,starts=0,returns=0,seenhead=0,cycles=0;reg [83:0] stalled_d=0;reg held=0;
 always @(posedge ek) if(rs) begin
  cycles=cycles+1;
  if(hv) seenhead=seenhead+1;
  if(ha !== (ev&&er)) errors=errors+1;
  if(ev&&er) begin
   if(ed!==desc(starts==1,7'(starts)))errors=errors+1;
   starts=starts+1;
  end
  if(held && (!hv || hd!==stalled_d))errors=errors+1;
  held=hv&&!ha;stalled_d=hd;
 end
 always @(posedge ck) if(rs && dv)returns=returns+1;
 task automatic issue(input bit slot,input [6:0] op);
  @(negedge ck);cv=1;cd=desc(slot,op);@(negedge ck);cv=0;
 endtask
 initial begin
  repeat(6)@(negedge ck);rs=1;wait(online);issue(0,0);issue(1,1);
  repeat(25)@(negedge ek);
  if(starts!=0||!hv||hd!==desc(0,0)||seenhead==0)errors=errors+1;
  normal=1;repeat(2)@(negedge ek);normal=0;
  repeat(30)@(negedge ek);
  if(starts!=2)errors=errors+1;
  @(negedge ek);done=1;tag=0;@(negedge ek);tag=8'h81;@(negedge ek);done=0;
  repeat(25)@(negedge ck);
  if(returns!=2||fault)errors=errors+1;
  $display("TB_S81_QUEUED_HEAD mut=%0d starts=%0d returns=%0d head_cycles=%0d errors=%0d fault=%0d %s",MUT,starts,returns,seenhead,errors,fault,errors==0?"PASS":"FAIL");$finish;
 end
endmodule
