`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One V4.1 QE ROM/MAC neighborhood for physical hardening (W2 rung 4).
//
//   * one block-dot lane group: ot_hdc_v41x_wgt_tile KIND 0, G = 1 (8 lanes x
//     32-MAC FP8/FP4 block dots, 256 MACs/cycle), the same parameters as the
//     routed ot_hdc_v41x_wgt_qtile except RL = 3 (see READ PIPELINE);
//   * the bank-local weight ROM of the source-pinned QE local tile witness
//     (results/rtl/v41x_qe_local_tile_bank_l0.json): 16 ot_rom_8192x274_m8,
//     banks 0-7 one FP8 264-bit {UE8M0, codes} lane each, banks 8-15 two
//     136-bit paired-FP4 lanes per row selected by beat parity -- the
//     ot_chip_v41x_qtile_pair_bank mapping, bit for bit;
//   * one activation SRAM (ot_sram_1r1w_64x512_m1_r2c2) per chain position,
//     written from the spine edge, read by the lane's beat index (rq_q), as in
//     ot_chip_v41x_ptile;
//   * registered spine-edge descriptor, activation-write, credit and result
//     pipes.
//
// READ PIPELINE.  The ROM macro's TT clock-to-q is ~792 ps; a 0.92 ns cycle
// with 60 ps uncertainty leaves no room for the pair-bank's 16:1 bank-set mux
// and FP4 half select between the macro and its capture.  So every macro
// output is captured UNCONDITIONALLY by a register beside its pins (cap_q:
// nothing between the macro pin and the flop D), and the lane select / FP4
// expansion runs in the next cycle into rd_w.  Request (tile rq, edge n) ->
// macro samples (edge n+1) -> cap_q (n+2) -> rd_w (n+3): RL = 3 instead of the
// pair bank's 2.  The activation path is delayed to the same RL.  RL is a
// parameter of the tile: the cost is one cycle of op latency, not throughput.
//
// FORMAT PER LANE.  Lanes of different chain positions are skewed, so two ops
// of different formats can be in flight on different lanes; each lane's format
// is looked up from its request tag (fmt[tag] <= d_fp4 at descriptor accept).
// Contract: a tag is not reused while an older op with that tag still issues.
//
// Faults are sticky and fail closed: conflict (two lanes needing different rows
// of one bank in a cycle), address (row >= 8192), reserved (nonzero unused
// macro bits in a read word).
// ---------------------------------------------------------------------------
module ot_chip_v41x_qe_romac #(
    parameter integer NP = 2        // spine-edge register stages
) (
    input  wire              clk,
    input  wire              rst_n,
    // descriptor (spine edge), valid/ready with registered ready
    input  wire              s_d_v,
    output reg               s_d_rdy,
    input  wire [3:0]        s_d_plg,
    input  wire [9:0]        s_d_nb,
    input  wire [15:0]       s_d_nrows,
    input  wire [19:0]       s_d_wbase,
    input  wire              s_d_ind,
    input  wire [8:0]        s_d_eid,
    input  wire [19:0]       s_d_estride,
    input  wire              s_d_fp4,
    input  wire [3:0]        s_d_tag,
    input  wire              s_o_cr,
    // activation writes: one chain position's 264-bit word a cycle
    input  wire              s_x_we,
    input  wire [2:0]        s_x_pos,
    input  wire [5:0]        s_x_addr,
    input  wire [263:0]      s_x_data,
    // results
    output wire              r_v,
    output wire [15:0]       r_rg,
    output wire [3:0]        r_tag,
    output wire              r_mask,
    output wire [31:0]       r_y,
    output wire [15:0]       r_bf,
    output wire              r_f,
    output reg               f_conflict,
    output reg               f_address,
    output reg               f_reserved,
    output reg               idle
);
    localparam integer RL = 3;
    integer i;
    // ------------------------------------------------------------ spine edge
    // descriptor: NP-stage registered pipe into a 4-entry queue; s_d_rdy is a
    // registered credit: the queue plus everything in the pipe never exceeds 4.
    localparam integer DW = 4 + 10 + 16 + 20 + 1 + 9 + 20 + 1 + 4;
    reg [DW:0]   dpipe [0:NP-1];
    reg          cpipe [0:NP-1];
    reg [DW-1:0] dq [0:3];
    reg [1:0]    dq_wp, dq_rp;
    reg [2:0]    dq_n;
    wire         t_d_rdy;
    wire         dq_pop = (dq_n != 0) && t_d_rdy;
    wire         dq_push = dpipe[NP-1][DW];
    reg  [2:0]   inflight;          // accepted into the pipe, not yet in the queue
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < NP; i = i + 1) begin dpipe[i] <= '0; cpipe[i] <= 1'b0; end
            dq_wp <= 0; dq_rp <= 0; dq_n <= 0; s_d_rdy <= 1'b0; inflight <= 0;
        end else begin
            dpipe[0] <= {s_d_v && s_d_rdy, s_d_plg, s_d_nb, s_d_nrows, s_d_wbase, s_d_ind, s_d_eid, s_d_estride,
                         s_d_fp4, s_d_tag};
            cpipe[0] <= s_o_cr;
            for (i = 1; i < NP; i = i + 1) begin dpipe[i] <= dpipe[i-1]; cpipe[i] <= cpipe[i-1]; end
            if (dq_push) begin dq[dq_wp] <= dpipe[NP-1][DW-1:0]; dq_wp <= dq_wp + 1'b1; end
            if (dq_pop) dq_rp <= dq_rp + 1'b1;
            dq_n <= dq_n + {2'd0, dq_push} - {2'd0, dq_pop};
            inflight <= inflight + {2'd0, s_d_v && s_d_rdy} - {2'd0, dq_push};
            // after this edge: queue <= dq_n+push-pop, pipe <= inflight+acc-push; allow one more only if
            // the total is at most 3
            s_d_rdy <= (dq_n + {2'd0, dq_push} - {2'd0, dq_pop}) + (inflight + {2'd0, s_d_v && s_d_rdy} - {2'd0, dq_push}) <= 3'd2;
        end
    end
    wire         d_v = (dq_n != 0);
    wire [3:0]   d_plg, d_tag;
    wire [9:0]   d_nb;
    wire [15:0]  d_nrows;
    wire [19:0]  d_wbase, d_estride;
    wire [8:0]   d_eid;
    wire         d_ind, d_fp4;
    assign {d_plg, d_nb, d_nrows, d_wbase, d_ind, d_eid, d_estride, d_fp4, d_tag} = dq[dq_rp];
    wire o_cr = cpipe[NP-1];
    // activation writes
    localparam integer XW = 1 + 3 + 6 + 264;
    reg [XW-1:0] xpipe [0:NP-1];
    always @(posedge clk) begin
        if (!rst_n) for (i = 0; i < NP; i = i + 1) xpipe[i] <= '0;
        else begin
            xpipe[0] <= {s_x_we, s_x_pos, s_x_addr, s_x_data};
            for (i = 1; i < NP; i = i + 1) xpipe[i] <= xpipe[i-1];
        end
    end
    wire         x_we;
    wire [2:0]   x_pos;
    wire [5:0]   x_addr;
    wire [263:0] x_data;
    assign {x_we, x_pos, x_addr, x_data} = xpipe[NP-1];

    // ------------------------------------------------------------ lane group
    wire [7:0]      rq_v;
    wire [8*20-1:0] rq_a;
    wire [8*10-1:0] rq_q;
    wire [8*4-1:0]  rq_tag;
    reg  [8*264-1:0] rd_w;
    reg  [8*264-1:0] rd_x;
    wire t_o_v, t_o_f, t_o_mask, t_idle;
    wire [15:0] t_o_rg, t_o_bf;
    wire [3:0]  t_o_tag;
    wire [31:0] t_o_y;
    wire [7:0] u_src, u_spl;
    wire [8*4-1:0] u_plg;
    wire [8*16-1:0] u_rg;
    wire [0:0] u_sm, u_fs;
    wire [31:0] u_ys, u_c0, u_c1, u_c2;
    wire [15:0] u_bfs;
    ot_hdc_v41x_wgt_tile #(.KIND(0), .G(1), .M(1), .LB(5), .PMIN_LG(0), .AW(20), .NBW(10), .RWW(16), .EIW(9),
                           .TGW(4), .RL(RL), .OCRED(128), .POOL(0)) u_t (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(t_d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .d_src(1'b0), .d_split(1'b0),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(u_plg), .rq_tag(rq_tag), .rq_src(u_src),
        .rq_split(u_spl), .rq_rg(u_rg), .rd_w(rd_w), .rd_k({(8*264){1'b0}}), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(t_o_v), .o_rg(t_o_rg), .o_tag(t_o_tag), .o_mask(t_o_mask), .o_y(t_o_y), .o_bf(t_o_bf),
        .o_f(t_o_f), .o_smask(u_sm), .o_ys(u_ys), .o_bfs(u_bfs), .o_fs(u_fs), .o_cnt_rom(u_c0),
        .o_cnt_stream(u_c1), .o_cnt_split(u_c2), .idle(t_idle));

    // per-tag operand format
    reg [15:0] fmt;
    always @(posedge clk)
        if (!rst_n) fmt <= '0;
        else if (d_v && t_d_rdy) fmt[d_tag] <= d_fp4;

    // ------------------------------------------------------------ bank requests (combinational from rq)
    reg  [15:0]      bank_re;
    reg  [16*13-1:0] bank_addr;
    reg  [7:0]       l_fp4;
    reg  [4*8-1:0]   l_bank;
    reg              c_conflict, c_address;
    reg  [19:0]      beat, row;
    reg  [3:0]       bank;
    integer c;
    always @(*) begin
        bank_re = '0; bank_addr = '0; c_conflict = 1'b0; c_address = 1'b0; l_fp4 = '0; l_bank = '0;
        for (c = 0; c < 8; c = c + 1) begin
            l_fp4[c] = fmt[rq_tag[c*4 +: 4]];
            beat = rq_a[c*20 +: 20];
            row = l_fp4[c] ? beat >> 1 : beat;
            bank = l_fp4[c] ? (4'd8 + {beat[0], 2'b00} + 4'(c >> 1)) : 4'(c);
            l_bank[c*4 +: 4] = bank;
            if (rq_v[c]) begin
                if (row >= 20'd8192) c_address = 1'b1;
                if (bank_re[bank] && bank_addr[bank*13 +: 13] != row[12:0]) c_conflict = 1'b1;
                bank_re[bank] = 1'b1;
                bank_addr[bank*13 +: 13] = row[12:0];
            end
        end
    end

    // ------------------------------------------------------------ weight ROM + capture beside the macro
    wire [16*274-1:0] rom_q;
    reg  [16*274-1:0] cap_q;
    genvar b;
    generate for (b = 0; b < 16; b = b + 1) begin : g_rom
        ot_rom_8192x274_m8 u_rom (.clk(clk), .ce_in(bank_re[b]), .addr_in(bank_addr[b*13 +: 13]),
                                  .rd_out(rom_q[b*274 +: 274]));
    end endgenerate
    always @(posedge clk) cap_q <= rom_q;      // no enable, no reset: the D pin is the macro pin's net

    // lane controls to the capture cycle: stage 1 at the macro read edge, stage 2 at capture
    reg [7:0]     v1, v2, f1, f2;
    reg [4*8-1:0] k1, k2;
    always @(posedge clk) begin
        if (!rst_n) begin v1 <= 0; v2 <= 0; end
        else begin v1 <= rq_v; v2 <= v1; end
        f1 <= l_fp4; f2 <= f1; k1 <= l_bank; k2 <= k1;
    end

    // lane select / FP4 expansion into rd_w (RL = 3)
    reg [273:0] sel;
    reg [135:0] compact;
    reg         r_res;
    integer k;
    always @(posedge clk) begin
        r_res = 1'b0;
        for (k = 0; k < 8; k = k + 1) begin
            sel = cap_q[k2[k*4 +: 4]*274 +: 274];
            if (f2[k]) begin
                compact = k[0] ? sel[271:136] : sel[135:0];
                rd_w[k*264 +: 264] <= {compact[135:128], 128'b0, compact[127:0]};
                if (v2[k] && sel[273:272] != 2'b00) r_res = 1'b1;
            end else begin
                rd_w[k*264 +: 264] <= sel[263:0];
                if (v2[k] && sel[273:264] != 10'b0) r_res = 1'b1;
            end
        end
        if (!rst_n) begin f_conflict <= 1'b0; f_address <= 1'b0; f_reserved <= 1'b0; end
        else begin
            if (c_conflict) f_conflict <= 1'b1;
            if (c_address) f_address <= 1'b1;
            if (r_res) f_reserved <= 1'b1;
        end
    end

    // ------------------------------------------------------------ activation buffer, same RL
    wire [8*512-1:0] act_q;
    reg  [8*264-1:0] act_cap;
    generate for (b = 0; b < 8; b = b + 1) begin : g_act
        ot_sram_1r1w_64x512_m1_r2c2 u_act (
            .clk(clk), .r_ce_in(rq_v[b]), .r_addr_in(rq_q[b*10 +: 6]), .rd_out(act_q[b*512 +: 512]),
            .w_ce_in(x_we && x_pos == b), .w_addr_in(x_addr), .wd_in({248'd0, x_data}), .w_mask_in({512{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
        always @(posedge clk) act_cap[b*264 +: 264] <= act_q[b*512 +: 264];
    end endgenerate
    always @(posedge clk) rd_x <= act_cap;

    // ------------------------------------------------------------ results
    localparam integer RW = 1 + 16 + 4 + 1 + 32 + 16 + 1;
    reg [RW-1:0] rpipe [0:NP-1];
    always @(posedge clk) begin
        if (!rst_n) begin for (i = 0; i < NP; i = i + 1) rpipe[i] <= '0; idle <= 1'b1; end
        else begin
            rpipe[0] <= {t_o_v, t_o_rg, t_o_tag, t_o_mask, t_o_y, t_o_bf, t_o_f};
            for (i = 1; i < NP; i = i + 1) rpipe[i] <= rpipe[i-1];
            idle <= t_idle && (dq_n == 0) && (inflight == 0);
        end
    end
    assign {r_v, r_rg, r_tag, r_mask, r_y, r_bf, r_f} = rpipe[NP-1];
endmodule
