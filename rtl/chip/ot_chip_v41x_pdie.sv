`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PHYSICAL layer die of the adopted DeepSeek-V4.1 array at REDUCED SCALE, for
// the die-level floorplan route (tools/v41x_die_pnr.py die_s4).  It keeps the
// die's top-level structure and the die-assembly floorplan's geometry
// (docs/ARCH_V41_DIE_ASSEMBLY.md 4.2, results/arch/v41_die_assembly.json, every
// coordinate x 1/4): four HBM3E stack interfaces on the long edges, the vector /
// control spine in the middle, 48 tiles, the UCIe edge with the in-package
// collective engine, the board SerDes edge with the package-pair collective.
//
// What is the adopted RTL, unchanged:
//   u_arb[s]   ot_chip_v41x_hbm_karb (NPC = 32) per stack, beside its PHY
//   u_kv       ot_chip_v41x_kv_prefetch (staging reduced to STG words a slot),
//              wired to the four arbiters' K channels exactly as ot_chip_v41x_die
//              wires it (no register between: the adopted die's connectivity)
// What is a hard-macro abstract (tools/v41x_die_pnr.py pdie_views):
//   u_phy[s]   the HBM3E PHY + controller with the adopted port list, at 1/4 length
//   tiles      48 tile abstracts (4 with operand / result pins, 44 blockages)
//   collectives, UCIe, SerDes: placeholder abstracts with record / flit pins
// What stands in for the core (physical study, not functional):
//   the spine hub: per-trunk LFSR sources and XOR-folded sinks, so every trunk
//   bit is a distinct, kept net;
//   u_ks[s]    a key streamer per stack: the pooled bridge's per-pseudo-channel
//              port (b_*) fed from ONE registered request channel that the spine
//              addresses to a pseudo-channel, and the 32 response ports gathered
//              (8:1 then 4:1, registered) into ONE response channel back.
// Every spine <-> edge / tile traversal is a register trunk
// (ot_chip_v41x_pdie_trunk) of N stages: the die-assembly study's "registered
// at its per-cycle reach"; the stage counts are parameters so the route measures
// the delay of each stage's length.
// ---------------------------------------------------------------------------
module ot_chip_v41x_pdie_trunk #(parameter integer W = 64, parameter integer N = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (N == 0) begin : g_w
        assign q = d;
    end else begin : g_r
        reg [W-1:0] s [0:N-1];
        integer i;
        always @(posedge clk) begin
            s[0] <= d;
            for (i = 1; i < N; i = i + 1) s[i] <= s[i-1];
        end
        assign q = s[N-1];
    end endgenerate
endmodule

// a W-bit maximal-ish LFSR source, distinct per SEED
module ot_chip_v41x_pdie_src #(parameter integer W = 64, parameter integer SEED = 1) (
    input  wire         clk,
    input  wire         rst_n,
    output reg  [W-1:0] q
);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q <= {{(W - 1){1'b0}}, 1'b1} ^ W'(SEED * 32'h9E3779B1);
        else        q <= {q[W-2:0], q[W-1] ^ q[W/2] ^ q[W/3] ^ q[1]};
endmodule

// registered sink, folded to 16 observable bits
module ot_chip_v41x_pdie_sink #(parameter integer W = 64) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [15:0]  o
);
    reg [W-1:0] r;
    integer i;
    reg [15:0] f;
    always @(*) begin
        f = 16'd0;
        for (i = 0; i < W; i = i + 1) f[i % 16] = f[i % 16] ^ r[i];
    end
    always @(posedge clk) begin r <= d; o <= f; end
endmodule

// per-stack key streamer beside the PHY strip (see the header)
module ot_chip_v41x_pdie_kstream #(parameter integer NPC = 32) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [1+5+338-1:0]   req,          // {v, pc, addr28 len4 tag16 we wdata256 wstrb32}
    output reg  [1+5+277-1:0]   rsp,          // {v, pc, tag16 beat4 data256 wr_done}
    output reg  [NPC-1:0]       b_v,
    input  wire [NPC-1:0]       b_rdy,
    output reg  [NPC*28-1:0]    b_addr,
    output reg  [NPC*4-1:0]     b_len,
    output reg  [NPC*16-1:0]    b_tag,
    output reg  [NPC-1:0]       b_we,
    output reg  [NPC*256-1:0]   b_wdata,
    output reg  [NPC*32-1:0]    b_wstrb,
    input  wire [NPC-1:0]       b_wr_done,
    input  wire [NPC-1:0]       b_rsp_v,
    output wire [NPC-1:0]       b_rsp_rdy,
    input  wire [NPC*16-1:0]    b_rsp_tag,
    input  wire [NPC*4-1:0]     b_rsp_beat,
    input  wire [NPC*256-1:0]   b_rsp_data
);
    reg [1+5+338-1:0] rq;
    integer p;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rq <= '0; else rq <= req;
    // the request, broadcast along the strip, valid on its pseudo-channel only
    always @(*)
        for (p = 0; p < NPC; p = p + 1) begin
            b_v[p] = rq[343] && rq[342:338] == p;
            {b_addr[p*28 +: 28], b_len[p*4 +: 4], b_tag[p*16 +: 16], b_we[p], b_wdata[p*256 +: 256],
             b_wstrb[p*32 +: 32]} = rq[337:0];
        end
    assign b_rsp_rdy = {NPC{1'b1}};
    // gather: 8:1 per group of 8 pseudo-channels (registered at the group), then 4:1
    localparam integer RW = 1 + 5 + 277;
    reg [RW-1:0] grp [0:NPC/8-1];
    integer g, k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (g = 0; g < NPC / 8; g = g + 1) grp[g] <= '0;
            rsp <= '0;
        end else begin
            for (g = 0; g < NPC / 8; g = g + 1) begin
                grp[g] <= '0;
                for (k = 7; k >= 0; k = k - 1)
                    if (b_rsp_v[g*8 + k] || b_wr_done[g*8 + k])
                        grp[g] <= {1'b1, 5'(g*8 + k), b_rsp_tag[(g*8 + k)*16 +: 16], b_rsp_beat[(g*8 + k)*4 +: 4],
                                   b_rsp_data[(g*8 + k)*256 +: 256], b_wr_done[g*8 + k]};
            end
            rsp <= '0;
            for (g = NPC / 8 - 1; g >= 0; g = g - 1) if (grp[g][RW-1]) rsp <= grp[g];
        end
endmodule

module ot_chip_v41x_pdie #(
    parameter integer N_FAR   = 5,     // spine <-> farthest tiles (5.8 mm at 1/4 scale)
    parameter integer N_FAR2  = 4,
    parameter integer N_MID   = 2,
    parameter integer N_NEAR  = 1,
    parameter integer N_KEY   = 2,     // spine <-> each stack's key streamer
    parameter integer N_COLL  = 3,     // spine <-> the collective engines at the link edges
    parameter integer N_SER   = 3,     // spine <-> the SerDes edge (stage hop)
    parameter integer STG     = 16,    // KV staging words a slot (the die's KV_STG, reduced)
    parameter integer TILE_RT = 0      // 1: the four pinned tiles are the ROUTED physical tile
                                       //    (ot_chip_v41x_ptile NQ = 2, NM = 0 at the tile slot, its
                                       //    ORFS abstract); 0: the ot_pdie_tile_io placeholder
) (
    input  wire         clk,
    input  wire         rst_n,
    output wire [63:0]  obs
);
    localparam integer OPW = 380, RESW = 140, RECW = 547, FLW = 512;
    localparam integer NS = 4;
    wire [15:0] fo [0:31];

    // ------------------------------------------------------------------ four HBM3E stacks
    wire [NS-1:0] pm_v, pm_rdy, pm_we, ps_v, ps_rdy, pk_wd;
    wire [NS*28-1:0] pm_addr; wire [NS*4-1:0] pm_len, ps_beat; wire [NS*16-1:0] pm_tag, ps_tag;
    wire [NS*256-1:0] pm_wdata, ps_data; wire [NS*32-1:0] pm_wstrb;
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_s
        wire [343:0] kreq_s, kreq_t;
        wire [282:0] krsp_t, krsp_s;
        ot_chip_v41x_pdie_src #(.W(344), .SEED(11 + s)) u_ksrc (.clk(clk), .rst_n(rst_n), .q(kreq_s));
        ot_chip_v41x_pdie_trunk #(.W(344), .N(N_KEY)) u_ktr (.clk(clk), .d(kreq_s), .q(kreq_t));
        wire [31:0] b_v, b_rdy, b_we, b_wr_done, b_rsp_v, b_rsp_rdy;
        wire [32*28-1:0] b_addr; wire [32*4-1:0] b_len, b_rsp_beat; wire [32*16-1:0] b_tag, b_rsp_tag;
        wire [32*256-1:0] b_wdata, b_rsp_data; wire [32*32-1:0] b_wstrb;
        ot_chip_v41x_pdie_kstream u_ks (
            .clk(clk), .rst_n(rst_n), .req(kreq_t), .rsp(krsp_t),
            .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag), .b_we(b_we),
            .b_wdata(b_wdata), .b_wstrb(b_wstrb), .b_wr_done(b_wr_done), .b_rsp_v(b_rsp_v),
            .b_rsp_rdy(b_rsp_rdy), .b_rsp_tag(b_rsp_tag), .b_rsp_beat(b_rsp_beat), .b_rsp_data(b_rsp_data));
        ot_chip_v41x_pdie_trunk #(.W(283), .N(N_KEY)) u_krt (.clk(clk), .d(krsp_t), .q(krsp_s));
        ot_chip_v41x_pdie_sink #(.W(283)) u_ksnk (.clk(clk), .d(krsp_s), .o(fo[s]));
        wire [31:0] h_v, h_rdy, h_we, h_wr_done, r_v, r_rdy;
        wire [32*28-1:0] h_addr; wire [32*4-1:0] h_len, r_beat; wire [32*17-1:0] h_tag, r_tag;
        wire [32*256-1:0] h_wdata, r_data; wire [32*32-1:0] h_wstrb;
        ot_chip_v41x_hbm_karb #(.NPC(32), .AW(28), .TAGW(16)) u_arb (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag), .b_we(b_we),
            .b_wdata(b_wdata), .b_wstrb(b_wstrb), .b_wr_done(b_wr_done),
            .b_rsp_v(b_rsp_v), .b_rsp_rdy(b_rsp_rdy), .b_rsp_tag(b_rsp_tag), .b_rsp_beat(b_rsp_beat),
            .b_rsp_data(b_rsp_data),
            .k_v(pm_v[s]), .k_rdy(pm_rdy[s]), .k_addr(pm_addr[s*28 +: 28]), .k_len(pm_len[s*4 +: 4]),
            .k_tag(pm_tag[s*16 +: 16]), .k_we(pm_we[s]), .k_wdata(pm_wdata[s*256 +: 256]),
            .k_wstrb(pm_wstrb[s*32 +: 32]), .k_wr_done(pk_wd[s]),
            .k_rsp_v(ps_v[s]), .k_rsp_rdy(ps_rdy[s]), .k_rsp_tag(ps_tag[s*16 +: 16]),
            .k_rsp_beat(ps_beat[s*4 +: 4]), .k_rsp_data(ps_data[s*256 +: 256]),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done),
            .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data),
            .k_grants(), .b_grants(), .contended());
        ot_hbm3e_phy_v41x_s4 u_phy (
            .clk(clk), .rst_n(rst_n),
            .k_v(h_v), .k_rdy(h_rdy), .k_addr(h_addr), .k_len(h_len), .k_tag(h_tag), .k_we(h_we),
            .k_wdata(h_wdata), .k_wstrb(h_wstrb), .k_wr_done(h_wr_done),
            .kr_v(r_v), .kr_rdy(r_rdy), .kr_tag(r_tag), .kr_beat(r_beat), .kr_data(r_data),
            .w_v(1'b0), .w_rdy(), .w_addr(24'd0), .w_len(6'd0), .w_tag(10'd0), .w_room(), .wr_v(),
            .wr_rdy(8'd0), .wr_tag(), .wr_beat(), .wr_data(), .k_oor(), .refreshes(), .w_reads());
    end endgenerate

    // ------------------------------------------------------------------ KV prefetch (spine), adopted wiring
    wire [2047:0] kvq;
    wire [1619:0] kvin;
    ot_chip_v41x_pdie_src #(.W(1620), .SEED(3)) u_kvsrc (.clk(clk), .rst_n(rst_n), .q(kvin));
    wire kv_ok, kv_fault; wire [4:0] kv_code; wire [31:0] st0, st1, st2, st3, st4, st5;
    ot_chip_v41x_kv_prefetch #(.STG(STG), .SAW($clog2(STG)), .WQD(8)) u_kv (
        .clk(clk), .rst_n(rst_n), .base(kvin[23:0]),
        .kvd_v(kvin[24]), .kvd_wbase(kvin[48:25]), .kvd_ts(kvin[72:49]), .kvd_ks(kvin[96:73]),
        .kvd_js(kvin[120:97]), .kvd_tiles(kvin[136:121]), .kvd_k(kvin[152:137]), .kvd_hg(kvin[154:153]),
        .kv_ok(kv_ok),
        .re(kvin[155]), .raddr(kvin[251:156]), .q(kvq),
        .we(kvin[259:252]), .waddr(kvin[451:260]), .wdata(kvin[707:452]),
        .xwe(kvin[723:708]), .xwaddr(kvin[1107:724]), .xwdata(kvin[1619:1108]),
        .m_v(pm_v), .m_rdy(pm_rdy), .m_addr(pm_addr), .m_len(pm_len), .m_tag(pm_tag), .m_we(pm_we),
        .m_wdata(pm_wdata), .m_wstrb(pm_wstrb), .s_v(ps_v), .s_rdy(ps_rdy), .s_tag(ps_tag), .s_beat(ps_beat),
        .s_data(ps_data), .fault(kv_fault), .fault_code(kv_code), .st_ops(st0), .st_words(st1),
        .st_sectors_written(st2), .st_refetches(st3), .st_wq_high(st4), .st_hold_cycles(st5));
    ot_chip_v41x_pdie_sink #(.W(2048 + 1 + 1 + 5 + 4)) u_kvsnk (.clk(clk),
        .d({kvq, kv_ok, kv_fault, kv_code, pk_wd}), .o(fo[4]));

    // ------------------------------------------------------------------ tiles: 4 with pins, 44 blockages
    localparam integer NIO = 4;
    genvar t;
    generate for (t = 0; t < NIO; t = t + 1) begin : g_tio
        localparam integer NT = (t == 0) ? N_FAR : (t == 1) ? N_FAR2 : (t == 2) ? N_MID : N_NEAR;
        wire [OPW-1:0] op_s, op_t;
        wire [RESW-1:0] res_t, res_s;
        ot_chip_v41x_pdie_src #(.W(OPW), .SEED(21 + t)) u_src (.clk(clk), .rst_n(rst_n), .q(op_s));
        ot_chip_v41x_pdie_trunk #(.W(OPW), .N(NT)) u_op (.clk(clk), .d(op_s), .q(op_t));
        if (TILE_RT) begin : g_rt
            // op_t: the tile's spine-edge inputs {s_x_*, s_o_cr, s_d_*} (361 of OPW bits);
            // res_t: its results {r_*} (NQ = 2: 140 bits), with d_rdy and idle folded into bit 0
            wire [1:0] r_v, r_f; wire [31:0] r_rg, r_bf; wire [7:0] r_tag; wire [63:0] r_y;
            wire d_rdy, idle;
            ot_chip_v41x_ptile u_tile (
                .clk(clk), .rst_n(rst_n),
                .s_d_v(op_t[0]), .s_d_rdy(d_rdy), .s_d_plg(op_t[4:1]), .s_d_nb(op_t[14:5]),
                .s_d_nrows(op_t[30:15]), .s_d_wbase(op_t[50:31]), .s_d_ind(op_t[51]), .s_d_eid(op_t[60:52]),
                .s_d_estride(op_t[80:61]), .s_d_fp4(op_t[81]), .s_d_tag(op_t[85:82]), .s_o_cr(op_t[86]),
                .s_x_we(op_t[87]), .s_x_pos(op_t[90:88]), .s_x_addr(op_t[96:91]), .s_x_data(op_t[360:97]),
                .r_v(r_v), .r_rg(r_rg), .r_tag(r_tag), .r_y(r_y), .r_bf(r_bf), .r_f(r_f),
                .m_d_v(1'b0), .m_d_rdy(), .m_d_plg(4'd0), .m_d_nb(14'd0), .m_d_nrows(16'd0), .m_d_wbase(20'd0),
                .m_d_ind(1'b0), .m_d_eid(9'd0), .m_d_estride(20'd0), .m_d_tag(4'd0), .m_o_cr(1'b0),
                .m_x_we(1'b0), .m_x_pos(3'd0), .m_x_addr(9'd0), .m_x_data(128'd0),
                .m_r_v(), .m_r_rg(), .m_r_tag(), .m_r_mask(), .m_r_y(), .m_r_bf(), .m_r_f(), .idle(idle));
            assign res_t = {r_f, r_bf, r_y, r_tag, r_rg, r_v[1], r_v[0] ^ d_rdy ^ idle};
        end else begin : g_ph
            ot_pdie_tile_io u_tile (.clk(clk), .op_in(op_t), .res_out(res_t));
        end
        ot_chip_v41x_pdie_trunk #(.W(RESW), .N(NT)) u_res (.clk(clk), .d(res_t), .q(res_s));
        ot_chip_v41x_pdie_sink #(.W(RESW)) u_snk (.clk(clk), .d(res_s), .o(fo[5 + t]));
    end endgenerate
    generate for (t = 0; t < 44; t = t + 1) begin : g_tbk
        ot_pdie_tile_bk u_tile (.clk(clk));
    end endgenerate

    // ------------------------------------------------------------------ collectives and link edges
    //   c = 0: the in-package (UCIe) level at the UCIe edge; c = 1: the package-pair level at the SerDes edge
    genvar c;
    generate for (c = 0; c < 2; c = c + 1) begin : g_coll
        wire [RECW-1:0] rin_s, rin_t, rout_t, rout_s;
        wire [FLW-1:0] lk_out, lk_in;
        ot_chip_v41x_pdie_src #(.W(RECW), .SEED(31 + c)) u_src (.clk(clk), .rst_n(rst_n), .q(rin_s));
        ot_chip_v41x_pdie_trunk #(.W(RECW), .N(N_COLL)) u_in (.clk(clk), .d(rin_s), .q(rin_t));
        ot_pdie_coll u_coll (.clk(clk), .rec_in(rin_t), .rec_out(rout_t), .link_out(lk_out), .link_in(lk_in));
        ot_chip_v41x_pdie_trunk #(.W(RECW), .N(N_COLL)) u_out (.clk(clk), .d(rout_t), .q(rout_s));
        ot_chip_v41x_pdie_sink #(.W(RECW)) u_snk (.clk(clk), .d(rout_s), .o(fo[9 + c]));
        if (c == 0) begin : g_ucie
            ot_pdie_ucie u_link (.clk(clk), .tx(lk_out), .rx(lk_in));
        end else begin : g_ser
            ot_pdie_serdes u_link (.clk(clk), .tx(lk_out), .rx(lk_in));
        end
    end endgenerate
    // stage hop: spine <-> the SerDes edge's hop port (a second SerDes placeholder, the stage-hop lanes)
    wire [FLW-1:0] hop_s, hop_t, hin_t, hin_s;
    ot_chip_v41x_pdie_src #(.W(FLW), .SEED(41)) u_hsrc (.clk(clk), .rst_n(rst_n), .q(hop_s));
    ot_chip_v41x_pdie_trunk #(.W(FLW), .N(N_SER)) u_htx (.clk(clk), .d(hop_s), .q(hop_t));
    ot_pdie_serdes u_hop (.clk(clk), .tx(hop_t), .rx(hin_t));
    ot_chip_v41x_pdie_trunk #(.W(FLW), .N(N_SER)) u_hrx (.clk(clk), .d(hin_t), .q(hin_s));
    ot_chip_v41x_pdie_sink #(.W(FLW)) u_hsnk (.clk(clk), .d(hin_s), .o(fo[11]));

    genvar o;
    generate for (o = 12; o < 32; o = o + 1) begin : g_fz
        assign fo[o] = 16'd0;
    end endgenerate
    reg [63:0] ob, fb;
    integer j;
    always @(*) begin
        fb = 64'd0;
        for (j = 0; j < 12; j = j + 1) fb[(j % 4) * 16 +: 16] = fb[(j % 4) * 16 +: 16] ^ fo[j];
    end
    always @(posedge clk) ob <= fb;
    assign obs = ob;
endmodule
