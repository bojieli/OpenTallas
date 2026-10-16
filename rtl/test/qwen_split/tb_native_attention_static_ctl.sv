`timescale 1ns/1ps
module tb_native_attention_static_ctl;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,issue=0,run=0,rx_event=0;
 reg [547:0] payload=0;wire busy,fault;wire [15:0] age;
 wire req,qv,txv;wire [4:0] qb;wire [511:0] qd;wire [547:0] txp;
 reg rv=0,done=0,slot=0;reg [4:0] beat=0,sbeat=0;reg [3:0] skind=0;
 qkd_native_attention_programme #(.MUT(MUT)) u(.ck(ck),.rst_n(rst_n),.issue(issue),.run(run),
  
  .fused_program_capability(mode!=3),.authority_valid(mode!=2),.authority_epoch(16'd17),
  .authority_token(18'd19),.authority_position(18'd999),.authority_stage(6'd7),
  .compiled_calendar(176'h123),.compiled_rx_cmd(16'd4),.compiled_tx_first(16'd100),.compiled_end(mode==5?16'd133:16'd134),
  .rx_event(rx_event),.rx_payload(payload),.tx_slot(slot),.tx_slot_kind(skind),.tx_slot_beat(sbeat),
  .tx_valid(txv),.tx_payload(txp),.request_valid(req),.request_ready(1'b1),.request_epoch(),.request_layer(),
  .request_position(),.request_calendar(),.q_valid(qv),.q_beat(qb),.q_data(qd),
  .result_valid(rv),.result_beat(beat),.result_data({507'd0,beat}),.result_epoch(mode==7?16'd18:16'd17),.result_layer(6'd6),
  .result_done(done),.service_fault(1'b0),.result_reserved(),.busy(busy),.fault(fault),.age(age));
 integer nq=0,nt=0,nr=0;integer mode=0;
 // Explicit external stimuli at the declared SERVICE face; this bench proves
 // controller timing and payload transport, never native arithmetic completeness.
 always @(negedge ck)begin
  rx_event=0;rv=0;done=0;slot=0;
  if(busy)begin
   if(age>=4&&age<=36)begin
    rx_event=!(mode==1&&age==36);
    payload={5'd0,(age==4?4'd1:4'd2),6'd6,16'd17,(age==4?5'd0:5'(age-5)),
      (age==4?512'd1999:512'(age-5))};
   end
   if(((age>=100&&age<132)||age==133))begin slot=1;skind=(mode==8&&age==108)?4'd4:age==133?4'd4:4'd3;sbeat=age==133?0:5'(age-100);end
   if(age>=100&&age<132)begin rv=!(mode==6&&age==108);beat=5'(age-100);end
   if(age==132)done=1;
  end
 end
 always @(posedge ck)begin
  if(req)nr=nr+1;
  if(qv)begin
   if(qb!=nq||qd!=512'(nq))$fatal(1,"Q corrupt");nq=nq+1;
  end
  if(txv)begin
   if(nt<32&&(txp[542:539]!=3||txp[511:0]!=512'(nt)))$fatal(1,"TX corrupt");
   if(nt==32&&(txp[542:539]!=4||txp[511:0]!=0))$fatal(1,"STATUS corrupt");nt=nt+1;
  end
 end
 initial begin
  if($value$plusargs("MODE=%d",mode))begin end
  repeat(3)@(negedge ck);rst_n=1;
  @(negedge ck);issue=1;@(negedge ck);issue=0;
  repeat(mode==4?0:4)@(negedge ck);run=1;@(negedge ck);run=0;
  repeat(145)@(negedge ck);
  if(mode!=0)begin if(!fault)$fatal(1,"missing producer or schedule mismatch went undetected");end
  else if(fault||nr!=1||nq!=32||nt!=33)$fatal(1,"fault=%b req=%0d Q=%0d TX=%0d",fault,nr,nq,nt);
  $display("PASS mode%0d fault%0b req%0d Q%0d TX%0d",mode,fault,nr,nq,nt);$finish;
 end
endmodule
