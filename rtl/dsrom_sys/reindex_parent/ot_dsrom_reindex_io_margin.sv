`timescale 1ns/1ps
// Margin-first boundary for the RE-INDEX parent (owner rule 2026-10-06): every
// port of the hardened block is register-to-register. Inputs are captured in a
// flop at the pin; outputs are launched from flops; every valid/ready stream
// crosses a full register slice (skid buffer), so no ready is combinationally
// returned and no register sits inside a one-cycle loop. The wrapped parent
// files are unchanged. Bytes are moved, never transformed: order and content of
// every request, response and drain output are identical; only latency moves
// (+1 input edge on command/list/response, +1 output edge on requests/outputs).

// Full register slice: out_valid/out_data and in_ready are flop outputs.
module ot_dsrom_reindex_skid #(parameter integer W=1) (
    input  wire         clk, rst_n, flush,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [W-1:0] in_data,
    output reg          out_valid,
    input  wire         out_ready,
    output reg  [W-1:0] out_data
);
    reg         sv;          // skid entry
    reg [W-1:0] sd;
    assign in_ready = !sv;
    always @(posedge clk) begin
        if (!rst_n || flush) begin
            out_valid <= 1'b0; sv <= 1'b0;
        end else if (!out_valid || out_ready) begin
            if (sv) begin out_valid <= 1'b1; out_data <= sd; sv <= 1'b0; end
            else begin out_valid <= in_valid; if (in_valid) out_data <= in_data; end
        end else if (in_valid && !sv) begin
`ifdef OT_REINDEX_MARGIN_SKID_MUTANT
            sv <= 1'b1;              // negative control: skid keeps stale data
`else
            sv <= 1'b1; sd <= in_data;
`endif
        end
    end
endmodule

// Physical top: production control + list macros + drain header.
module ot_dsrom_reindex_parent_physctx_margin #(
    parameter integer SPLIT_COUNTERS = 0
) (
    input  wire          clk, rst_n,
    input  wire          lw_v,
    input  wire [2:0]    lw_slot,
    input  wire [10:0]   lw_addr,
    input  wire [13:0]   lw_blk,
    input  wire          cmd_v,
    input  wire [2:0]    cmd_slot,
    input  wire [19:0]   cmd_base,
    input  wire [9:0]    cmd_skip,
    input  wire [11:0]   cmd_n,
    output reg           busy,
    output reg           fault,
    output wire [31:0]   req_v,
    input  wire [31:0]   req_rdy,
    output wire [32*28-1:0] req_addr,
    output wire [32*4-1:0]  req_len,
    output wire [32*16-1:0] req_tag,
    input  wire [31:0]   rsp_v,
    output wire [31:0]   rsp_rdy,
    input  wire [32*16-1:0] rsp_tag,
    input  wire [32*4-1:0]  rsp_beat,
    output wire          o_valid,
    input  wire          o_ready,
    output wire [70:0]   o_metadata
);
    reg i_lw_v, i_cmd_v; reg [2:0] i_lw_slot, i_cmd_slot; reg [10:0] i_lw_addr; reg [13:0] i_lw_blk;
    reg [19:0] i_cmd_base; reg [9:0] i_cmd_skip; reg [11:0] i_cmd_n;
    reg [31:0] i_rsp_v; reg [32*16-1:0] i_rsp_tag; reg [32*4-1:0] i_rsp_beat;
    always @(posedge clk) begin
        if (!rst_n) begin i_lw_v <= 1'b0; i_cmd_v <= 1'b0; i_rsp_v <= 0; end
        else begin i_lw_v <= lw_v; i_cmd_v <= cmd_v; i_rsp_v <= rsp_v; end
        i_lw_slot <= lw_slot; i_lw_addr <= lw_addr; i_lw_blk <= lw_blk;
        i_cmd_slot <= cmd_slot; i_cmd_base <= cmd_base; i_cmd_skip <= cmd_skip; i_cmd_n <= cmd_n;
        i_rsp_tag <= rsp_tag; i_rsp_beat <= rsp_beat;
    end
    wire c_busy, c_fault, c_o_valid, c_o_ready;
    wire [31:0] c_req_v, c_req_rdy;
    wire [32*28-1:0] c_req_addr; wire [32*4-1:0] c_req_len; wire [32*16-1:0] c_req_tag;
    wire [70:0] c_o_metadata;
    ot_dsrom_reindex_parent_physctx #(.SPLIT_COUNTERS(SPLIT_COUNTERS)) u_core (
        .clk(clk), .rst_n(rst_n), .lw_v(i_lw_v), .lw_slot(i_lw_slot), .lw_addr(i_lw_addr), .lw_blk(i_lw_blk),
        .cmd_v(i_cmd_v), .cmd_slot(i_cmd_slot), .cmd_base(i_cmd_base), .cmd_skip(i_cmd_skip), .cmd_n(i_cmd_n),
        .busy(c_busy), .fault(c_fault), .req_v(c_req_v), .req_rdy(c_req_rdy), .req_addr(c_req_addr),
        .req_len(c_req_len), .req_tag(c_req_tag), .rsp_v(i_rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(i_rsp_tag),
        .rsp_beat(i_rsp_beat), .o_valid(c_o_valid), .o_ready(c_o_ready), .o_metadata(c_o_metadata));
    genvar p;
    generate for (p = 0; p < 32; p = p + 1) begin : g_req
        ot_dsrom_reindex_skid #(.W(48)) u_slice (
            .clk(clk), .rst_n(rst_n), .flush(c_fault),
            .in_valid(c_req_v[p]), .in_ready(c_req_rdy[p]),
            .in_data({c_req_addr[p*28 +: 28], c_req_len[p*4 +: 4], c_req_tag[p*16 +: 16]}),
            .out_valid(req_v[p]), .out_ready(req_rdy[p]),
            .out_data({req_addr[p*28 +: 28], req_len[p*4 +: 4], req_tag[p*16 +: 16]}));
    end endgenerate
    ot_dsrom_reindex_skid #(.W(71)) u_out (
        .clk(clk), .rst_n(rst_n), .flush(c_fault),
        .in_valid(c_o_valid), .in_ready(c_o_ready), .in_data(c_o_metadata),
        .out_valid(o_valid), .out_ready(o_ready), .out_data(o_metadata));
    // Registered status: a command at the pin, in the input register, or any
    // request/output still held in a slice keeps the block busy.
    always @(posedge clk) begin
        if (!rst_n) begin busy <= 1'b0; fault <= 1'b0; end
        else begin
            busy  <= c_busy || cmd_v || i_cmd_v || (|req_v) || o_valid;
            fault <= c_fault;
        end
    end
endmodule

// Exact-bench twin around the gather parent (control + real key data path).
module ot_dsrom_reindex_gather_parent_margin #(
    parameter integer SPLIT_COUNTERS = 0,
    parameter integer NPC = 32, WB = 128, AW = 28, HW = 20, TAGW = 16, LENW = 4, BEATW = 4,
    parameter integer DW = 256, LBW = 14, LMW = 11, DF = 8, LSW = 3,
    localparam integer SLW = (LSW > 0) ? LSW : 1
) (
    input  wire                 clk, rst_n,
    input  wire                 lw_v,
    input  wire [SLW-1:0]       lw_slot,
    input  wire [LMW-1:0]       lw_addr,
    input  wire [LBW-1:0]       lw_blk,
    input  wire                 cmd_v,
    input  wire [SLW-1:0]       cmd_slot,
    input  wire [HW-1:0]        cmd_base,
    input  wire [9:0]           cmd_skip,
    input  wire [LMW:0]         cmd_n,
    output reg                  busy,
    output reg                  fault,
    output wire [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output wire [NPC*AW-1:0]    req_addr,
    output wire [NPC*LENW-1:0]  req_len,
    output wire [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    input  wire [NPC*DW-1:0]    rsp_data,
    output wire                 o_valid,
    input  wire                 o_ready,
    output wire [15:0]          o_kv,
    output wire [16*544-1:0]    o_key,
    output wire [2*LBW-1:0]     o_blk,
    output wire [47:0]          cnt_keys_streamed,
    output wire [47:0]          cnt_hbm_beats
);
    localparam integer OW = 16 + 16*544 + 2*LBW;
    reg i_lw_v, i_cmd_v; reg [SLW-1:0] i_lw_slot, i_cmd_slot; reg [LMW-1:0] i_lw_addr; reg [LBW-1:0] i_lw_blk;
    reg [HW-1:0] i_cmd_base; reg [9:0] i_cmd_skip; reg [LMW:0] i_cmd_n;
    reg [NPC-1:0] i_rsp_v; reg [NPC*TAGW-1:0] i_rsp_tag; reg [NPC*BEATW-1:0] i_rsp_beat; reg [NPC*DW-1:0] i_rsp_data;
    always @(posedge clk) begin
        if (!rst_n) begin i_lw_v <= 1'b0; i_cmd_v <= 1'b0; i_rsp_v <= 0; end
        else begin i_lw_v <= lw_v; i_cmd_v <= cmd_v; i_rsp_v <= rsp_v; end
        i_lw_slot <= lw_slot; i_lw_addr <= lw_addr; i_lw_blk <= lw_blk;
        i_cmd_slot <= cmd_slot; i_cmd_base <= cmd_base; i_cmd_skip <= cmd_skip; i_cmd_n <= cmd_n;
        i_rsp_tag <= rsp_tag; i_rsp_beat <= rsp_beat; i_rsp_data <= rsp_data;
    end
    wire c_busy, c_fault, c_o_valid, c_o_ready;
    wire [NPC-1:0] c_req_v, c_req_rdy;
    wire [NPC*AW-1:0] c_req_addr; wire [NPC*LENW-1:0] c_req_len; wire [NPC*TAGW-1:0] c_req_tag;
    wire [15:0] c_kv; wire [16*544-1:0] c_key; wire [2*LBW-1:0] c_blk;
    ot_dsrom_reindex_gather_parent #(.SPLIT_COUNTERS(SPLIT_COUNTERS), .NPC(NPC), .WB(WB), .AW(AW), .HW(HW),
        .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW), .LBW(LBW), .LMW(LMW), .DF(DF), .LSW(LSW)) u_core (
        .clk(clk), .rst_n(rst_n), .lw_v(i_lw_v), .lw_slot(i_lw_slot), .lw_addr(i_lw_addr), .lw_blk(i_lw_blk),
        .cmd_v(i_cmd_v), .cmd_slot(i_cmd_slot), .cmd_base(i_cmd_base), .cmd_skip(i_cmd_skip), .cmd_n(i_cmd_n),
        .busy(c_busy), .fault(c_fault), .req_v(c_req_v), .req_rdy(c_req_rdy), .req_addr(c_req_addr),
        .req_len(c_req_len), .req_tag(c_req_tag), .rsp_v(i_rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(i_rsp_tag),
        .rsp_beat(i_rsp_beat), .rsp_data(i_rsp_data), .o_valid(c_o_valid), .o_ready(c_o_ready),
        .o_kv(c_kv), .o_key(c_key), .o_blk(c_blk),
        .cnt_keys_streamed(cnt_keys_streamed), .cnt_hbm_beats(cnt_hbm_beats));
    genvar p;
    generate for (p = 0; p < NPC; p = p + 1) begin : g_req
        ot_dsrom_reindex_skid #(.W(AW+LENW+TAGW)) u_slice (
            .clk(clk), .rst_n(rst_n), .flush(c_fault),
            .in_valid(c_req_v[p]), .in_ready(c_req_rdy[p]),
            .in_data({c_req_addr[p*AW +: AW], c_req_len[p*LENW +: LENW], c_req_tag[p*TAGW +: TAGW]}),
            .out_valid(req_v[p]), .out_ready(req_rdy[p]),
            .out_data({req_addr[p*AW +: AW], req_len[p*LENW +: LENW], req_tag[p*TAGW +: TAGW]}));
    end endgenerate
    ot_dsrom_reindex_skid #(.W(OW)) u_out (
        .clk(clk), .rst_n(rst_n), .flush(c_fault),
        .in_valid(c_o_valid), .in_ready(c_o_ready), .in_data({c_kv, c_key, c_blk}),
        .out_valid(o_valid), .out_ready(o_ready), .out_data({o_kv, o_key, o_blk}));
    always @(posedge clk) begin
        if (!rst_n) begin busy <= 1'b0; fault <= 1'b0; end
        else begin
            busy  <= c_busy || cmd_v || i_cmd_v || (|req_v) || o_valid;
            fault <= c_fault;
        end
    end
endmodule
