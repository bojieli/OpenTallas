`timescale 1ns/1ps
`default_nettype none
// Real finite transport -> exact arithmetic -> corrected native publisher.
// Context remains owned through the last native output handshake.
//
// REGB=1 (mtp-lead 2026-10-09, default; routes mtp-p2-path-{a,b}-91473d972 EARLY_FAIL_SETUP TT -1,003 at the input:
// in_expert / start_ids / abort decoded straight into the SECDED encoders, state and 512-bit data enables):
//  * every input is a flop: abort pin flop; start = registered start_r + free-running capture (start_v & start_r) of
//    start_identity / start_ids, the inner start fires one cycle later; each input lane and the output go through an
//    ot_sc_pfifo pin FIFO (registered in_r / out_v, no pin bit on a data enable);
//  * transport -> arithmetic channel through an ot_sc_pfifo (cuts read pointer -> 8:1 queue mux -> SECDED syndrome);
//  * transport SB_REG / ACC_REG, arithmetic and publisher BREG (registered duplicate-state gating, registered accept);
//  * fault / corrected outputs registered.
// Context ownership is unchanged: start_r stays low from the accepted start through the last external out handshake.
// REGB=0 is the original wiring.
module ot_mtp_p2_prefix_path #(parameter integer ENABLE=0, parameter integer REGB=1, parameter integer MUT_COPY_FIRST=0, parameter integer MUT_ORDER=0)(
 input wire clk,rst_n,start_v,output wire start_r,
 input wire [73:0] start_identity,input wire [26:0] start_ids,
 input wire [1:0] in_v,output wire [1:0] in_r,input wire [147:0] in_identity,
 input wire [17:0] in_expert,input wire [1:0] in_shared,in_last,
 input wire [13:0] in_word,input wire [1023:0] in_data,
 output wire out_v,input wire out_r,output wire [511:0] out_data,
 output wire [73:0] out_identity,output wire [6:0] out_word,output wire out_last,
 input wire abort,output wire done,fault,corrected
);
 generate if(!ENABLE)begin: disabled
 assign start_r=0;assign in_r=0;assign out_v=0;assign out_data=0;
 assign out_identity=0;assign out_word=0;assign out_last=0;
 assign done=0;assign fault=0;assign corrected=0;
 end else if(!REGB)begin: enabled
 reg busy,busy_copy,done_q;
 wire tr_sr,ar_sr,tr_v,tr_r,tr_fault,ar_fault,pub_fault;
 wire [73:0] tr_id;wire [8:0] tr_expert;wire [6:0] tr_word;
 wire tr_shared,tr_last,tr_tlast;wire [575:0] tr_code;
 wire ar_v,ar_r,ar_last,ar_ce,pub_ce;wire [73:0] ar_id;
 wire [6:0] ar_word;wire [575:0] ar_code;
 wire broken=busy!=busy_copy;
 assign fault=tr_fault||ar_fault||pub_fault||broken;
 wire poison=abort||fault;
 assign start_r=!busy&&!poison&&tr_sr&&ar_sr;
 wire fire=start_v&&start_r;
 assign done=done_q;assign corrected=ar_ce||pub_ce;
 ot_mtp_p2_ordered_rows #(.ENABLE(1),.PRIMARY_SHARED(1),.MUT_ORDER(MUT_ORDER)) transport(
 .clk(clk),.rst_n(rst_n),.start_v(fire),.start_r(tr_sr),
 .start_identity(start_identity),.start_ids(start_ids),
 .in_v(in_v),.in_r(in_r),.in_identity(in_identity),.in_expert(in_expert),
 .in_shared(in_shared),.in_last(in_last),.in_word(in_word),.in_data(in_data),
 .out_v(tr_v),.out_r(tr_r),.out_identity(tr_id),.out_expert(tr_expert),
 .out_shared(tr_shared),.out_row_last(tr_last),.out_transaction_last(tr_tlast),
 .out_word(tr_word),.out_secded(tr_code),.sink_abort(poison),.done(),.fault(tr_fault));
 ot_mtp_p2_prefix #(.ENABLE(1),.MUT_COPY_FIRST(MUT_COPY_FIRST)) arithmetic(.clk(clk),.rst_n(rst_n),
 .start_v(fire),.start_r(ar_sr),.start_identity(start_identity),.start_ids(start_ids),
 .in_v(tr_v),.in_r(tr_r),.in_identity(tr_id),.in_expert(tr_expert),
 .in_shared(tr_shared),.in_row_last(tr_last),.in_transaction_last(tr_tlast),
 .in_word(tr_word),.in_secded(tr_code),.out_v(ar_v),.out_r(ar_r),
 .out_identity(ar_id),.out_word(ar_word),.out_last(ar_last),.out_secded(ar_code),
 .abort(poison),.done(),.fault(ar_fault),.corrected(ar_ce));
 ot_mtp_p2_prefix_native #(.ENABLE(1)) publisher(.clk(clk),.rst_n(rst_n),.abort(poison),
 .in_v(ar_v),.in_r(ar_r),.in_secded(ar_code),.in_identity(ar_id),
 .in_word(ar_word),.in_last(ar_last),.out_v(out_v),.out_r(out_r),
 .out_data(out_data),.out_identity(out_identity),.out_word(out_word),.out_last(out_last),
 .fault(pub_fault),.corrected(pub_ce));
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin busy<=0;busy_copy<=0;done_q<=0;end
 else begin done_q<=0;
 if(fire)begin busy<=1;busy_copy<=1;end
 if(out_v&&out_r&&out_last&&!poison)begin busy<=0;busy_copy<=0;done_q<=1;end
 end end
 end else begin: enabled
 reg busy,busy_copy,done_q,abort_q,sr_q,sv_q,fault_q,corrected_q;
 reg [73:0] sid_q;reg [26:0] sids_q;
 wire tr_sr,ar_sr,tr_v,tr_r,tr_fault,ar_fault,pub_fault;
 wire [73:0] tr_id;wire [8:0] tr_expert;wire [6:0] tr_word;
 wire tr_shared,tr_last,tr_tlast;wire [575:0] tr_code;
 wire ar_v,ar_r,ar_last,ar_ce,pub_ce;wire [73:0] ar_id;
 wire [6:0] ar_word;wire [575:0] ar_code;
 wire broken=busy!=busy_copy;
 // a registered start that the inner blocks are not ready for (only after a fault) is itself a fault
 // (registered: ar_sr depends on poison, so a combinational term here would close a loop)
 reg lost_q;
 wire fault_i=tr_fault||ar_fault||pub_fault||broken||lost_q;
 wire poison=abort_q||fault_i;
 assign start_r=sr_q;
 wire fire_ext=start_v&&sr_q;
 wire fire=sv_q;
 assign done=done_q;assign fault=fault_q;assign corrected=corrected_q;
 // ---- input lanes: pin FIFOs {identity74, expert9, shared, last, word7, data512} = 604
 wire [1:0] li_v,li_r;wire [603:0] li_d[0:1];
 for(genvar l=0;l<2;l=l+1)begin: lanes
 ot_sc_pfifo #(.W(604),.S(2),.G(32)) pin(.clk(clk),.rst_n(rst_n),
 .in_valid(in_v[l]),.in_ready(in_r[l]),
 .in_data({in_identity[74*l+:74],in_expert[9*l+:9],in_shared[l],in_last[l],in_word[7*l+:7],in_data[512*l+:512]}),
 .out_valid(li_v[l]),.out_ready(li_r[l]),.out_data(li_d[l]));
 end
 ot_mtp_p2_ordered_rows #(.ENABLE(1),.PRIMARY_SHARED(1),.SB_REG(1),.ACC_REG(1),.MUT_ORDER(MUT_ORDER)) transport(
 .clk(clk),.rst_n(rst_n),.start_v(fire),.start_r(tr_sr),
 .start_identity(sid_q),.start_ids(sids_q),
 .in_v(li_v),.in_r(li_r),.in_identity({li_d[1][603:530],li_d[0][603:530]}),
 .in_expert({li_d[1][529:521],li_d[0][529:521]}),
 .in_shared({li_d[1][520],li_d[0][520]}),.in_last({li_d[1][519],li_d[0][519]}),
 .in_word({li_d[1][518:512],li_d[0][518:512]}),.in_data({li_d[1][511:0],li_d[0][511:0]}),
 .out_v(tr_v),.out_r(tr_r),.out_identity(tr_id),.out_expert(tr_expert),
 .out_shared(tr_shared),.out_row_last(tr_last),.out_transaction_last(tr_tlast),
 .out_word(tr_word),.out_secded(tr_code),.sink_abort(poison),.done(),.fault(tr_fault));
 // ---- transport -> arithmetic: {identity74, expert9, shared, row_last, transaction_last, word7, code576} = 669
 wire xa_v,xa_r;wire [668:0] xa_d;
 ot_sc_pfifo #(.W(669),.S(2),.G(32)) xfer(.clk(clk),.rst_n(rst_n),
 .in_valid(tr_v),.in_ready(tr_r),
 .in_data({tr_id,tr_expert,tr_shared,tr_last,tr_tlast,tr_word,tr_code}),
 .out_valid(xa_v),.out_ready(xa_r),.out_data(xa_d));
 ot_mtp_p2_prefix #(.ENABLE(1),.BREG(1),.MUT_COPY_FIRST(MUT_COPY_FIRST)) arithmetic(.clk(clk),.rst_n(rst_n),
 .start_v(fire),.start_r(ar_sr),.start_identity(sid_q),.start_ids(sids_q),
 .in_v(xa_v),.in_r(xa_r),.in_identity(xa_d[668:595]),.in_expert(xa_d[594:586]),
 .in_shared(xa_d[585]),.in_row_last(xa_d[584]),.in_transaction_last(xa_d[583]),
 .in_word(xa_d[582:576]),.in_secded(xa_d[575:0]),.out_v(ar_v),.out_r(ar_r),
 .out_identity(ar_id),.out_word(ar_word),.out_last(ar_last),.out_secded(ar_code),
 .abort(poison),.done(),.fault(ar_fault),.corrected(ar_ce));
 // ---- publisher -> output pin FIFO {data512, identity74, word7, last} = 594
 wire po_v,po_r,po_last;wire [511:0] po_data;wire [73:0] po_id;wire [6:0] po_word;wire [593:0] oq;
 ot_mtp_p2_prefix_native #(.ENABLE(1),.BREG(1)) publisher(.clk(clk),.rst_n(rst_n),.abort(poison),
 .in_v(ar_v),.in_r(ar_r),.in_secded(ar_code),.in_identity(ar_id),
 .in_word(ar_word),.in_last(ar_last),.out_v(po_v),.out_r(po_r),
 .out_data(po_data),.out_identity(po_id),.out_word(po_word),.out_last(po_last),
 .fault(pub_fault),.corrected(pub_ce));
 ot_sc_pfifo #(.W(594),.S(2),.G(32)) opin(.clk(clk),.rst_n(rst_n),
 .in_valid(po_v),.in_ready(po_r),.in_data({po_data,po_id,po_word,po_last}),
 .out_valid(out_v),.out_ready(out_r),.out_data(oq));
 assign out_data=oq[593:82];assign out_identity=oq[81:8];assign out_word=oq[7:1];assign out_last=oq[0];
 wire last_pop=out_v&&out_r&&out_last&&!poison;
 wire busy_nx=(busy||fire)&&!last_pop;
 always @(posedge clk)begin sid_q<=start_identity;sids_q<=start_ids;end   // free-running pin capture
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin busy<=0;busy_copy<=0;done_q<=0;abort_q<=0;sr_q<=0;sv_q<=0;fault_q<=0;corrected_q<=0;lost_q<=0;end
 else begin done_q<=0;abort_q<=abort;sv_q<=fire_ext;
 if(sv_q&&!(tr_sr&&ar_sr))lost_q<=1;
 fault_q<=fault_i;corrected_q<=ar_ce||pub_ce;
 sr_q<=!busy_nx&&!poison&&tr_sr&&ar_sr&&!fire_ext&&!fire;
 if(fire)begin busy<=1;busy_copy<=1;end
 if(last_pop)begin busy<=0;busy_copy<=0;done_q<=1;end
 end end
 end endgenerate
endmodule
`default_nettype wire
