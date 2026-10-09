`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// dsfd_engram_sink: the hardened Engram row sink of the S81 layer1e die (in
// eng_SE beside dsfd_engram_lkp).  ot_dsrom_engram_rowsink (NSLOT 8: the MTP
// verify's 6 positions + 2 in flight) with pin flops on the status and release
// inputs and on every output; the 4 beat sources keep the rowsink's skid
// (in_ready is a flop).  The 512-bit write port drives the prefetch buffer
// SRAM macros (12 x ot_sram_1r1w_256x256 at NSLOT 8), placed by the die.
// ---------------------------------------------------------------------------
module dsfd_engram_sink #(
    parameter integer NSLOT = 8,
    parameter integer SLW   = 3
) (
    input  wire              ck,
    input  wire              rst_n,
    input  wire [3:0]        in_v,
    output wire [3:0]        in_r,
    input  wire [19:0]       in_col,
    input  wire [11:0]       in_beat,
    input  wire [4*SLW-1:0]  in_slot,
    input  wire [1055:0]     in_d,
    input  wire [3:0]        st_v,
    input  wire [4*SLW-1:0]  st_slot,
    input  wire [3:0]        st_bad,
    output reg               wr_en,
    output reg  [SLW+7:0]    wr_addr,
    output reg  [511:0]      wr_data,
    output reg  [NSLOT-1:0]  rdy,
    output reg  [NSLOT-1:0]  perr,
    input  wire              rel_v,
    input  wire [SLW-1:0]    rel_slot
);
    reg [3:0]       stv_q, stb_q;
    reg [4*SLW-1:0] sts_q;
    reg             relv_q;
    reg [SLW-1:0]   rels_q;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin stv_q <= 4'd0; relv_q <= 1'b0; end
        else begin stv_q <= st_v; relv_q <= rel_v; end
    end
    always @(posedge ck) begin sts_q <= st_slot; stb_q <= st_bad; rels_q <= rel_slot; end
    wire               w_en;
    wire [SLW+7:0]     w_addr;
    wire [511:0]       w_data;
    wire [NSLOT-1:0]   s_rdy, s_perr;
    ot_dsrom_engram_rowsink #(.NSRC(4), .NC(24), .NSLOT(NSLOT)) u_s (
        .clk(ck), .rst_n(rst_n), .in_valid(in_v), .in_ready(in_r), .in_col(in_col), .in_beat(in_beat),
        .in_slot(in_slot), .in_data(in_d), .st_valid(stv_q), .st_slot(sts_q), .st_bad(stb_q),
        .wr_en(w_en), .wr_addr(w_addr), .wr_data(w_data), .rdy(s_rdy), .perr(s_perr),
        .rel_valid(relv_q), .rel_slot(rels_q));
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin wr_en <= 1'b0; rdy <= {NSLOT{1'b0}}; perr <= {NSLOT{1'b0}}; end
        else begin wr_en <= w_en; rdy <= s_rdy & ~({NSLOT{relv_q}} & (1 << rels_q)); perr <= s_perr; end
    end
    always @(posedge ck) begin wr_addr <= w_addr; wr_data <= w_data; end
endmodule
