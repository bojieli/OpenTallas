`timescale 1ns/1ps
// KV-PLAN-FIN 2026-10-17: stream result face bench (copy of tb_qkd_attn_result_face.sv; DUT qkd_attn_result_face_s, F_DLY 1:
// RESULT_AGE = PV + max(P0, P1, R) + 16 + 1 (QXF-FACE 10-18, F3: R is in the max, as in the 16-kb face, the service root's
// END_AGE and the compiler; the pre-fix face used max(P0, P1) and this bench hid it with R = P1 + 1 and RESULT_AGE 88).
// R_P = 32 (R one above the pairs) and R_P = 600 (the die's STRETCH=1 regime: R far after the pairs); face MUT 4 (R left
// out) must fail MODE 0 at R_P = 600.  Stimulus = the qkd_pv_fin_s beat stream: beat b on service age RESULT_AGE + b.
// MODE 1 all beats one edge late, 2 wrong f_epoch, 3 a unit fault, 4 no beats, 5 a 33rd beat right after the run,
// 6 a wrong beat index, 7 one beat missing mid-run: each must end in programme fault.  Face MUT 1..3 must fail MODE 0.
// (original header follows)
// KVJ-SMALL (a) 2026-10-17: result face bench.  Actual consumer and actual context producer:
//   qkd_native_attention_programme (descriptor producer + guard + static ctl + record codec)  <- the RESULT face consumer
//   qkd_attn_service_root  (accepts the programme's request; q window; held ep / layer / cal; age)
//   qkd_attn_result_face   (DUT) behind RELAY registered relay edges
// The final join (ot_qwen_tp8_pv256_finalize_static_cal) is the declared stimulus: f_valid on its fixed capture slot
// (service age RESULT_AGE = PV_START + max(P0,P1,R) + 16) with a 16,384-bit vector.  compiled_tx_first is the compiler
// law  request edge + 1 + RESULT_AGE + 1 + RELAY.  PASS = no programme / root / face fault, 1 request, 32 Q beats,
// 33 TX records whose 32 RESULT payloads are the vector's 512-bit slices in order.
// MODE 1 f_valid one edge late, 2 wrong f_epoch, 3 a unit fault, 4 f_valid missing, 5 extra f_valid during emission:
// each must end in programme fault.  Face MUT 1..3 must fail MODE 0.
module tb_qkd_attn_result_face_s;
 parameter integer MUT=0,RELAY=0,R_P=32;
 localparam [15:0] PV=16'd40,P0=16'd30,P1=16'd31,R=16'(R_P);
 localparam integer LASTC=(R_P>31)?R_P:31;
 localparam integer RESULT_AGE=40+LASTC+16+1;          // + F_DLY 1
 localparam integer REQ_AGE=5;                       // programme age of request_valid (rx_cmd 4 + codec register)
 localparam integer TXF=REQ_AGE+1+RESULT_AGE+1+RELAY;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,issue=0,run=0,rx_event=0;integer mode=0;
 reg [547:0] payload=0;wire busy,fault;wire [15:0] age;
 wire req,qv,txv;wire [4:0] qb;wire [511:0] qd;wire [547:0] txp;
 reg slot=0;reg [4:0] sbeat=0;reg [3:0] skind=0;
 wire [15:0] rq_ep;wire [5:0] rq_layer;wire [17:0] rq_pos;wire [175:0] rq_cal;
 wire rv,rdone,sfault,rready;wire [4:0] rbeat;wire [511:0] rdata;wire [15:0] repoch;wire [5:0] rlayer;
 qkd_native_attention_programme u_prog(.ck(ck),.rst_n(rst_n),.issue(issue),.run(run),
  .fused_program_capability(1'b1),.authority_valid(1'b1),.authority_epoch(16'd17),
  .authority_token(18'd19),.authority_position(18'd999),.authority_stage(6'd7),
  .compiled_calendar({R,P1,P0,PV,112'd0}),.compiled_rx_cmd(16'd4),.compiled_tx_first(16'(TXF)),.compiled_end(16'(TXF+34)),
  .rx_event(rx_event),.rx_payload(payload),.tx_slot(slot),.tx_slot_kind(skind),.tx_slot_beat(sbeat),
  .tx_valid(txv),.tx_payload(txp),.request_valid(req),.request_ready(rready),.request_epoch(rq_ep),.request_layer(rq_layer),
  .request_position(rq_pos),.request_calendar(rq_cal),.q_valid(qv),.q_beat(qb),.q_data(qd),
  .result_valid(rv),.result_beat(rbeat),.result_data(rdata),.result_epoch(repoch),.result_layer(rlayer),
  .result_done(rdone),.service_fault(sfault),.result_reserved(),.busy(busy),.fault(fault),.age(age));
 wire running,start_qk,start_pv,lf,iof;wire [15:0] sage,sep;wire [5:0] slayer;wire [13:0] sctx;wire [175:0] scal;
 qkd_attn_service_root u_root(.ck(ck),.rst_n(rst_n),.request_valid(req),.request_ready(rready),.request_epoch(rq_ep),
  .request_layer(rq_layer),.request_position(rq_pos),.fused_program_capability(1'b1),.request_calendar(rq_cal),
  .q_valid(qv),.q_beat(qb),.q_ready(),.running(running),.start_qk(start_qk),.start_pv(start_pv),.age(sage),.ep(sep),
  .layer(slayer),.ctx(sctx),.cal(scal),.cycles(),.local_fault(lf),.io_fault(iof));
 reg m5=0;
 reg fv=0;reg [4:0] fb=0;reg [511:0] fd=0;reg [15:0] fe=0;reg [9:0] uf=0;
 wire face_fault;
 qkd_attn_result_face_s #(.NF(10),.RESULT_RELAY(RELAY),.F_DLY(1),.MUT(MUT)) u_face(.ck(ck),.rst_n(rst_n),.running(running),
  .start_qk(start_qk),.age(sage),.ep(sep),.layer(slayer),.cal(scal),.root_local_fault(lf),.root_io_fault(iof),
  .f_valid(fv),.f_beat(fb),.f_data(fd),.f_epoch(fe),.unit_fault(uf),
  .result_valid(rv),.result_beat(rbeat),.result_data(rdata),.result_epoch(repoch),.result_layer(rlayer),
  .result_done(rdone),.service_fault(sfault),.result_fault(face_fault));
 reg [16383:0] vec;integer i;
 initial for(i=0;i<512;i=i+1)vec[32*i+:32]=32'h9e3779b9*(i+1)^(i<<7);
 // link stimulus (as tb_native_attention_static_ctl) + final join stimulus + TX slots, all from fixed ages
 always @(negedge ck)begin
  rx_event=0;slot=0;fv=0;fb=5'hx;fd={512{1'bx}};fe=16'hx;
  if(busy)begin
   if(age>=4&&age<=36)begin
    rx_event=1;
    payload={5'd0,(age==4?4'd1:4'd2),6'd6,16'd17,(age==4?5'd0:5'(age-5)),(age==4?512'd1999:512'(age-5))};
   end
   if((age>=TXF&&age<TXF+32)||age==TXF+33)begin slot=1;skind=age==TXF+33?4'd4:4'd3;sbeat=age==TXF+33?0:5'(age-TXF);end
  end
  if(running&&!start_qk)begin
   if(mode!=4&&sage>=RESULT_AGE+(mode==1)&&sage<RESULT_AGE+(mode==1)+32&&!(mode==7&&sage==RESULT_AGE+13))begin
    fv=1;fb=5'(sage-RESULT_AGE-(mode==1))^((mode==6&&sage==RESULT_AGE+5)?5'd1:5'd0);fd=vec[512*fb+:512];
    fe=(mode==2&&sage==RESULT_AGE+3)?16'd18:sep;
   end
   if(mode==3&&sage==50)uf[6]=1;
  end
  // a 33rd beat on the edge after the run (age RESULT_AGE + 32 = END_AGE with F_DLY 1: the root has just stopped)
  if(mode==5&&!m5&&!start_qk&&sage==RESULT_AGE+32)begin fv=1;fb=0;fd=0;fe=sep;m5=1;end
 end
 integer nq=0,nt=0,nr=0;
 always @(posedge ck)begin
  if(req)nr=nr+1;
  if(qv)begin if(qb!=nq||qd!=512'(nq))$fatal(1,"Q corrupt");nq=nq+1;end
  if(txv)begin
   if(nt<32&&(txp[542:539]!=3||txp[511:0]!==vec[512*nt+:512]))$fatal(1,"TX %0d corrupt",nt);
   if(nt==32&&(txp[542:539]!=4||txp[511:0]!={507'd0,5'b01001}))$fatal(1,"STATUS corrupt (namespace {q_ready,done,fault,busy,ready} = 01001)");nt=nt+1;
  end
 end
 initial begin
  if($value$plusargs("MODE=%d",mode))begin end
  repeat(3)@(negedge ck);rst_n=1;
  repeat(85)@(negedge ck);            // service root boot count (80)
  issue=1;@(negedge ck);issue=0;
  repeat(4)@(negedge ck);run=1;@(negedge ck);run=0;
  repeat(TXF+60)@(negedge ck);
  if(mode!=0)begin if(!fault)$fatal(1,"MODE %0d went undetected",mode);end
  else if(fault||lf||iof||face_fault||nr!=1||nq!=32||nt!=33)
   $fatal(1,"fault=%b root=%b%b face=%b req=%0d Q=%0d TX=%0d",fault,lf,iof,face_fault,nr,nq,nt);
  $display("PASS R%0d MUT%0d RELAY%0d mode%0d fault%0b req%0d Q%0d TX%0d",R_P,MUT,RELAY,mode,fault,nr,nq,nt);$finish;
 end
endmodule
