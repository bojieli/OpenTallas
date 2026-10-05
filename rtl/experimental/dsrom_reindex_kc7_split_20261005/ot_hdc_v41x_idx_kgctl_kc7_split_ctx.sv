module ot_reindex_ctx_launch_kc7_split #(parameter integer N = 1) (
    input  wire         clk,
    input  wire [31:0]  din,
    output reg  [N-1:0] q
);
    integer i;
    always @(posedge clk) for (i = 0; i < N; i = i + 1) q[i] <= q[i] ^ din[i % 32];
endmodule

module ot_reindex_ctx_capture_kc7_split #(parameter integer N = 1) (
    input  wire         clk,
    input  wire [N-1:0] d,
    output wire [7:0]   so
);
    reg [N-1:0] q;
    always @(posedge clk) q <= d;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_x
        wire [N-1:0] m;
        genvar b;
        for (b = 0; b < N; b = b + 1) begin : g_b
            assign m[b] = (b % 8 == g) ? q[b] : 1'b0;
        end
        assign so[g] = ^m;
    end endgenerate
endmodule

module ot_hdc_v41x_idx_kgctl_kc7_split_ctx #(
    parameter integer OPT_KC6 = 1,
    parameter integer OPT_KC7 = 0,
    parameter integer OPT_SPLIT_CMP = 0,
    parameter integer NPC = 32, WB = 128, AW = 28, HW = 20, TAGW = 16, LENW = 4, BEATW = 4,
    parameter integer LBW = 14, LMW = 11, DF = 8
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] din,
    output wire [7:0]  so
);
    localparam integer SW = $clog2(WB);
    localparam integer NI = 2*LBW + 1 + HW + 10 + (LMW+1) + NPC + NPC + NPC*TAGW + NPC*BEATW + 1;
    localparam integer NO = 1 + (LMW-1) + 1 + 1 + NPC + NPC*AW + NPC*LENW + NPC*TAGW + NPC
                          + 2 + SW + 14 + 10 + 10 + 2*LBW;
    reg rst_q;
    always @(posedge clk) rst_q <= rst_n;
    wire [NI-1:0] i;
    wire [NO-1:0] o;
    ot_reindex_ctx_launch_kc7_split #(.N(NI)) u_l (.clk(clk), .din(din), .q(i));
    wire [LBW-1:0] lr_e, lr_o;
    wire cmd_v, dr_ready, lr_re, busy, fault;
    wire [HW-1:0] cmd_base;
    wire [9:0] cmd_skip;
    wire [LMW:0] cmd_n;
    wire [NPC-1:0] req_rdy, rsp_v, req_v, rsp_rdy;
    wire [NPC*TAGW-1:0] rsp_tag, req_tag;
    wire [NPC*BEATW-1:0] rsp_beat;
    wire [LMW-2:0] lr_addr;
    wire [NPC*AW-1:0] req_addr;
    wire [NPC*LENW-1:0] req_len;
    wire [1:0] dr_v;
    wire [SW-1:0] dr_slot;
    wire [13:0] dr_j;
    wire [9:0] dr_fc, dr_f0;
    wire [2*LBW-1:0] dr_blk;
    assign {lr_e, lr_o, cmd_v, cmd_base, cmd_skip, cmd_n, req_rdy, rsp_v, rsp_tag, rsp_beat, dr_ready} = i;
    ot_hdc_v41x_idx_kgctl_kc7_split #(.OPT_KC6(OPT_KC6), .OPT_KC7(OPT_KC7), .OPT_SPLIT_CMP(OPT_SPLIT_CMP), .NPC(NPC), .WB(WB), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
                            .LBW(LBW), .LMW(LMW), .DF(DF)) u_dut (
        .clk(clk), .rst_n(rst_q), .lr_re(lr_re), .lr_addr(lr_addr), .lr_e(lr_e), .lr_o(lr_o),
        .cmd_v(cmd_v), .cmd_base(cmd_base), .cmd_skip(cmd_skip), .cmd_n(cmd_n), .busy(busy), .fault(fault),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat),
        .dr_v(dr_v), .dr_slot(dr_slot), .dr_j(dr_j), .dr_fc(dr_fc), .dr_f0(dr_f0), .dr_blk(dr_blk),
        .dr_ready(dr_ready));
    assign o = {lr_re, lr_addr, busy, fault, req_v, req_addr, req_len, req_tag, rsp_rdy,
                dr_v, dr_slot, dr_j, dr_fc, dr_f0, dr_blk};
    ot_reindex_ctx_capture_kc7_split #(.N(NO)) u_c (.clk(clk), .d(o), .so(so));
endmodule
