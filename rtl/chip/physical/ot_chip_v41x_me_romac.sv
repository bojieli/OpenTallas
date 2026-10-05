`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One V4.1 ME (BF16/FP32/FP8-weight) ROM/MAC neighborhood for physical
// hardening (W2 rung 4).
//
//   * one BF16 lane group: ot_hdc_v41x_wgt_mtile (KIND 1, G = 8: 64 MAC lanes,
//     RL = 2), unchanged;
//   * one ot_rom_8192x274_m8 weight bank per chain position c, holding the
//     34-bit operand words {fmt, data} of lanes j = 8u + c (u = 0..7) in bits
//     34u+33..34u; bits 273:272 are reserved (a nonzero read fails closed);
//   * one MP1 activation macro (ot_sram_1r1w_128x256_m1_r2c2, the qualified
//     ME local cut's macro) per chain position: eight BF16 activations of lanes
//     8u + c in the low 128 bits of a word addressed by the beat index rq_q;
//   * registered spine-edge descriptor, activation-write, credit and result pipes.
//
// READ PIPELINE, as in ot_chip_v41x_qe_romac: every macro output is captured
// unconditionally by a register beside its pins, and the lane words run
// combinationally into the ME lane's P0 input register.  RL = 2 unchanged.
// ---------------------------------------------------------------------------
module ot_chip_v41x_me_romac #(
    parameter integer NP = 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              s_d_v,
    output reg               s_d_rdy,
    input  wire [3:0]        s_d_plg,
    input  wire [13:0]       s_d_nb,
    input  wire [15:0]       s_d_nrows,
    input  wire [19:0]       s_d_wbase,
    input  wire              s_d_ind,
    input  wire [8:0]        s_d_eid,
    input  wire [19:0]       s_d_estride,
    input  wire [3:0]        s_d_tag,
    input  wire              s_o_cr,
    input  wire              s_x_we,
    input  wire [2:0]        s_x_pos,
    input  wire [6:0]        s_x_addr,
    input  wire [127:0]      s_x_data,
    output wire              r_v,
    output wire [15:0]       r_rg,
    output wire [3:0]        r_tag,
    output wire [3:0]        r_mask,
    output wire [127:0]      r_y,
    output wire [63:0]       r_bf,
    output wire [3:0]        r_f,
    output reg               f_reserved,
    output reg               idle
);
    integer i;
    // ------------------------------------------------------------ spine edge (as ot_chip_v41x_qe_romac)
    localparam integer DW = 4 + 14 + 16 + 20 + 1 + 9 + 20 + 4;
    reg [DW:0]   dpipe [0:NP-1];
    reg          cpipe [0:NP-1];
    reg [DW-1:0] dq [0:3];
    reg [1:0]    dq_wp, dq_rp;
    reg [2:0]    dq_n;
    wire         t_d_rdy;
    wire         dq_pop = (dq_n != 0) && t_d_rdy;
    wire         dq_push = dpipe[NP-1][DW];
    reg  [2:0]   inflight;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < NP; i = i + 1) begin dpipe[i] <= '0; cpipe[i] <= 1'b0; end
            dq_wp <= 0; dq_rp <= 0; dq_n <= 0; s_d_rdy <= 1'b0; inflight <= 0;
        end else begin
            dpipe[0] <= {s_d_v && s_d_rdy, s_d_plg, s_d_nb, s_d_nrows, s_d_wbase, s_d_ind, s_d_eid, s_d_estride,
                         s_d_tag};
            cpipe[0] <= s_o_cr;
            for (i = 1; i < NP; i = i + 1) begin dpipe[i] <= dpipe[i-1]; cpipe[i] <= cpipe[i-1]; end
            if (dq_push) begin dq[dq_wp] <= dpipe[NP-1][DW-1:0]; dq_wp <= dq_wp + 1'b1; end
            if (dq_pop) dq_rp <= dq_rp + 1'b1;
            dq_n <= dq_n + {2'd0, dq_push} - {2'd0, dq_pop};
            inflight <= inflight + {2'd0, s_d_v && s_d_rdy} - {2'd0, dq_push};
            s_d_rdy <= (dq_n + {2'd0, dq_push} - {2'd0, dq_pop}) + (inflight + {2'd0, s_d_v && s_d_rdy} - {2'd0, dq_push}) <= 3'd2;
        end
    end
    wire         d_v = (dq_n != 0);
    wire [3:0]   d_plg, d_tag;
    wire [13:0]  d_nb;
    wire [15:0]  d_nrows;
    wire [19:0]  d_wbase, d_estride;
    wire [8:0]   d_eid;
    wire         d_ind;
    assign {d_plg, d_nb, d_nrows, d_wbase, d_ind, d_eid, d_estride, d_tag} = dq[dq_rp];
    wire o_cr = cpipe[NP-1];
    localparam integer XW = 1 + 3 + 7 + 128;
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
    wire [6:0]   x_addr;
    wire [127:0] x_data;
    assign {x_we, x_pos, x_addr, x_data} = xpipe[NP-1];

    // ------------------------------------------------------------ lane group
    wire [7:0]      rq_v;
    wire [8*20-1:0] rq_a;
    wire [8*14-1:0] rq_q;
    reg  [64*34-1:0] rd_w;
    reg  [64*16-1:0] rd_x;
    wire t_o_v, t_idle;
    wire [15:0] t_o_rg;
    wire [3:0]  t_o_tag, t_o_mask, t_o_f;
    wire [127:0] t_o_y;
    wire [63:0] t_o_bf;
    ot_hdc_v41x_wgt_mtile u_m (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(t_d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_tag(d_tag),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(), .rq_tag(), .rd_w(rd_w), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(t_o_v), .o_rg(t_o_rg), .o_tag(t_o_tag), .o_mask(t_o_mask), .o_y(t_o_y), .o_bf(t_o_bf),
        .o_f(t_o_f), .idle(t_idle));

    // ------------------------------------------------------------ weight ROM + activation macro per chain position
    wire [8*274-1:0] rom_q;
    reg  [8*274-1:0] cap_q;
    wire [8*256-1:0] act_q;
    reg  [8*128-1:0] act_cap;
    reg  [7:0]       v1, v2;
    genvar c;
    generate for (c = 0; c < 8; c = c + 1) begin : g_mc
        ot_rom_8192x274_m8 u_rom (.clk(clk), .ce_in(rq_v[c]), .addr_in(rq_a[c*20 +: 13]),
                                  .rd_out(rom_q[c*274 +: 274]));
        ot_sram_1r1w_128x256_m1_r2c2 u_act (
            .clk(clk), .r_ce_in(rq_v[c]), .r_addr_in(rq_q[c*14 +: 7]), .rd_out(act_q[c*256 +: 256]),
            .w_ce_in(x_we && x_pos == c), .w_addr_in(x_addr), .wd_in({128'd0, x_data}),
            .w_mask_in({128'd0, {128{1'b1}}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    always @(posedge clk) begin
        cap_q <= rom_q;                                    // unconditional: D is the macro pin's net
        for (i = 0; i < 8; i = i + 1) act_cap[i*128 +: 128] <= act_q[i*256 +: 128];
    end
    always @(posedge clk)
        if (!rst_n) begin v1 <= 0; v2 <= 0; end
        else begin v1 <= rq_v; v2 <= v1; end
    integer u, k;
    reg r_res;
    always @(*) begin
        r_res = 1'b0;
        for (k = 0; k < 8; k = k + 1) begin
            for (u = 0; u < 8; u = u + 1) begin
                rd_w[(8*u + k)*34 +: 34] = cap_q[k*274 + u*34 +: 34];
                rd_x[(8*u + k)*16 +: 16] = act_cap[k*128 + u*16 +: 16];
            end
            if (v2[k] && cap_q[k*274 + 272 +: 2] != 2'b00) r_res = 1'b1;
        end
    end
    always @(posedge clk)
        if (!rst_n) f_reserved <= 1'b0;
        else if (r_res) f_reserved <= 1'b1;

    // ------------------------------------------------------------ results
    localparam integer RW = 1 + 16 + 4 + 4 + 128 + 64 + 4;
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
