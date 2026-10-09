`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// dsrom_mtp_head_full340_A: production head-die Markov head (mtp-lead 2026-10-09).
//
// What it computes (released DeepSeek-V4.1 MTP Markov head, K = 256): for the die's contiguous slice of the
// 129,280-row vocabulary, joined[v] = lm_head[v] . x (A K0:4096 + B K4096:5120, golden chunk8 order) +
// markov_head[v] . embed[d_i] (K 256, separate add), then the lowest-row first-max argmax over the die's VALID rows
// (-0 canonical, sign-magnitude key, invalid / padding rows never a candidate). The rank merges the 12 die results.
//
// Organisation (tools/mtp_die_reprice.py markov_ports; semantic manifest 12 dies x 85 bundles):
//   NB = 85 bundles a die, each = 1 B + 4 A ot_dsrom_head_elem (10 ROM4096) + 4 Markov row engines
//   (ot_dsrom_markov_head_driver: 2 ROM4096 + K256 dot + post-Markov argmax) = 340 A / 340 Markov / 680 Markov ROMs.
//   ONE shared released-embedding lookup a die (ot_dsrom_markov_embed_rom, 506 ROM4096; MD6 lookup element), NOT one
//   per bundle: its 16-beat stream is PUSHED to all 340 Markov engines through a registered broadcast tree.
// Hardened elements (placed N times by the die, not routed flat): ot_dsrom_head_elem A/B (closed views),
// ot_dsrom_markov_head_driver (the Markov element, one per A). Everything in this file outside those is glue:
// registered trees only, every tree level a flop stage (pin flops at each element face; no combinational fan-out
// wider than FAN, no combinational fan-in wider than 2 (argmax) / FAN (AND trees)).
//
// Lockstep contract (why no ready crosses the die): every bundle receives start, the embedding beats and go/x at
// the same depth, so all 340 drivers are in the same state each cycle. Readiness is still checked, never assumed:
//   - a pushed embedding beat at a not-ready driver, or a start at a busy bundle, is a sticky fault (fail closed);
//   - head_go is the registered AND of every bundle's head_go; the registered OR must agree (else fault);
//   - start_ready is the registered AND of every bundle's start_ready (plus the lookup's).
// Timing (cycles, FAN 8, NB 85: broadcast depth DB = 3): start/embed reach the bundles DB after the lookup; head_go
// leaves the die DB after the drivers raise it; x must then carry slice m at head_go + 5 + m (unchanged bundle
// contract; go and x travel together through the DB-deep go/x tree); done = all bundle results + leaf capture +
// ceil(log2 NB) registered pick levels + 1.
// MUTANT (bench negatives only): 1 = the die reduction ignores bundle MUTANT_BUNDLE; 2 = bundle 0's embedding
// arrives one cycle late (lockstep broken).
// ---------------------------------------------------------------------------

// Registered broadcast tree: q[i] = d delayed by DEPTH, every node drives at most FAN children.
module ot_mtp_bcast_tree #(
    parameter integer W = 8, parameter integer RW = 1,   // low RW bits are reset (validity), the rest are not
    parameter integer N = 4, parameter integer FAN = 8,
    parameter integer DEPTH = 1
) (
    input wire clk, rst_n, input wire [W-1:0] d, output wire [N*W-1:0] q
);
    function automatic integer cnt(input integer k);  // nodes at level k (level DEPTH = leaves)
        integer c, s; begin c = N; for (s = k; s < DEPTH; s = s + 1) c = (c + FAN - 1) / FAN; cnt = c; end
    endfunction
    wire [W-1:0] lv [0:DEPTH][0:N-1];
    assign lv[0][0] = d;
    genvar k, i;
    generate for (k = 1; k <= DEPTH; k = k + 1) begin : g_l
        for (i = 0; i < cnt(k); i = i + 1) begin : g_n
            reg [RW-1:0] node_v;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) node_v <= {RW{1'b0}}; else node_v <= lv[k-1][i / FAN][RW-1:0];
            if (W > RW) begin : g_d
                reg [W-RW-1:0] node_d;
                always @(posedge clk) node_d <= lv[k-1][i / FAN][W-1:RW];
                assign lv[k][i] = {node_d, node_v};
            end else begin : g_v
                assign lv[k][i] = node_v;
            end
        end
    end endgenerate
    generate for (i = 0; i < N; i = i + 1) begin : g_q
        assign q[i*W +: W] = lv[DEPTH][i];
    end endgenerate
endmodule

// Registered bitwise-AND reduction tree (OR quantities ride inverted). Missing children are 1.
module ot_mtp_and_tree #(
    parameter integer W = 1, parameter integer N = 4, parameter integer FAN = 8, parameter integer DEPTH = 1
) (
    input wire clk, rst_n, input wire [N*W-1:0] d, output wire [W-1:0] q
);
    function automatic integer cnt(input integer k);
        integer c, s; begin c = N; for (s = k; s < DEPTH; s = s + 1) c = (c + FAN - 1) / FAN; cnt = c; end
    endfunction
    wire [W-1:0] lv [0:DEPTH][0:N-1];
    genvar k, i, c;
    generate for (i = 0; i < N; i = i + 1) begin : g_in
        assign lv[DEPTH][i] = d[i*W +: W];
    end endgenerate
    generate for (k = DEPTH - 1; k >= 0; k = k - 1) begin : g_l
        for (i = 0; i < cnt(k); i = i + 1) begin : g_n
            wire [W-1:0] child [0:FAN-1];
            for (c = 0; c < FAN; c = c + 1) begin : g_c
                if (i * FAN + c < cnt(k + 1)) begin : g_have
                    assign child[c] = lv[k+1][i * FAN + c];
                end else begin : g_none
                    assign child[c] = {W{1'b1}};
                end
            end
            reg [W-1:0] node;
            integer j;
            reg [W-1:0] acc;
            always @(*) begin acc = {W{1'b1}}; for (j = 0; j < FAN; j = j + 1) acc = acc & child[j]; end
            always @(posedge clk or negedge rst_n) if (!rst_n) node <= {W{1'b0}}; else node <= acc;
            assign lv[k][i] = node;
        end
    end endgenerate
    assign q = lv[0][0];
endmodule

// One bundle (1 B + 4 A + 4 Markov) without its own lookup: start / embedding pushed, go and x from the die.
module ot_dsrom_markov_head_bundle_x #(
    parameter bit ENABLE = 0, parameter integer PINREG = 1, parameter integer CACHE_PINREG = 0,
    parameter integer VALID_ROWS = 128, parameter integer A_INPUT_STAGES = 4,
    parameter [8:0] CUT = 511, parameter integer SPLIT9 = 1,
    parameter integer SK = 1+CUT[0]+CUT[1]+CUT[2]+CUT[3]+CUT[4]+CUT[5]+CUT[6]+CUT[7]+CUT[8]+SPLIT9,
    parameter PFX = "b000_"
) (
    input wire clk, rst_n,
    input wire start, output wire start_ready,
    input wire [16:0] row0, input wire [31:0] transaction,
    input wire embed_valid, input wire [255:0] embed_data, input wire [3:0] embed_beat,
    input wire [31:0] embed_id, input wire embed_last,
    output wire mg_all, output wire mg_any,
    input wire go, input wire [255:0] xa, xb,
    output reg done, output reg best_valid, output reg [16:0] best_row, output reg [31:0] best_bits,
    output wire fault
);
    wire [3:0] sr, er, mg, md, mf, mhave, af;
    wire [127:0] mb; wire [67:0] mr;
    reg busy, control_fault; reg [16:0] base;
    wire accept = start && start_ready;
    assign start_ready = ENABLE && !busy && (&sr) && !fault;
    assign mg_all = &mg; assign mg_any = |mg;
    wire [255:0] xsa, xsb;
    genvar j, q;
    generate for (j = 0; j < 16; j = j + 1) begin : g_sk
        ot_hdc_delay #(.W(16), .D(SK*(j%8))) sa (.clk(clk), .rst_n(rst_n), .d(xa[16*j+:16]), .q(xsa[16*j+:16]));
        ot_hdc_delay #(.W(16), .D(SK*(j%8))) sb (.clk(clk), .rst_n(rst_n), .d(xb[16*j+:16]), .q(xsb[16*j+:16]));
    end endgenerate
    wire bo, bfault; wire [31:0] bd;
    ot_dsrom_head_elem #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(CUT), .SPLIT9(SPLIT9), .INSTANCE($sformatf("%shb", PFX)), .SAFE(1)) b (
        .clk(clk), .rst_n(rst_n), .go(go), .row0(17'd0), .x(xsb), .b_v(1'b0), .b_d(32'b0),
        .o_v(bo), .o_d(bd), .l_v(), .l_d(), .done(), .best_row(), .best_bits(), .best_key(), .fault(bfault));
    reg [1:0] bq; reg [3:0] bv; reg [31:0] held_b;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin bq <= 0; bv <= 0; end
        else begin if (go) bq <= 0; else if (bo) bq <= bq + 1; bv <= bo ? (4'b1 << bq) : 0; end
    always @(posedge clk) if (bo) held_b <= bd;
    generate for (q = 0; q < 4; q = q + 1) begin : g_a
        localparam integer NVALID = VALID_ROWS <= 32*q ? 0 : (VALID_ROWS >= 32*(q+1) ? 32 : VALID_ROWS - 32*q);
        wire [16:0] driver_row = row0 + 17'd32*q; wire [16:0] landed_row = base + 17'd32*q;
        wire ag, bvalid, hv; wire [16:0] ar; wire [255:0] ax; wire [31:0] ad, hb;
        ot_hdc_delay #(.W(2), .D(A_INPUT_STAGES), .RESET(1)) landing_valid (
            .clk(clk), .rst_n(rst_n), .d({go, bv[q]}), .q({ag, bvalid}));
        ot_hdc_delay #(.W(305), .D(A_INPUT_STAGES)) landing_payload (
            .clk(clk), .rst_n(rst_n), .d({landed_row, xsa, held_b}), .q({ar, ax, ad}));
        ot_dsrom_head_elem #(.LV(8), .PAD(0), .JOIN(1), .ROWS(32), .CUT(CUT), .SPLIT9(SPLIT9),
            .INSTANCE($sformatf("%sha%0d", PFX, q)), .SAFE(1)) a (
            .clk(clk), .rst_n(rst_n), .go(ag), .row0(ar), .x(ax), .b_v(bvalid), .b_d(ad), .o_v(), .o_d(),
            .l_v(hv), .l_d(hb), .done(), .best_row(), .best_bits(), .best_key(), .fault(af[q]));
        ot_dsrom_markov_head_driver #(.ENABLE(ENABLE), .PINREG(PINREG), .CACHE_PINREG(CACHE_PINREG), .VALID_ROWS(NVALID),
            .CUT(CUT), .SPLIT9(SPLIT9), .INSTANCE($sformatf("%smk%0d", PFX, q))) markov (
            .clk(clk), .rst_n(rst_n), .start(accept), .start_ready(sr[q]), .row0(driver_row), .transaction(transaction),
            .embed_valid(embed_valid), .embed_ready(er[q]), .embed_data(embed_data), .embed_beat(embed_beat),
            .embed_id(embed_id), .embed_last(embed_last),
            .head_go(mg[q]), .head_valid(hv), .head_bits(hb), .head_fault(af[q]),
            .joined_valid(), .joined_bits(), .joined_row(),
            .done(md[q]), .best_valid(mhave[q]), .best_row(mr[17*q+:17]), .best_bits(mb[32*q+:32]), .fault(mf[q]));
    end endgenerate
    function automatic [31:0] key(input [31:0] v);
        reg [31:0] z; begin z = (v[30:0] == 0) ? 0 : v; key = z[31] ? ~z : (z ^ 32'h80000000); end
    endfunction
    function automatic [81:0] pick(input [81:0] u, v);
        begin
            if (!u[81]) pick = v; else if (!v[81]) pick = u;
            else pick = (v[80:49] > u[80:49] || (v[80:49] == u[80:49] && v[48:32] < u[48:32])) ? v : u;
        end
    endfunction
    reg [81:0] c0, c1; wire [81:0] result = pick(c0, c1); reg reduce_valid, reduce_started;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin
        busy <= 0; base <= 0; control_fault <= 0; done <= 0; best_valid <= 0; best_row <= 0; best_bits <= 0;
        reduce_valid <= 0; reduce_started <= 0; c0 <= 0; c1 <= 0;
    end else begin
        done <= 0; reduce_valid <= 0;
        if (start && !start_ready) control_fault <= 1;                // pushed start at a busy bundle
        if (embed_valid && !(&er)) control_fault <= 1;                // pushed beat at a not-ready driver
        if ((|mg) && !(&mg)) control_fault <= 1;
        if (accept) begin busy <= 1; base <= row0; reduce_started <= 0; best_valid <= 0; end
        if (busy && (&md) && !reduce_started && !fault) begin
            c0 <= pick({mhave[0], key(mb[31:0]), mr[16:0], mb[31:0]}, {mhave[1], key(mb[63:32]), mr[33:17], mb[63:32]});
            c1 <= pick({mhave[2], key(mb[95:64]), mr[50:34], mb[95:64]}, {mhave[3], key(mb[127:96]), mr[67:51], mb[127:96]});
            reduce_valid <= 1; reduce_started <= 1;
        end
        if (reduce_valid && !fault) begin
            done <= 1; busy <= 0; best_valid <= result[81]; best_row <= result[48:32]; best_bits <= result[31:0];
        end
    end
    assign fault = bfault | (|af) | (|mf) | control_fault;
endmodule

// The die: NB bundles + one shared embedding lookup + registered trees.
module ot_dsrom_markov_head_full340 #(
    parameter bit ENABLE = 0,
    parameter integer NB = 85,               // bundles on this die (production 85 = 340 A)
    parameter integer ROW_BASE = 0,          // global vocabulary row of bundle 0's first row
    parameter integer DIE_ROWS = 10774,      // valid rows of this die (manifest; the tail bundle is ragged)
    parameter integer FIRST_BUNDLE = 0,      // bundle id of instance 0 (ROM image names b<id>_*)
    parameter integer PINREG = 1, parameter integer CACHE_PINREG = 0, parameter integer A_INPUT_STAGES = 4,
    parameter [8:0] CUT = 511, parameter integer SPLIT9 = 1,
    parameter integer FAN = 8,
    parameter integer LOOKUP = 1,            // 1: the die's shared lookup is inside; 0: embed_* pins (MD6 element)
    parameter integer MUTANT = 0, parameter integer MUTANT_BUNDLE = 0
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
        ot_dsrom_markov_head_bundle_x #(.ENABLE(ENABLE), .PINREG(PINREG), .CACHE_PINREG(CACHE_PINREG), .VALID_ROWS(VR),
            .A_INPUT_STAGES(A_INPUT_STAGES), .CUT(CUT), .SPLIT9(SPLIT9),
            .PFX($sformatf("b%03d_", FIRST_BUNDLE + b))) u (
            .clk(clk), .rst_n(rst_n), .start(s_m[0]), .start_ready(b_rdy[b]),
            .row0(17'(ROW_BASE + 128*b)), .transaction(s_m[33:2]),
            .embed_valid(s_m[1]), .embed_data(s_m[289:34]), .embed_beat(s_m[293:290]), .embed_id(s_m[325:294]),
            .embed_last(s_m[326]),
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
    ot_mtp_and_tree #(.W(4), .N(NB), .FAN(FAN), .DEPTH(DB)) u_t (.clk(clk), .rst_n(rst_n), .d(tin), .q(tq));
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
