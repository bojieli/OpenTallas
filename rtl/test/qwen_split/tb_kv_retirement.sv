`timescale 1ns/1ps
module tb_kv_retirement;
 parameter integer RET_MUT=0;
 localparam integer STATUS=(RET_MUT==1)?133:333;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,issue=0,run=0,rx_event=0;
 reg [547:0] payload=0;wire busy,fault;wire [15:0] age;
 wire req,qv,txv;wire [4:0] qb;wire [511:0] qd;wire [547:0] txp;
 reg rv=0,done=0,slot=0;reg [4:0] beat=0,sbeat=0;reg [3:0] skind=0;
 qkd_native_attention_programme #(.MUT(MUT),.LAND(1),.RETIRE_STATIC(1)) u(.ck(ck),.rst_n(rst_n),.issue(issue),.run(run),
  
  .fused_program_capability(1'b1),.authority_valid(1'b1),.authority_epoch(16'd17),
  .authority_token(18'd19),.authority_position(18'd999),.authority_stage(6'd7),
  .compiled_calendar(176'h123),.compiled_rx_cmd(16'd4),.compiled_tx_first(16'd100),.compiled_end(16'(STATUS+1)),
  .rx_event(rx_event),.rx_payload(payload),.tx_slot(slot),.tx_slot_kind(skind),.tx_slot_beat(sbeat),
  .tx_valid(txv),.tx_payload(txp),.request_valid(req),.request_ready(1'b1),.request_epoch(),.request_layer(),
  .request_position(),.request_calendar(),.q_valid(qv),.q_beat(qb),.q_data(qd),
  .result_valid(rv),.result_beat(beat),.result_data({507'd0,beat}),.result_epoch(mode==7?16'd18:16'd17),.result_layer(6'd6),
  .result_done(done),.service_fault(service_health),.result_reserved(),.busy(busy),.fault(fault),.age(age));
 integer nq=0,nt=0,nr=0;integer mode=0;integer source_index=0;
 wire [355:0] source_faults;
 reg work_seen;
 // Nominal functional check at131; absence becomes a fault at its fixed132
 // deadline. This checker continues independently of STATUS scheduling.
 always @(posedge ck or negedge rst_n)
   if(!rst_n)work_seen<=0;
   else if(busy&&age==131&&mode!=4)work_seen<=1;
 wire missing_check=busy&&age==132&&!work_seen;
 wire inject=((mode==1&&age==125)||(mode==2&&age==132)||missing_check||(mode==3&&!busy&&age==335));
 // Full source-pinned GEN4 candidate graph, including its abstract transport
 // cycles. Common-clock logical proof only; physical qualification stays OPEN.
 assign source_faults=(RET_MUT==2)?356'd0:(356'(inject)<<source_index);
 wire health;
 kv_retirement_collector collector(.ck(ck),.rst_n(rst_n),.src(source_faults),.health(health));
 wire [9:0] af;
 qkd_attn_fault_root afr(.ck(ck),.rst_n(rst_n),.d({7'd0,health}),.c(4'd0),.unit_fault(af));
 wire service_health=|af;
 reg [2:0] lv;reg [547:0] lp[0:2]; integer healthy_status=0;integer completed_before_retry=0;
 // Explicit three-edge link/consumer fixture after the real codec+TX landing.
 always @(posedge ck)begin
   lv<={lv[1:0],txv};lp[0]<=txp;lp[1]<=lp[0];lp[2]<=lp[1];
   if(rst_n&&lv[2]&&lp[2][542:539]==4)begin
     if(lp[2][511:0]==512'd9)healthy_status=healthy_status+1;
     if(mode==1||mode==2||mode==4)$fatal(1,"healthy STATUS escaped functional fault path");
   end
 end
 // Explicit external stimuli at the declared SERVICE face; this bench proves
 // controller timing and payload transport, never native arithmetic completeness.
 always @(negedge ck)begin
  rx_event=0;rv=0;done=0;slot=0;
  if(busy)begin
   if(age>=4&&age<=36)begin
    rx_event=1;
    payload={5'd0,(age==4?4'd1:4'd2),6'd6,16'd17,(age==4?5'd0:5'(age-5)),
      (age==4?512'd1999:512'(age-5))};
   end
   if(((age>=100&&age<132)||age==STATUS))begin slot=1;skind=(mode==8&&age==108)?4'd4:age==STATUS?4'd4:4'd3;sbeat=age==STATUS?0:5'(age-100);end
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
   if(nt==32&&(txp[542:539]!=4||txp[511:0]!={507'd0,5'b01001}))$fatal(1,"STATUS corrupt (namespace {q_ready,done,fault,busy,ready} = 01001)");nt=nt+1;
  end
 end
 initial begin
  if($value$plusargs("MODE=%d",mode))begin end
  if($value$plusargs("SOURCE=%d",source_index))begin end
  if(source_index<0||source_index>=356)$fatal(1,"source outside candidate inventory");
  repeat(3)@(negedge ck);rst_n=1;
  @(negedge ck);issue=1;@(negedge ck);issue=0;
  repeat(4)@(negedge ck);run=1;@(negedge ck);run=0;
  repeat(550)@(negedge ck);
  if(mode!=0)begin
    if(!fault||!service_health)$fatal(1,"fault path lost early/cutoff/late/missing detection");
    if(mode==3&&healthy_status!=1)$fatal(1,"late continuous health changed earlier completed STATUS");
    // Health remains live after busy deasserts; a subsequent run is refused.
    completed_before_retry=healthy_status;
    issue=1;@(negedge ck);issue=0;repeat(4)@(negedge ck);
    run=1;@(negedge ck);run=0;repeat(400)@(negedge ck);
    if(healthy_status!=completed_before_retry)$fatal(1,"late health permitted subsequent healthy completion");
    if(!fault||!service_health)$fatal(1,"late health failed subsequent admission/completion guard");
   end
  else if(fault||nr!=1||nq!=32||nt!=33)$fatal(1,"fault=%b req=%0d Q=%0d TX=%0d",fault,nr,nq,nt);
  $display("PASS retirement fixture mode%0d fault%0b req%0d Q%0d TX%0d",mode,fault,nr,nq,nt);$finish;
 end
endmodule
