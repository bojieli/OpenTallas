`timescale 1ns/1ps
// Hardened composition of dsrom_mtp_head_full340_A (bench / die-composition vehicle; the element is
// ot_dsrom_markov_bundle_glue.sv). Requires ot_dsrom_markov_head_full340.sv (trees) and the child element sources.
// One full340 bundle built from the hardened glue + the 5 head elements + the 4 Markov drivers, wired as the die
// wires the macros.  transaction / embed_* arrive already delayed by 2 (die stages, see ot_dsrom_markov_head_full340
// HARD=1) so that the drivers see them aligned with d_start.
module ot_dsrom_markov_head_bundle_h #(
    parameter bit ENABLE = 0, parameter integer PINREG = 1, parameter integer CACHE_PINREG = 0, parameter integer IOREG = 0, parameter integer RINGDLY = 0,
    parameter integer VALID_ROWS = 128, parameter integer A_INPUT_STAGES = 4,
    parameter [8:0] CUT = 511, parameter integer SPLIT9 = 1,
    parameter integer GLUE_RING = 1,
    parameter [39:0] PFX = "b000_"
) (
    input wire clk, rst_n,
    input wire start, output wire start_ready,
    input wire [16:0] row0, input wire [31:0] transaction,
    input wire embed_valid, input wire [255:0] embed_data, input wire [3:0] embed_beat,
    input wire [31:0] embed_id, input wire embed_last,
    output wire mg_all, output wire mg_any,
    input wire go, input wire [255:0] xa, xb,
    output wire done, output wire best_valid, output wire [16:0] best_row, output wire [31:0] best_bits,
    output wire fault
);
    wire b_go, bo, bfault; wire [255:0] b_x; wire [31:0] bd;
    wire [3:0] a_go, a_bv, af, d_start, sr, er, mg, md, mhave, mf;
    wire [67:0] a_row, d_row0, mr; wire [1023:0] a_x; wire [127:0] a_bd, mb;
    ot_dsrom_markov_bundle_glue #(.ENABLE(ENABLE), .A_INPUT_STAGES(A_INPUT_STAGES), .CUT(CUT), .SPLIT9(SPLIT9), .RING(GLUE_RING)) glue (
        .clk(clk), .rst_n(rst_n), .start(start), .start_ready(start_ready), .row0(row0), .embed_valid(embed_valid),
        .mg_all(mg_all), .mg_any(mg_any), .go(go), .xa(xa), .xb(xb),
        .done(done), .best_valid(best_valid), .best_row(best_row), .best_bits(best_bits), .fault(fault),
        .b_go(b_go), .b_x(b_x), .b_o_v(bo), .b_o_d(bd), .b_fault(bfault),
        .a_go(a_go), .a_row(a_row), .a_x(a_x), .a_bv(a_bv), .a_bd(a_bd), .a_fault(af),
        .d_start(d_start), .d_row0(d_row0), .d_sr(sr), .d_er(er), .d_mg(mg), .d_md(md), .d_mhave(mhave), .d_mf(mf),
        .d_mr(mr), .d_mb(mb));
    ot_dsrom_head_elem #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(CUT), .SPLIT9(SPLIT9), .INSTANCE({PFX, "hb"}), .SAFE(1)) b (
        .clk(clk), .rst_n(rst_n), .go(b_go), .row0(17'd0), .x(b_x), .b_v(1'b0), .b_d(32'b0),
        .o_v(bo), .o_d(bd), .l_v(), .l_d(), .done(), .best_row(), .best_bits(), .best_key(), .fault(bfault));
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_a
        localparam integer NVALID = VALID_ROWS <= 32*q ? 0 : (VALID_ROWS >= 32*(q+1) ? 32 : VALID_ROWS - 32*q);
        wire hv; wire [31:0] hb;
        ot_dsrom_head_elem #(.LV(8), .PAD(0), .JOIN(1), .ROWS(32), .CUT(CUT), .SPLIT9(SPLIT9),
            .INSTANCE({PFX, (q==0 ? "ha0" : q==1 ? "ha1" : q==2 ? "ha2" : "ha3")}), .SAFE(1)) a (
            .clk(clk), .rst_n(rst_n), .go(a_go[q]), .row0(a_row[17*q+:17]), .x(a_x[256*q+:256]), .b_v(a_bv[q]), .b_d(a_bd[32*q+:32]),
            .o_v(), .o_d(), .l_v(hv), .l_d(hb), .done(), .best_row(), .best_bits(), .best_key(), .fault(af[q]));
        ot_dsrom_markov_head_driver #(.ENABLE(ENABLE), .PINREG(PINREG), .CACHE_PINREG(CACHE_PINREG), .IOREG(IOREG), .RINGDLY(RINGDLY), .VALID_ROWS(NVALID),
            .CUT(CUT), .SPLIT9(SPLIT9), .INSTANCE({PFX, (q==0 ? "mk0" : q==1 ? "mk1" : q==2 ? "mk2" : "mk3")})) markov (
            .clk(clk), .rst_n(rst_n), .start(d_start[q]), .start_ready(sr[q]), .row0(d_row0[17*q+:17]), .transaction(transaction),
            .embed_valid(embed_valid), .embed_ready(er[q]), .embed_data(embed_data), .embed_beat(embed_beat),
            .embed_id(embed_id), .embed_last(embed_last),
            .head_go(mg[q]), .head_valid(hv), .head_bits(hb), .head_fault(af[q]),
            .joined_valid(), .joined_bits(), .joined_row(),
            .done(md[q]), .best_valid(mhave[q]), .best_row(mr[17*q+:17]), .best_bits(mb[32*q+:32]), .fault(mf[q]));
    end endgenerate
endmodule

// ---------------------------------------------------------------------------
// ot_dsrom_markov_head_full340_h: ot_dsrom_markov_head_full340 (unchanged, source-pinned) with every bundle built
// as ot_dsrom_markov_head_bundle_h = the hardened ot_dsrom_markov_bundle_glue element + 5 head elements + 4 drivers
// as separate macros.  Die-level difference: transaction / embedding reach the drivers through 2 die stages, matching
// the glue's start pin flop + per-driver start launch flop.  Same trees, same lockstep checks, same mutants.
// ---------------------------------------------------------------------------
module ot_dsrom_markov_head_full340_h #(
    parameter bit ENABLE = 0,
    parameter integer NB = 85,               // bundles on this die (production 85 = 340 A)
    parameter integer ROW_BASE = 0,          // global vocabulary row of bundle 0's first row
    parameter integer DIE_ROWS = 10774,      // valid rows of this die (manifest; the tail bundle is ragged)
    parameter integer FIRST_BUNDLE = 0,      // bundle id of instance 0 (ROM image names b<id>_*)
    parameter integer PINREG = 1, parameter integer CACHE_PINREG = 0, parameter integer A_INPUT_STAGES = 4,
    parameter integer IOREG = 1,             // Markov element pin-registered (margin-first; +2 cycles to head_go)
    parameter integer RINGDLY = 1,           // Markov dot lane delays as ring buffers (hold-safe; 0 cycles)
    parameter [8:0] CUT = 511, parameter integer SPLIT9 = 1,
    parameter integer FAN = 8,
    parameter integer LOOKUP = 1,            // 1: the die's shared lookup is inside; 0: embed_* pins (MD6 element)
    parameter integer MUTANT = 0, parameter integer MUTANT_BUNDLE = 0,
    parameter integer GLUE_RING = 1
) (
    input wire clk, rst_n,
    input wire start, output wire start_ready,
    input wire [16:0] d_i, input wire [31:0] transaction,
    // LOOKUP = 0: the MD6 lookup element's stream (pushed; out_ready of the element tied 1)
    input wire ext_embed_valid, input wire [255:0] ext_embed_data, input wire [3:0] ext_embed_beat,
    input wire [31:0] ext_embed_id, input wire ext_embed_last, input wire ext_embed_fault,
    output wire head_go,
    input wire [255:0] xa, xb,
    output reg done, output reg best_valid, output reg [16:0] best_row, output reg [31:0] best_bits,
    output reg fault
);
    function automatic integer clog(input integer n, input integer f);
        integer d, c; begin d = 0; c = 1; while (c < n) begin c = c * f; d = d + 1; end clog = (d == 0) ? 1 : d; end
    endfunction
    localparam integer DB = clog(NB, FAN);       // broadcast / AND-tree depth
    localparam integer DP = clog(NB, 2);         // argmax tree depth
    localparam integer WS = 1 + 1 + 32 + 256 + 4 + 32 + 1;   // {start, ev, transaction, data, beat, id, last}

    reg busy, armed; reg [7:0] since;
    wire rdy_all, hg_all, hg_any, fl_any;
    wire lk_ready, lk_fault;
    assign start_ready = ENABLE && !busy && rdy_all && (LOOKUP == 0 || lk_ready) && !fault;
    wire accept = start && start_ready;

    // shared lookup (pushed: every driver is ready by construction, checked in the bundles)
    wire ev, el; wire [255:0] ed; wire [3:0] eb; wire [31:0] ei;
    generate if (LOOKUP != 0) begin : g_lookup
        ot_dsrom_markov_embed_rom #(.ENABLE(ENABLE)) lookup (
            .clk(clk), .rst_n(rst_n), .req_valid(accept), .req_ready(lk_ready), .req_token(d_i), .req_id(transaction),
            .fault_valid(lk_fault), .fault_id(),
            .out_valid(ev), .out_ready(1'b1), .out_data(ed), .out_id(ei), .out_beat(eb), .out_last(el));
    end else begin : g_ext
        assign lk_ready = 1'b1; assign lk_fault = ext_embed_fault;
        assign ev = ext_embed_valid; assign ed = ext_embed_data; assign eb = ext_embed_beat;
        assign ei = ext_embed_id; assign el = ext_embed_last;
    end endgenerate

    // start + embedding broadcast (DB levels)
    wire [NB*WS-1:0] sb;
    ot_mtp_bcast_tree #(.W(WS), .RW(2), .N(NB), .FAN(FAN), .DEPTH(DB)) u_sb (
        .clk(clk), .rst_n(rst_n), .d({el, ei, eb, ed, transaction, ev, accept}), .q(sb));
    // go + x broadcast (DB levels; the external x contract is relative to the head_go pin)
    wire [NB*513-1:0] gx;
    reg hg_q;
    ot_mtp_bcast_tree #(.W(513), .RW(1), .N(NB), .FAN(FAN), .DEPTH(DB)) u_gx (
        .clk(clk), .rst_n(rst_n), .d({xb, xa, hg_q}), .q(gx));

    wire [NB-1:0] b_rdy, b_mga, b_mgo, b_done, b_bv, b_fault;
    wire [NB*17-1:0] b_row; wire [NB*32-1:0] b_bits;
    genvar b;
    generate for (b = 0; b < NB; b = b + 1) begin : g_b
        localparam integer BI = FIRST_BUNDLE + b;
        localparam [39:0] PFX = {"b", 8'(48 + (BI / 100) % 10), 8'(48 + (BI / 10) % 10), 8'(48 + BI % 10), "_"};
        localparam integer VR = (DIE_ROWS - 128*b) >= 128 ? 128 : ((DIE_ROWS - 128*b) <= 0 ? 0 : DIE_ROWS - 128*b);
        wire [WS-1:0] s = sb[b*WS +: WS];
        // MUTANT 2: bundle 0's embedding one cycle late (lockstep broken)
        wire [WS-1:0] s_m;
        if (MUTANT == 2 && b == 0) begin : g_late
            reg [WS-2:0] late;
            always @(posedge clk) late <= s[WS-1:1];
            assign s_m = {late[WS-2:1], late[0] && rst_n, s[0]};
        end else begin : g_on
            assign s_m = s;
        end
        wire [WS-1:0] s_h;   // die stages: transaction / embedding 2 deep (aligned with the glue's start launch)
        ot_hdc_delay #(.W(1), .D(2), .RESET(1)) u_hev (.clk(clk), .rst_n(rst_n), .d(s_m[1]), .q(s_h[1]));
        ot_hdc_delay #(.W(WS-2), .D(2)) u_hd (.clk(clk), .rst_n(rst_n), .d(s_m[WS-1:2]), .q(s_h[WS-1:2]));
        assign s_h[0] = s_m[0];
        ot_dsrom_markov_head_bundle_h #(.ENABLE(ENABLE), .PINREG(PINREG), .CACHE_PINREG(CACHE_PINREG), .IOREG(IOREG), .RINGDLY(RINGDLY), .VALID_ROWS(VR),
            .A_INPUT_STAGES(A_INPUT_STAGES), .CUT(CUT), .SPLIT9(SPLIT9), .GLUE_RING(GLUE_RING),
            .PFX(PFX)) u (
            .clk(clk), .rst_n(rst_n), .start(s_m[0]), .start_ready(b_rdy[b]),
            .row0(17'(ROW_BASE + 128*b)), .transaction(s_h[33:2]),
            .embed_valid(s_h[1]), .embed_data(s_h[289:34]), .embed_beat(s_h[293:290]), .embed_id(s_h[325:294]),
            .embed_last(s_h[326]),
            .mg_all(b_mga[b]), .mg_any(b_mgo[b]),
            .go(gx[b*513]), .xa(gx[b*513+1 +: 256]), .xb(gx[b*513+257 +: 256]),
            .done(b_done[b]), .best_valid(b_bv[b]), .best_row(b_row[b*17 +: 17]), .best_bits(b_bits[b*32 +: 32]),
            .fault(b_fault[b]));
    end endgenerate

    // registered AND trees: {ready, head_go all, ~head_go any, ~fault any}
    wire [NB*4-1:0] tin;
    generate for (b = 0; b < NB; b = b + 1) begin : g_t
        assign tin[b*4 +: 4] = {~b_fault[b], ~b_mgo[b], b_mga[b], b_rdy[b]};
    end endgenerate
    wire [3:0] tq;
    ot_mtp_and_tree #(.W(4), .N(NB), .FAN(FAN), .DEPTH(DB), .RV(4'b1100)) u_t (.clk(clk), .rst_n(rst_n), .d(tin), .q(tq));
    assign rdy_all = tq[0]; assign hg_all = tq[1]; assign hg_any = ~tq[2]; assign fl_any = ~tq[3];
    always @(posedge clk or negedge rst_n) if (!rst_n) hg_q <= 0; else hg_q <= hg_all && !fault;
    assign head_go = hg_q;

    // argmax: per-bundle leaf capture, then a DP-level registered pick tree (2:1, lowest row wins a tie)
    function automatic [31:0] key(input [31:0] v);
        reg [31:0] z; begin z = (v[30:0] == 0) ? 0 : v; key = z[31] ? ~z : (z ^ 32'h80000000); end
    endfunction
    function automatic [82:0] pick(input [82:0] u, v);   // {seen, valid, key, row, bits}
        reg [81:0] r;
        begin
            if (!u[81]) r = v[81:0]; else if (!v[81]) r = u[81:0];
            else r = (v[80:49] > u[80:49] || (v[80:49] == u[80:49] && v[48:32] < u[48:32])) ? v[81:0] : u[81:0];
            pick = {u[82] & v[82], r};
        end
    endfunction
    function automatic integer pcnt(input integer k);
        integer c, s; begin c = NB; for (s = k; s < DP; s = s + 1) c = (c + 1) / 2; pcnt = c; end
    endfunction
    wire [82:0] pl [0:DP][0:NB-1];
    generate for (b = 0; b < NB; b = b + 1) begin : g_leaf
        reg [82:0] leaf;
        wire drop = (MUTANT == 1) && (b == MUTANT_BUNDLE);
        always @(posedge clk or negedge rst_n)
            if (!rst_n) leaf <= 0;
            else if (accept) leaf <= 0;
            else if (b_done[b]) leaf <= {1'b1, b_bv[b] && !drop, key(b_bits[b*32 +: 32]), b_row[b*17 +: 17], b_bits[b*32 +: 32]};
        assign pl[DP][b] = leaf;
    end endgenerate
    genvar k, i;
    generate for (k = DP - 1; k >= 0; k = k - 1) begin : g_pl
        for (i = 0; i < pcnt(k); i = i + 1) begin : g_pn
            wire [82:0] l = pl[k+1][2*i];
            wire [82:0] r = (2*i + 1 < pcnt(k + 1)) ? pl[k+1][2*i+1] : {1'b1, 82'b0};
            reg [82:0] node;
            always @(posedge clk or negedge rst_n) if (!rst_n) node <= 0; else node <= pick(l, r);
            assign pl[k][i] = node;
        end
    end endgenerate
    wire [82:0] root = pl[0][0];

    always @(posedge clk or negedge rst_n) if (!rst_n) begin
        busy <= 0; armed <= 0; since <= 0; done <= 0; best_valid <= 0; best_row <= 0; best_bits <= 0; fault <= 0;
    end else begin
        done <= 0;
        if (start && !start_ready) fault <= 1;
        if (lk_fault || fl_any || (hg_any && !hg_all)) fault <= 1;
        if (accept) begin busy <= 1; armed <= 0; since <= 0; best_valid <= 0; end
        else if (busy && !armed) begin since <= since + 1; if (since == 8'(DP + 2)) armed <= 1; end
        if (busy && armed && root[82] && !fault) begin
            done <= 1; busy <= 0; armed <= 0; best_valid <= root[81]; best_row <= root[48:32]; best_bits <= root[31:0];
        end
    end
endmodule
