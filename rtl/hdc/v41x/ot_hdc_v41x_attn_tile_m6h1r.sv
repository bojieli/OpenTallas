`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// H16 attention tile, registered parent (opt-in 1.2 GHz hardening top; the plain ot_attn_tile_m6h1 is unchanged).
// Sixteen hardened one-head leaves ot_attn_hgrp_m6h1 (closed routed SS +18.91 / FF +1.55 ps) in a 4 x 4 array of
// two macro PAIRS per row: in each pair the left leaf is mirrored (MY) so both leaves' input pins (left edge, M4)
// face one shared register channel.  The 1,618-bit input packet {ld_v, ld_mode, ld_bank, ld_grp, ld_w, ld_w2v, iv,
// ibank, ib} plus rst_n is distributed by a positive-edge register tree whose every hop is a short wire:
//   ROOT (1 copy) -> RV centre-chain registers -> COL (2 copies, one per pair channel) [-> MID] -> HC (4 copies, one per channel half;
//   each drives the input pins of the 4 leaves of two rows of its pair, <= ~300 um)
// and (ROC = 1) each leaf's 33/34 output bits are captured next to its output pins (OC, one per leaf); ROC = 0 takes the
// outputs straight from the leaves, whose outputs are register-direct inside the hardened macro.
// Every register bank is a kept-hierarchy instance (ot_attn_rp_reg), so synthesis keeps the copies.
// Function: ot_attn_tile_m6h1 with every input (rst_n included) delayed by RIN = 3 + RV + RMID cycles and every output by
// ROC cycles (+3 + ROC cycles on the tile's latency; tb_hdc_v41x_attn_tile_m6h1r_lockstep against tile_l).
// rst_n is carried as data (the leaves' asynchronous reset is driven from the HC register).
// Sources: this file, ot_hdc_v41x_attn_tile_m8_phys.sv (ot_attn_hgrp_m6h1) and its sources.
// ---------------------------------------------------------------------------
(* keep_hierarchy = "yes" *)
module ot_attn_rp_reg #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

module ot_attn_tile_m6h1r #(
    parameter integer ROC = 1,              // 1: per-leaf output capture (+1 cycle); 0: outputs straight from the leaves
                                            //    (the leaf's outputs are register-direct inside the macro)
    parameter integer RMID = 0,             // 1: one more register (MID) between COL and each HC (+1 cycle)
    parameter integer RV = 0                // centre-chain registers between ROOT and the COLs (+RV cycles): the tree
) (                                         //    climbs the centre gap from inputs at the bottom-edge centre
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [511:0]  oy,
    output wire [15:0]   oflt
);
    localparam integer PW = 1 + 1618;
    wire [PW-1:0] pk = {rst_n, ld_v, ld_mode, ld_bank, ld_grp, ld_w, ld_w2v, iv, ibank, ib};
    wire [PW-1:0] root_q;
    (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_root (.clk(clk), .d(pk), .q(root_q));
    wire [(RV+1)*PW-1:0] v_q;                   // v_q[k*PW +: PW]: centre-chain register k (0 = ROOT)
    assign v_q[0 +: PW] = root_q;
    genvar gv;
    generate for (gv = 0; gv < RV; gv = gv + 1) begin : g_v
        (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_v (.clk(clk), .d(v_q[gv*PW +: PW]), .q(v_q[(gv+1)*PW +: PW]));
    end endgenerate
    wire [15:0] gov;
    genvar p, h, s, r;
    generate
        for (p = 0; p < 2; p = p + 1) begin : g_p                   // macro pair p: physical columns 2p (MY), 2p+1 (R0)
            wire [PW-1:0] col_q;
            (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_col (.clk(clk), .d(v_q[RV*PW +: PW]), .q(col_q));
            for (h = 0; h < 2; h = h + 1) begin : g_h               // channel half h: rows 2h, 2h+1
                wire [PW-1:0] mid_q, hc_q;
                if (RMID > 0) begin : g_mid
                    (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_mid (.clk(clk), .d(col_q), .q(mid_q));
                end else begin : g_nomid
                    assign mid_q = col_q;
                end
                (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_hc (.clk(clk), .d(mid_q), .q(hc_q));
                wire          l_rst_n, l_ld_v, l_ld_mode, l_ld_w2v, l_iv;
                wire [2:0]    l_ld_bank, l_ibank;
                wire [7:0]    l_ld_grp;
                wire [1023:0] l_ld_w;
                wire [575:0]  l_ib;
                assign {l_rst_n, l_ld_v, l_ld_mode, l_ld_bank, l_ld_grp, l_ld_w, l_ld_w2v, l_iv, l_ibank, l_ib} = hc_q;
                for (r = 0; r < 2; r = r + 1) begin : g_r
                    for (s = 0; s < 2; s = s + 1) begin : g_s       // side: 0 = column 2p (MY), 1 = column 2p+1 (R0)
                        localparam integer ROW = 2 * h + r;
                        localparam integer COLM = 2 * p + s;
                        localparam integer G = ROW * 4 + COLM;      // head index (gid, oy slot)
                        wire        hv;
                        wire [31:0] hy;
                        wire [0:0]  hf;
                        ot_attn_hgrp_m6h1 u_g (
                            .clk(clk), .rst_n(l_rst_n), .gid(G[7:0]), .ld_v(l_ld_v), .ld_mode(l_ld_mode),
                            .ld_bank(l_ld_bank), .ld_grp(l_ld_grp), .ld_w(l_ld_w), .ld_w2v(l_ld_w2v), .iv(l_iv),
                            .ibank(l_ibank), .ib(l_ib), .ov(hv), .oy(hy), .oflt(hf));
                        if (ROC == 0) begin : g_od
                            assign {gov[G], oflt[G], oy[G*32 +: 32]} = {hv, hf, hy};
                        end else if (G == 0) begin : g_ov
                            wire [33:0] oc_q;
                            (* keep = "true" *) ot_attn_rp_reg #(.W(34)) u_oc (.clk(clk), .d({hv, hf, hy}), .q(oc_q));
                            assign {gov[G], oflt[G], oy[G*32 +: 32]} = oc_q;
                        end else begin : g_o
                            wire [32:0] oc_q;
                            (* keep = "true" *) ot_attn_rp_reg #(.W(33)) u_oc (.clk(clk), .d({hf, hy}), .q(oc_q));
                            assign {oflt[G], oy[G*32 +: 32]} = oc_q;
                            assign gov[G] = 1'b0;
                        end
                    end
                end
            end
        end
    endgenerate
    assign ov = gov[0];
    // The leaves' rst_n is a 3-cycle path (the leaf's reset recovery is 1,062 ps against its clk pin at SS, longer
    // than a cycle; physical/hbm_attn_tile_r/leaf_reset_mcp.sdc): the tile's rst_n must hold every value for at
    // least 3 cycles (a quasi-static reset).  Checked here in simulation.
    // synthesis translate_off
    reg rst_prev = 1'b0;
    integer rst_age = 3;
    always @(posedge clk) begin
        if (rst_n !== rst_prev) begin
            if (rst_age < 3) begin
                $display("OT_ATTN_TILE_RST_PROTOCOL rst_n changed after %0d cycles (need >= 3)", rst_age);
                $fatal(1, "ot_attn_tile_m6h1r: rst_n held < 3 cycles");
            end
            rst_age = 1;
        end else if (rst_age < 3) rst_age = rst_age + 1;
        rst_prev <= rst_n;
    end
    // synthesis translate_on
endmodule

// ---------------------------------------------------------------------------
// Half tile (one register strip, H8): eight one-head leaves, rows 0 (R0) and 1 (MX) facing one strip; ROOT at the
// strip centre -> HC (2 copies, one per half strip, each driving the 4 leaves of its half) -> leaves.  Heads
// GB .. GB + 7 of the H16 tile (gid GB + 4 * row + column); ot_attn_tile_m6h1r's function on those heads with every
// input, rst_n included, delayed RIN = 2 cycles and the outputs taken straight from the leaves.  The H16 tile is two
// of these (GB 0 and 8) fed the same packet (ot_attn_tile_m6h1h).
// ---------------------------------------------------------------------------
module ot_attn_tile_m6h1s #(
    parameter integer GB = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire [7:0]    gov,
    output wire [255:0]  oy,
    output wire [7:0]    oflt
);
    localparam integer PW = 1 + 1618;
    wire [PW-1:0] pk = {rst_n, ld_v, ld_mode, ld_bank, ld_grp, ld_w, ld_w2v, iv, ibank, ib};
    wire [PW-1:0] root_q;
    (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_root (.clk(clk), .d(pk), .q(root_q));
    genvar h, s, r;
    generate
        for (h = 0; h < 2; h = h + 1) begin : g_h                   // half strip h: columns 2h, 2h+1
            wire [PW-1:0] hc_q;
            (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_hc (.clk(clk), .d(root_q), .q(hc_q));
            wire          l_rst_n, l_ld_v, l_ld_mode, l_ld_w2v, l_iv;
            wire [2:0]    l_ld_bank, l_ibank;
            wire [7:0]    l_ld_grp;
            wire [1023:0] l_ld_w;
            wire [575:0]  l_ib;
            assign {l_rst_n, l_ld_v, l_ld_mode, l_ld_bank, l_ld_grp, l_ld_w, l_ld_w2v, l_iv, l_ibank, l_ib} = hc_q;
            for (r = 0; r < 2; r = r + 1) begin : g_r               // 0: the row below the strip (R0), 1: above (MX)
                for (s = 0; s < 2; s = s + 1) begin : g_s
                    localparam integer L = r * 4 + 2 * h + s;       // local head (oy slot)
                    localparam integer G = GB + L;
                    wire [31:0] hy;
                    wire [0:0]  hf;
                    wire        hv;
                    ot_attn_hgrp_m6h1 u_g (
                        .clk(clk), .rst_n(l_rst_n), .gid(G[7:0]), .ld_v(l_ld_v), .ld_mode(l_ld_mode),
                        .ld_bank(l_ld_bank), .ld_grp(l_ld_grp), .ld_w(l_ld_w), .ld_w2v(l_ld_w2v), .iv(l_iv),
                        .ibank(l_ibank), .ib(l_ib), .ov(hv), .oy(hy), .oflt(hf));
                    assign {gov[L], oflt[L], oy[L*32 +: 32]} = {hv, hf, hy};
                end
            end
        end
    endgenerate
endmodule

// The H16 tile as two half tiles (simulation / function; each half is the hardened element)
module ot_attn_tile_m6h1h (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [511:0]  oy,
    output wire [15:0]   oflt
);
    wire [7:0] gov0, gov1;
    ot_attn_tile_m6h1s #(.GB(0)) u_s0 (.clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
        .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .gov(gov0), .oy(oy[0 +: 256]),
        .oflt(oflt[0 +: 8]));
    ot_attn_tile_m6h1s #(.GB(8)) u_s1 (.clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
        .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .gov(gov1), .oy(oy[256 +: 256]),
        .oflt(oflt[8 +: 8]));
    assign ov = gov0[0];
endmodule
