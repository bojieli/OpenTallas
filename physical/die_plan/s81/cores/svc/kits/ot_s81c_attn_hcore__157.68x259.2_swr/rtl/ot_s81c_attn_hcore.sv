`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// CORE-S81-SVC (10-23): the S81 svc attention engine's planned HARD CORE = one attention HEAD with its own front end.
//
// The S81 die plan (physical/die_plan/s81, svc partitions) carries the attention engine of dsdv_svc_att
// (ot_hdc_v41x_attn_s, NT = 4 tiles of ot_hdc_v41x_attn_tile_s at H16 TD32 NBANK5 BW3 PWORDS2 FPL4 FML6 F12) as
// 12.4 M soft cells: 64 head datapaths ot_hdc_v41x_attn_hdp_s (183,981 cells) + 16 head-group front ends (30,272).
// Neither boundary has a register on every pin (hdp_s: we / wbank are decoded combinationally in the group from the
// R0 load registers, sk_bank drives the bank-select mux, the DS = 0 skew positions are the dequantiser's output
// logic, y / f leave the adder tree before the group's output register).  The head GROUP (4 heads) is ~770 k cells,
// over the 400 k-cell P&R cap (hgrp8 history: lanes/STW-S81-COLLB.md).
//
// Hard core = ot_hdc_v41x_attn_hgrp_s at HG = 1 (one head per group) and PCOLP = 1 (the head's p-mode columns
// pre-selected by the tile wiring): the tile_s RTL already defines a head group as H/HG identical copies of the front
// end (R0 boundary registers, dequantiser, D1, skew lines -- registers only, same cycles for any HG), so HG = 1 is
// the existing design point with one head per copy.  At this boundary every input lands in a flop (R0 r_iv / r_ibank /
// r_ib, the head's kreg copies of ld_*, ld_wp's kreg, hh <= gid) and every output leaves one (ov, oy, oflt).
// ld_w[1023:512] (the second p-word) is read only by the PCOLP = 0 column select, so the core exposes ld_w[511:0].
// Cost vs HG = 4: the front end is replicated per head (+~1/4 of a group front end per head; measured by synth).
//
// ot_s81c_attn_tile_hc: tile_s's ports and cycles with H = 16 such cores (bench tb_s81c_hcore: lockstep vs
// ot_hdc_v41x_attn_tile_s at the default HG = 4 / PCOLP = 0, every output every cycle).  tile_s instantiates it under
// -DOT_ATTN_HCORE (opt-in, off by default).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81c_attn_hcore #(
    // S81-P10 (opt-in, off by default): hgrp_s WPRE = 1, the write predicates captured at R0 (same values, same edges);
    // the hard-core kit sets it with -DOT_S81C_HCORE_WPRE
`ifdef OT_S81C_HCORE_CTLA
    // S81-CORES2/EH 10-25: control-ahead (ld_grp / ld_w2v one cycle ahead of the rest of the load word), every pin
    // registered once (face_guard clean) and the predicates still captured on the data's R0 edge (hgrp_s WPRE 2)
    parameter integer WPRE = 2
`elsif OT_S81C_HCORE_WPRE
    parameter integer WPRE = 1
`else
    parameter integer WPRE = 0
`endif
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        gid,        // static: the tile head index of this core (0 .. 15)
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [2:0]        ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [511:0]      ld_w,       // p-word 0 of the tile's load word (the normal-mode row)
    input  wire [63:0]       ld_wp,      // this head's p-mode columns, both p-words ((w*2 + j)*16)
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [2:0]        ibank,
    input  wire [575:0]      ib,
    output wire              ov,
    output wire [31:0]       oy,
    output wire              oflt
);
    // S81-CORES2/EH 10-25 (-DOT_S81C_HCORE_RSTE, decision 13b): the rst_n pin drives only the reset ENTRY flop and the
    // relay flop (async assert, synchronous release); the relay (kept, placed at the core centroid) drives every
    // reset pin of the core over a full cycle.  Release +2 cycles, static and equal for all 1024 cores (hardened once).
    wire rst_core_n;
`ifdef OT_S81C_HCORE_RSTE
    (* keep = "true", dont_touch = "true" *) reg rst_e_q, rst_r_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rst_e_q <= 1'b0; rst_r_q <= 1'b0; end
        else begin rst_e_q <= 1'b1; rst_r_q <= rst_e_q; end
    end
    assign rst_core_n = rst_r_q;
`else
    assign rst_core_n = rst_n;
`endif
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(1), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1),
                              .PCOLP(1), .WPRE(WPRE)) u_h (
        .clk(clk), .rst_n(rst_core_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w({512'd0, ld_w}), .ld_wp(ld_wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy),
        .oflt(oflt));
endmodule

// The S81 tile (H16 TD32 NBANK5 BW3 PWORDS2 FPL4 FML6 F12) as 16 head cores: ot_hdc_v41x_attn_tile_s's ports/cycles.
module ot_s81c_attn_tile_hc (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [2:0]        ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [1023:0]     ld_w,
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [2:0]        ibank,
    input  wire [575:0]      ib,
    output wire              ov,
    output wire [511:0]      oy,
    output wire [15:0]       oflt
);
    localparam integer H = 16, TD = 32, PW = 2, RT = TD / H;
    wire [H-1:0] hov;
    genvar g, gw, gj;
    generate
        for (g = 0; g < H; g = g + 1) begin : g_h
            // head g's p-mode columns: word j*H + g of each p-word (tile_s PCOLP wiring at HG = 1)
            wire [PW*RT*16-1:0] wp;
            for (gw = 0; gw < PW; gw = gw + 1) begin : g_ww
                for (gj = 0; gj < RT; gj = gj + 1) begin : g_wj
`ifdef OT_S81C_HCORE_MUT
                    // bench negative control: head g takes head (g+1)'s column of p-word 1
                    assign wp[(gw*RT + gj)*16 +: 16] = ld_w[gw*TD*16 + (gj*H + ((gw == 1) ? ((g + 1) % H) : g))*16 +: 16];
`else
                    assign wp[(gw*RT + gj)*16 +: 16] = ld_w[gw*TD*16 + (gj*H + g)*16 +: 16];
`endif
                end
            end
            wire [7:0] gid = g;
            ot_s81c_attn_hcore u_c (
                .clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w[511:0]), .ld_wp(wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib),
                .ov(hov[g]), .oy(oy[g*32 +: 32]), .oflt(oflt[g]));
        end
    endgenerate
    assign ov = hov[0];
endmodule
