`timescale 1ns/1ps
// R-U2 pooled-indexer output bridge.  The pooled weight tile emits ordered
// (key, head) dot products.  This block collects one key's heads, joins its
// independently streamed mask/refusal bits in key order, and computes the
// golden's BF16 index score.  A producer holds m_v until m_ready; the
// FIFO covers the tile's in-flight keys and decouples metadata from dot timing.
// The four-stack HBM kmerge and the tile's rd_k/rd_x read network are upstream.
module ot_hdc_v41x_idx_pool_finish #(
    parameter integer G = 4,
    parameter integer M = 2,
    parameter integer IH = 32,
    parameter integer MD = 128              // metadata entries, power of two
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 m_v,
    output wire                 m_ready,
    input  wire                 m_keep,
    input  wire                 m_ref,
    input  wire                 w_v,
    input  wire [7:0]           w_head,
    input  wire [15:0]          w_w,
    input  wire [31:0]          w_qsc,
    input  wire                 p_v,
    input  wire [G-1:0]         p_smask,
    input  wire [G*M*32-1:0]    p_ys,
    input  wire [G*M-1:0]       p_fs,
    input  wire [G-1:0]         p_mask,
    input  wire [G*M*32-1:0]    p_y,
    input  wire [G*M-1:0]       p_f,
    output wire                 o_v,
    output wire [15:0]          o_score,
    output wire                 o_fault,
    output wire [47:0]          cnt_refused,
    output reg                  protocol_fault
);
    localparam integer MW = $clog2(MD);
    reg [1:0] meta [0:MD-1];
    reg [MW-1:0] wr, rd;
    reg [MW:0] count;
    wire k_v;
    wire [IH*32-1:0] k_score;
    wire [IH-1:0] k_fault;
    ot_hdc_v41x_idx_pcol #(.G(G), .M(M), .IH(IH)) col (
        .clk(clk), .rst_n(rst_n), .i_v(p_v), .i_smask(p_smask), .i_ys(p_ys), .i_fs(p_fs),
        .i_mask(p_mask), .i_y(p_y), .i_f(p_f),
        .k_v(k_v), .k_score(k_score), .k_fault(k_fault));

    wire pop = k_v && count != 0;
    wire push = m_v && m_ready;
    assign m_ready = count < MD || pop;
    wire [1:0] head_meta = meta[rd];
    wire [0:0] out_kv;
    ot_hdc_v41x_idx_hsum #(.IH(IH), .NKT(1), .NBQ(4)) hs (
        .clk(clk), .rst_n(rst_n), .w_v(w_v), .w_head(w_head), .w_w(w_w), .w_qsc(w_qsc),
        .i_v(k_v), .i_kv(1'b1), .i_ref(!pop || head_meta[1]), .i_keep(pop && head_meta[0]),
        .i_score(k_score), .i_fault(k_fault),
        .o_v(o_v), .o_kv(out_kv), .o_score(o_score), .o_fault(o_fault), .cnt_refused(cnt_refused));

    always @(posedge clk) begin
        if (!rst_n) begin
            wr <= 0;
            rd <= 0;
            count <= 0;
            protocol_fault <= 1'b0;
        end else begin
            if (k_v && !pop) protocol_fault <= 1'b1;
            if (push) begin meta[wr] <= {m_ref, m_keep}; wr <= wr + 1'b1; end
            if (pop) rd <= rd + 1'b1;
            case ({push, pop})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: count <= count;
            endcase
        end
    end
endmodule
