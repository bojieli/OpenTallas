// SOURCE-ONLY RSO CANDIDATE: new master/port; existing closed views do not bind this variant.
`timescale 1ns/1ps
// ot_engc_pbank (el1011-ds-misc/engram, 2026-10-11): ONE BANK of the dsfd_engram_c prefetch buffer as a hardened tile
// (6 x ot_sram_1r1w_256x256_m2_r2c2 = groups 0..5 of the bank, compact1536 addressing as ot_dsrom_engram_prefetch_h).
// ALL-TILE engram_c (textbook class 1): the bank is a tile with its own clock tree; every input is a pin flop (= the old
// per-bank W2 / R1 copies), every output a flop.
//   write  P   pin flops {w_oh 6 (valid-folded group one-hot), w_a 8, w_d BW, x_d XW}
//          W3  per-macro {w_ce, w_addr, data} (kept copies)         -> the macro writes at the next edge
//          x_oh / x_a / x_do = the pin flops (write TRANSIT to the next bank tile: registered, no logic)
//   read   P   pin flops {r_oh 6, r_a 8}   R2 per-macro {r_ce, r_addr}   macro samples at the next edge
//          R3  capture of rd_out (no logic before it)   R4 pair select   R5 3:1   R6 out flop r_d (tile face)
//          r_d is the OR of the selected group (zero when no group is read): read latency P -> r_d = 6 edges.
// Bank 2 (64 b) uses this tile with w_d[255:64] = 0 (the old zero pad) and ignores r_d[255:64].
module ot_engc_pbank_rso #(
    parameter integer BW = 256,
    parameter integer XW = 64,
    // CKL: per-SRAM clock leaf (el1011-ds-misc/engram 2026-10-11, T_PBC macro clock fix).  TritonCTS builds the 6 SRAM
    // clock pins as a separate macro tree that ends with NO leaf buffers (2 branch nets, 3 SRAMs each, 124-188 um,
    // SRAM clk slew 239 ps FF -> slew-dependent library hold 42-61 ps on every wd_in / addr pin; CTS macro-clustering
    // options do not change it, CTS-stop x1-x3).  An explicit clock cell per group gives each SRAM its own short driver:
    //   (gated off while the tile is in reset: only valid-reset / unreset data flops sit on it, no observable change)
    //   0 = none (T_PBB as closed);  1 = per-group ICG drives only the SRAM clk;
    //   2 = per-group ICG drives the SRAM clk AND its access (W3 / R2) and capture flops (macro + launch flops on one leaf).
    parameter integer CKL = 0
) (
    input  wire          ck,
    input  wire          rst,          // async die reset (active low); synchronised here (2 flops, as every tile)
    input  wire [5:0]    w_oh,
    input  wire [7:0]    w_a,
    input  wire [BW-1:0] w_d,
    input  wire [XW-1:0] x_d,
    output wire [5:0]    x_oh,
    output wire [7:0]    x_a,
    output wire [XW-1:0] x_do,
    input  wire [5:0]    r_oh,
    input  wire [7:0]    r_a,
    output reg  [BW-1:0] r_d,
    output wire rso
);
    localparam integer NG = 6;
    reg [1:0] rs_q;
    always @(posedge ck or negedge rst) if (!rst) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    assign rso = rn;
    // ---------------- pin flops (datapath unreset; one-hots reset)
    reg [5:0] woh_p, roh_p; reg [7:0] wa_p, ra_p; reg [BW-1:0] wd_p; reg [XW-1:0] xd_p;
    always @(posedge ck or negedge rn) if (!rn) begin woh_p <= 6'd0; roh_p <= 6'd0; end
                                       else begin woh_p <= w_oh; roh_p <= r_oh; end
    always @(posedge ck) begin wa_p <= w_a; ra_p <= r_a; wd_p <= w_d; xd_p <= x_d; end
    assign x_oh = woh_p; assign x_a = wa_p; assign x_do = xd_p;

    wire [BW-1:0] cap [0:NG-1];
    wire [NG-1:0] sel3;
    genvar g;
    generate for (g = 0; g < NG; g = g + 1) begin : g_grp
        wire w3_v, r2_v; wire [7:0] w3_a, r2_a; wire [BW-1:0] w3_d; wire [255:0] rd_out;
        wire ckm;                       // SRAM clock
        wire ckg;                       // access / capture flop clock
        if (CKL == 0) begin : g_ck0 assign ckm = ck; end
        else begin : g_ckl
`ifdef SYNTHESIS
            // ENA = the synchronised reset (clock runs once out of reset).  NOT a tie: OpenSTA propagates the ENA=1 constant
            // through the ICG statetable and drops the CLK->GCLK arc (CTS-stop x5: SRAM clk unclocked, 1,536 unconstrained D).
            ICGx4_ASAP7_75t_R u_ckl (.CLK(ck), .ENA(rn), .SE(1'b0), .GCLK(ckm));
`else
            assign ckm = ck;
`endif
        end
        if (CKL == 2) begin : g_ckg2 assign ckg = ckm; end else begin : g_ckg0 assign ckg = ck; end
        ot_v41_kreg #(.W(8+BW), .AR(0)) u_w3d (.clk(ckg), .arst_n(rn), .d({wd_p, wa_p}), .q({w3_d, w3_a}));
        ot_v41_kreg #(.W(1), .AR(1)) u_w3v (.clk(ckg), .arst_n(rn), .d(woh_p[g]), .q(w3_v));
        ot_v41_kreg #(.W(8), .AR(0)) u_r2a (.clk(ckg), .arst_n(rn), .d(ra_p), .q(r2_a));
        ot_v41_kreg #(.W(1), .AR(1)) u_r2v (.clk(ckg), .arst_n(rn), .d(roh_p[g]), .q(r2_v));
        wire [255:0] wd_m;
        if (BW < 256) begin : g_wpad assign wd_m = {{(256-BW){1'b0}}, w3_d}; end
        else begin : g_wfull assign wd_m = w3_d; end
        ot_sram_1r1w_256x256_m2_r2c2 u_sram(
            .clk(ckm), .r_ce_in(r2_v), .r_addr_in(r2_a), .rd_out(rd_out),
            .w_ce_in(w3_v), .w_addr_in(w3_a), .wd_in(wd_m), .w_mask_in({256{1'b1}}),
            .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(16'd0));
        reg [BW-1:0] cap_q; reg sm_q, s3_q;
        always @(posedge ckg) cap_q <= rd_out[BW-1:0];
        always @(posedge ck or negedge rn) if (!rn) begin sm_q <= 1'b0; s3_q <= 1'b0; end
                                           else begin sm_q <= r2_v; s3_q <= sm_q; end
        assign cap[g] = cap_q;
        assign sel3[g] = s3_q;
    end endgenerate
    // R4 pairs (groups 2k / 2k+1 are vertical neighbours)
    reg [BW-1:0] p_q [0:2]; reg [2:0] ps_q;
    integer k;
`ifdef OT_ENGC_PB_MUT
    // negative control: the pair select ignores the odd group's select (reads of odd groups return the even group)
    always @(posedge ck) for (k = 0; k < 3; k = k + 1)
        p_q[k] <= (sel3[2*k] | sel3[2*k+1]) ? cap[2*k] : {BW{1'b0}};
`else
    always @(posedge ck) for (k = 0; k < 3; k = k + 1)
        p_q[k] <= (cap[2*k] & {BW{sel3[2*k]}}) | (cap[2*k+1] & {BW{sel3[2*k+1]}});
`endif
    always @(posedge ck or negedge rn) if (!rn) ps_q <= 3'd0;
        else for (k = 0; k < 3; k = k + 1) ps_q[k] <= sel3[2*k] | sel3[2*k+1];
    // R5 3:1, R6 out flop
    reg [BW-1:0] m_q;
    always @(posedge ck) m_q <= (p_q[0] & {BW{ps_q[0]}}) | (p_q[1] & {BW{ps_q[1]}}) | (p_q[2] & {BW{ps_q[2]}});
    always @(posedge ck) r_d <= m_q;
endmodule

`ifndef OT_ENGC_PBC_CKL
`define OT_ENGC_PBC_CKL 2
`endif
// tile tops (parameterless, so the hardened views and the composition's black boxes agree)
module ot_engc_t_pbb_rso (    // bank 1 band tile: write transit {bank2 64, bank0 256} N face -> E face
    input wire ck, rst, input wire [5:0] w_oh, input wire [7:0] w_a, input wire [255:0] w_d, input wire [319:0] x_d,
    output wire [5:0] x_oh, output wire [7:0] x_a, output wire [319:0] x_do,
    input wire [5:0] r_oh, input wire [7:0] r_a, output wire [255:0] r_d,
    output wire rso
);
    ot_engc_pbank_rso #(.BW(256), .XW(320)) u_b (.ck(ck), .rst(rst), .w_oh(w_oh), .w_a(w_a), .w_d(w_d), .x_d(x_d),
        .x_oh(x_oh), .x_a(x_a), .x_do(x_do), .r_oh(r_oh), .r_a(r_a), .r_d(r_d), .rso(rso));
endmodule
module ot_engc_t_pbc_rso (    // bank 0 / bank 2 column tile: write W face, transit {bank2 64} E face, read N face
    input wire ck, rst, input wire [5:0] w_oh, input wire [7:0] w_a, input wire [255:0] w_d, input wire [63:0] x_d,
    output wire [5:0] x_oh, output wire [7:0] x_a, output wire [63:0] x_do,
    input wire [5:0] r_oh, input wire [7:0] r_a, output wire [255:0] r_d,
    output wire rso
);
    ot_engc_pbank_rso #(.BW(256), .XW(64), .CKL(`OT_ENGC_PBC_CKL)) u_b (.ck(ck), .rst(rst), .w_oh(w_oh), .w_a(w_a), .w_d(w_d), .x_d(x_d),
        .x_oh(x_oh), .x_a(x_a), .x_do(x_do), .r_oh(r_oh), .r_a(r_a), .r_d(r_d), .rso(rso));
endmodule
