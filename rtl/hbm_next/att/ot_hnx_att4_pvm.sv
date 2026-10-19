`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_att4_pvm: the per-lane PV merge master of the P = 4 attention leaf (hnx_rp4a4, HBM-NEXT-ATT4 2026-10-19).
// At P = 4 every BF16 column of the SM carries 4 query lanes, and each lane owns one PV binary-counter merge
// (ot_hnx_att_pv_merge, PUBLISH = 1: the production leaf's publication path, as ot_hbm_sm_attn_native_col) on its own
// 64x512 stack macro.  This tile is that merge hardened ONCE and replicated 4x per column (owner 10-15: few tiles, one
// master replicated) beside the 4-lane tcl of hnx_rp4lp4.
// PIN REGISTERS (owner 10-15): every input lands in one register at its pin and every output launches from one register
// at its pin (+1 edge each way, fixed: the compiler schedule counts it; the merge's barrel turn is a free-running
// residue, so a fixed input delay only rotates which barrel entry a slot uses -- every slot still owns one residue).
// The reset lands in one kept register beside the pin (RSTPIN style).  No credit / ready / stall; faults are sticky.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_att4_pvm #(
    parameter integer LV    = 4,
    parameter integer MUT   = 0,
    parameter integer STORE = 0         // A1 fallback: 1 = the stack in flops (ot_hnx_att_stack_flop, LV 3 + node word)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         ev,
    input  wire [511:0] sum,
    input  wire [15:0]  tag_d,
    input  wire         pub_start,
    input  wire [2:0]   pub_slot,
    input  wire         fold_start,
    input  wire [2:0]   fold_a,
    input  wire [2:0]   fold_b,
    output reg          pub_v,
    output reg  [31:0]  pub_data,
    output reg  [3:0]   pub_word,
    output reg  [2:0]   pub_out_slot,
    output reg  [15:0]  pub_tag,
    output reg          fault
);
    (* keep *) reg rq;
    always @(posedge clk) rq <= rst_n;
    reg         ev_q, ps_q, fs_q;
    reg [511:0] sum_q;
    reg [15:0]  tag_q;
    reg [2:0]   psl_q, fa_q, fb_q;
    always @(posedge clk or negedge rq)
        if (!rq) begin ev_q <= 1'b0; ps_q <= 1'b0; fs_q <= 1'b0; end
        else begin ev_q <= ev; ps_q <= pub_start; fs_q <= fold_start; end
    always @(posedge clk) begin sum_q <= sum; tag_q <= tag_d; psl_q <= pub_slot; fa_q <= fold_a; fb_q <= fold_b; end
    wire        m_pv_v, m_pub_v, m_fault;
    wire [511:0] m_pv_y;
    wire [15:0] m_pv_tag, m_pub_tag;
    wire [31:0] m_pub_data;
    wire [3:0]  m_pub_word;
    wire [2:0]  m_pub_slot;
    ot_hnx_att_pv_merge #(.L(16), .IL(8), .TAGW(16), .ALAT(7), .LV(LV), .MUT(MUT), .PUBLISH(1), .STORE(STORE)) u_pvm (
        .clk(clk), .rst_n(rq), .ev(ev_q), .sum(sum_q), .tag_d(tag_q),
        .pv_v(m_pv_v), .pv_y(m_pv_y), .pv_tag(m_pv_tag), .fault(m_fault),
        .pub_start(ps_q), .pub_slot(psl_q), .pub_v(m_pub_v), .pub_data(m_pub_data), .pub_word(m_pub_word),
        .pub_out_slot(m_pub_slot), .pub_tag(m_pub_tag), .fold_start(fs_q), .fold_a(fa_q), .fold_b(fb_q));
    always @(posedge clk or negedge rq)
        if (!rq) begin pub_v <= 1'b0; fault <= 1'b0; end
        else begin pub_v <= m_pub_v; fault <= fault | m_fault; end
    always @(posedge clk) begin pub_data <= m_pub_data; pub_word <= m_pub_word; pub_out_slot <= m_pub_slot; pub_tag <= m_pub_tag; end
endmodule
`default_nettype wire
