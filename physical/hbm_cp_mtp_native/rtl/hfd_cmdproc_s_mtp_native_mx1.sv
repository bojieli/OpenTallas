`timescale 1ns/1ps
`default_nettype none
// Fresh physical master. Original AR south source is instantiated unchanged.
// Native MTP full-list backend is independent of legacy single-token doorbell.
// Default-off until real providers, operation translator and physical context qualify.
//
// mtp-lead 2026-10-09 (MX1 r2, REGB): REGISTERED MTP BOUNDARY.  The first loop routes (6adb6c001) failed on the
// unregistered MTP side: post-CTS TT -656.8 ps on input->output paths (f_backend identity -> owned -> t_mtp[179],
// admit -> t_host[0], t_emit / t_provider pure feedthroughs) and input->reg -547.9 (f_backend[72] -> emit-queue
// storage) under the die IO budgets, and GRT-0183 twice on f_mtp[3] / f_mtp[8] (the f_mtp[0 +: 43] provider
// address feedthrough ran ~100 um along the dense bottom-edge pin row to t_provider).  REGB=1 puts every MTP-side
// pin behind a flop:
//   * valid/ready channels cross ot_sc_pfifo pin FIFOs (2 entries, in_ready / out_valid from flops):
//       job f_host[0] / t_host[0]; emit f_mtp[43] / t_mtp[139]; command in f_mtp[82] / t_mtp[82];
//       command out t_backend[0] / f_backend[0]; completion f_backend[1] / t_backend[270];
//       host records t_emit_host[0] / f_emit_host[0]; host done t_emit_host[74] / f_emit_host[1].
//   * level inputs (native done / status, CP-result AM, backend identity / quiescent / fault) get one pin flop;
//     native done is held behind the emit FIFO and host done behind the host-record FIFO (ordering kept).
//   * every other output is a flop at the pin; t_emit carries the ACCEPTED emit beat (one valid per token).
//   * the MTP side runs on a registered reset (2-flop, async assert); AR keeps the pin reset.
// Cost: +1 cycle on every crossing (+2 per round trip); the prompt / forced-token read loop (t_provider -> provider
// -> f_provider -> t_mtp) gains 2 cycles: the controller must wait PRL = 4 (hgi_mtp_native default).  REGB=0 is the
// original unregistered wiring (the 6adb6c001 cycle-exact bench runs it).  MUT (bench mutants, REGB=1 only):
//   1 native done not held behind the emit FIFO; 2 host done not held behind the host-record FIFO;
//   3 ARGMAX dispatch relay sends without the unit's ready (a record lost while the unit is busy).
//
// mtp-lead 2026-10-09 (r25gm die integration): HGI ARGMAX DISPATCH RELAY.  The R25G dispatch plan
// (tools/hgi_die_dispatch.py 'argmax', cp_band_alias -> this band) puts the CP -> ARGMAX unit record bus on this band's
// S face: t_hgi_argmax 683 = {n_O, n_A, desc_O, desc_A, header, valid} / f_hgi_argmax 3 = {fault, done, ready} (the
// unit ot_hgi_argmax_slot, instance hb_mtp_am).  The record's producer is the HGI sequencer (ot_hgi_seq: u_v / u_rdy /
// u_done / u_fault), which is not in this band: it arrives over the N cross-band pair x_hgi_argmax_rec 683 (in) /
// x_hgi_argmax_ret 3 (out) from the band that hosts the sequencer (decision hgi-takeover (5)).  REGB=0: wires.
// REGB=1 (r4, after f7d744101 post-CTS TT -460 / -402 on a single FIFO serving pins 700 um apart): three stages
// down the band, each crossing <= ~350 um of wire inside one register-to-register cycle --
//   T (top, by the x_* pins): ot_sc_pfifo, valid = rec[0]; the sequencer's ready = T's registered in_ready AND a
//     dedicated reset replica (fanout 1), so the ready pin is two flops and an AND gate;
//   M (mid band): ot_sc_pfifo wire stage;
//   B (bottom, by the t_/f_ pins): one record register; the unit's ready ret[0] lands in ONE pin flop (fanout 1);
//     a record is sent as a ONE-CYCLE valid pulse when that flopped ready is 1 and no record was sent in the two
//     previous cycles.  Exact for this unit: ot_hgi_argmax_record's ret[0] stays 1 until it accepts (it drops only
//     on accept, returns at retire) and MX1 is its only producer, so a ready seen one cycle late is still true
//     unless our own previous send consumed it -- which the two-cycle hold-off covers.
//   done / fault: three flops up the band (bottom, mid, top).
// Cost: record +3 cycles (T, M, B) +1 (flopped ready); retire +3.
// The job pin ready also carries a registered admission-open bit: no job is parked in the pin FIFO while admission
// is closed (the held native done lasts until the drained reset, which would discard it).
module hfd_cmdproc_s_mtp_native_mx1 #(parameter integer ENABLE_MTP=0, parameter integer REGB=1, parameter integer MUT=0)(
 inout wire [826:0] cSE,cSW,
 input wire [0:0] ck,rst,
 input wire [340:0] f_loader,input wire [63:0] f_router,
 output wire [63:0] t_su_SE,t_su_SW,
 input wire [15:0] xb,output wire [146:0] xl,output wire [15:0] xt,
 input wire [516:0] f_mtp,output wire [196:0] t_mtp,
 input wire [215:0] f_host,output wire [4:0] t_host,
 input wire [178:0] f_provider,
 output wire [37:0] t_emit,output wire [42:0] t_provider,
 input wire [1:0] f_emit_host,output wire [99:0] t_emit_host,
 output wire [0:0] t_abort,
 output wire [0:0] t_drained,
 input wire [17:0] f_am,
 input wire [72:0] f_backend,output wire [270:0] t_backend,
 input wire [682:0] x_hgi_argmax_rec,output wire [2:0] x_hgi_argmax_ret,
 output wire [682:0] t_hgi_argmax,input wire [2:0] f_hgi_argmax
);
 hfd_cmdproc_s ar(.cSE(cSE),.cSW(cSW),.ck(ck),.rst(rst),
  .f_loader(f_loader),.f_router(f_router),.t_su_SE(t_su_SE),.t_su_SW(t_su_SW),
  .xb(xb),.xl(xl),.xt(xt));
 generate if (REGB == 0) begin: g_direct
  assign t_hgi_argmax=x_hgi_argmax_rec;assign x_hgi_argmax_ret=f_hgi_argmax;
  hfd_cmdproc_s_mtp_native_mx1_mtp #(.ENABLE_MTP(ENABLE_MTP)) mtp(.ck(ck[0]),.rst(rst[0]),
   .f_mtp(f_mtp),.emit_pend(f_mtp[43]),.t_mtp(t_mtp),.f_host(f_host),.t_host(t_host),.f_provider(f_provider),
   .t_emit(t_emit),.t_provider(t_provider),.f_emit_host(f_emit_host),.t_emit_host(t_emit_host),
   .t_abort(t_abort),.t_drained(t_drained),.f_am(f_am),.f_backend(f_backend),.t_backend(t_backend));
 end else begin: g_regb
  wire c=ck[0];
  // registered reset for the MTP side (async assert, 2-flop deassert)
  reg [1:0] rs;
  always @(posedge c or posedge rst[0]) if (rst[0]) rs<=2'b11; else rs<={rs[0],1'b0};
  wire rm=rs[1];wire rn=~rm;
  // ---- core view of the pins
  wire [516:0] mi;wire [196:0] mo;wire [215:0] hi;wire [4:0] ho;wire [37:0] eo;wire [42:0] po;
  wire [1:0] ehi;wire [99:0] eho;wire ab,dr;wire [17:0] ami;wire [72:0] bi;wire [270:0] bo;
  // ---- level pin flops
  reg q81,q71,q72;reg [2:0] qst;reg qam;reg [16:0] qami;reg [67:0] qid;
  always @(posedge c or posedge rm) if (rm) begin q81<=0;q71<=0;q72<=0;qam<=0;end
   else begin q81<=f_mtp[81];q71<=f_backend[71];q72<=f_backend[72];qam<=f_am[0];end
  always @(posedge c) begin qst<=f_mtp[514+:3];qami<=f_am[1+:17];qid<=f_backend[2+:68];end
  // ---- input channels
  // job: the pin ready is the FIFO's AND a registered "admission open" (the core's admit, closed by a push or a
  // waiting job), so a job is never parked in the pin FIFO while admission is closed (held native done until the
  // drained reset, which would discard it): one job per admission window, as without the boundary
  wire jf_ir,jf_ov;wire [214:0] jf_od;reg open_q;
  wire jf_push=f_host[0]&&rn&&open_q&&jf_ir;
  always @(posedge c or posedge rm) if (rm) open_q<=1'b0; else open_q<=ho[0]&&!jf_push&&!jf_ov;
  ot_sc_pfifo #(.W(215),.S(2),.G(32)) jf(.clk(c),.rst_n(rn),.in_valid(f_host[0]&&rn&&open_q),.in_ready(jf_ir),.in_data(f_host[1+:215]),
   .out_valid(jf_ov),.out_ready(ho[0]),.out_data(jf_od));
  wire ef_ir,ef_ov;wire [36:0] ef_od;
  ot_sc_pfifo #(.W(37),.S(2),.G(37)) ef(.clk(c),.rst_n(rn),.in_valid(f_mtp[43]&&rn),.in_ready(ef_ir),.in_data(f_mtp[44+:37]),
   .out_valid(ef_ov),.out_ready(mo[139]),.out_data(ef_od));
  wire cf_ir,cf_ov;wire [200:0] cf_od;
  ot_sc_pfifo #(.W(201),.S(2),.G(32)) cf(.clk(c),.rst_n(rn),.in_valid(f_mtp[82]&&rn),.in_ready(cf_ir),.in_data(f_mtp[83+:201]),
   .out_valid(cf_ov),.out_ready(mo[82]),.out_data(cf_od));
  wire kf_ir,kf_ov;wire [68:0] kf_od;
  ot_sc_pfifo #(.W(69),.S(2),.G(35)) kf(.clk(c),.rst_n(rn),.in_valid(f_backend[1]&&rn),.in_ready(kf_ir),.in_data(f_backend[2+:69]),
   .out_valid(kf_ov),.out_ready(bo[270]),.out_data(kf_od));
  // ---- output channels
  wire bf_ir,bf_ov;wire [268:0] bf_od;
  ot_sc_pfifo #(.W(269),.S(2),.G(32)) bf(.clk(c),.rst_n(rn),.in_valid(bo[0]),.in_ready(bf_ir),.in_data(bo[1+:269]),
   .out_valid(bf_ov),.out_ready(f_backend[0]),.out_data(bf_od));
  wire hf_ir,hf_ov;wire [72:0] hf_od;
  ot_sc_pfifo #(.W(73),.S(2),.G(37)) hf(.clk(c),.rst_n(rn),.in_valid(eho[0]),.in_ready(hf_ir),.in_data(eho[1+:73]),
   .out_valid(hf_ov),.out_ready(f_emit_host[0]),.out_data(hf_od));
  wire hf_empty=(MUT==2)?1'b1:!hf_ov;
  wire df_ir,df_ov;wire [2:0] df_od;
  ot_sc_pfifo #(.W(3),.S(2),.G(3)) df(.clk(c),.rst_n(rn),.in_valid(eho[74]&&hf_empty),.in_ready(df_ir),.in_data(eho[75+:3]),
   .out_valid(df_ov),.out_ready(f_emit_host[1]),.out_data(df_od));
  // ---- core inputs
  assign mi[42:0]=43'b0;                                   // provider addresses leave through t_provider (below)
  assign mi[43]=ef_ov&&mo[139];                            // the queue pushes exactly the beats the FIFO pops
  assign mi[44+:37]=ef_od;
  assign mi[81]=q81&&((MUT==1)?1'b1:!ef_ov);               // native done stays behind the last emitted token
  assign mi[82]=cf_ov;assign mi[83+:201]=cf_od;
  assign mi[284+:230]=230'b0;assign mi[514+:3]=qst;
  assign hi={jf_od,jf_ov};
  assign ehi={df_ir&&hf_empty,hf_ir};
  assign ami={qami,qam};
  // completion identity: the FIFO head while a completion waits, else the backend identity lines (CP-result
  // AM ownership compares them during the in-flight command; flopped like the AM pulse, so aligned).  (ot_sc_pfifo's
  // empty head also tracks its input one cycle late; the explicit flops keep this independent of that detail.)
  wire [67:0] id=kf_ov?kf_od[67:0]:qid;
  assign bi={q72,q71&&!bf_ov&&!kf_ov,kf_od[68],id,kf_ov,bf_ir};
  hfd_cmdproc_s_mtp_native_mx1_mtp #(.ENABLE_MTP(ENABLE_MTP)) mtp(.ck(c),.rst(rm),
   .f_mtp(mi),.emit_pend(ef_ov),.t_mtp(mo),.f_host(hi),.t_host(ho),.f_provider(f_provider),
   .t_emit(eo),.t_provider(po),.f_emit_host(ehi),.t_emit_host(eho),
   .t_abort(ab),.t_drained(dr),.f_am(ami),.f_backend(bi),.t_backend(bo));
  // ---- registered outputs
  reg [196:0] tm_q;reg [4:1] th_q;reg [37:0] te_q;reg [42:0] tp_q;reg [24:0] teh_q;reg ab_q,dr_q;
  wire fifos_empty=!(jf_ov||ef_ov||cf_ov||kf_ov||bf_ov||hf_ov||df_ov);
  always @(posedge c or posedge rm) if (rm) begin tm_q<=0;th_q<=0;te_q<=0;tp_q<=0;teh_q<=0;ab_q<=0;dr_q<=0;end
   else begin
    tm_q<=mo;th_q<=ho[4:1];te_q<=ENABLE_MTP?{ef_od,ef_ov&&mo[139]}:38'b0;tp_q<=ENABLE_MTP?f_mtp[0+:43]:43'b0;
    teh_q<={eho[99],eho[78+:21],eho[75+:3]};ab_q<=ab;dr_q<=dr&&fifos_empty;
   end
  assign t_mtp={tm_q[196:140],ef_ir&&rn,tm_q[138:83],cf_ir&&rn,tm_q[81:0]};
  assign t_host={th_q,jf_ir&&rn&&open_q};
  assign t_emit=te_q;assign t_provider=tp_q;
  assign t_emit_host={teh_q[24],teh_q[23:3],teh_q[2:0],df_ov,hf_od,hf_ov};
  assign t_abort=ab_q;assign t_drained=dr_q;
  assign t_backend={kf_ir&&rn,bf_od,bf_ov};
  // ---- HGI ARGMAX dispatch relay (sequencer band -> ARGMAX unit), three stages (see header)
  wire rn_t;   // reset replica for the top ready pin (fanout 1)
  ot_sc_rep_ff #(.RV(1'b0)) u_rn_t(.clk(c),.rst_n(1'b1),.d(~rs[0]),.q(rn_t));
  wire at_ir,at_ov,am_ir,am_ov;wire [681:0] at_od,am_od;
  wire b_take;
  ot_sc_pfifo #(.W(682),.S(2),.G(32)) a_t(.clk(c),.rst_n(rn),.in_valid(x_hgi_argmax_rec[0]&&rn),.in_ready(at_ir),
   .in_data(x_hgi_argmax_rec[682:1]),.out_valid(at_ov),.out_ready(am_ir),.out_data(at_od));
  ot_sc_pfifo #(.W(682),.S(2),.G(32)) a_m(.clk(c),.rst_n(rn),.in_valid(at_ov),.in_ready(am_ir),
   .in_data(at_od),.out_valid(am_ov),.out_ready(b_take),.out_data(am_od));
  reg b_full,b_v,u_rdy_q;reg [1:0] b_hold;reg [681:0] b_d;
  assign b_take=!b_full;
  wire b_send=b_full&&!b_v&&(b_hold==2'd0)&&((MUT==3)?1'b1:u_rdy_q);
  always @(posedge c or posedge rm) if (rm) begin b_full<=0;b_v<=0;u_rdy_q<=0;b_hold<=0; end
   else begin
    u_rdy_q<=f_hgi_argmax[0];
    b_v<=b_send;
    b_hold<=b_send?2'd2:(b_hold==2'd0?2'd0:b_hold-2'd1);
    if (b_v) b_full<=1'b0; else if (am_ov&&b_take) b_full<=1'b1;
   end
  always @(posedge c) if (am_ov&&b_take) b_d<=am_od;
  reg [2:1] ar_b,ar_m,ar_t;
  always @(posedge c or posedge rm) if (rm) begin ar_b<=0;ar_m<=0;ar_t<=0; end
   else begin ar_b<=f_hgi_argmax[2:1];ar_m<=ar_b;ar_t<=ar_m; end
  assign t_hgi_argmax={b_d,b_v};
  assign x_hgi_argmax_ret={ar_t,at_ir&&rn_t};
 end endgenerate
endmodule

// The original MX1 MTP side (6adb6c001 hfd_cmdproc_s_mtp_native_mx1 minus the AR instance), unchanged except that
// the admission / drain tests read emit_pend (= f_mtp[43] when unregistered, the emit pin FIFO's head when REGB=1).
module hfd_cmdproc_s_mtp_native_mx1_mtp #(parameter integer ENABLE_MTP=0)(
 input wire ck,rst,
 input wire [516:0] f_mtp,input wire emit_pend,output wire [196:0] t_mtp,
 input wire [215:0] f_host,output wire [4:0] t_host,
 input wire [178:0] f_provider,
 output wire [37:0] t_emit,output wire [42:0] t_provider,
 input wire [1:0] f_emit_host,output wire [99:0] t_emit_host,
 output wire [0:0] t_abort,
 output wire [0:0] t_drained,
 input wire [17:0] f_am,
 input wire [72:0] f_backend,output wire [270:0] t_backend
);
 assign t_emit=ENABLE_MTP?f_mtp[43+:38]:38'b0;
 assign t_provider=ENABLE_MTP?f_mtp[0+:43]:43'b0;
 wire guard_rdy,queue_rdy,queue_ready,queue_fault,guard_fault;
 wire guard_drained,queue_drained;
 // f_backend[71] is actual backend drained_ready AND SM/service quiescence.
 // Native S_DONE holds done until the coordinated drained reset.
 wire [178:0] provider_owned={f_provider[178:140],queue_ready,f_provider[138:0]};
 wire admit=guard_rdy&&queue_rdy&&f_backend[0]&&f_backend[71]&&!emit_pend&&!f_mtp[81]&&!f_mtp[82];
 assign t_host[0]=admit&&!rst;
 assign t_drained[0]=guard_drained&&queue_drained&&f_backend[71]&&f_mtp[81]&&!emit_pend&&!f_mtp[82]&&!rst;
 assign t_host[4]=guard_fault||queue_fault;
 assign t_abort[0]=guard_fault||queue_fault;
 ot_hbm_native_mtp_emit_queue_mx1 #(.ENABLE(ENABLE_MTP),.DEPTH(8)) emit_queue(
  .clk(ck),.rst_n(~rst),.external_fault(f_backend[72]||guard_fault),
  .job_v(f_host[0]&&admit),.job_rdy(queue_rdy),.job_id(f_host[1+:32]),
  .job_generation(f_host[33+:4]),
  .emit(f_mtp[43+:38]),.native_done(f_mtp[81]),.native_status(f_mtp[514+:3]),
  .emit_ready(queue_ready),.host_v(t_emit_host[0]),.host_ready(f_emit_host[0]),
  .host_data(t_emit_host[1+:73]),.host_done_v(t_emit_host[74]),.host_done_ready(f_emit_host[1]),
  .host_status(t_emit_host[75+:3]),.accepted_count(t_emit_host[78+:21]),.drained_ready(queue_drained),.fault(queue_fault));
 assign t_emit_host[99]=queue_fault;
 ot_hbm_native_mtp_transaction_cp_join_mx1 #(.ENABLE(ENABLE_MTP),.SEQ_W(32)) mtp_owner(
  .clk(ck),.rst_n(~rst),.external_fault(f_backend[72]||queue_fault),.backend_quiescent(f_backend[71]),
  .job_v(f_host[0]&&admit),.job_rdy(guard_rdy),.job_id(f_host[1+:32]),
  .job_generation(f_host[33+:4]),.job_config(f_host[37+:179]),
  .provider_controls(provider_owned),.f_mtp(f_mtp),.t_mtp(t_mtp),
  .eng_cmd_v(t_backend[0]),.eng_cmd_rdy(f_backend[0]),.eng_cmd(t_backend[1+:201]),
  .eng_job(t_backend[202+:32]),.eng_generation(t_backend[234+:4]),
  .eng_sequence(t_backend[238+:32]),
  .cp_am_v(f_am[0]),.cp_am_idx(f_am[1+:17]),
  .eng_cpl_v(f_backend[1]),.eng_cpl_rdy(t_backend[270]),.eng_cpl_job(f_backend[2+:32]),
  .eng_cpl_generation(f_backend[34+:4]),.eng_cpl_sequence(f_backend[38+:32]),
  .eng_cpl_fault(f_backend[70]),
  .drained_ready(guard_drained),.active(t_host[1]),.inflight(t_host[2]),.identity_fault(t_host[3]),.fault(guard_fault));
endmodule
`default_nettype wire
