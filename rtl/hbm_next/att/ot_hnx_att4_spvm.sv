`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_att4_spvm: the SHARED 4-lane PV merge tile of the P = 4 attention leaf (hnx_rp4a4_spvm, HBM-NEXT-ATT4 A1
// 2026-10-19, PROG decision: one merge datapath a BF16 column, not one per lane).  ot_hnx_att4_smerge (16 FP32 adders,
// per-lane LV 3 flop rings = 24 words a lane, PUBLISH = 1) with every pin registered (owner 10-15), as ot_hnx_att4_pvm:
// +1 edge in, +1 edge out, fixed, counted by the compiler; the merge's turn is a free-running residue, so the fixed input
// delay only rotates which residue a slot owns (every lane's slot keeps one residue).  The reset lands in one kept
// register (RSTPIN style).  Lanes 0-1 enter on the N face, lanes 2-3 on the S face (beside the two lane pairs' tcl
// columns).  No credit / ready / stall; faults are sticky.  Replaces 4 x hnx_rp4a4_pvm per column.
// P3 (owner 10-19 0le, lane HBM-NEXT-P3-UNITS): NL = P query lanes, production default 3 (generic 3..4): lanes 0-1 on
// the N face (sum_lo / tag_lo, unchanged), lanes 2..NL-1 on the S face (sum_hi / tag_hi = (NL - 2) lanes); the merge
// datapath (16 adders) is the same, the per-lane LV 3 flop rings scale with NL.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_att4_spvm #(
    parameter integer NL  = 3,
    parameter integer LV  = 3,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NL-1:0]     ev,
    input  wire [1023:0]     sum_lo,     // lanes 0, 1 chunk sums (N face)
    input  wire [31:0]       tag_lo,
    input  wire [(NL-2)*512-1:0] sum_hi, // lanes 2 .. NL-1 chunk sums (S face)
    input  wire [(NL-2)*16-1:0]  tag_hi,
    input  wire              pub_start,
    input  wire [1:0]        pub_lane,
    input  wire [2:0]        pub_slot,
    output reg               pub_v,
    output reg  [31:0]       pub_data,
    output reg  [3:0]        pub_word,
    output reg  [2:0]        pub_out_slot,
    output reg  [1:0]        pub_out_lane,
    output reg  [15:0]       pub_tag,
    output reg               fault
);
    initial if (NL < 3 || NL > 4) $fatal(1, "ot_hnx_att4_spvm: 3 <= NL <= 4 (2 lanes N face + NL - 2 S face)");
    localparam integer RST_COPIES = `ifdef OT_HNX_ATT_SAFE_RESET 32 `else 1 `endif;
    (* keep = "true", ot_rst_split = 1 *) reg [RST_COPIES-1:0] rqv;
    wire rq = rqv[0];
    always @(posedge clk) rqv <= {RST_COPIES{rst_n}};
    reg [NL-1:0]     ev_q;
    reg              ps_q;
    reg [NL*512-1:0] sum_q;
    reg [NL*16-1:0]  tag_q;
    reg [1:0]        pl_q;
    reg [2:0]        psl_q;
    always @(posedge clk or negedge rq)
        if (!rq) begin ev_q <= {NL{1'b0}}; ps_q <= 1'b0; end
        else begin ev_q <= ev; ps_q <= pub_start; end
    always @(posedge clk) begin
        sum_q <= {sum_hi, sum_lo}; tag_q <= {tag_hi, tag_lo}; pl_q <= pub_lane; psl_q <= pub_slot;
    end
    wire m_pub_v, m_fault;
    wire [31:0] m_pub_data;
    wire [3:0]  m_pub_word;
    wire [2:0]  m_pub_slot;
    wire [1:0]  m_pub_lane;
    wire [15:0] m_pub_tag;
    ot_hnx_att4_smerge #(.NL(NL), .L(16), .TAGW(16), .ALAT(7), .LV(LV), .MUT(MUT), .PUBLISH(1)) u_sm (
        .clk(clk), .rst_n(rq), .ev(ev_q), .sum(sum_q), .tag_d(tag_q),
        .pv_v(), .pv_y(), .pv_tag(), .pv_lane(),
        .pub_start(ps_q), .pub_lane(pl_q), .pub_slot(psl_q), .pub_v(m_pub_v), .pub_data(m_pub_data),
        .pub_word(m_pub_word), .pub_out_slot(m_pub_slot), .pub_out_lane(m_pub_lane), .pub_tag(m_pub_tag), .fault(m_fault));
    always @(posedge clk or negedge rq)
        if (!rq) begin pub_v <= 1'b0; fault <= 1'b0; end
        else begin pub_v <= m_pub_v; fault <= fault | m_fault; end
    always @(posedge clk) begin
        pub_data <= m_pub_data; pub_word <= m_pub_word; pub_out_slot <= m_pub_slot; pub_out_lane <= m_pub_lane;
        pub_tag <= m_pub_tag;
    end
endmodule
`default_nettype wire
