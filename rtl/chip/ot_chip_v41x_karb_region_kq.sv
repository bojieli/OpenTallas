`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// K side of one four-PC region of the local K arbitration partition
// (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md).  Physically it sits between
// the region's four slices and the stack trunk:
//   request   a two-entry registered queue (kq_rdy = its registered room); its
//             head is presented to the one slice it addresses and pops when
//             that slice's PHY handshake takes it (in order);
//   response  captures the lowest-index local slice holding a K response into
//             a two-entry registered queue while it has room, then sends the
//             head up the trunk whenever it holds a credit of the stack
//             endpoint's per-region queue (CREDITS entries; a credit returns,
//             registered, when the endpoint pops that queue);
//   events    registered OR of the slices' K write completions and registered
//             per-cycle counts of B grants and arbitration conflicts.
// Every trunk-facing output is a register or a function of this region's own
// registers, and every trunk input lands in a register here, so no
// combinational path runs root -> region -> root.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_region_kq #(
    parameter integer AW      = 28,
    parameter integer TAGW    = 16,
    parameter integer LENW    = 4,
    parameter integer BEATW   = 4,
    parameter integer DW      = 256,
    parameter integer CREDITS = 3
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // trunk: request
    input  wire                 kq_v,
    output wire                 kq_rdy,
    input  wire [1:0]           kq_lpc,
    input  wire [AW-1:0]        kq_addr,
    input  wire [LENW-1:0]      kq_len,
    input  wire [TAGW-1:0]      kq_tag,
    input  wire                 kq_we,
    input  wire [DW-1:0]        kq_wdata,
    input  wire [DW/8-1:0]      kq_wstrb,
    // trunk: response
    output wire                 ks_v,
    output wire [TAGW-1:0]      ks_tag,
    output wire [BEATW-1:0]     ks_beat,
    output wire [DW-1:0]        ks_data,
    input  wire                 ks_cr,
    // trunk: events
    output reg                  k_wr_done,
    output reg  [2:0]           b_grant_n,
    output reg  [2:0]           contend_n,
    // slices: request head
    output wire [3:0]           s_kv,
    input  wire [3:0]           s_take,
    output wire [AW-1:0]        s_addr,
    output wire [LENW-1:0]      s_len,
    output wire [TAGW-1:0]      s_tag,
    output wire                 s_we,
    output wire [DW-1:0]        s_wdata,
    output wire [DW/8-1:0]      s_wstrb,
    // slices: responses
    input  wire [3:0]           s_krv,
    output wire [3:0]           s_krdy,
    input  wire [4*TAGW-1:0]    s_rtag,
    input  wire [4*BEATW-1:0]   s_rbeat,
    input  wire [4*DW-1:0]      s_rdata,
    // slices: events
    input  wire [3:0]           s_kwd,
    input  wire [3:0]           s_bg,
    input  wire [3:0]           s_ct
);
    localparam integer QW = 2 + AW + LENW + TAGW + 1 + DW + DW / 8;
    localparam integer RW = TAGW + BEATW + DW;
    localparam integer CW = $clog2(CREDITS + 1);
    wire          hq_v; wire [QW-1:0] hq_d; wire [1:0] h_lpc;
    assign {h_lpc, s_addr, s_len, s_tag, s_we, s_wdata, s_wstrb} = hq_d;
    assign s_kv = {4{hq_v}} & (4'b1 << h_lpc);
    ot_chip_v41x_karb_q2 #(.W(QW)) u_rq (
        .clk(clk), .rst_n(rst_n), .in_v(kq_v), .in_rdy(kq_rdy),
        .in_d({kq_lpc, kq_addr, kq_len, kq_tag, kq_we, kq_wdata, kq_wstrb}),
        .out_v(hq_v), .out_rdy(|s_take), .out_d(hq_d));
    // capture
    reg  [1:0] csel; reg cany;
    wire       cap_rdy, sq_v;
    integer i;
    always @(*) begin
        csel = 2'd0; cany = 1'b0;
        for (i = 3; i >= 0; i = i - 1) if (s_krv[i]) begin csel = 2'(i); cany = 1'b1; end
    end
    assign s_krdy = {4{cap_rdy}} & (4'b1 << csel);
    reg [CW-1:0] cred;
    assign ks_v = sq_v && cred != 0;
    ot_chip_v41x_karb_q2 #(.W(RW)) u_sq (
        .clk(clk), .rst_n(rst_n), .in_v(cany), .in_rdy(cap_rdy),
        .in_d({s_rtag[csel*TAGW +: TAGW], s_rbeat[csel*BEATW +: BEATW], s_rdata[csel*DW +: DW]}),
        .out_v(sq_v), .out_rdy(ks_v), .out_d({ks_tag, ks_beat, ks_data}));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cred <= CW'(CREDITS); k_wr_done <= 1'b0; b_grant_n <= 3'd0; contend_n <= 3'd0;
        end else begin
            cred <= cred - CW'(ks_v) + CW'(ks_cr);
            k_wr_done <= |s_kwd;
            b_grant_n <= 3'(s_bg[0]) + 3'(s_bg[1]) + 3'(s_bg[2]) + 3'(s_bg[3]);
            contend_n <= 3'(s_ct[0]) + 3'(s_ct[1]) + 3'(s_ct[2]) + 3'(s_ct[3]);
        end
endmodule
