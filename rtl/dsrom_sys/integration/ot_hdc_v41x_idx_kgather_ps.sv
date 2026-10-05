`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41x_idx_kgather_ps: the candidate-block gather (rtl/hdc/v41x/ot_hdc_v41x_idx_kgather.sv,
// unchanged control ot_hdc_v41x_idx_kgctl and data ot_hdc_v41x_idx_kgdata, reused from that file)
// with a POSITION-SLOTTED candidate list (DS-ROM integration checkpoint, 2026-10-04).
//
// Why: the as-built unit holds ONE candidate list, written ahead through lw_* (the list is
// produced by the candidate-source layer L20 >= 4 layers earlier).  With the wavefront
// controller on (ot_rom_pkg_ctrl_wf WAVE = 1, WIN = 6) up to WIN positions of the same user are
// in flight one stage apart, and L20's list for position q+1 .. q+WIN-1 arrives before the
// re-index stages (L24 .. L36) have consumed position q's list (L20 -> L36 is ~32 stages, an
// interval II is ~1 stage occupancy).  A single list is then overwritten while still needed.
// LSW > 0 keeps 2^LSW lists (2^LSW >= WIN), the writer and each command naming the slot
// (position mod 2^LSW); the command latches its slot, so a later list may be written while the
// current one is being read.  LSW = 0 is the as-built single list (lw_slot / cmd_slot ignored).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kgather_ps #(
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer AW   = 28,
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer LMW  = 11,
    parameter integer DF   = 8,
    parameter integer LSW  = 0,          // list slots = 2^LSW (0: the as-built single list)
    localparam integer SLW = (LSW > 0) ? LSW : 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 lw_v,
    input  wire [SLW-1:0]       lw_slot,
    input  wire [LMW-1:0]       lw_addr,
    input  wire [LBW-1:0]       lw_blk,
    input  wire                 cmd_v,
    input  wire [SLW-1:0]       cmd_slot,
    input  wire [HW-1:0]        cmd_base,
    input  wire [9:0]           cmd_skip,
    input  wire [LMW:0]         cmd_n,
    output wire                 busy,
    output wire                 fault,
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
    output reg  [47:0]          cnt_keys_streamed,
    output reg  [47:0]          cnt_hbm_beats
);
    localparam integer NS = 1 << LSW;
    localparam integer RA = LMW - 1 + LSW;          // list read address bits (slot, pair)
    wire [1:0] dr_v;
    wire [$clog2(WB)-1:0] dr_slot;
    wire [13:0] dr_j;
    wire [9:0] dr_fc, dr_f0;
    wire [2*LBW-1:0] dr_blk;
    wire dr_ready, cbusy;
    assign busy = cbusy || o_valid;
    // candidate-list SRAM: two banks (even / odd entries), NS lists, 1W1R, synchronous read
    reg [LBW-1:0] lm_e [0:NS * (1 << (LMW - 1)) - 1];
    reg [LBW-1:0] lm_o [0:NS * (1 << (LMW - 1)) - 1];
    reg [LBW-1:0] lr_e, lr_o;
    wire          lr_re;
    wire [LMW-2:0] lr_addr;
    reg  [SLW-1:0] rd_slot;                          // the running command's list
    wire [RA-1:0] wa, ra;
    generate if (LSW > 0) begin : g_slot
        assign wa = {lw_slot, lw_addr[LMW-1:1]};
        assign ra = {rd_slot, lr_addr};
    end else begin : g_one
        assign wa = lw_addr[LMW-1:1];
        assign ra = lr_addr;
    end endgenerate
    always @(posedge clk) begin
        if (!rst_n) rd_slot <= {SLW{1'b0}};
        else if (cmd_v && !cbusy) rd_slot <= cmd_slot;   // the command is taken on this edge
        if (lw_v) begin
            if (lw_addr[0]) lm_o[wa] <= lw_blk;
            else            lm_e[wa] <= lw_blk;
        end
        if (lr_re) begin lr_e <= lm_e[ra]; lr_o <= lm_o[ra]; end
    end
    integer ck;
    reg [4:0] nko;
    reg [5:0] nbt;
    always @* begin
        nko = 0; nbt = 0;
        for (ck = 0; ck < 16; ck = ck + 1) nko = nko + o_kv[ck];
        for (ck = 0; ck < NPC; ck = ck + 1) nbt = nbt + rsp_v[ck];
    end
    always @(posedge clk)
        if (!rst_n) begin cnt_keys_streamed <= 0; cnt_hbm_beats <= 0; end
        else begin
            if (o_valid && o_ready) cnt_keys_streamed <= cnt_keys_streamed + nko;
            cnt_hbm_beats <= cnt_hbm_beats + nbt;
        end
    ot_hdc_v41x_idx_kgctl #(.NPC(NPC), .WB(WB), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
                            .LBW(LBW), .LMW(LMW), .DF(DF)) u_c (
        .clk(clk), .rst_n(rst_n), .lr_re(lr_re), .lr_addr(lr_addr), .lr_e(lr_e), .lr_o(lr_o),
        .cmd_v(cmd_v), .cmd_base(cmd_base), .cmd_skip(cmd_skip), .cmd_n(cmd_n), .busy(cbusy), .fault(fault),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat),
        .dr_v(dr_v), .dr_slot(dr_slot), .dr_j(dr_j), .dr_fc(dr_fc), .dr_f0(dr_f0), .dr_blk(dr_blk),
        .dr_ready(dr_ready));
    ot_hdc_v41x_idx_kgdata #(.NPC(NPC), .WB(WB), .TAGW(TAGW), .BEATW(BEATW), .DW(DW), .LBW(LBW)) u_d (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data),
        .dr_v(dr_v), .dr_slot(dr_slot), .dr_j(dr_j), .dr_fc(dr_fc), .dr_f0(dr_f0), .dr_blk(dr_blk),
        .dr_ready(dr_ready), .o_valid(o_valid), .o_ready(o_ready), .o_kv(o_kv), .o_key(o_key), .o_blk(o_blk));
endmodule
