`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// STW-S81c-TOK4-BAND (10-22, tree MU.BAL.SX.3): the BANDED idx rg3 -- the clock-rule successor of the one-root rg3
// kits (rg3p 26,984 / rg3nqq2 32,218 sinks on ONE ck: TT spread 223-233 ps).  The reader is cut at existing registers
// into hard bands, each with its own small clock tree and registered faces (cut analysis:
// results/arch/s81_band_1022/cut_analysis.json):
//   R   dsdv_idx_rg3_br  (generated from dsdv_idx_rg3.sv by mk_rg3_br.py): reader control, q / s chain front, rqo
//   X   dsdv_idx_rg3_bx  response lanes (rri pins, RH relays), landing writes + 8 landing SRAMs, S/C/K read stages,
//                        key mux, kq = the old per-column kr[0] (one shared copy)
//   S01 dsdv_idx_rg3_bs01  chunk columns 0, 1 + tail adder u_a0
//   S23 dsdv_idx_rg3_bs23  chunk columns 2, 3 + u_a1 / u_a2 / BF16 + the q / s / st output stage (qo / so / st pins)
// dsdv_idx_rg3_bf = the wires-only flat parent (lp.py input).  With LX = PD = 0 it is cycle-exact to
// dsdv_idx_rg3 #(IH 0, OH 1, KR 1) on qo / so / rqo, and st one edge later (S23's st stage) -- tb_dsdv_idx_rg3_band.
// The landed parent (lp.py, D 2 / E 1: +2 edges a crossing) re-schedules the engine loop by LX = 8 (R -> X, X -> S,
// S01 -> S23, S23 -> R) and pads the S23 tail half by PD = 2 to meet the landed u_a0 result.
// ---------------------------------------------------------------------------------------------------------------------

// ===================================================================================================================== X
module dsdv_idx_rg3_bx #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer RH = 1
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [1087:0] rri,           // 4 x 272-b response lanes {data 256, tag10, beat 4, pop, v}
    input  wire [14:0]   sx_i,          // R's S stage {gatk[1], s_v, s_it[34:25], s_it[2:0]}
    output wire [67:0]   xr_o,          // {rkc[3:0], rrr[3][15:0], .., rrr[0][15:0]}
    output wire [543:0]  kq_o           // key word, one edge after the K stage (= the old kr[0])
);
    // reset: same forest depth as dsdv_idx_rg3 (rs 2 + u_r0 3 + u_r1 3 edges) -> same release edge
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire       r0;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r0 (.clk(ck), .rst_n_in(rs[1]), .rst_n(r0));
    wire [2:0] rl;                                  // [0] rrr valid / pop (rg3 rl[1]), [1] lw_v (rl[22]), [2] c_v (rl[25])
    ot_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r1 (.clk(ck), .rst_n_in(r0), .rst_n(rl));
    // response relay hops (rh[0] = the N pin flops) and the landing-side lane register
    wire [1087:0] rrh;
    generate if (RH == 0) begin : g_khrz
        assign rrh = rri;
    end else begin : g_khrp
        (* keep = "true" *) reg [1087:0] rh [0:RH-1];
        always @(posedge ck) begin
            rh[0] <= rri;
            for (int k = 1; k < RH; k++) rh[k] <= rh[k - 1];
        end
        assign rrh = rh[RH - 1];
    end endgenerate
    reg [3:0][271:0] rrr;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin rrr[0][1:0] <= 2'd0; rrr[1][1:0] <= 2'd0; rrr[2][1:0] <= 2'd0; rrr[3][1:0] <= 2'd0; end
        else begin
            rrr[0][1:0] <= rrh[1:0]; rrr[1][1:0] <= rrh[273:272]; rrr[2][1:0] <= rrh[545:544]; rrr[3][1:0] <= rrh[817:816];
        end
    always @(posedge ck) begin
        rrr[0][271:2] <= rrh[271:2]; rrr[1][271:2] <= rrh[543:274]; rrr[2][271:2] <= rrh[815:546]; rrr[3][271:2] <= rrh[1087:818];
    end
    (* keep = "true" *) reg [3:0] rkc;
    always @(posedge ck) rkc <= {rrh[817], rrh[545], rrh[273], rrh[1]};
    assign xr_o = {rkc, rrr[3][15:0], rrr[2][15:0], rrr[1][15:0], rrr[0][15:0]};
    // landing writes (registered one edge after rrr; the same functions of rrr as R's slot-count copy)
    wire [3:0][16:0] rt;
    wire [3:0][3:0]  rb;
    wire [3:0]       mine;
    genvar gu;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_rdw
        assign rt[gu] = {2'b11, rrr[gu][15:6], 5'd0};
        assign rb[gu] = rrr[gu][5:2];
        assign mine[gu] = rrr[gu][0] && !(MUT == 5 && rt[gu][7]);
    end endgenerate
    reg  [3:0]  lw_v, lw_h1;
    reg  [3:0][9:0] lw_a;
    reg  [3:0][255:0] lw_d;
    integer u;
    always @(posedge ck) for (u = 0; u < 4; u = u + 1) begin : g_rsp
        reg g; reg [3:0] s_; reg [3:0] cl; reg sc; reg [3:0] bt;
        g = rt[u][14]; s_ = {rt[u][5], rt[u][13:11]}; cl = rt[u][10:7]; sc = rt[u][6]; bt = rb[u];
        lw_d[u] <= rrr[u][271:16];
        lw_h1[u] <= !sc && bt[0];
        if (!sc) lw_a[u] <= {2'b00, s_, g ? cl : cl + {3'd0, bt[1]}};
        else if (!g) lw_a[u] <= {5'b01000, s_, bt[0]};
        else lw_a[u] <= {2'b10, s_, cl};
    end
    always @(posedge ck or negedge rl[1]) if (!rl[1]) lw_v <= 4'd0; else lw_v <= mine;
    // read side: R's S stage, the C stage copy, the landing SRAMs, scale / key selects (as dsdv_idx_rg3)
    wire        gatk1 = sx_i[14];
    wire        s_v   = sx_i[13];
    wire [34:25] s_hi = sx_i[12:3];
    wire [2:0]  s_lo  = sx_i[2:0];
    reg         c_v;
    reg  [34:25] c_hi;
    always @(posedge ck or negedge rl[2]) if (!rl[2]) c_v <= 1'b0; else c_v <= s_v;
    always @(posedge ck) c_hi <= s_hi;
    wire [1:0]  su_b = s_hi[34:33];                 // == R's su_a / su_b (registered from ih[34:33] with s_it)
    wire [1:0]  c_u  = c_hi[34:33];
    wire [9:0]  s_row = gatk1 ? {2'b10, s_hi[32:29], s_hi[28:25]} : {5'b01000, s_hi[32:29], s_hi[28]};
    wire [9:0]  c_row = {2'b00, c_hi[32:29], c_hi[28:25]};
    wire [3:0][255:0] h0q, h1q;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_land
        wire rs0 = s_v && su_b == 2'(gu);
        wire rc  = c_v && c_u == 2'(gu);
        dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_h0 (
            .ck(ck), .re(rs0 || rc), .ra(rs0 ? s_row : c_row), .rd(h0q[gu]),
            .we(lw_v[gu] && !lw_h1[gu]), .wa(lw_a[gu]), .wd(lw_d[gu]));
        dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_h1 (
            .ck(ck), .re(rc), .ra(c_row), .rd(h1q[gu]),
            .we(lw_v[gu] && lw_h1[gu]), .wa(lw_a[gu]), .wd(lw_d[gu]));
    end endgenerate
    (* keep = "true" *) reg [31:0] ssel;
    always @(posedge ck) begin : g_ss
        integer a_;
        for (a_ = 0; a_ < 32; a_ = a_ + 1) ssel[a_] <= su_b == 2'(a_ / 8) && s_lo == 3'(a_ % 8);
    end
    reg [31:0] k_sc;
    always @(posedge ck) begin : g_sc
        reg [31:0] x; integer a_;
        x = 32'd0;
        for (a_ = 0; a_ < 32; a_ = a_ + 1) x = x | ({32{ssel[a_]}} & h0q[a_ / 8][32 * (a_ % 8) +: 32]);
        k_sc <= x;
    end
    (* keep = "true" *) reg [1:0] cu_a, cu_b;
    (* keep = "true" *) reg [31:0] ks0, ks1, ks2, ks3;
    always @(posedge ck) begin
        cu_a <= s_hi[34:33]; cu_b <= s_hi[34:33];
        ks0 <= {{16{cu_b == 2'd0}}, {16{cu_a == 2'd0}}}; ks1 <= {{16{cu_b == 2'd1}}, {16{cu_a == 2'd1}}};
        ks2 <= {{16{cu_b == 2'd2}}, {16{cu_a == 2'd2}}}; ks3 <= {{16{cu_b == 2'd3}}, {16{cu_a == 2'd3}}};
    end
    wire [543:0] k_key;
    genvar gk;
    generate for (gk = 0; gk < 32; gk = gk + 1) begin : g_km
        localparam integer H = gk / 16, O = 16 * (gk % 16);
        wire [15:0] d0_ = ({16{ks0[gk]}} & (H ? h1q[0][O +: 16] : h0q[0][O +: 16])) | ({16{ks1[gk]}} & (H ? h1q[1][O +: 16] : h0q[1][O +: 16])) |
                          ({16{ks2[gk]}} & (H ? h1q[2][O +: 16] : h0q[2][O +: 16])) | ({16{ks3[gk]}} & (H ? h1q[3][O +: 16] : h0q[3][O +: 16]));
        assign k_key[256 * H + O +: 16] = d0_;
    end endgenerate
    assign k_key[543:512] = k_sc;
    (* keep = "true" *) reg [543:0] kq;            // the old kr[0] of every column, one copy (S face)
    always @(posedge ck) kq <= k_key;
    assign kq_o = kq;
endmodule

// ============================================================================ S: shared column inputs + chunk columns
// One band's chunk columns: the query-code / head / scale / valid stages of dsdv_idx_rg3's KR relays (cr / hr / vr; the
// key's kr[0] is X's kq, kr[1..KR-1] are here), one shared copy for the band's columns, then the columns.
module dsdv_idx_rg3_scols #(
    parameter integer C0 = 0,           // first column index (hb = 8 C)
    parameter integer NC = 2,
    parameter integer KR = 1
) (
    input  wire              ck,
    input  wire [NC-1:0]     rl,         // column resets (rg3 rl[26 + c])
    input  wire [511:0]      qlc,        // = rg3 qlc_c (qoi[512:1] one edge later)
    input  wire [56:0]       ql_i,       // {ql_v, ql_h, ql_sw} (same edge as qlc)
    input  wire [543:0]      kq_i,       // = rg3 kr[0]
    output wire [NC*32-1:0]  csum,
    output wire [NC-1:0]     cfl
);
    (* keep = "true" *) reg [511:0] cr [0:KR-1];
    (* keep = "true" *) reg [55:0]  hr [0:KR-1];
    (* keep = "true" *) reg [KR-1:0] vr;
    wire [543:0] kk;
    always @(posedge ck) begin
        cr[0] <= qlc; hr[0] <= ql_i[55:0];
        for (int k = 1; k < KR; k++) begin cr[k] <= cr[k - 1]; hr[k] <= hr[k - 1]; end
    end
    always @(posedge ck or negedge rl[0]) if (!rl[0]) vr <= '0; else vr <= KR'({vr, ql_i[56]});
    generate if (KR == 1) begin : g_k1
        assign kk = kq_i;
    end else begin : g_kn
        (* keep = "true" *) reg [543:0] kr [1:KR-1];
        always @(posedge ck) begin
            kr[1] <= kq_i;
            for (int k = 2; k < KR; k++) kr[k] <= kr[k - 1];
        end
        assign kk = kr[KR - 1];
    end endgenerate
    wire [7:0]  qh_c = hr[KR - 1][55:48];
    wire [47:0] qs_c = hr[KR - 1][47:0];
    genvar gc;
    generate for (gc = 0; gc < NC; gc = gc + 1) begin : g_ch
        dsdv_idx_rg2_chunk u_c (.clk(ck), .rst_n(rl[gc]), .hb(8'(8 * (C0 + gc))), .ql_v(vr[KR - 1]), .ql_head(qh_c),
            .ql_codes(cr[KR - 1]), .ql_sc(qs_c[31:0]), .ql_w(qs_c[47:32]), .k_key(kk),
            .c_sum(csum[32 * gc +: 32]), .c_fault(cfl[gc]));
    end endgenerate
endmodule

// ============================================================================ S01: columns 0, 1 + u_a0
module dsdv_idx_rg3_bs01 #(
    parameter integer KR = 1
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [512:0]  qoi_i,         // R's q chain (codes = qoi[512:1])
    input  wire [56:0]   ql_i,
    input  wire [543:0]  kq_i,
    output wire [34:0]   a0_o           // {pf0 msb, e01, s01}: u_a0 result + its fault line
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire       r0;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r0 (.clk(ck), .rst_n_in(rs[1]), .rst_n(r0));
    wire [1:0] rl;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r1 (.clk(ck), .rst_n_in(r0), .rst_n(rl));
    (* keep = "true" *) reg [511:0] qlc;
    always @(posedge ck) qlc <= qoi_i[512:1];
    wire [63:0] cs; wire [1:0] cf;
    dsdv_idx_rg3_scols #(.C0(0), .NC(2), .KR(KR)) u_cols (.ck(ck), .rl(rl), .qlc(qlc), .ql_i(ql_i), .kq_i(kq_i),
        .csum(cs), .cfl(cf));
    // tail, first half (dsdv_idx_rg2_tail: rsum / rf input register, u_a0, pf0)
    localparam integer FAL = 8;
    reg [63:0] rsum; reg [1:0] rf;
    always @(posedge ck) begin rsum <= cs; rf <= cf; end
    wire [31:0] s01; wire [1:0] e01;
    dsdv_idx_rg2_fadd u_a0 (.clk(ck), .a(rsum[31:0]), .b(rsum[63:32]), .y(s01), .err(e01));
    reg [FAL-1:0] pf0;
    always @(posedge ck) pf0 <= {pf0[FAL-2:0], rf[0] || rf[1]};
    assign a0_o = {pf0[FAL-1], e01, s01};
endmodule

// ============================================================================ S23: columns 2, 3 + u_a1 / u_a2 + outputs
module dsdv_idx_rg3_bs23 #(
    parameter integer KR = 1,
    parameter integer PD = 0            // landed: s23 / e23 / pf1 wait PD edges for the landed u_a0 result
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [512:0]  qoi_i,
    input  wire [275:0]  soi_i,
    input  wire [9:0]    st_i,
    input  wire [56:0]   ql_i,
    input  wire [543:0]  kq_i,
    input  wire [34:0]   a0_i,
    output wire [16:0]   sc_o,          // {o_fault, o_score} to R
    output wire [512:0]  qo,
    output wire [275:0]  so,
    output wire [9:0]    st
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire       r0;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r0 (.clk(ck), .rst_n_in(rs[1]), .rst_n(r0));
    wire [1:0] rl;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r1 (.clk(ck), .rst_n_in(r0), .rst_n(rl));
    // the chain output stage (rg3 OH relay qh[0] / sh[0]; st one stage, sticky status): no reset, flushes like OH.
    // qh[512:1] is also this band's query-code copy (== qlc_c: qoi one edge later).
    (* keep = "true" *) reg [512:0] qh;
    (* keep = "true" *) reg [275:0] sh;
    (* keep = "true" *) reg [9:0]   sth;
    always @(posedge ck) begin qh <= qoi_i; sh <= soi_i; sth <= st_i; end
    assign qo = qh; assign so = sh; assign st = sth;
    wire [63:0] cs; wire [1:0] cf;
    dsdv_idx_rg3_scols #(.C0(2), .NC(2), .KR(KR)) u_cols (.ck(ck), .rl(rl), .qlc(qh[512:1]), .ql_i(ql_i), .kq_i(kq_i),
        .csum(cs), .cfl(cf));
    // tail, second half: u_a1 + pf1 (padded PD), u_a2, pf2, BF16, output register
    localparam integer FAL = 8;
    reg [63:0] rsum; reg [1:0] rf;
    always @(posedge ck) begin rsum <= cs; rf <= cf; end
    wire [31:0] s23x; wire [1:0] e23x;
    dsdv_idx_rg2_fadd u_a1 (.clk(ck), .a(rsum[31:0]), .b(rsum[63:32]), .y(s23x), .err(e23x));
    reg [FAL-1:0] pf1;
    always @(posedge ck) pf1 <= {pf1[FAL-2:0], rf[0] || rf[1]};
    wire [31:0] s23; wire [1:0] e23; wire p1m;
    generate if (PD == 0) begin : g_pz
        assign s23 = s23x; assign e23 = e23x; assign p1m = pf1[FAL-1];
    end else begin : g_pp
        (* keep = "true" *) reg [34:0] pd [0:PD-1];
        always @(posedge ck) begin
            pd[0] <= {pf1[FAL-1], e23x, s23x};
            for (int k = 1; k < PD; k++) pd[k] <= pd[k - 1];
        end
        assign {p1m, e23, s23} = pd[PD - 1];
    end endgenerate
    wire [31:0] s01 = a0_i[31:0]; wire [1:0] e01 = a0_i[33:32]; wire p0m = a0_i[34];
    wire f01 = p0m || (e01 != 2'd0), f23 = p1m || (e23 != 2'd0);
    wire [31:0] s; wire [1:0] e;
    dsdv_idx_rg2_fadd u_a2 (.clk(ck), .a(s01), .b(s23), .y(s), .err(e));
    reg [FAL-1:0] pf2;
    always @(posedge ck) pf2 <= {pf2[FAL-2:0], f01 || f23};
    wire ft = pf2[FAL-1] || (e != 2'd0);
    wire [15:0] s16; wire so_;
    ot_hdc_v41x_bf16 u_b (.x(s), .y(s16), .ovf(so_));
    reg [15:0] o_score; reg o_fault;
    always @(posedge ck) begin o_fault <= ft || so_; o_score <= (ft || so_) ? 16'd0 : s16; end
    assign sc_o = {o_fault, o_score};
endmodule

// ============================================================================ flat parent (wires only; lp.py input)
module dsdv_idx_rg3_bf #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQR = 24,
    parameter integer IQD = 512,
    parameter integer SQD = 256,
    parameter integer LFD = 256,
    parameter integer EL = 124,
    parameter integer RH = 1,
    parameter integer KR = 1,
    parameter integer LX = 0,
    parameter integer PD = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,
    output wire [512:0]  qo,
    input  wire [275:0]  si,
    output wire [275:0]  so,
    output wire [183:0]  rqo,
    input  wire [1087:0] rri,
    output wire [9:0]    st
);
    wire [512:0] qoi;
    wire [275:0] soi;
    wire [9:0]   sti;
    wire [56:0]  ql;
    wire [14:0]  sx;
    wire [67:0]  xr;
    wire [16:0]  sc;
    wire [543:0] kq;
    wire [34:0]  a0;
    dsdv_idx_rg3_br #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .IH(0),
                      .KR(KR), .LX(LX)) u_r (
        .ck(ck), .rst(rst), .sid(sid), .qi(qi), .si(si), .rqo(rqo), .qoi_o(qoi), .soi_o(soi), .st_o(sti), .ql_o(ql),
        .sx_o(sx), .xr_i(xr), .sc_i(sc));
    dsdv_idx_rg3_bx #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .RH(RH)) u_x (
        .ck(ck), .rst(rst), .rri(rri), .sx_i(sx), .xr_o(xr), .kq_o(kq));
    dsdv_idx_rg3_bs01 #(.KR(KR)) u_s01 (.ck(ck), .rst(rst), .qoi_i(qoi), .ql_i(ql), .kq_i(kq), .a0_o(a0));
    dsdv_idx_rg3_bs23 #(.KR(KR), .PD(PD)) u_s23 (.ck(ck), .rst(rst), .qoi_i(qoi), .soi_i(soi), .st_i(sti), .ql_i(ql),
        .kq_i(kq), .a0_i(a0), .sc_o(sc), .qo(qo), .so(so), .st(st));
endmodule
