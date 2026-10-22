`timescale 1ns/1ps
// KV-RETIRE 10-19: whole-path retirement bench on the COMPILED die ages (kv_retirement_contract.py, die profile):
// RX_CMD 2, TX_FIRST 1752, functional cutoff 1785, contract STATUS age +STATUS (compiled_end = STATUS + 1).
// Real qkd_native_attention_programme (LAND=1, RETIRE_STATIC=1: STATUS at compiled_end-1) + real qkd_attn_fault_root.
// A fault source raised at age +INJ (sticky, as every plane source / collector join) reaches the AFR after +D edges
// (D = the contract's source_to_collector + ufh edges of that source); STATUS then crosses the explicit suffix fixture
// (TX landing 1 + link 11 + consumer 1 = the contract's suffix edges) to the compute consumer.
// +MODE: 0 healthy (one healthy STATUS); 1 inject at +INJ (no healthy STATUS may reach the consumer); 2 late (inject
// after STATUS: the earlier healthy STATUS stands, health stays sticky and a subsequent op cannot complete healthy);
// 3 missing done; 4 missing RESULT beat 31; 5 missing RX Q beat 31.
// +EXPECT_ESCAPE=1 (negative control): the run must observe a healthy STATUS despite the fault (STATUS compiled too
// early), printing RETIRE_ESCAPE_WITNESS; otherwise exits fatal.
module tb_kv_retire_wholepath;
 localparam integer SUFFIX=13;
 reg ck=0;always #5 ck=~ck;
 integer mode=0,inj=0,dly=1,status=1982,txf=1752,rxc=2,expect_escape=0;
 integer healthy_status=0,any_status=0,ops=0;
 reg rst_n=0,issue=0,run=0,rx_event=0;
 reg [547:0] payload=0;wire busy,fault;wire [15:0] age;
 wire req,qv,txv;wire [4:0] qb;wire [511:0] qd;wire [547:0] txp;
 reg rv=0,done=0,slot=0;reg [4:0] beat=0,sbeat=0;reg [3:0] skind=0;
 reg [15:0] c_rx=0,c_txf=0,c_end=0;
 wire service_health;
 qkd_native_attention_programme #(.LAND(1),.RETIRE_STATIC(1)) u(.ck(ck),.rst_n(rst_n),.issue(issue),.run(run),
  .fused_program_capability(1'b1),.authority_valid(1'b1),.authority_epoch(16'd17),
  .authority_token(18'd19),.authority_position(18'd999),.authority_stage(6'd7),
  .compiled_calendar(176'h123),.compiled_rx_cmd(c_rx),.compiled_tx_first(c_txf),.compiled_end(c_end),
  .rx_event(rx_event),.rx_payload(payload),.tx_slot(slot),.tx_slot_kind(skind),.tx_slot_beat(sbeat),
  .tx_valid(txv),.tx_payload(txp),.request_valid(req),.request_ready(1'b1),.request_epoch(),.request_layer(),
  .request_position(),.request_calendar(),.q_valid(qv),.q_beat(qb),.q_data(qd),
  .result_valid(rv),.result_beat(beat),.result_data({507'd0,beat}),.result_epoch(16'd17),.result_layer(6'd6),
  .result_done(done),.service_fault(service_health),.result_reserved(),.busy(busy),.fault(fault),.age(age),.prg_l());
 // source: sticky from its injection edge (plane sources and every collector join are sticky)
 reg src=0;reg [255:0] dl=0;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin src<=0;dl<=0;end
  else begin
   if(((mode==1)&&busy&&age==inj)||((mode==2)&&busy&&ops==1&&age==16'(status+1)))src<=1;
   dl<={dl[254:0],src};
  end
 wire path_out=dl[dly-1];
 wire [9:0] af;
 qkd_attn_fault_root afr(.ck(ck),.rst_n(rst_n),.d({7'd0,path_out}),.c(4'd0),.unit_fault(af));
 assign service_health=|af;
 // explicit suffix fixture: TX landing + link + consumer
 reg [SUFFIX-1:0] lv=0;reg [547:0] lp[0:SUFFIX-1];integer k;
 always @(posedge ck)begin
  lv<={lv[SUFFIX-2:0],txv};lp[0]<=txp;for(k=1;k<SUFFIX;k=k+1)lp[k]<=lp[k-1];
  if(rst_n&&lv[SUFFIX-1]&&lp[SUFFIX-1][542:539]==4)begin
   any_status=any_status+1;
   if(lp[SUFFIX-1][511:0]==512'd9)healthy_status=healthy_status+1;
  end
 end
 // the die's static stimulus at the SERVICE / link faces on the compiled ages
 always @(negedge ck)begin
  rx_event=0;rv=0;done=0;slot=0;
  if(busy)begin
   if(age>=rxc&&age<=rxc+32&&!(mode==5&&age==rxc+32))begin
    rx_event=1;
    payload={5'd0,(age==rxc?4'd1:4'd2),6'd6,16'd17,(age==rxc?5'd0:5'(age-rxc-1)),
      (age==rxc?512'd1999:512'(age-rxc-1))};
   end
   if((age>=txf&&age<txf+32)||age==status)begin slot=1;skind=(age==status)?4'd4:4'd3;sbeat=(age==status)?5'd0:5'(age-txf);end
   if(age>=txf&&age<txf+32)begin rv=!(mode==4&&age==txf+31);beat=5'(age-txf);end
   if(age==txf+32&&mode!=3)done=1;
  end
 end
 task op;begin
  @(negedge ck);issue=1;@(negedge ck);issue=0;repeat(4)@(negedge ck);run=1;@(negedge ck);run=0;ops=ops+1;
  repeat(status+SUFFIX+40)@(negedge ck);
 end endtask
 integer first;
 initial begin
  if($value$plusargs("MODE=%d",mode))begin end
  if($value$plusargs("INJ=%d",inj))begin end
  if($value$plusargs("D=%d",dly))begin end
  if($value$plusargs("STATUS=%d",status))begin end
  if($value$plusargs("TXF=%d",txf))begin end
  if($value$plusargs("RX=%d",rxc))begin end
  if($value$plusargs("EXPECT_ESCAPE=%d",expect_escape))begin end
  if(dly<1||dly>256||status<txf+33||status>65533)$fatal(1,"bad plusargs D=%0d STATUS=%0d",dly,status);
  c_rx=16'(rxc);c_txf=16'(txf);c_end=16'(status+1);
  repeat(3)@(negedge ck);rst_n=1;
  op();
  first=healthy_status;
  if(expect_escape)begin
   if(mode==1&&first!=0)$display("RETIRE_ESCAPE_WITNESS healthy STATUS escaped functional fault path INJ=%0d D=%0d STATUS=%0d",inj,dly,status);
   else $fatal(1,"negative control did not escape INJ=%0d D=%0d STATUS=%0d",inj,dly,status);
  end else begin
   case(mode)
    0:if(fault||first!=1||any_status!=1)$fatal(1,"healthy op: fault=%b healthy=%0d status=%0d",fault,first,any_status);
    2:begin
      if(first!=1)$fatal(1,"late health changed the earlier completed STATUS (%0d)",first);
      repeat(dly+10)@(negedge ck);
      if(!fault)$fatal(1,"late health not live after STATUS");
      op();
      if(healthy_status!=first)$fatal(1,"late health permitted subsequent healthy completion");
     end
    default:if(first!=0||!fault)$fatal(1,"healthy STATUS escaped functional fault path mode=%0d INJ=%0d D=%0d STATUS=%0d fault=%b",mode,inj,dly,status,fault);
   endcase
   if(mode!=0&&!fault)$fatal(1,"continuous health lost");
   $display("RETIRE_WHOLEPATH_PASS mode=%0d INJ=%0d D=%0d STATUS=%0d healthy=%0d statuses=%0d fault=%b",mode,inj,dly,status,healthy_status,any_status,fault);
  end
  $finish;
 end
endmodule
