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
// X: dsdv_idx_rg3_bx / _bxn / _bxm / _bxmh live in dsdv_idx_rg3_bx.sv.


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
