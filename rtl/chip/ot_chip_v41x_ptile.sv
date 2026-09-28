`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PHYSICAL tile of the adopted DeepSeek-V4.1 layer die, at a reduced width:
// the unit the die-assembly floorplan replicates 48 times
// (docs/ARCH_V41_DIE_ASSEMBLY.md 4.2: "ROM | lane column | ROM", 3.24 x 3.99 mm).
//
// ot_chip_v41x_tile.sv is the LOGICAL tile (one core and its behavioural
// memories); the die-assembly tiles are a physical partition of that core's
// pooled engines.  This module is one such partition, built from the routed
// engine tiles and the memory compiler's macros, for place-and-route:
//
//   NQ   block-dot lane groups   ot_hdc_v41x_wgt_qtile (KIND 0, G = 1: 8 lanes of
//                                32-MAC FP8/FP4 block dots, 256 MACs/cycle each)
//   NM   BF16 lane groups        ot_hdc_v41x_wgt_mtile (KIND 1, G = 8: 64 MAC lanes)
//   weight ROM                   one mask-ROM macro per chain position and lane
//                                group (tools/mem_compiler, physical/asap7_memory_macros):
//                                ot_rom_8192x266_m8 per block-dot lane (264-bit
//                                {we, codes} word), ot_rom_8192x274_m8 per BF16 chain
//                                position (8 lanes x 34 bits)
//   activation buffer            one ot_sram_1r1w_64x512_m1_r2c2 per block-dot chain
//                                position (264-bit {xe, codes} word, SHARED by every
//                                block-dot lane group: they run the same op on
//                                different rows) and one ot_sram_1r1w_512x128_m4_r2c2
//                                per BF16 chain position (8 lanes x BF16); written
//                                from the spine edge
//   edge registers               NP register stages on every spine-edge signal
//                                (descriptor, activation writes, credits, results)
//
// Read timing is the engines' RL = 2 contract: the engine's registered request
// reaches the macro, which answers after its clock-to-q; a capture register next
// to the macro presents the word on the next cycle.  The ROM macros' 787 ps
// clock-to-q (TT, 8192 x 266) leaves ~0.1 ns of a 0.92 ns cycle, so the capture
// register must sit at the macro.
//
// Scope and stand-ins (physical study, not a functional tile):
//   * one macro per lane is the bank-port count; the macro depth (8192 words)
//     is one bank, not the tile's 56 MB share of the weights: rq_a's low 13
//     bits address it;
//   * the spine-edge descriptor is a registered broadcast (d_v into every group,
//     d_rdy the registered AND), not a protocol-exact skid buffer;
//   * the macros' redundancy ports are tied off.
// ---------------------------------------------------------------------------
module ot_chip_v41x_ptile #(
    parameter integer NQ = 2,       // block-dot lane groups
    parameter integer NM = 0,       // BF16 lane groups (0 or 1)
    parameter integer NP = 2        // spine-edge register stages
) (
    input  wire              clk,
    input  wire              rst_n,
    // -- block-dot descriptor (spine edge) --------------------------------------
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
    // -- activation writes (spine edge): one chain position's word a cycle -------
    input  wire              s_x_we,
    input  wire [2:0]        s_x_pos,
    input  wire [5:0]        s_x_addr,
    input  wire [263:0]      s_x_data,
    // -- block-dot results (spine edge) -------------------------------------------
    output wire [NQ-1:0]     r_v,
    output wire [NQ*16-1:0]  r_rg,
    output wire [NQ*4-1:0]   r_tag,
    output wire [NQ*32-1:0]  r_y,
    output wire [NQ*16-1:0]  r_bf,
    output wire [NQ-1:0]     r_f,
    // -- BF16 group (spine edge; unused when NM = 0) ----------------------------------
    input  wire              m_d_v,
    output reg               m_d_rdy,
    input  wire [3:0]        m_d_plg,
    input  wire [13:0]       m_d_nb,
    input  wire [15:0]       m_d_nrows,
    input  wire [19:0]       m_d_wbase,
    input  wire              m_d_ind,
    input  wire [8:0]        m_d_eid,
    input  wire [19:0]       m_d_estride,
    input  wire [3:0]        m_d_tag,
    input  wire              m_o_cr,
    input  wire              m_x_we,
    input  wire [2:0]        m_x_pos,
    input  wire [8:0]        m_x_addr,
    input  wire [127:0]      m_x_data,
    output wire              m_r_v,
    output wire [15:0]       m_r_rg,
    output wire [3:0]        m_r_tag,
    output wire [3:0]        m_r_mask,
    output wire [127:0]      m_r_y,
    output wire [63:0]       m_r_bf,
    output wire [3:0]        m_r_f,
    output reg               idle
);
    // ---------------------------------------------------------------- spine-edge pipes
    localparam integer DW = 1 + 4 + 10 + 16 + 20 + 1 + 9 + 20 + 1 + 4 + 1;        // descriptor + credit
    localparam integer XW = 1 + 3 + 6 + 264;
    reg [DW-1:0] dpipe [0:NP-1];
    reg [XW-1:0] xpipe [0:NP-1];
    integer i;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < NP; i = i + 1) begin dpipe[i] <= {DW{1'b0}}; xpipe[i] <= {XW{1'b0}}; end
        end else begin
            dpipe[0] <= {s_d_v, s_d_plg, s_d_nb, s_d_nrows, s_d_wbase, s_d_ind, s_d_eid, s_d_estride, s_d_fp4,
                         s_d_tag, s_o_cr};
            xpipe[0] <= {s_x_we, s_x_pos, s_x_addr, s_x_data};
            for (i = 1; i < NP; i = i + 1) begin dpipe[i] <= dpipe[i-1]; xpipe[i] <= xpipe[i-1]; end
        end
    end
    wire         d_v, d_ind, d_fp4, o_cr;
    wire [3:0]   d_plg, d_tag;
    wire [9:0]   d_nb;
    wire [15:0]  d_nrows;
    wire [19:0]  d_wbase, d_estride;
    wire [8:0]   d_eid;
    assign {d_v, d_plg, d_nb, d_nrows, d_wbase, d_ind, d_eid, d_estride, d_fp4, d_tag, o_cr} = dpipe[NP-1];
    wire         x_we;
    wire [2:0]   x_pos;
    wire [5:0]   x_addr;
    wire [263:0] x_data;
    assign {x_we, x_pos, x_addr, x_data} = xpipe[NP-1];

    // ---------------------------------------------------------------- block-dot lane groups
    wire [NQ-1:0]      q_rdy, q_idle;
    wire [NQ*8-1:0]    q_rq_v;
    wire [NQ*8*20-1:0] q_rq_a;
    wire [NQ*8*10-1:0] q_rq_q;
    reg  [NQ*8*264-1:0] q_rd_w;
    reg  [8*264-1:0]   q_rd_x;
    wire [NQ-1:0]      q_o_v, q_o_f, q_o_mask;
    wire [NQ*16-1:0]   q_o_rg, q_o_bf;
    wire [NQ*4-1:0]    q_o_tag;
    wire [NQ*32-1:0]   q_o_y;
    genvar g, c;
    generate for (g = 0; g < NQ; g = g + 1) begin : g_q
        ot_hdc_v41x_wgt_qtile u_q (
            .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(q_rdy[g]), .d_plg(d_plg), .d_nb(d_nb),
            .d_nrows(d_nrows), .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride),
            .d_fp4(d_fp4), .d_tag(d_tag),
            .rq_v(q_rq_v[g*8 +: 8]), .rq_a(q_rq_a[g*160 +: 160]), .rq_q(q_rq_q[g*80 +: 80]), .rq_plg(),
            .rq_tag(), .rd_w(q_rd_w[g*8*264 +: 8*264]), .rd_x(q_rd_x),
            .o_cr(o_cr), .o_v(q_o_v[g]), .o_rg(q_o_rg[g*16 +: 16]), .o_tag(q_o_tag[g*4 +: 4]),
            .o_mask(q_o_mask[g]), .o_y(q_o_y[g*32 +: 32]), .o_bf(q_o_bf[g*16 +: 16]), .o_f(q_o_f[g]),
            .idle(q_idle[g]));
        // one weight ROM macro per lane (chain position c), captured beside the macro
        for (c = 0; c < 8; c = c + 1) begin : g_rom
            wire [265:0] rd;
            ot_rom_8192x266_m8 u_rom (.clk(clk), .ce_in(q_rq_v[g*8 + c]),
                                      .addr_in(q_rq_a[(g*8 + c)*20 +: 13]), .rd_out(rd));
            always @(posedge clk) q_rd_w[(g*8 + c)*264 +: 264] <= rd[263:0];
        end
    end endgenerate
    // the activation buffer: one SRAM per chain position, read at group 0's beat index
    generate for (c = 0; c < 8; c = c + 1) begin : g_act
        wire [511:0] rd;
        ot_sram_1r1w_64x512_m1_r2c2 u_act (
            .clk(clk), .r_ce_in(q_rq_v[c]), .r_addr_in(q_rq_q[c*10 +: 6]), .rd_out(rd),
            .w_ce_in(x_we && x_pos == c), .w_addr_in(x_addr), .wd_in({248'd0, x_data}), .w_mask_in({512{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
        always @(posedge clk) q_rd_x[c*264 +: 264] <= rd[263:0];
    end endgenerate

    // results to the spine edge
    localparam integer RW = 1 + 16 + 4 + 32 + 16 + 1;
    reg [NQ*RW-1:0] rpipe [0:NP-1];
    always @(posedge clk) begin
        if (!rst_n) for (i = 0; i < NP; i = i + 1) rpipe[i] <= {NQ*RW{1'b0}};
        else begin
            for (i = 0; i < NQ; i = i + 1)
                rpipe[0][i*RW +: RW] <= {q_o_v[i], q_o_rg[i*16 +: 16], q_o_tag[i*4 +: 4], q_o_y[i*32 +: 32],
                                         q_o_bf[i*16 +: 16], q_o_f[i]};
            for (i = 1; i < NP; i = i + 1) rpipe[i] <= rpipe[i-1];
        end
    end
    generate for (g = 0; g < NQ; g = g + 1) begin : g_r
        assign {r_v[g], r_rg[g*16 +: 16], r_tag[g*4 +: 4], r_y[g*32 +: 32], r_bf[g*16 +: 16], r_f[g]} =
            rpipe[NP-1][g*RW +: RW];
    end endgenerate

    // ---------------------------------------------------------------- BF16 lane group
    wire m_idle;
    generate if (NM != 0) begin : g_m
        localparam integer MDW = 1 + 4 + 14 + 16 + 20 + 1 + 9 + 20 + 4 + 1;
        localparam integer MXW = 1 + 3 + 9 + 128;
        localparam integer MRW = 1 + 16 + 4 + 4 + 128 + 64 + 4;
        reg [MDW-1:0] mdp [0:NP-1];
        reg [MXW-1:0] mxp [0:NP-1];
        reg [MRW-1:0] mrp [0:NP-1];
        integer k;
        wire        md_v, md_ind, mo_cr, md_rdy;
        wire [3:0]  md_plg, md_tag;
        wire [13:0] md_nb;
        wire [15:0] md_nrows;
        wire [19:0] md_wbase, md_estride;
        wire [8:0]  md_eid;
        wire        mx_we;
        wire [2:0]  mx_pos;
        wire [8:0]  mx_addr;
        wire [127:0] mx_data;
        assign {md_v, md_plg, md_nb, md_nrows, md_wbase, md_ind, md_eid, md_estride, md_tag, mo_cr} = mdp[NP-1];
        assign {mx_we, mx_pos, mx_addr, mx_data} = mxp[NP-1];
        wire [7:0]      m_rq_v;
        wire [8*20-1:0] m_rq_a;
        wire [8*14-1:0] m_rq_q;
        reg  [64*34-1:0] m_rd_w;
        reg  [64*16-1:0] m_rd_x;
        wire        mo_v;
        wire [15:0] mo_rg;
        wire [3:0]  mo_tag, mo_mask, mo_f;
        wire [127:0] mo_y;
        wire [63:0] mo_bf;
        ot_hdc_v41x_wgt_mtile u_m (
            .clk(clk), .rst_n(rst_n), .d_v(md_v), .d_rdy(md_rdy), .d_plg(md_plg), .d_nb(md_nb), .d_nrows(md_nrows),
            .d_wbase(md_wbase), .d_ind(md_ind), .d_eid(md_eid), .d_estride(md_estride), .d_tag(md_tag),
            .rq_v(m_rq_v), .rq_a(m_rq_a), .rq_q(m_rq_q), .rq_plg(), .rq_tag(), .rd_w(m_rd_w), .rd_x(m_rd_x),
            .o_cr(mo_cr), .o_v(mo_v), .o_rg(mo_rg), .o_tag(mo_tag), .o_mask(mo_mask), .o_y(mo_y), .o_bf(mo_bf),
            .o_f(mo_f), .idle(m_idle));
        // chain position c serves lanes j = 8u + c: one 274-bit ROM word and one 128-bit activation word
        for (c = 0; c < 8; c = c + 1) begin : g_mc
            wire [273:0] rw;
            wire [127:0] rx;
            ot_rom_8192x274_m8 u_rom (.clk(clk), .ce_in(m_rq_v[c]), .addr_in(m_rq_a[c*20 +: 13]), .rd_out(rw));
            ot_sram_1r1w_512x128_m4_r2c2 u_act (
                .clk(clk), .r_ce_in(m_rq_v[c]), .r_addr_in(m_rq_q[c*14 +: 9]), .rd_out(rx),
                .w_ce_in(mx_we && mx_pos == c), .w_addr_in(mx_addr), .wd_in(mx_data), .w_mask_in({128{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
            integer u;
            always @(posedge clk)
                for (u = 0; u < 8; u = u + 1) begin
                    m_rd_w[(8*u + c)*34 +: 34] <= rw[u*34 +: 34];
                    m_rd_x[(8*u + c)*16 +: 16] <= rx[u*16 +: 16];
                end
        end
        always @(posedge clk) begin
            if (!rst_n) begin
                for (k = 0; k < NP; k = k + 1) begin mdp[k] <= {MDW{1'b0}}; mxp[k] <= {MXW{1'b0}}; mrp[k] <= {MRW{1'b0}}; end
                m_d_rdy <= 1'b0;
            end else begin
                mdp[0] <= {m_d_v, m_d_plg, m_d_nb, m_d_nrows, m_d_wbase, m_d_ind, m_d_eid, m_d_estride, m_d_tag, m_o_cr};
                mxp[0] <= {m_x_we, m_x_pos, m_x_addr, m_x_data};
                mrp[0] <= {mo_v, mo_rg, mo_tag, mo_mask, mo_y, mo_bf, mo_f};
                for (k = 1; k < NP; k = k + 1) begin mdp[k] <= mdp[k-1]; mxp[k] <= mxp[k-1]; mrp[k] <= mrp[k-1]; end
                m_d_rdy <= md_rdy;
            end
        end
        assign {m_r_v, m_r_rg, m_r_tag, m_r_mask, m_r_y, m_r_bf, m_r_f} = mrp[NP-1];
    end else begin : g_nm
        assign m_idle = 1'b1;
        always @(posedge clk) m_d_rdy <= 1'b0;
        assign {m_r_v, m_r_rg, m_r_tag, m_r_mask, m_r_y, m_r_bf, m_r_f} = {(1 + 16 + 4 + 4 + 128 + 64 + 4){1'b0}};
    end endgenerate

    always @(posedge clk) begin
        if (!rst_n) begin s_d_rdy <= 1'b0; idle <= 1'b1; end
        else begin s_d_rdy <= &q_rdy; idle <= (&q_idle) && m_idle; end
    end
endmodule
