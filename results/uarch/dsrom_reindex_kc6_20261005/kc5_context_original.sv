`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Physical-context harnesses (route vehicles only, never instantiated by the design) for the
// re-index candidate fixes: ot_hdc_v41x_sel_mdrop (MDROP=1) and ot_hdc_v41x_idx_kgctl.
//
// In the die the units sit between registered neighbours on the same clock tree (index
// scorer -> drop -> select; list SRAM / HBM channel queues / drain <-> kgctl), not behind
// thousands of chip pins.  Routed bare, mdrop's 4,847 ports force a 465 um perimeter
// (PPL-0024 at 35% utilisation) and the stretched clock tree turns every port-to-flop path
// into a hold failure against an ideal input edge (RSZ-0060 at 10%).  Here every DUT input
// is launched by a harness flop and every DUT output is captured by one, all on the DUT's
// clock tree, so the DUT boundary is timed register to register in both corners (SS setup,
// FF hold) with real wire.  Harness flops toggle from a 32-bit port bus (distinct D per
// flop, so synthesis cannot merge them); outputs are XOR-folded onto 8 pins.  Ports of the
// harness are false-pathed (--false-path-io); only harness <-> DUT and DUT-internal paths
// are timed.  Paths combinational through the DUT boundary (mdrop in_ready from out_ready;
// kgctl lr_re/lr_addr, req_rdy -> issue, dr_ready -> drain) are reported separately and
// must keep the 20% neighbour budget (tools/dsrom_reindex_close.py), except mdrop's out_ready, which is
// generated here by the downstream select slice's own in_ready logic (the neighbour as built).
// ---------------------------------------------------------------------------
module ot_reindex_ctx_launch #(parameter integer N = 1) (
    input  wire         clk,
    input  wire [31:0]  din,
    output reg  [N-1:0] q
);
    integer i;
    always @(posedge clk) for (i = 0; i < N; i = i + 1) q[i] <= q[i] ^ din[i % 32];
endmodule

module ot_reindex_ctx_capture #(parameter integer N = 1) (
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

module ot_hdc_v41x_sel_mdrop_ctx #(
    parameter integer Q = 4, W = 16, IW = 20, KW = 10, MDROP = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] din,
    output wire [7:0]  so
);
    // out_ready is the select slice's in_ready (ot_hdc_v41x_sel_slice.sv:147) over launch flops of its
    // state: (init == 0) && !last_seen && ((ph == P_ING && r_ing && !r_stop) || (sw_st == SW_RD && sw_rp))
    localparam integer NS = 3 + 1 + 3 + 1 + 1 + 3 + 1;                          // per quarter
    localparam integer NI = Q + Q + Q*W + Q*W + Q*W*16 + Q*W*IW + KW + Q*NS;
    localparam integer NO = Q + Q + Q + Q*W + Q*W*16 + Q*W*IW + KW + 1;
    reg rst_q;
    always @(posedge clk) rst_q <= rst_n;
    wire [NI-1:0] i;
    wire [NO-1:0] o;
    ot_reindex_ctx_launch #(.N(NI)) u_l (.clk(clk), .din(din), .q(i));
    wire [Q-1:0] in_valid, in_last, out_ready, in_ready, out_valid, out_last;
    wire [Q*W-1:0] in_lv, in_keep, out_lv;
    wire [Q*W*16-1:0] in_val, out_val;
    wire [Q*W*IW-1:0] in_idx, out_idx;
    wire [KW-1:0] in_k, out_k;
    wire short;
    wire [Q*NS-1:0] sl;
    assign {in_valid, in_last, in_lv, in_keep, in_val, in_idx, in_k, sl} = i;
    genvar gq;
    generate for (gq = 0; gq < Q; gq = gq + 1) begin : g_rdy
        wire [NS-1:0] t = sl[gq*NS +: NS];
        wire [2:0] init = t[2:0], ph = t[6:4], sw_st = t[11:9];
        wire last_seen = t[3], r_ing = t[7], r_stop = t[8], sw_rp = t[12];
        assign out_ready[gq] = (init == 3'd0) && !last_seen &&
                               (((ph == 3'd0) && r_ing && !r_stop) || ((sw_st == 3'd1) && sw_rp));
    end endgenerate
    ot_hdc_v41x_sel_mdrop #(.Q(Q), .W(W), .IW(IW), .KW(KW), .MDROP(MDROP)) u_dut (
        .clk(clk), .rst_n(rst_q), .in_valid(in_valid), .in_ready(in_ready), .in_last(in_last), .in_lv(in_lv),
        .in_keep(in_keep), .in_val(in_val), .in_idx(in_idx), .in_k(in_k),
        .out_valid(out_valid), .out_ready(out_ready), .out_last(out_last), .out_lv(out_lv), .out_val(out_val),
        .out_idx(out_idx), .out_k(out_k), .short(short));
    assign o = {in_ready, out_valid, out_last, out_lv, out_val, out_idx, out_k, short};
    ot_reindex_ctx_capture #(.N(NO)) u_c (.clk(clk), .d(o), .so(so));
endmodule

module ot_hdc_v41x_idx_kgctl_ctx #(
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
    ot_reindex_ctx_launch #(.N(NI)) u_l (.clk(clk), .din(din), .q(i));
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
    ot_hdc_v41x_idx_kgctl #(.NPC(NPC), .WB(WB), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
                            .LBW(LBW), .LMW(LMW), .DF(DF)) u_dut (
        .clk(clk), .rst_n(rst_q), .lr_re(lr_re), .lr_addr(lr_addr), .lr_e(lr_e), .lr_o(lr_o),
        .cmd_v(cmd_v), .cmd_base(cmd_base), .cmd_skip(cmd_skip), .cmd_n(cmd_n), .busy(busy), .fault(fault),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat),
        .dr_v(dr_v), .dr_slot(dr_slot), .dr_j(dr_j), .dr_fc(dr_fc), .dr_f0(dr_f0), .dr_blk(dr_blk),
        .dr_ready(dr_ready));
    assign o = {lr_re, lr_addr, busy, fault, req_v, req_addr, req_len, req_tag, rsp_rdy,
                dr_v, dr_slot, dr_j, dr_fc, dr_f0, dr_blk};
    ot_reindex_ctx_capture #(.N(NO)) u_c (.clk(clk), .d(o), .so(so));
endmodule
