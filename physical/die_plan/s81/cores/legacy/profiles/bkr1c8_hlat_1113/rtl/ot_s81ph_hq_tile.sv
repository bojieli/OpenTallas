`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// S81-TOPK7 (2026-10-20) HIERARCHICAL QUARTER tile dsfd_selt_q_hq (opt-in OT_S81PH_SEL_HQ; dsdv_bksel_q binds it).
// Same ports, function and EVERY edge as dsfd_selt_q2 #(DM 4, CMP_RETIME 1, PIPE2 1, QIO 1, ILD 1, FRPR 1) with the
// successor defines (INDEXED13, FIFO_SRAM, P192, SUCC, FAN32, ACC32); structural changes only (see
// ot_s81ph_hq_slice.sv for the slice):
//  T1 reset: the quarter's flops reset from the rst port; the kit LANDS it at the face in two registered stages with
//     balanced kept copies (reset_landing first_copies / copies + reset_relay_split max_loads 32: ot_pin_regs.tcl /
//     ot_rst_copies.tcl), so no reset net has more than 32 loads.  Datapath / payload registers carry no reset: status
//     payload (gsum / gbin), selected-beat payload, command data fields (each is overwritten every edge from reset-held
//     sources while the reset is asserted).  The 16 hardened histogram banks land their own reset (rst_l0 / rst_l1 +
//     20 leaves).  Same release depth as the RST64 tile (2 landed stages).
//  T2 lane decode (ot_s81ph_hq_in): the type-8 select is held in kept copies from FOUR distinct decodes that agree on
//     every legal type (8 -> 1; 1 / 2 / 6 -> 0) and differ only on illegal types 9 / 10 / 12, which never produce a beat
//     (fault path; the captured data of such a word is never consumed): each copy steers <= 10 data bits; the position
//     cur has 4 kept copies (4 lanes of index adders each).
//  T3 x stage: kept sign copies per lane / key nibble (in_sg); command copies of c_T / c_Bt per 4-lane group and of
//     c_cg / c_fg per histogram bank, all registered from the same D as cq.
//  T4 line memory ot_s81ph_hq_mem2: each depth bank of macros has its own write-data register copy (launched beside its
//     three macros).
// ---------------------------------------------------------------------------------------------------------------

module ot_s81ph_hq_in #(
    // DIE-S81-51/RF-H 11-03: FACE 1 = lane is already a face flop (dsdv_bksel_q RFH 1): the type-8 selects and the
    // position copies s0c / s0d are kept registers decoded from lane at the s0 edge (same edge, same values as the raw
    // form), so no s0 type bit broadcasts to the 53 payload muxes.  FACE 0 = the PINCOPY profile form (unchanged).
    parameter integer FACE = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [514:0] lane,
    output reg          b_v,
    output reg  [15:0]  b_lv,
    output reg  [255:0] b_val,
    output reg  [319:0] b_idx,
    output reg          b_last,
    output reg          h_v,
    output reg  [9:0]   h_k,
    output reg  [7:0]   h_tag,
    output reg  [1:0]   h_q,
    output reg          act,
    output reg  [1:0]   act_q,
    output reg          e_fmt,
    output reg          e_orphan,
    output reg          e_link
);
    localparam integer DW = 482;
    localparam integer UW = DW + 15;
    wire [UW-1:0] u = {lane[514], lane[513], lane[512:501], lane[DW:1], lane[0]};
    reg  [UW-1:0] s0;
    always @(posedge clk) s0 <= u;
    // kept copy of {type, valid} for the position next state (cur_n): the case decode keeps s0's own bits
    // Explicit PINCOPY parent profile: one first-capture flop per external bit.
    // Existing s0 owns this edge; aliases retain exact type/valid values.
    wire [4:0] s0c, s0d;
    (* keep = "true" *) reg [4:0] s0c_r, s0d_r;           // FACE 1: one per half of cur (unloaded at FACE 0)
    always @(posedge clk) begin s0c_r <= {lane[512:509], lane[0]}; s0d_r <= {lane[512:509], lane[0]}; end
    assign s0c = FACE != 0 ? s0c_r : {s0[DW+12:DW+9], s0[0]};
    assign s0d = FACE != 0 ? s0d_r : {s0[DW+12:DW+9], s0[0]};
    (* keep = "true" *) reg [17:0] lane_spare_capture;
    always @(posedge clk) lane_spare_capture <= lane[500:483];
    // Type-8 select decodes retain their existing second-edge consumers.
    // FACE 1: registered selects from the face-flopped lane (the non-RAW form), whatever the RAW define says
    localparam integer NF = 53;
    wire [NF-1:0] f, f_raw, f_reg;
    genvar fs;
    assign f = FACE != 0 ? f_reg : f_raw;
    wire [3:0] tq = lane[512:509];
    wire [3:0] decq = {tq[3] & ~tq[1] & ~tq[0],         // {8, 12}
                       tq[3] & ~tq[2] & ~tq[0],         // {8, 10}
                       tq[3] & ~tq[2] & ~tq[1],         // {8, 9}
                       tq == 4'd8};
    generate for (fs = 0; fs < NF; fs = fs + 1) begin : g_fr
        (* keep = "true" *) reg r;
`ifdef OT_RFH_MUT_SEL     // bench mutant: select copy 9 (lane 2 val hi) takes the inverted decode
        always @(posedge clk) r <= (fs == 9) ? ~decq[fs % 4] : decq[fs % 4];
`else
        always @(posedge clk) r <= decq[fs % 4];
`endif
        assign f_reg[fs] = r;
    end endgenerate
`ifdef OT_S81PH_HQ_INPUT_RAW
    // Profile-only boundary successor: existing s0 is the single raw-type capture;
    // decode locally at the unchanged second-stage payload mux. Actual mapped
    // fanout must pass the normal <=64 data-load gate before floorplan.
    localparam integer NT = 14;
    wire [4*NT-1:0] raw_type = {NT{s0[DW+12:DW+9]}};
`ifdef OT_S81PH_HQ_INPUT_RAW_MUT
    reg [3:0] raw_type_prev;
    always @(posedge clk) raw_type_prev <= lane[512:509];
`endif
    generate for (fs = 0; fs < NF; fs = fs + 1) begin : g_f
        wire [3:0] t = raw_type[4*(fs / 4) +: 4];
        wire [3:0] dec = {t[3] & ~t[1] & ~t[0],
                          t[3] & ~t[2] & ~t[0],
                          t[3] & ~t[2] & ~t[1],
                          t == 4'd8};
`ifdef OT_S81PH_HQ_INPUT_RAW_MUT
        assign f_raw[fs] = (`OT_S81PH_HQ_INPUT_RAW_MUT == 1) ? ~dec[fs % 4] : dec[fs % 4];
`else
        assign f_raw[fs] = dec[fs % 4];
`endif
    end endgenerate
`else
    assign f_raw = f_reg;      // non-RAW build: the registered selects are the form
`endif
    wire          v   = s0[0];
    wire [481:0]  d   = s0[DW:1];
    wire [7:0]    tag = s0[DW+8:DW+1];
    wire [3:0]    t4  = s0[DW+12:DW+9];
    reg  [19:0]   cur;
    wire [20:0]   nxt = {1'b0, cur} + 21'd16;
    // position next state (the original update rule) and its kept copies (index adders, 4 lanes each)
    wire [19:0]   cur_n;
    assign cur_n[9:0]   = !s0c[0] ? cur[9:0] : (s0c[4:1] == 4'd1 || s0c[4:1] == 4'd6) ? d[9:0] :
                          (s0c[4:1] == 4'd2 && act) ? nxt[9:0] : cur[9:0];
    assign cur_n[19:10] = !s0d[0] ? cur[19:10] : (s0d[4:1] == 4'd1 || s0d[4:1] == 4'd6) ? d[19:10] :
                          (s0d[4:1] == 4'd2 && act) ? nxt[19:10] : cur[19:10];
`ifdef OT_BKQ_FO8
    localparam integer NCUR = 5;
`else
    localparam integer NCUR = 4;
`endif
    wire [NCUR*20-1:0] curc;
    generate for (fs = 0; fs < NCUR; fs = fs + 1) begin : g_cur
        (* keep = "true" *) reg [19:0] r;
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= 20'd0; else r <= cur_n;
        assign curc[20*fs +: 20] = r;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            b_v <= 1'b0; h_v <= 1'b0; act <= 1'b0; act_q <= 2'd0; cur <= 20'd0;
            e_fmt <= 1'b0; e_orphan <= 1'b0; e_link <= 1'b0;
        end else begin
            b_v <= 1'b0; h_v <= 1'b0; e_fmt <= 1'b0; e_orphan <= 1'b0;
            e_link <= s0[UW-1] | (v & ~s0[UW-2]);
            cur <= cur_n;
            if (v) begin
                case (t4)
                    4'd1: begin h_v <= 1'b1; act <= 1'b1; act_q <= d[31:30]; end
                    4'd6: begin if (!act) e_orphan <= 1'b1; end
                    4'd8: begin
                        if (!act) e_orphan <= 1'b1;
                        else begin b_v <= 1'b1; if (d[481]) act <= 1'b0; end
                    end
                    4'd2: begin
                        if (!act) e_orphan <= 1'b1;
                        else begin
                            b_v <= 1'b1;
                            if (nxt[20] && !d[272]) e_fmt <= 1'b1;
                            if (d[272]) act <= 1'b0;
                        end
                    end
                    default: e_fmt <= 1'b1;
                endcase
            end
        end
    end
    integer l;
    always @(posedge clk) begin
        b_lv   <= f[52] ? {3'b000, d[480:468]} : d[271:256];
        b_last <= f[52] ? d[481] : d[272];
        for (l = 0; l < 16; l = l + 1) begin
            if (l < 13) begin
                b_val[16*l +: 8]      <= f[4*l + 0] ? d[36*l +: 8]        : d[16*l +: 8];
                b_val[16*l + 8 +: 8]  <= f[4*l + 1] ? d[36*l + 8 +: 8]    : d[16*l + 8 +: 8];
                b_idx[20*l +: 10]     <= f[4*l + 2] ? d[36*l + 16 +: 10]  : 10'(curc[20*(l/4) +: 20] + l[19:0]);
                b_idx[20*l + 10 +: 10] <= f[4*l + 3] ? d[36*l + 26 +: 10] : 10'((curc[20*(l/4) +: 20] + l[19:0]) >> 10);
            end else begin
                b_val[16*l +: 16] <= d[16*l +: 16];
                b_idx[20*l +: 20] <= curc[20*((NCUR == 5 && l >= 14) ? 4 : l/4) +: 20] + l[19:0];
            end
        end
        h_k <= d[29:20];
        h_tag <= tag;
        h_q <= d[31:30];
    end
endmodule

// line memory: as ot_s81ph_sel_mem2 (OT_SRAM_P192 + OT_S81PH_SEL_SUCC) with one write-data copy per depth bank
module ot_s81ph_hq_mem2 (
    input  wire         clk,
    input  wire         we,
    input  wire [7:0]   waddr,
    input  wire [591:0] wdata0,       // depth bank 0 copy
    input  wire [591:0] wdata1,       // depth bank 1 copy (identical value)
    input  wire         re,
    input  wire [7:0]   raddr,
    output wire [591:0] rdata
);
    wire [2*768-1:0] wd = {176'd0, wdata1, 176'd0, wdata0};
    wire [767:0] rd [0:1];
    reg  [767:0] q [0:1];
    genvar b, w;
    generate for (b = 0; b < 2; b = b + 1) begin : g_b
        for (w = 0; w < 3; w = w + 1) begin : g_w
            ot_sram_1r1w_128x256_m1_r2c2_p192_mir u_m (.clk(clk), .r_ce_in(re && raddr[7] == b), .r_addr_in(raddr[6:0]),
                .rd_out(rd[b][256*w +: 256]), .w_ce_in(we && waddr[7] == b), .w_addr_in(waddr[6:0]),
                .wd_in(wd[768*b + 256*w +: 256]), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00),
                .cr_sel(16'd0));
        end
        always @(posedge clk) q[b] <= rd[b];
    end endgenerate
    localparam integer NG = 37;
`ifdef OT_BKQ_FO8
    localparam integer NB1 = 6, GB1 = 7;     // S81-BKSEL-RF7: 6 kept copies, <= 7 groups (14 loads over 2 outputs: fanout <= 8)
`else
    localparam integer NB1 = 3, GB1 = 13;
`endif
    wire [NB1-1:0] b1c;
    wire [591:0] rsel;
    genvar c, g;
    for (c = 0; c < NB1; c = c + 1) begin : g_b1c
        (* keep = "true" *) reg r;
        always @(posedge clk) if (re) r <= raddr[7];
        assign b1c[c] = r;
    end
    for (g = 0; g < NG; g = g + 1) begin : g_oh
        (* keep = "true" *) reg oh0, oh1;
        always @(posedge clk) begin oh0 <= ~b1c[g / GB1]; oh1 <= b1c[g / GB1]; end
        assign rsel[16*g +: 16] = (q[0][16*g +: 16] & {16{oh0}}) | (q[1][16*g +: 16] & {16{oh1}});
    end
    assign rdata = rsel;
endmodule

module dsfd_selt_q_hq #(
    parameter integer DM  = 4,
    parameter integer MUT = 0,         // slice witnesses (ot_s81ph_hq_slice MUT)
    // DIE-S81-51/RF-H 11-03: FACE 1 = rst is a face flop (dsdv_bksel_q RFH 1): the reset reaches the quarter's flops
    // through posedge kept copies, one per consumer group (lane decode, slice, pin / status / credit flops), so no net
    // from the pin or one flop spans the core; assert and release both one edge later (synchronous).  ot_s81ph_hq_in
    // FACE 1 = registered type-8 selects.  FACE 0 = the old form.
    parameter integer HLAT = 0,        // S81-ARCH-RTL-2 11-12: ot_s81ph_hq_slice HLAT (zero-logic hop lockup latches)
    parameter integer FACE = 0
) (
    input  wire [0:0]            ck,
    input  wire [0:0]            rst,        // landed die reset (active low)
    input  wire [514:0]          lane,
    input  wire [`SELT_CB-1:0]   f_c,
    input  wire [0:0]            f_cr,
    output wire [`SELT_SB-1:0]   t_s,
    output wire [`SELT_OB-1:0]   t_o
);
    localparam integer W = 16, IW = 20, K = 512, AW = 8, KW = 10, CB = 11, EW = 37, GW = CB + 4;
    localparam integer CW = $clog2(DM + 1);
    // S81-BKSEL-RF vB 11-05 (OT_BKQ_RCP = N): rst_c_s / rst_c_t are N KEPT identical copies each (same D, same edge, 0
    // cycles); synthesis ot_rst_copies.tcl (OT_RST_COPIES_RE) proves them identical and re-points the loads over the copies
    // by hierarchy, so no reset copy spans the core (rfh6: one rst_c_s -> slice recovery -44 ps through a 760-ps tree).
`ifndef OT_BKQ_RCP
`define OT_BKQ_RCP 1
`endif
    localparam integer RCP = `OT_BKQ_RCP;
    (* keep = "true" *) reg rst_c_in;                       // FACE 1 reset copies (unloaded at FACE 0)
    (* keep = "true" *) reg [RCP-1:0] rst_c_s, rst_c_t;
`ifdef OT_BKQ_RCP_MUT   // bench mutant: copy 0 of rst_c_s never asserts (slice not reset)
    always @(posedge ck[0]) begin rst_c_in <= rst[0]; rst_c_s <= {{(RCP-1){rst[0]}}, 1'b1}; rst_c_t <= {RCP{rst[0]}}; end
`else
    always @(posedge ck[0]) begin rst_c_in <= rst[0]; rst_c_s <= {RCP{rst[0]}}; rst_c_t <= {RCP{rst[0]}}; end
`endif
    wire rst_n_in = FACE != 0 ? rst_c_in   : rst[0];
    wire rst_n_s  = FACE != 0 ? rst_c_s[0] : rst[0];
    wire rst_n    = FACE != 0 ? rst_c_t[0] : rst[0];
    wire b_v, b_last, h_v, act, e_fmt, e_orphan, e_link;
    wire [15:0] b_lv; wire [255:0] b_val; wire [319:0] b_idx; wire [1:0] h_q, act_q; wire [9:0] h_k; wire [7:0] h_tag;
    ot_s81ph_hq_in #(.FACE(FACE)) u_in (.clk(ck[0]), .rst_n(rst_n_in), .lane(lane), .b_v(b_v), .b_lv(b_lv), .b_val(b_val),
        .b_idx(b_idx), .b_last(b_last), .h_v(h_v), .h_k(h_k), .h_tag(h_tag), .h_q(h_q), .act(act),
        .act_q(act_q), .e_fmt(e_fmt), .e_orphan(e_orphan), .e_link(e_link));
    // beat register in front of the slice (+ kept sign copies, one per key nibble)
    reg x_v, x_last; reg [15:0] x_lv; reg [255:0] x_val; reg [319:0] x_idx;
    // HLAT (S81-ARCH-RTL-2 11-12): the ingest beat (u_in b_*) -> beat register x_* through one lockup latch
    wire b_last_l; wire [15:0] b_lv_l; wire [255:0] b_val_l; wire [319:0] b_idx_l;
    ot_s81ph_hlk #(.W(1 + 16 + 256 + 320), .EN(HLAT)) u_fl_x (.clk(ck[0]), .d({b_last, b_lv, b_val, b_idx}),
        .q({b_last_l, b_lv_l, b_val_l, b_idx_l}));
    (* keep = "true" *) reg [W*4-1:0] x_sg;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) x_v <= 1'b0; else x_v <= b_v;
    integer xs;
    always @(posedge ck[0]) begin
        x_last <= b_last_l; x_lv <= b_lv_l; x_val <= b_val_l; x_idx <= b_idx_l;
        for (xs = 0; xs < W; xs = xs + 1) x_sg[4*xs +: 4] <= {4{b_val[16*xs + 15]}};
    end
    // command pin flops (QIO: two stages); control fields reset, data fields not
    reg [`SELT_CB-1:0] cq0, cq; reg crq0, crq;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) begin cq0[24] <= 1'b0; cq0[37:33] <= 5'd0; cq0[65] <= 1'b0; crq0 <= 1'b0;
                          cq[24] <= 1'b0; cq[37:33] <= 5'd0; cq[65] <= 1'b0; crq <= 1'b0; end
        else begin cq0[24] <= f_c[24]; cq0[37:33] <= f_c[37:33]; cq0[65] <= f_c[65]; crq0 <= f_cr[0];
                   cq[24] <= cq0[24]; cq[37:33] <= cq0[37:33]; cq[65] <= cq0[65]; crq <= crq0; end
    always @(posedge ck[0]) begin
        cq0[23:0] <= f_c[23:0]; cq0[32:25] <= f_c[32:25]; cq0[64:38] <= f_c[64:38];
        cq[23:0] <= cq0[23:0]; cq[32:25] <= cq0[32:25]; cq[64:38] <= cq0[64:38];
    end
    // kept command copies (same D as cq): c_T / c_Bt per 4-lane group, c_cg / c_fg per histogram bank
`ifdef OT_BKQ_FO8
    (* keep = "true" *) reg [8*16-1:0] cq_T;    // S81-BKSEL-RF7: one copy per 2 lanes (fanout <= 8)
`else
    (* keep = "true" *) reg [4*16-1:0] cq_T;
`endif
    (* keep = "true" *) reg [4*8-1:0]  cq_Bt;
    (* keep = "true" *) reg [8*4-1:0]  cq_cg, cq_fg;
    always @(posedge ck[0]) begin
        cq_T <= {
`ifdef OT_BKQ_FO8
        8
`else
        4
`endif
        {cq0[15:0]}}; cq_Bt <= {4{cq0[23:16]}}; cq_cg <= {8{cq0[28:25]}}; cq_fg <= {8{cq0[32:29]}};
    end
    // the slice and its line memory
    wire s_rdy, o_valid, o_last; wire o_ready;
    wire [W-1:0] o_lv, o_ninf; wire [W*16-1:0] o_val; wire [W*IW-1:0] o_idx;
    wire [16*GW-1:0] s_gc, s_gf; wire [16*CB-1:0] s_bc, s_bf;
    wire s_last, s_hfin, s_stopped, s_done2, s_emitted, s_ovf;
    wire m_we, m_re; wire [AW-1:0] m_wa, m_ra; wire [W*EW-1:0] m_wd0, m_wd1, m_rd;
    ot_s81ph_hq_slice #(.W(W), .IW(IW), .K(K), .AW(AW), .DG(8), .OD(4), .KW(KW), .CB(CB), .MUT(MUT), .HLAT(HLAT)) u_s (
        .clk(ck[0]), .rst_n(rst_n_s), .in_valid(x_v), .in_ready(s_rdy), .in_last(x_last), .in_lv(x_lv), .in_val(x_val),
        .in_idx(x_idx), .in_sg(x_sg), .c_T(cq[15:0]), .c_Tc(cq_T), .c_Bt(cq[23:16]), .c_Btc(cq_Bt), .c_fclr(cq[24]),
        .c_cgc(cq_cg), .c_fgc(cq_fg), .c_ing(cq[33]), .c_stop(cq[34]), .c_p2(cq[35]), .c_p3(cq[36]), .c_rep(cq[37]),
        .c_st(cq[53:38]), .c_rem(cq[64:54]), .c_hclr(cq[65]), .s_gc(s_gc), .s_gf(s_gf), .s_bc(s_bc), .s_bf(s_bf),
        .s_last(s_last), .s_hfin(s_hfin), .s_stopped(s_stopped), .s_done2(s_done2), .s_emitted(s_emitted), .s_ovf(s_ovf),
        .mem_we(m_we), .mem_waddr(m_wa), .mem_wdata(m_wd0), .mem_wdata1(m_wd1), .mem_re(m_re), .mem_raddr(m_ra),
        .mem_rdata(m_rd), .out_valid(o_valid), .out_ready(o_ready), .out_last(o_last), .out_lv(o_lv), .out_val(o_val),
        .out_idx(o_idx), .out_ninf(o_ninf));
    ot_s81ph_hq_mem2 u_mem (.clk(ck[0]), .we(m_we), .waddr(m_wa), .wdata0(m_wd0), .wdata1(m_wd1), .re(m_re),
        .raddr(m_ra), .rdata(m_rd));
    // faults (sticky, fail closed)
    reg [2:0] flt;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) flt <= 3'd0;
        else flt <= flt | {e_link, e_fmt, (x_v & ~s_rdy) | e_orphan};
    // status from flops (QIO: two stages); control bits [864:832] reset, payload [831:0] not
    reg [`SELT_SB-1:0] sq, sq1;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) begin sq[864:832] <= 33'd0; sq1[864:832] <= 33'd0; end
        else begin
            sq[864:832] <= {flt, act_q, act, h_tag, h_k, h_v, x_v & s_rdy, s_rdy,
                            s_ovf, s_emitted, s_done2, s_stopped, s_hfin, s_last};
            sq1[864:832] <= sq[864:832];
        end
`ifdef OT_BKQ_GBREG2
    // S81-BKSEL-RF5 vD: s_bf / s_bc now come from gq (bk_q -> OR8 -> gq), one edge later than vC; every other t_s bit
    // gets one more stage so t_s is vC delayed by exactly one cycle (PIN CYCLES +1 on t_s[864:0]).  sqd = the extra
    // payload stage (gsum bits); sq2 = the extra control stage AFTER sq1 (no reset, so reset behaviour is vC delayed).
    reg [479:0] sqd; reg [864:832] sq2;
    always @(posedge ck[0]) begin sq[831:0] <= {352'd0, s_gf, s_gc}; sqd <= sq[479:0]; sq1[831:0] <= {s_bf, s_bc, sqd}; sq2 <= sq1[864:832]; end
`elsif OT_BKQ_GBREG
    // S81-BKSEL-RF3 vC: s_bf / s_bc already come from a register (bk_q in ot_s81ph_hq_hist), so they skip sq.
    always @(posedge ck[0]) begin sq[831:0] <= {352'd0, s_gf, s_gc}; sq1[831:0] <= {s_bf, s_bc, sq[479:0]}; end
`else
    always @(posedge ck[0]) begin sq[831:0] <= {s_bf, s_bc, s_gf, s_gc}; sq1[831:0] <= sq[831:0]; end
`endif
`ifdef OT_BKQ_BSTG
    // S81-BKSEL-RF7 vG: the banks are two edges later, so the control bits take two more stages (PIN CYCLES +2 on t_s).
    reg [864:832] sq3, sq4;
`ifdef OT_BKQ_BSTG_MUT_CTL
    always @(posedge ck[0]) begin sq3 <= sq2; sq4 <= sq2; end  // proof mutant: control one edge short
`else
    always @(posedge ck[0]) begin sq3 <= sq2; sq4 <= sq3; end
`endif
    assign t_s = {sq4, sq1[831:0]};
`elsif OT_BKQ_GBREG2
    assign t_s = {sq2, sq1[831:0]};
`else
    assign t_s = sq1;
`endif
    // selected beats under credits; valid bit reset, payload not
    reg [CW-1:0] crd;
    assign o_ready = crd != 0;
    reg [`SELT_OB-1:0] oq, oq1;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) begin crd <= DM[CW-1:0]; oq[0] <= 1'b0; oq1[0] <= 1'b0; end
        else begin
            crd <= crd + (crq ? 1'b1 : 1'b0) - ((o_valid && o_ready) ? 1'b1 : 1'b0);
            oq[0] <= o_valid && o_ready; oq1[0] <= oq[0];
        end
    always @(posedge ck[0]) begin oq[`SELT_OB-1:1] <= {o_last, o_ninf, o_lv, o_idx}; oq1[`SELT_OB-1:1] <= oq[`SELT_OB-1:1]; end
    assign t_o = oq1;
endmodule
