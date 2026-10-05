`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One pseudo-channel slice of the local K arbitration partition
// (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md): the per-PC logic of
// ot_chip_v41x_hbm_karb, with K arriving from its regional queue instead of a
// stack-wide broadcast.
//
// Unchanged from the monolithic arbiter: B/H pass-through, round-robin grant
// between eligible requesters (rr updates only when both are eligible and the
// PHY accepts), requester tag bit (1 = K), per-requester write-ownership
// counters (a write is granted only while the other requester has no write
// outstanding; wr_done goes to B first, as before), B responses local.
// Added (K_RD_FENCE = 1, the proposal's explicit same-PC fence): a K read is
// not eligible while a K write issued on this PC lacks its wr_done.  Older K
// writes still queued are necessarily ahead of it in the in-order K queues, so
// the issued-write counter is the whole dependency.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_slice #(
    parameter integer AW    = 28,
    parameter integer TAGW  = 16,
    parameter integer LENW  = 4,
    parameter integer BEATW = 4,
    parameter integer DW    = 256,
    parameter bit     K_RD_FENCE = 1'b1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // B
    input  wire                 b_v,
    output wire                 b_rdy,
    input  wire [AW-1:0]        b_addr,
    input  wire [LENW-1:0]      b_len,
    input  wire [TAGW-1:0]      b_tag,
    input  wire                 b_we,
    input  wire [DW-1:0]        b_wdata,
    input  wire [DW/8-1:0]      b_wstrb,
    output wire                 b_wr_done,
    output wire                 b_rsp_v,
    input  wire                 b_rsp_rdy,
    output wire [TAGW-1:0]      b_rsp_tag,
    output wire [BEATW-1:0]     b_rsp_beat,
    output wire [DW-1:0]        b_rsp_data,
    // K from the regional request queue head (k_v: head valid and addressed here)
    input  wire                 k_v,
    output wire                 k_take,
    input  wire [AW-1:0]        k_addr,
    input  wire [LENW-1:0]      k_len,
    input  wire [TAGW-1:0]      k_tag,
    input  wire                 k_we,
    input  wire [DW-1:0]        k_wdata,
    input  wire [DW/8-1:0]      k_wstrb,
    output wire                 k_wr_done,
    // K response towards the regional response queue (payload: the PC's r_* bus)
    output wire                 k_rsp_v,
    input  wire                 k_rsp_rdy,
    output wire [TAGW-1:0]      k_rsp_tag,
    output wire [BEATW-1:0]     k_rsp_beat,
    output wire [DW-1:0]        k_rsp_data,
    // the pseudo-channel
    output wire                 h_v,
    input  wire                 h_rdy,
    output wire [AW-1:0]        h_addr,
    output wire [LENW-1:0]      h_len,
    output wire [TAGW:0]        h_tag,
    output wire                 h_we,
    output wire [DW-1:0]        h_wdata,
    output wire [DW/8-1:0]      h_wstrb,
    input  wire                 h_wr_done,
    input  wire                 r_v,
    output wire                 r_rdy,
    input  wire [TAGW:0]        r_tag,
    input  wire [BEATW-1:0]     r_beat,
    input  wire [DW-1:0]        r_data,
    // status events
    output wire                 b_grant,
    output wire                 contend
);
    reg       rr;
    reg [7:0] bw_out, kw_out;
    wire k_ok = k_v && !(k_we && bw_out != 0) && !(K_RD_FENCE && !k_we && kw_out != 0);
    wire b_ok = b_v && !(b_we && kw_out != 0);
    wire gk = k_ok && (!b_ok || rr);
    wire gb = b_ok && !gk;
    assign h_v     = gk || gb;
    assign h_addr  = gk ? k_addr  : b_addr;
    assign h_len   = gk ? k_len   : b_len;
    assign h_tag   = gk ? {1'b1, k_tag} : {1'b0, b_tag};
    assign h_we    = gk ? k_we    : b_we;
    assign h_wdata = gk ? k_wdata : b_wdata;
    assign h_wstrb = gk ? k_wstrb : b_wstrb;
    assign b_rdy   = h_rdy && gb;
    assign k_take  = h_rdy && gk;
    assign b_wr_done = h_wr_done && bw_out != 0;
    assign k_wr_done = h_wr_done && bw_out == 0 && kw_out != 0;
    wire mine_k = r_tag[TAGW];
    assign b_rsp_v    = r_v && !mine_k;
    assign k_rsp_v    = r_v && mine_k;
    assign r_rdy      = mine_k ? k_rsp_rdy : b_rsp_rdy;
    assign b_rsp_tag  = r_tag[TAGW-1:0];
    assign b_rsp_beat = r_beat;
    assign b_rsp_data = r_data;
    assign k_rsp_tag  = r_tag[TAGW-1:0];
    assign k_rsp_beat = r_beat;
    assign k_rsp_data = r_data;
    assign b_grant = gb && h_rdy;
    assign contend = k_ok && b_ok;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            rr <= 1'b0; bw_out <= 8'd0; kw_out <= 8'd0;
        end else begin
            if (k_ok && b_ok && h_rdy) rr <= !gk;
            bw_out <= bw_out + {7'd0, gb && h_rdy && b_we} - {7'd0, b_wr_done};
            kw_out <= kw_out + {7'd0, gk && h_rdy && k_we} - {7'd0, k_wr_done};
        end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && ((bw_out == 8'hff && gb && h_rdy && b_we) || (kw_out == 8'hff && gk && h_rdy && k_we)))
        $error("ot_chip_v41x_karb_slice: write-owner counter overflow");
`endif
endmodule
