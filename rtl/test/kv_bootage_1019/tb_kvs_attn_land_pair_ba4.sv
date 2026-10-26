`timescale 1ns/1ps
// KV-ATTNKIT 10-18: PAIR LOCKSTEP of the registered kvs_attn boundary (die knob OT_KV_ATTN_LAND) against the as-built one.
//   A = qkd_native_attention_programme LAND 0 + qkd_attn_service_root CAL_PIPE 0 + qkd_attn_result_face_s CAL_PIPE 0
//   B = the same three with LAND 1 / CAL_PIPE 1 (programme MUT BMUT, face MUT FMUT)
// driven by ONE stimulus (tb_qkd_attn_result_face_s: link CMD + 32 Q beats on their compiled ages, the final-join beat
// stream on RESULT_AGE.., the TX slots; the stimulus follows A).  Every edge (pre-edge sample) B must equal A:
//   same edge : programme fault, request_valid (+ epoch / layer / position / calendar when valid), q_valid (+ beat / data),
//               root running / start_qk / start_pv / age / ep / layer / ctx / cal / local_fault / io_fault,
//               face result_valid (+ beat / data / epoch / layer) / result_done / service_fault / result_fault
//   one edge later (the launch flops, priced +1): tx_valid (+ payload), prg_l {request_valid, q_valid (+ fields)},
//               face hdr_l vs the generated tile's arh = {fin[0], 2'b00, fin[5:1]} = {f_valid, 2'b00, f_beat}
// MODE 0 legal (A must finish fault-free: 1 request, 32 Q, 33 TX), 1..7 the face bench's result-stream faults (5 = a stray
// beat one edge before the window: with R in RESULT_AGE the window ends on the root's last running age), and the
// RX / TX record faults the landing moves: 8 CMD data bit 300 set, 9 Q beat 6 wrong epoch, 10 Q beat 9 missing,
// 11 an extra RX record after the Q run, 12 TX slot 3 wrong kind, 13 a unit fault during the RESULT run, 14 Q beat 4
// wrong kind (STATUS on the RX face), 15 an out-of-range authority token (descriptor producer fault).  Modes 1..14 must fault A (else the stimulus did not reach the case).
// One line: KVS_LANDPAIR PASS|FAIL mode=M bmut=B fmut=F checks=N ...
module tb_kvs_attn_land_pair_ba4;
 parameter integer BMUT=0,FMUT=0;
 localparam [15:0] PV=16'd40,P0=16'd30,P1=16'd31,R=16'd32;
 localparam integer RESULT_AGE=40+32+16+1;             // face RESULT_AGE = PV + max(P0, P1, R) + 16 + F_DLY (QXF-FACE law)
 localparam integer REQ_AGE=5;
 localparam integer TXF=REQ_AGE+1+RESULT_AGE+1;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,issue=0,run=0,rx_event=0;integer mode=0,user_id=0;reg [17:0] tok=18'd19;
 reg [547:0] payload=0;
 reg slot=0;reg [4:0] sbeat=0;reg [3:0] skind=0;
 reg fv=0;reg [4:0] fb=0;reg [511:0] fd=0;reg [15:0] fe=0;reg [9:0] uf=0;
 // ---------------- chain A (as built) ----------------
 wire busy_a,fault_a;wire [15:0] age_a;
 wire req_a,qv_a,txv_a;wire [4:0] qb_a;wire [511:0] qd_a;wire [547:0] txp_a;wire [536:0] prg_a;
 wire [15:0] rq_ep_a;wire [5:0] rq_layer_a;wire [17:0] rq_pos_a;wire [175:0] rq_cal_a;
 wire rv_a,rdone_a,sfault_a,rready_a;wire [4:0] rbeat_a;wire [511:0] rdata_a;wire [15:0] repoch_a;wire [5:0] rlayer_a;
 qkd_native_attention_programme #(.MUT(0),.LAND(0)) u_prog_a(.ck(ck),.rst_n(rst_n),.issue(issue),.run(run),
  .fused_program_capability(1'b1),.authority_valid(1'b1),.authority_epoch(16'(17+user_id)),
  .authority_token(tok),.authority_position(18'd999),.authority_stage(6'd7),
  .compiled_calendar({R,P1,P0,PV,112'd0}),.compiled_rx_cmd(16'd4),.compiled_tx_first(16'(TXF)),.compiled_end(16'(TXF+34)),
  .rx_event(rx_event),.rx_payload(payload),.tx_slot(slot),.tx_slot_kind(skind),.tx_slot_beat(sbeat),
  .tx_valid(txv_a),.tx_payload(txp_a),.request_valid(req_a),.request_ready(rready_a),.request_epoch(rq_ep_a),
  .request_layer(rq_layer_a),.request_position(rq_pos_a),.request_calendar(rq_cal_a),.q_valid(qv_a),.q_beat(qb_a),
  .q_data(qd_a),.result_valid(rv_a),.result_beat(rbeat_a),.result_data(rdata_a),.result_epoch(repoch_a),
  .result_layer(rlayer_a),.result_done(rdone_a),.service_fault(sfault_a),.result_reserved(),.busy(busy_a),
  .fault(fault_a),.age(age_a),.prg_l(prg_a));
 wire running_a,start_qk_a,start_pv_a,lf_a,iof_a;wire [15:0] sage_a,sep_a;wire [5:0] slayer_a;wire [13:0] sctx_a;
 wire [175:0] scal_a;
 qkd_attn_service_root #(.PV_LEAD(0),.CAL_PIPE(0),.MUT(0)) u_root_a(.ck(ck),.rst_n(rst_n),.request_valid(req_a),
  .request_ready(rready_a),.request_epoch(rq_ep_a),.request_layer(rq_layer_a),.request_position(rq_pos_a),
  .fused_program_capability(1'b1),.request_calendar(rq_cal_a),.q_valid(qv_a),.q_beat(qb_a),.q_ready(),
  .running(running_a),.start_qk(start_qk_a),.start_pv(start_pv_a),.age(sage_a),.ep(sep_a),.layer(slayer_a),
  .ctx(sctx_a),.cal(scal_a),.cycles(),.local_fault(lf_a),.io_fault(iof_a));
 wire face_fault_a;wire [7:0] hdr_a;
 qkd_attn_result_face_s #(.NF(10),.RESULT_RELAY(0),.F_DLY(1),.CAL_PIPE(0),.MUT(0)) u_face_a(.ck(ck),.rst_n(rst_n),
  .running(running_a),.start_qk(start_qk_a),.age(sage_a),.ep(sep_a),.layer(slayer_a),.cal(scal_a),
  .root_local_fault(lf_a),.root_io_fault(iof_a),.f_valid(fv),.f_beat(fb),.f_data(fd),.f_epoch(fe),.unit_fault(uf),
  .result_valid(rv_a),.result_beat(rbeat_a),.result_data(rdata_a),.result_epoch(repoch_a),.result_layer(rlayer_a),
  .result_done(rdone_a),.service_fault(sfault_a),.result_fault(face_fault_a),.hdr_l(hdr_a));
 // ---------------- chain B (registered boundary) ----------------
 wire busy_b,fault_b;wire [15:0] age_b;
 wire req_b,qv_b,txv_b;wire [4:0] qb_b;wire [511:0] qd_b;wire [547:0] txp_b;wire [536:0] prg_b;
 wire [15:0] rq_ep_b;wire [5:0] rq_layer_b;wire [17:0] rq_pos_b;wire [175:0] rq_cal_b;
 wire rv_b,rdone_b,sfault_b,rready_b;wire [4:0] rbeat_b;wire [511:0] rdata_b;wire [15:0] repoch_b;wire [5:0] rlayer_b;
 qkd_native_attention_programme_ba4 #(.MUT(BMUT),.LAND(1)) u_prog_b(.ck(ck),.rst_n(rst_n),.issue(issue),.run(run),
  .fused_program_capability(1'b1),.authority_valid(1'b1),.authority_epoch(16'(17+user_id)),
  .authority_token(tok),.authority_position(18'd999),.authority_stage(6'd7),
  .compiled_calendar({R,P1,P0,PV,112'd0}),.compiled_rx_cmd(16'd4),.compiled_tx_first(16'(TXF)),.compiled_end(16'(TXF+34)),
  .rx_event(rx_event),.rx_payload(payload),.tx_slot(slot),.tx_slot_kind(skind),.tx_slot_beat(sbeat),
  .tx_valid(txv_b),.tx_payload(txp_b),.request_valid(req_b),.request_ready(rready_b),.request_epoch(rq_ep_b),
  .request_layer(rq_layer_b),.request_position(rq_pos_b),.request_calendar(rq_cal_b),.q_valid(qv_b),.q_beat(qb_b),
  .q_data(qd_b),.result_valid(rv_b),.result_beat(rbeat_b),.result_data(rdata_b),.result_epoch(repoch_b),
  .result_layer(rlayer_b),.result_done(rdone_b),.service_fault(sfault_b),.result_reserved(),.busy(busy_b),
  .fault(fault_b),.age(age_b),.prg_l(prg_b));
 wire running_b,start_qk_b,start_pv_b,lf_b,iof_b;wire [15:0] sage_b,sep_b;wire [5:0] slayer_b;wire [13:0] sctx_b;
 wire [175:0] scal_b;
 qkd_attn_service_root #(.PV_LEAD(0),.CAL_PIPE(1),.MUT(0)) u_root_b(.ck(ck),.rst_n(rst_n),.request_valid(req_b),
  .request_ready(rready_b),.request_epoch(rq_ep_b),.request_layer(rq_layer_b),.request_position(rq_pos_b),
  .fused_program_capability(1'b1),.request_calendar(rq_cal_b),.q_valid(qv_b),.q_beat(qb_b),.q_ready(),
  .running(running_b),.start_qk(start_qk_b),.start_pv(start_pv_b),.age(sage_b),.ep(sep_b),.layer(slayer_b),
  .ctx(sctx_b),.cal(scal_b),.cycles(),.local_fault(lf_b),.io_fault(iof_b));
 wire face_fault_b;wire [7:0] hdr_b;
 qkd_attn_result_face_s #(.NF(10),.RESULT_RELAY(0),.F_DLY(1),.CAL_PIPE(1),.MUT(FMUT)) u_face_b(.ck(ck),.rst_n(rst_n),
  .running(running_b),.start_qk(start_qk_b),.age(sage_b),.ep(sep_b),.layer(slayer_b),.cal(scal_b),
  .root_local_fault(lf_b),.root_io_fault(iof_b),.f_valid(fv),.f_beat(fb),.f_data(fd),.f_epoch(fe),.unit_fault(uf),
  .result_valid(rv_b),.result_beat(rbeat_b),.result_data(rdata_b),.result_epoch(repoch_b),.result_layer(rlayer_b),
  .result_done(rdone_b),.service_fault(sfault_b),.result_fault(face_fault_b),.hdr_l(hdr_b));
 // ---------------- stimulus (tb_qkd_attn_result_face_s, follows A) ----------------
 reg [16383:0] vec;integer i;
 initial begin
 if($value$plusargs("USER=%d",user_id))begin end
 for(i=0;i<512;i=i+1)vec[32*i+:32]=32'h9e3779b9*(i+1)^(i<<7)^(32'h6c078965*user_id);
 end
 always @(negedge ck)begin
  rx_event=0;slot=0;fv=0;fb=5'h0;fd=512'd0;fe=16'h0;
  if(busy_a)begin
   if(age_a>=4&&age_a<=36&&!(mode==10&&age_a==4+1+9))begin
    rx_event=1;
    payload={5'd0,(age_a==4?4'd1:4'd2),6'd6,16'(17+user_id),(age_a==4?5'd0:5'(age_a-5)),(age_a==4?512'd1999:512'(age_a-5))};
    if(mode==8&&age_a==4)payload[300]=1'b1;
    if(mode==9&&age_a==4+1+6)payload[532:517]=16'(18+user_id);
    if(mode==14&&age_a==4+1+4)payload[542:539]=4'd4;
   end
   if(mode==11&&age_a==40)begin rx_event=1;payload={5'd0,4'd2,6'd6,16'(17+user_id),5'd0,512'd0};end
   if((age_a>=TXF&&age_a<TXF+32)||age_a==TXF+33)begin
    slot=1;skind=age_a==TXF+33?4'd4:4'd3;sbeat=age_a==TXF+33?0:5'(age_a-TXF);
    if(mode==12&&age_a==TXF+3)skind=4'd4;
   end
  end
  if(running_a&&!start_qk_a)begin
   if(mode!=4&&sage_a>=RESULT_AGE+(mode==1)&&sage_a<RESULT_AGE+(mode==1)+32&&!(mode==7&&sage_a==RESULT_AGE+13))begin
    fv=1;fb=5'(sage_a-RESULT_AGE-(mode==1))^((mode==6&&sage_a==RESULT_AGE+5)?5'd1:5'd0);fd=vec[512*fb+:512];
    fe=(mode==2&&sage_a==RESULT_AGE+3)?16'(18+user_id):sep_a;
   end
   if(mode==5&&sage_a==RESULT_AGE-1)begin fv=1;fb=0;fd=0;fe=sep_a;end   // a stray beat (the window ends with running)
   if(mode==3&&sage_a==50)uf[6]=1;
   if(mode==13&&sage_a==RESULT_AGE+8)uf[2]=1;
  end
 end
 // ---------------- lockstep (pre-edge sample) ----------------
 integer checks=0,errors=0,nq=0,nt=0,nr=0,cyc=0;
 reg p_txv=0;reg [547:0] p_txp=0;reg p_rv=0,p_qv=0;reg [536:0] p_prg=0;reg p_fv=0;reg [4:0] p_fb=0;
 task automatic chk(input ok,input [8*24-1:0] what);
  begin checks=checks+1;if(!ok)begin errors=errors+1;if(errors<=8)$display("MISMATCH cyc=%0d %0s",cyc,what);end end
 endtask
 always @(posedge ck)if(rst_n)begin
  cyc=cyc+1;
  chk(fault_b===fault_a,"fault");
  chk(req_b===req_a,"request_valid");
  if(req_a)chk({rq_ep_b,rq_layer_b,rq_pos_b,rq_cal_b}==={rq_ep_a,rq_layer_a,rq_pos_a,rq_cal_a},"request fields");
  chk(qv_b===qv_a,"q_valid");
  if(qv_a)chk({qb_b,qd_b}==={qb_a,qd_a},"q fields");
  chk({running_b,start_qk_b,start_pv_b,sage_b,sep_b,slayer_b,sctx_b,scal_b,lf_b,iof_b}===
      {running_a,start_qk_a,start_pv_a,sage_a,sep_a,slayer_a,sctx_a,scal_a,lf_a,iof_a},"root");
  chk({rv_b,rdone_b,sfault_b,face_fault_b}==={rv_a,rdone_a,sfault_a,face_fault_a},"face flags");
  if(rv_a)chk({rbeat_b,rdata_b,repoch_b,rlayer_b}==={rbeat_a,rdata_a,repoch_a,rlayer_a},"face fields");
  // launched words: B now == A one edge ago
  chk(txv_b===p_txv,"tx_valid +1");
  if(p_txv)chk(txp_b===p_txp,"tx_payload +1");
  chk(prg_b[0]===p_rv&&prg_b[19]===p_qv,"prg valids +1");
  if(p_rv)chk(prg_b[18:1]===p_prg[18:1],"prg position +1");
  if(p_qv)chk(prg_b[536:20]===p_prg[536:20],"prg q +1");
  chk(hdr_b[7]===p_fv&&hdr_b[6:5]===2'b00,"arh valid +1");
  if(p_fv)chk(hdr_b[4:0]===p_fb,"arh beat +1");
  // A's own record (as tb_qkd_attn_result_face_s)
  if(req_a)nr=nr+1;
  if(qv_a)begin if(qb_a!=nq||qd_a!=512'(nq))begin errors=errors+1;$display("MISMATCH reference Q corrupt");end nq=nq+1;end
  if(txv_a)begin
   if(nt<32&&(txp_a[542:539]!=3||txp_a[511:0]!==vec[512*nt+:512]))begin errors=errors+1;$display("MISMATCH reference TX");end
   nt=nt+1;
  end
  p_txv=txv_a;p_txp=txp_a;p_rv=prg_a[0];p_qv=prg_a[19];p_prg=prg_a;p_fv=fv;p_fb=fb;
 end
 initial begin
  if($value$plusargs("MODE=%d",mode))begin end
  tok=18'(19+user_id*101);
  if(mode==15)tok=18'd200000;          // authority token out of range: producer fault, no load
  repeat(3)@(negedge ck);rst_n=1;
  repeat(85)@(negedge ck);
  issue=1;@(negedge ck);issue=0;
  repeat(4)@(negedge ck);run=1;@(negedge ck);run=0;
  repeat(TXF+60)@(negedge ck);
  if(mode==0&&(fault_a||lf_a||iof_a||face_fault_a||nr!=1||nq!=32||nt!=33))begin
   errors=errors+1;$display("MISMATCH reference not legal: fault=%b root=%b%b face=%b req=%0d Q=%0d TX=%0d",fault_a,lf_a,iof_a,
    face_fault_a,nr,nq,nt);
  end
  if(mode!=0&&!fault_a)begin errors=errors+1;$display("MISMATCH reference mode %0d went undetected",mode);end
  $display("KVS_LANDPAIR %s mode=%0d bmut=%0d fmut=%0d checks=%0d errors=%0d fault=%0b req=%0d Q=%0d TX=%0d",
   errors==0?"PASS":"FAIL",mode,BMUT,FMUT,checks,errors,fault_a,nr,nq,nt);
  $finish;
 end
endmodule
