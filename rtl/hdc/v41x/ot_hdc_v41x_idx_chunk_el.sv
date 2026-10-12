`timescale 1ns/1ps
// hgi-1010/g2 2026-10-10: the indexer's HARDENED ELEMENT = one 8-head chunk with its head base as an input strap (one view
// serves all 4 chunks of a score engine; the L4 column tap = 4 chunk macros + ot_hdc_v41x_idx_tail_l + the front end).
// el1011-hbm-idx 2026-10-11 (owner textbook audit, classes 1+2: the flat chunk_l was 146.7k flops on one clock root, 52k
// async-reset, CTS hold repair stalled at -70 ps): the chunk is now NKT columns of 8 hardened slices
// (ot_hdc_v41x_idx_hslice: one head x one key, identical, local clock tree each) on registered SYSTOLIC seams -- q beats and
// keys travel down a column, the running head sum travels with them; no chunk-wide broadcast, datapath reset-free, reset
// through ot_rst_relay.  Arithmetic is chunk_l's, bit for bit; latency is chunk_l's + XLAT = FPL + 16.
module ot_hdc_v41x_idx_chunk_el #(
    parameter integer NB  = 4,
    parameter integer NKT = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [7:0]            hb,
    input  wire                  ql_v,
    input  wire [7:0]            ql_head,
    input  wire [NB*128-1:0]     ql_codes,
    input  wire [NB*8-1:0]       ql_sc,
    input  wire [15:0]           ql_w,
    input  wire                  k_v,
    input  wire [NKT-1:0]        k_kv,
    input  wire [NKT*NB*136-1:0] k_key,
    output reg                   c_v,
    output reg  [NKT-1:0]        c_kv,
    output reg  [NKT*32-1:0]     c_sum,
    output reg  [NKT-1:0]        c_fault
);
    localparam integer HC = 8;
    localparam integer KW = NB * 136;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    localparam integer XLAT   = FPL + 16;
    localparam integer LATE   = LAT_T + FPL * (HC - 1) + XLAT;   // input register -> output register
    wire [NKT:0] rr;
    ot_rst_relay #(.REGIONS(NKT + 1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[NKT];
    // input registers
    reg rql_v; reg [7:0] rql_head; reg [NB*128-1:0] rql_codes; reg [NB*8-1:0] rql_sc; reg [15:0] rql_w;
    reg rv; reg [NKT-1:0] rkv; reg [NKT*KW-1:0] rkey; reg [7:0] hb_p; reg [7:0] hid [0:HC-1];
    integer i;
    always @(posedge clk) begin
        rql_v <= ql_v && rn; rql_head <= ql_head; rql_codes <= ql_codes; rql_sc <= ql_sc; rql_w <= ql_w;
        rv <= k_v && rn; rkv <= k_kv; rkey <= k_key; hb_p <= hb;
        for (i = 0; i < HC; i = i + 1) hid[i] <= hb_p + 8'(i);
    end
    wire [NKT:0] vl;
    ot_hdc_delay #(.W(NKT + 1), .D(LATE), .RESET(1)) u_vl (.clk(clk), .rst_n(rn), .d({rkv, rv}), .q(vl));
    genvar g, h;
    generate for (g = 0; g < NKT; g = g + 1) begin : g_col
        wire qv [0:HC]; wire [7:0] qh [0:HC]; wire [NB*128-1:0] qc [0:HC]; wire [NB*8-1:0] qs [0:HC]; wire [15:0] qw [0:HC];
        wire [KW-1:0] ky [0:HC]; wire [31:0] cs [0:HC]; wire cf [0:HC];
        assign qv[0] = rql_v; assign qh[0] = rql_head; assign qc[0] = rql_codes; assign qs[0] = rql_sc; assign qw[0] = rql_w;
        assign ky[0] = rkey[g*KW +: KW]; assign cs[0] = 32'd0; assign cf[0] = 1'b0;
        for (h = 0; h < HC; h = h + 1) begin : g_s
`ifdef OT_IDX_HSLICE_HARD
            ot_hdc_v41x_idx_hslice u_s (.clk(clk),
`else
            ot_hdc_v41x_idx_hslice #(.NB(NB), .FPL(FPL), .FML(FML), .QL(QL)) u_s (.clk(clk),
`endif .rst_n(rr[g]), .hid(hid[h]), .first(h == 0),
                .ql_v(qv[h]), .ql_head(qh[h]), .ql_codes(qc[h]), .ql_sc(qs[h]), .ql_w(qw[h]),
                .qo_v(qv[h+1]), .qo_head(qh[h+1]), .qo_codes(qc[h+1]), .qo_sc(qs[h+1]), .qo_w(qw[h+1]),
                .k_key(ky[h]), .ko_key(ky[h+1]), .cs_in(cs[h]), .cf_in(cf[h]), .cs_out(cs[h+1]), .cf_out(cf[h+1]));
        end
        always @(posedge clk) begin c_sum[32*g +: 32] <= cs[HC]; c_fault[g] <= cf[HC]; end
    end endgenerate
    always @(posedge clk) begin c_v <= vl[0] && rn; c_kv <= vl[NKT:1]; end
endmodule
