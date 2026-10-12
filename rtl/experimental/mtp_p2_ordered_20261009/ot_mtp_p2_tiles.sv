`timescale 1ns/1ps
`default_nettype none
// el1011-ds-mtp [p2pfx] 2026-10-11: ot_mtp_p2_prefix_path as FOUR hard tiles assembled by the die (owner TWO-LEVEL
// HIERARCHY: no intermediate parent route).  The flat streaming route put 36.7k flops + 12 SRAMs under one clock root
// (latency 418-515 ps, SRAM-clock vs capture skew -123 ps; CTS hold repair stuck).  Each tile has its own clock tree
// and reset synchroniser; every seam is registered on both sides (sender flop / pfifo out, receiver pin flop or PINREG
// pfifo with a registered in_ready); IO budget 0.2 T each side.
//   ot_p2h_xport      ordered transport: 2 lane PINREG pin FIFOs + ot_mtp_p2_ordered_rows (9 SRAMs) + output pfifo
//   ot_p2h_arith      A-prefix core: PINREG xfer FIFO + ot_mtp_p2_prefix EXT_ADD (3 SRAMs, codecs) + output pfifo
//   ot_p2h_fadd16     16-lane FP32 adder array: pin flops + 16 x LAT8 ot_v41_fadd (registered outputs)
//   ot_mtp_p2_prefix_path_hub  glue: start/abort pins, context ownership, PINREG input FIFO, native publisher, output station
// Ports: ck / rst (async active-low, synchronised inside), f_* inputs, t_* outputs (S81 contract convention).
// Parameters exist only for the simulation mutants; the defaults are the hardened configuration (tiles are routed
// with no overrides).

module ot_p2h_xport #(parameter integer MUT_ORDER=0)(
 input wire [0:0] ck,rst,
 input wire [1209:0] f_in,     // {in_v[1:0], in_identity[147:0], in_expert[17:0], in_shared[1:0], in_last[1:0], in_word[13:0], in_data[1023:0]}
 output wire [1:0] t_inr,      // lane in_ready (registered)
 input wire [102:0] f_c,       // {start_v, abort, start_identity[73:0], start_ids[26:0]}
 output reg [1:0] t_c,         // {start_r, fault}
 output wire [669:0] t_o,      // {out_v, identity74, expert9, shared, row_last, transaction_last, word7, code576}
 input wire [0:0] f_or          // out_ready
);
 wire clk=ck[0];wire rn;
 ot_dsrom_mtp_rstsync u_rs(.clk(clk),.rst_n_async(rst[0]),.rst_n(rn));
 // control pin flops
 reg c_sv,c_ab;reg [73:0] c_id;reg [26:0] c_ids;
 always @(posedge clk or negedge rn)if(!rn)begin c_sv<=0;c_ab<=0;end else begin c_sv<=f_c[102];c_ab<=f_c[101];end
 always @(posedge clk)begin c_id<=f_c[100:27];c_ids<=f_c[26:0];end
 // lanes: {identity74, expert9, shared, last, word7, data512} = 604; PINREG pin FIFOs (data/valid captured at the pin)
 wire [1:0] iv=f_in[1209:1208];wire [147:0] iid=f_in[1207:1060];wire [17:0] iex=f_in[1059:1042];
 wire [1:0] ish=f_in[1041:1040];wire [1:0] ila=f_in[1039:1038];wire [13:0] iwd=f_in[1037:1024];wire [1023:0] idt=f_in[1023:0];
 wire [1:0] li_v,li_r;wire [603:0] li_d[0:1];
 for(genvar l=0;l<2;l=l+1)begin: lanes
 ot_sc_pfifo #(.W(604),.S(3),.G(32),.PINREG(1)) pin(.clk(clk),.rst_n(rn),
 .in_valid(iv[l]),.in_ready(t_inr[l]),
 .in_data({iid[74*l+:74],iex[9*l+:9],ish[l],ila[l],iwd[7*l+:7],idt[512*l+:512]}),
 .out_valid(li_v[l]),.out_ready(li_r[l]),.out_data(li_d[l]));
 end
 wire tr_sr,tr_fault,tr_v,tr_r,tr_shared,tr_last,tr_tlast;wire [73:0] tr_id;wire [8:0] tr_expert;wire [6:0] tr_word;wire [575:0] tr_code;
 ot_mtp_p2_ordered_rows #(.ENABLE(1),.PRIMARY_SHARED(1),.SB_REG(1),.ACC_REG(2),.PRE_DEC(1),.BSEL_REP(1),.MUT_ORDER(MUT_ORDER)) rows(
 .clk(clk),.rst_n(rn),.start_v(c_sv),.start_r(tr_sr),
 .start_identity(c_id),.start_ids(c_ids),
 .in_v(li_v),.in_r(li_r),.in_identity({li_d[1][603:530],li_d[0][603:530]}),
 .in_expert({li_d[1][529:521],li_d[0][529:521]}),
 .in_shared({li_d[1][520],li_d[0][520]}),.in_last({li_d[1][519],li_d[0][519]}),
 .in_word({li_d[1][518:512],li_d[0][518:512]}),.in_data({li_d[1][511:0],li_d[0][511:0]}),
 .out_v(tr_v),.out_r(tr_r),.out_identity(tr_id),.out_expert(tr_expert),
 .out_shared(tr_shared),.out_row_last(tr_last),.out_transaction_last(tr_tlast),
 .out_word(tr_word),.out_secded(tr_code),.sink_abort(c_ab),.done(),.fault(tr_fault));
 // registered output station (the rows queue read is an 8:1 mux)
 // READY-LATENCY seam to arith (el1011-ds-mtp 2026-10-12, mtp-p2h-xp-50b05596a TT class f_or -> opin pop -> 84 pointer
 // copies, -79 ps under the die-link budget): f_or (arith's registered in_ready) lands in ONE pin flop rq; the station
 // pops on rq (flops only) into registered outputs t_o = {t_v, t_d} (pin flops); arith's xfer receiver (PINREG=2) captures
 // every valid beat and reserves room for the two in_ready values in flight.  +1 cycle on the seam, exact.
 wire o_v;wire [668:0] o_d;reg rq,t_v;reg [668:0] t_d;
 ot_sc_pfifo #(.W(669),.S(2),.G(32)) opin(.clk(clk),.rst_n(rn),
 .in_valid(tr_v),.in_ready(tr_r),.in_data({tr_id,tr_expert,tr_shared,tr_last,tr_tlast,tr_word,tr_code}),
 .out_valid(o_v),.out_ready(rq),.out_data(o_d));
 always @(posedge clk or negedge rn)if(!rn)begin rq<=1'b0;t_v<=1'b0;end else begin rq<=f_or[0];t_v<=o_v&&rq;end
 always @(posedge clk)t_d<=o_d;
 assign t_o={t_v,t_d};
 always @(posedge clk or negedge rn)if(!rn)t_c<=2'b0;else t_c<={tr_sr,tr_fault};
endmodule

module ot_p2h_arith #(parameter integer MUT_COPY_FIRST=0)(
 input wire [0:0] ck,rst,
 input wire [669:0] f_x,       // {in_v, identity74, expert9, shared, row_last, transaction_last, word7, code576}
 output wire [0:0] t_xr,       // xfer in_ready (registered)
 input wire [102:0] f_c,       // {start_v, abort, start_identity[73:0], start_ids[26:0]}
 output reg [2:0] t_c,         // {start_r, fault, corrected}
 output wire [1024:0] t_ab,    // {issue_v, add_a[511:0], add_b[511:0]} -> ot_p2h_fadd16
 input wire [559:0] f_y,       // {valid_out[15:0], err[31:0], y[511:0]} <- ot_p2h_fadd16
 output wire [658:0] t_o,      // {out_v, identity74, word7, last, code576}
 input wire [0:0] f_or
);
 wire clk=ck[0];wire rn;
 ot_dsrom_mtp_rstsync u_rs(.clk(clk),.rst_n_async(rst[0]),.rst_n(rn));
 reg c_sv,c_ab;reg [73:0] c_id;reg [26:0] c_ids;
 always @(posedge clk or negedge rn)if(!rn)begin c_sv<=0;c_ab<=0;end else begin c_sv<=f_c[102];c_ab<=f_c[101];end
 always @(posedge clk)begin c_id<=f_c[100:27];c_ids<=f_c[26:0];end
 wire xa_v,xa_r;wire [668:0] xa_d;
 // READY-LATENCY receiver (PINREG=2, S=6): xport registers this in_ready before using it (see ot_p2h_xport)
 ot_sc_pfifo #(.W(669),.S(6),.G(32),.PINREG(2)) xfer(.clk(clk),.rst_n(rn),
 .in_valid(f_x[669]),.in_ready(t_xr[0]),.in_data(f_x[668:0]),
 .out_valid(xa_v),.out_ready(xa_r),.out_data(xa_d));
 wire ar_sr,ar_fault,ar_ce,ar_v,ar_r,ar_last;wire [73:0] ar_id;wire [6:0] ar_word;wire [575:0] ar_code;
 wire x_v;wire [511:0] x_a,x_b;
 // result pin flops: the fadd tile's outputs land in flops before any logic (valid bits reset)
 reg [15:0] y_v;reg [543:0] y_q;
 always @(posedge clk or negedge rn)if(!rn)y_v<=16'd0;else y_v<=f_y[559:544];
 always @(posedge clk)y_q<=f_y[543:0];
 ot_mtp_p2_prefix #(.ENABLE(1),.BREG(1),.DSTAGE(1),.ROOTPIPE(1),.EXT_ADD(1),.MUT_COPY_FIRST(MUT_COPY_FIRST)) arithmetic(.clk(clk),.rst_n(rn),
 .start_v(c_sv),.start_r(ar_sr),.start_identity(c_id),.start_ids(c_ids),
 .in_v(xa_v),.in_r(xa_r),.in_identity(xa_d[668:595]),.in_expert(xa_d[594:586]),
 .in_shared(xa_d[585]),.in_row_last(xa_d[584]),.in_transaction_last(xa_d[583]),
 .in_word(xa_d[582:576]),.in_secded(xa_d[575:0]),.out_v(ar_v),.out_r(ar_r),
 .out_identity(ar_id),.out_word(ar_word),.out_last(ar_last),.out_secded(ar_code),
 .abort(c_ab),.done(),.fault(ar_fault),.corrected(ar_ce),
 .x_add_v(x_v),.x_add_a(x_a),.x_add_b(x_b),.x_add_y(y_q[511:0]),.x_add_err(y_q[543:512]),.x_add_vo(y_v));
 assign t_ab={x_v,x_a,x_b};
 wire o_v;wire [657:0] o_d;
 ot_sc_pfifo #(.W(658),.S(2),.G(32)) opin(.clk(clk),.rst_n(rn),
 .in_valid(ar_v),.in_ready(ar_r),.in_data({ar_id,ar_word,ar_last,ar_code}),
 .out_valid(o_v),.out_ready(f_or[0]),.out_data(o_d));
 assign t_o={o_v,o_d};
 always @(posedge clk or negedge rn)if(!rn)t_c<=3'b0;else t_c<={ar_sr,ar_fault,ar_ce};
endmodule

module ot_p2h_fadd16(
 input wire [0:0] ck,rst,
 input wire [1024:0] f_ab,     // {issue_v, a[511:0], b[511:0]}
 output wire [559:0] t_y        // {valid_out[15:0], err[31:0], y[511:0]} (ot_v41_fadd output registers)
);
 wire clk=ck[0];wire rn;
 ot_dsrom_mtp_rstsync u_rs(.clk(clk),.rst_n_async(rst[0]),.rst_n(rn));
 reg v_q;reg [511:0] a_q,b_q;
 always @(posedge clk or negedge rn)if(!rn)v_q<=0;else v_q<=f_ab[1024];
 always @(posedge clk)begin a_q<=f_ab[1023:512];b_q<=f_ab[511:0];end
 for(genvar lane=0;lane<16;lane=lane+1)begin: adds
 ot_v41_fadd #(.CUT(9'b1_0111_1011),.SPLIT9(0)) a(.clk(clk),.rst_n(rn),
 .valid_in(v_q),.a(a_q[32*lane+:32]),.b(b_q[32*lane+:32]),
 .y(t_y[32*lane+:32]),.err(t_y[512+2*lane+:2]),.valid_out(t_y[544+lane]));
 end
endmodule

module ot_mtp_p2_prefix_path_hub #(parameter integer AIN=1)(
 input wire [0:0] ck,rst,
 input wire [102:0] f_s,       // die: {start_v, abort, start_identity[73:0], start_ids[26:0]}
 output wire [3:0] t_s,        // die: {start_r, done, fault, corrected}
 output wire [594:0] t_out,    // die: {out_v, out_data[511:0], out_identity[73:0], out_word[6:0], out_last}
 input wire [0:0] f_outr,      // die: out_ready
 output wire [102:0] t_xc,      // -> xport f_c {start_v, abort, identity, ids}
 input wire [1:0] f_xc,        // <- xport t_c {start_r, fault}
 output wire [102:0] t_ac,      // -> arith f_c
 input wire [2:0] f_ac,        // <- arith t_c {start_r, fault, corrected}
 input wire [658:0] f_a,       // <- arith t_o {out_v, identity74, word7, last, code576}
 output wire [0:0] t_ar        // -> arith f_or (registered PINREG in_ready)
);
 wire clk=ck[0];wire rn;
 ot_dsrom_mtp_rstsync u_rs(.clk(clk),.rst_n_async(rst[0]),.rst_n(rn));
 wire start_v=f_s[102],abort=f_s[101];wire [73:0] start_identity=f_s[100:27];wire [26:0] start_ids=f_s[26:0];
 reg busy,busy_copy,done_q,abort_q,sr_q,sv_q,fault_q,corrected_q,lost_q;
 reg [73:0] sid_q;reg [26:0] sids_q;
 reg tr_sr,tr_fault,ar_sr,ar_fault,ar_ce;     // seam pin flops
 always @(posedge clk or negedge rn)if(!rn)begin tr_sr<=0;tr_fault<=0;ar_sr<=0;ar_fault<=0;ar_ce<=0;end
  else begin {tr_sr,tr_fault}<=f_xc;{ar_sr,ar_fault,ar_ce}<=f_ac;end
 wire pub_fault,pub_ce;
 wire broken=busy!=busy_copy;
 wire fault_i=tr_fault||ar_fault||pub_fault||broken||lost_q;
 wire poison=abort_q||fault_i;
 wire fire_ext=start_v&&sr_q;
 wire fire=sv_q;
 assign t_s={sr_q,done_q,fault_q,corrected_q};
 // arith -> publisher: PINREG input FIFO {identity74, word7, last, code576} = 658
 wire ai_v,ai_r;wire [657:0] ai_d;
 // AIN=0 (inside ot_p2h_head): the arith output pfifo is in the same tile, so no seam FIFO; ready is internal
 generate if(AIN)begin: g_ain
 ot_sc_pfifo #(.W(658),.S(3),.G(32),.PINREG(1)) ain(.clk(clk),.rst_n(rn),
 .in_valid(f_a[658]),.in_ready(t_ar[0]),.in_data(f_a[657:0]),
 .out_valid(ai_v),.out_ready(ai_r),.out_data(ai_d));
 end else begin: g_noain
 assign ai_v=f_a[658];assign ai_d=f_a[657:0];assign t_ar[0]=ai_r;
 end endgenerate
 wire po_v,po_r,po_last;wire [511:0] po_data;wire [73:0] po_id;wire [6:0] po_word;wire [593:0] oq;wire out_v,out_last;
 ot_mtp_p2_prefix_native #(.ENABLE(1),.BREG(1)) publisher(.clk(clk),.rst_n(rn),.abort(poison),
 .in_v(ai_v),.in_r(ai_r),.in_secded(ai_d[575:0]),.in_identity(ai_d[657:584]),
 .in_word(ai_d[583:577]),.in_last(ai_d[576]),.out_v(po_v),.out_r(po_r),
 .out_data(po_data),.out_identity(po_id),.out_word(po_word),.out_last(po_last),
 .fault(pub_fault),.corrected(pub_ce));
 ot_mtp_p2_pin_output #(.W(594),.G(32)) opin(.clk(clk),.rst_n(rn),
 .in_valid(po_v),.in_ready(po_r),.in_data({po_data,po_id,po_word,po_last}),
 .out_valid(out_v),.out_ready(f_outr[0]),.out_data(oq));
 assign t_out={out_v,oq};assign out_last=oq[0];
 wire last_pop=out_v&&f_outr[0]&&out_last&&!poison;
 wire busy_nx=(busy||fire)&&!last_pop;
 always @(posedge clk)begin sid_q<=start_identity;sids_q<=start_ids;end   // free-running pin capture
 reg [1:0] xc_c,ac_c;reg [100:0] xc_d,ac_d;               // seam output registers (control reset, data not)
 assign t_xc={xc_c,xc_d};assign t_ac={ac_c,ac_d};
 always @(posedge clk)begin xc_d<={sid_q,sids_q};ac_d<={sid_q,sids_q};end
 always @(posedge clk or negedge rn)begin
 if(!rn)begin busy<=0;busy_copy<=0;done_q<=0;abort_q<=0;sr_q<=0;sv_q<=0;fault_q<=0;corrected_q<=0;lost_q<=0;
  xc_c<=2'b0;ac_c<=2'b0;end
 else begin done_q<=0;abort_q<=abort;sv_q<=fire_ext;
 // tile start / abort leave on a register (fault terms from the tiles are already one seam later)
 xc_c<={sv_q,poison};ac_c<={sv_q,poison};
 if(sv_q&&!(tr_sr&&ar_sr))lost_q<=1;
 fault_q<=fault_i;corrected_q<=ar_ce||pub_ce;
 sr_q<=!busy_nx&&!poison&&tr_sr&&ar_sr&&!fire_ext&&!fire;
 if(fire)begin busy<=1;busy_copy<=1;end
 if(last_pop)begin busy<=0;busy_copy<=0;done_q<=1;end
 end end
endmodule

// el1011-ds-mtp r5 2026-10-12 (owner GLUE PLACEMENT): the P2 glue (start/abort control, context ownership, native
// SECDED publisher, output pin station; < 20k cells, no one-cycle loop to any tile) is pushed into the arith tile, which
// already ends the stream: ot_p2h_head = ot_p2h_arith + that glue, so P2 = 3 die-placed hard tiles (xport, head,
// fadd16) and no hub element / cluster parent.  The arith -> publisher seam is internal (its PINREG FIFO is removed);
// the control seam to the arith core keeps its register (same start timing as the 4-tile composition); the xport
// control seam (t_xc / f_xc) stays registered on both sides at the die.
module ot_p2h_head #(parameter integer MUT_COPY_FIRST=0)(
 input wire [0:0] ck,rst,
 input wire [102:0] f_s,       // die: {start_v, abort, start_identity[73:0], start_ids[26:0]}
 output wire [3:0] t_s,        // die: {start_r, done, fault, corrected}
 output wire [594:0] t_out,    // die: {out_v, out_data[511:0], out_identity[73:0], out_word[6:0], out_last}
 input wire [0:0] f_outr,      // die: out_ready
 output wire [102:0] t_xc,     // -> xport f_c
 input wire [1:0] f_xc,        // <- xport t_c
 input wire [669:0] f_x,       // <- xport t_o
 output wire [0:0] t_xr,       // -> xport f_or
 output wire [1024:0] t_ab,    // -> ot_p2h_fadd16
 input wire [559:0] f_y        // <- ot_p2h_fadd16
);
 wire [102:0] acf;wire [2:0] ac;wire [658:0] ao;wire [0:0] ar;
 ot_mtp_p2_prefix_path_hub #(.AIN(0)) ctl(.ck(ck),.rst(rst),.f_s(f_s),.t_s(t_s),.t_out(t_out),.f_outr(f_outr),
  .t_xc(t_xc),.f_xc(f_xc),.t_ac(acf),.f_ac(ac),.f_a(ao),.t_ar(ar));
 ot_p2h_arith #(.MUT_COPY_FIRST(MUT_COPY_FIRST)) arith(.ck(ck),.rst(rst),.f_x(f_x),.t_xr(t_xr),.f_c(acf),.t_c(ac),
  .t_ab(t_ab),.f_y(f_y),.t_o(ao),.f_or(ar));
endmodule
`default_nettype wire
