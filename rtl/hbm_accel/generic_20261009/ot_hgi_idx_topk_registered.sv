`timescale 1ns/1ps
// Three registered boundary relays around the measured, byte-identical TOPK core.
// Command, score and result are each captured before boundary logic. A command
// retires only after its final accepted output; faults clear prefetched scores.
module ot_hgi_idx_topk_registered #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048, parameter bit MUTANT_TIE=0,
 parameter bit MUTANT_EARLY_DONE=0,
 // RESET-APPLY / pin-register opt-ins (drive-1010 2026-10-10; default 0 = the historical, byte-identical behaviour).
 // RST_RELAY 1: rst_n drives only rtl/lib/ot_rst_relay (async assert, synchronous release): region 0 -> one local kept
 //   stage -> this wrapper's flops, region 1 -> the core (systolic core only: its own per-leaf stage), so wrapper and
 //   core leave reset on the same edge, 4 edges after the port; cmd_ready is held low until then.
 // OUT_SKID 1: out_ready is registered at the pin: it only selects the output register (q) load; the core sees a
 //   registered ready (skid empty) and completion waits for an empty output stage (q and skid), never on out_ready.
 //   Results, order and handshake are unchanged; done may come one edge later.
 parameter integer RST_RELAY=0, parameter integer OUT_SKID=0
)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [31:0] in_score,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output reg done, output reg [3:0] error
);
 reg active,c_valid,s_valid,q_valid,pending_done;
 reg [3:0] c_unit;
 reg [5:0] c_op;
 reg [24:0] c_param;
 reg [31:0] c_n,c_m,s_score;
 reg c_values;
 reg [31:0] q_id,q_score,q_row;
 reg q_last,q_values;
 wire core_cmd_ready,core_in_ready,core_out_valid,core_done;
 wire [3:0] core_error;
 wire [31:0] core_id,core_score,core_row;
 wire core_last,core_values;
 reg sk_valid; reg [31:0] sk_id,sk_score,sk_row; reg sk_last,sk_values;
 wire rw,core_rst_n,up;                             // wrapper flops' reset, the core's reset, wrapper out of reset
 generate if(RST_RELAY) begin:g_rr
  wire [1:0] rr;
  ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
  (* keep = "true", dont_touch = "true" *) reg rw_q;
  always @(posedge clk or negedge rr[0]) if(!rr[0]) rw_q<=1'b0; else rw_q<=1'b1;
  assign rw=rw_q; assign core_rst_n=rr[1]; assign up=rw_q;
 end else begin:g_rr_port
  assign rw=rst_n; assign core_rst_n=rst_n; assign up=1'b1;
 end endgenerate
 wire core_out_ready=OUT_SKID?!sk_valid:(!q_valid||out_ready);
 assign cmd_ready=!active&&!c_valid&&core_cmd_ready&&!pending_done&&!q_valid&&!(OUT_SKID&&sk_valid)&&up;
 assign in_ready=active&&(!s_valid||core_in_ready);
 assign out_valid=q_valid;
 assign out_id=q_id;assign out_score=q_score;assign out_row=q_row;
 assign out_last=q_last;assign out_values_valid=q_valid&&q_values;
 generate if(RST_RELAY) begin:g_core_rr                 // only the systolic core has RST_RELAY
 ot_hgi_idx_topk #(.ENABLE(ENABLE),.MAX_K(MAX_K),.MUTANT_TIE(MUTANT_TIE),.RST_RELAY(1)) core(
  .clk(clk),.rst_n(core_rst_n),.cmd_valid(c_valid),.cmd_ready(core_cmd_ready),
  .cmd_unit(c_unit),.cmd_op(c_op),.cmd_param(c_param),.cmd_n(c_n),.cmd_m(c_m),.cmd_values(c_values),
  .in_valid(s_valid&&active),.in_ready(core_in_ready),.in_score(s_score),
  .out_valid(core_out_valid),.out_ready(core_out_ready),.out_id(core_id),.out_score(core_score),
  .out_row(core_row),.out_last(core_last),.out_values_valid(core_values),.done(core_done),.error(core_error));
 end else begin:g_core
 ot_hgi_idx_topk #(.ENABLE(ENABLE),.MAX_K(MAX_K),.MUTANT_TIE(MUTANT_TIE)) core(
  .clk(clk),.rst_n(core_rst_n),.cmd_valid(c_valid),.cmd_ready(core_cmd_ready),
  .cmd_unit(c_unit),.cmd_op(c_op),.cmd_param(c_param),.cmd_n(c_n),.cmd_m(c_m),.cmd_values(c_values),
  .in_valid(s_valid&&active),.in_ready(core_in_ready),.in_score(s_score),
  .out_valid(core_out_valid),.out_ready(core_out_ready),.out_id(core_id),.out_score(core_score),
  .out_row(core_row),.out_last(core_last),.out_values_valid(core_values),.done(core_done),.error(core_error));
 end endgenerate
 // OUT_SKID: the skid's data follows the core head while it is empty (enable = a flop, not out_ready)
 always @(posedge clk) if(OUT_SKID&&!sk_valid) begin
  sk_id<=core_id;sk_score<=core_score;sk_row<=core_row;sk_last<=core_last;sk_values<=core_values;
 end
 always @(posedge clk or negedge rw)begin
  if(!rw)begin
   active<=0;c_valid<=0;s_valid<=0;q_valid<=0;pending_done<=0;done<=0;error<=0;
   c_unit<=0;c_op<=0;c_param<=0;c_n<=0;c_m<=0;c_values<=0;s_score<=0;
   q_id<=0;q_score<=0;q_row<=0;q_last<=0;q_values<=0;sk_valid<=0;
  end else begin
   done<=0;
   if(c_valid&&core_cmd_ready)c_valid<=0;
   if(cmd_valid&&cmd_ready)begin
    active<=1;c_valid<=1;c_unit<=cmd_unit;c_op<=cmd_op;c_param<=cmd_param;
    c_n<=cmd_n;c_m<=cmd_m;c_values<=cmd_values;error<=0;
   end
   if(in_ready)begin
    s_valid<=in_valid;
    if(in_valid)s_score<=in_score;
   end
   if(OUT_SKID)begin
    if(!q_valid||out_ready)begin                    // out_ready: the q load select only
     q_valid<=sk_valid||core_out_valid;
     if(sk_valid)begin
      q_id<=sk_id;q_score<=sk_score;q_row<=sk_row;q_last<=sk_last;q_values<=sk_values;
     end else if(core_out_valid)begin
      q_id<=core_id;q_score<=core_score;q_row<=core_row;q_last<=core_last;q_values<=core_values;
     end
     sk_valid<=0;
    end else if(core_out_valid&&!sk_valid) sk_valid<=1;   // q held: the core head (already in sk_*) is taken
   end else if(core_out_ready)begin
    q_valid<=core_out_valid;
    if(core_out_valid)begin
     q_id<=core_id;q_score<=core_score;q_row<=core_row;
     q_last<=core_last;q_values<=core_values;
    end
   end
   if(core_done)begin pending_done<=1;error<=core_error;end
   if((pending_done||core_done)&&((OUT_SKID?(!q_valid&&!sk_valid):(!q_valid||out_ready))||MUTANT_EARLY_DONE))begin
    done<=1;active<=0;pending_done<=0;c_valid<=0;s_valid<=0;
   end
  end
 end
endmodule
