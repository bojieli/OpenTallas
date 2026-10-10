`timescale 1ns/1ps
// kv-die 2026-10-09 (review-1149 KV14): the KV-die write path end to end for one stack -- posted new-position rows ->
// ot_qkvd_kv_wq (landing write queue) -> 32 x ot_qwen_stream4_cdc_pc (core 833.333 ps -> HBM 1,024 ps) -> an HBM-side
// controller model (hand-off, WR column after CTRL_LAT hclk, write-done) -> 32 x ot_qfd_emb_pcport KVW = 2 (SECDED
// encode of the CDC's h_cdata, PHY write data two edges after the column) -> an HBM array keyed {pc, sector}.
// Checks: every row's 4 sectors land at the layout address (pc = {q, t[2:0]}, sec = {layer, g, v, t[13:9], t[6:3]},
// computed here independently), the stored 288-b codeword is the SECDED72 x 4 encoding of the row's bytes (decoded
// here with no error), exactly NROW x 4 writes, every row retired (rw_v), no fault.
// MUT: 1..3 the write-queue mutants (ot_qkvd_kv_wq), 4 the pcport check-column mutant (MUT 4 in ot_qfd_emb_pcport).
module tb_qkvd_kv_wq #(parameter integer DIST = 0, parameter integer RLY = 1, parameter integer MUT = 0, parameter integer NROW = 24, parameter integer CTRL_LAT = 6);
    localparam integer HD = 128, NPC = 32, TAGW = 9;
    import ot_qfd_emb_pkg::*;
    reg clk = 0, hclk = 0, rst_n = 0;
    always #0.4166665 clk = ~clk;
    always #0.512 hclk = ~hclk;
    // ---- source rows ----
    reg              kvw_v;
    reg  [1:0]       kvw_vg;
    reg  [13:0]      kvw_t;
    reg  [5:0]       kvw_layer;
    reg  [HD*8-1:0]  kvw_d;
    wire             kvw_cr;
    reg  [HD*8-1:0]  rows  [0:NROW-1];
    reg  [21:0]      rid   [0:NROW-1];
    // ---- DUT ----
    wire [NPC-1:0]       w_v, w_room, wd_v;
    wire [24*NPC-1:0]    w_sec;
    wire [256*NPC-1:0]   w_data;
    wire [TAGW*NPC-1:0]  w_tag, wd_tag;
    wire                 rw_v, wq_fault;
    wire [21:0]          rw_id;
    // redesign-qwen: DIST = 1 benches the distributed successor ot_qkvd_kv_wq_dist (same ports)
    generate if (DIST == 0) begin : g_wq
    ot_qkvd_kv_wq #(.HD(HD), .NPC(NPC), .QD(4), .TAGW(TAGW), .MUT(MUT >= 1 && MUT <= 3 ? MUT : 0)) u_wq (
        .clk(clk), .rst_n(rst_n), .kvw_v(kvw_v), .kvw_vg(kvw_vg), .kvw_t(kvw_t), .kvw_layer(kvw_layer), .kvw_d(kvw_d),
        .kvw_cr(kvw_cr), .w_v(w_v), .w_sec(w_sec), .w_data(w_data), .w_tag(w_tag), .w_room(w_room), .wd_v(wd_v),
        .wd_tag(wd_tag), .rw_v(rw_v), .rw_id(rw_id), .fault(wq_fault));
    end else if (DIST == 2) begin : g_wqt
    ot_qkvd_kv_wq_tiles #(.HD(HD), .NPC(NPC), .QD(4), .TAGW(TAGW), .MUT(MUT >= 1 && MUT <= 3 ? MUT : 0), .RLY(RLY)) u_wq (
        .clk(clk), .rst_n(rst_n), .kvw_v(kvw_v), .kvw_vg(kvw_vg), .kvw_t(kvw_t), .kvw_layer(kvw_layer), .kvw_d(kvw_d),
        .kvw_cr(kvw_cr), .w_v(w_v), .w_sec(w_sec), .w_data(w_data), .w_tag(w_tag), .w_room(w_room), .wd_v(wd_v),
        .wd_tag(wd_tag), .rw_v(rw_v), .rw_id(rw_id), .fault(wq_fault));
    end else begin : g_wqd
    ot_qkvd_kv_wq_dist #(.HD(HD), .NPC(NPC), .QD(4), .TAGW(TAGW), .MUT(MUT >= 1 && MUT <= 3 ? MUT : 0)) u_wq (
        .clk(clk), .rst_n(rst_n), .kvw_v(kvw_v), .kvw_vg(kvw_vg), .kvw_t(kvw_t), .kvw_layer(kvw_layer), .kvw_d(kvw_d),
        .kvw_cr(kvw_cr), .w_v(w_v), .w_sec(w_sec), .w_data(w_data), .w_tag(w_tag), .w_room(w_room), .wd_v(wd_v),
        .wd_tag(wd_tag), .rw_v(rw_v), .rw_id(rw_id), .fault(wq_fault));
    end endgenerate
    // ---- per PC: CDC + HBM-side controller model + pcport (KVW 2) ----
    reg  [287:0] mem [int];          // key {pc, sec}
    int          nwrites = 0, bad_key = 0;
    wire [NPC-1:0] c_fault, h_fault, p_fault;
    genvar p;
    generate for (p = 0; p < NPC; p = p + 1) begin : g_pc
        wire        h_wv, h_cv;
        wire [23:0] h_wsec, h_csec;
        wire [255:0] h_cdata;
        wire [TAGW-1:0] h_ctag;
        wire [2:0]  h_cred;
        wire        l_v; wire [16:0] l_sec; wire [7:0] l_row; wire [255:0] l_data;
        reg         h_hand, h_wcon, h_av;
        reg  [TAGW-1:0] h_atag;
        ot_qwen_stream4_cdc_pc #(.TAGW(TAGW)) u_cdc (
            .clk(clk), .c_arst_n(rst_n), .l_v(l_v), .l_sec(l_sec), .l_row(l_row), .l_data(l_data), .l_pop(1'b0),
            .w_v(w_v[p]), .w_sec(w_sec[24*p +: 24]), .w_data(w_data[256*p +: 256]), .w_tag(w_tag[TAGW*p +: TAGW]),
            .w_room(w_room[p]), .wd_v(wd_v[p]), .wd_tag(wd_tag[TAGW*p +: TAGW]), .c_fault(c_fault[p]),
            .hclk(hclk), .h_arst_n(rst_n), .h_lv(1'b0), .h_lsec(17'd0), .h_lrow(8'd0), .h_ldata(256'd0),
            .h_cred(h_cred), .h_wv(h_wv), .h_wsec(h_wsec), .h_hand(h_hand), .h_wcon(h_wcon), .h_cv(h_cv),
            .h_csec(h_csec), .h_cdata(h_cdata), .h_ctag(h_ctag), .h_av(h_av), .h_atag(h_atag), .h_fault(h_fault[p]));
        wire [287:0] wd;
        wire kv_v_unused, em_v_unused; wire [287:0] kv_d_unused; wire [257:0] em_d_unused;
        ot_qfd_emb_pcport #(.KVW(2), .MUT(MUT == 4 ? 4 : 0)) u_port (
            .clk(hclk), .rst_n(rst_n), .col_v(h_wcon), .col_we(h_wcon), .col_sr(1'b0), .w_v(1'b0), .w_d(256'd0),
            .wd(wd), .kw_v(h_cv), .kw_d(h_cdata), .r_v(1'b0), .r_d(288'd0), .kv_v(kv_v_unused), .kv_d(kv_d_unused),
            .em_v(em_v_unused), .em_d(em_d_unused), .fault(p_fault[p]));
        // HBM-side controller model: hand-off, WR column CTRL_LAT hclk later, the PHY takes wd two edges after the
        // column (the sector from the CDC's completion capture), write-done one edge after that
        int st = 0, cnt = 0;
        reg [23:0] sec1, sec2;
        reg [TAGW-1:0] tag1, tag2;
        reg c1 = 0, c2 = 0;
        always @(posedge hclk) begin
            h_hand <= 1'b0; h_wcon <= 1'b0; h_av <= 1'b0;
            c1 <= h_wcon; c2 <= c1;
            if (h_cv) begin sec1 <= h_csec; tag1 <= h_ctag; end
            sec2 <= sec1; tag2 <= tag1;
            if (c2) begin
                if (mem.exists((p << 24) | sec1)) bad_key++;
                mem[(p << 24) | sec1] = wd; nwrites++;
                h_av <= 1'b1; h_atag <= tag1;
            end
            case (st)
                0: if (h_wv && rst_n) begin h_hand <= 1'b1; st = 1; cnt = CTRL_LAT; end
                1: if (cnt > 0) cnt--; else begin h_wcon <= 1'b1; st = 2; cnt = 4; end
                2: if (cnt > 0) cnt--; else st = 0;
            endcase
        end
    end endgenerate
    // ---- stimulus ----
    int nsent = 0, credits = 4, nret = 0, cyc = 0, i, b;
    initial begin
        for (i = 0; i < NROW; i++) begin
            for (b = 0; b < HD; b++) rows[i][8*b +: 8] = $urandom;
            rid[i] = {6'(i / 4 + 3 * (i % 5)), 2'(i % 4), 14'((($urandom % 64) << 9) | (0 << 7) | ($urandom % 128))};
            // distinct (layer, vg, t) keys
            rid[i][21:16] = 6'(i / 4); rid[i][15:14] = 2'(i % 4);
        end
        kvw_v = 0;
        repeat (20) @(posedge clk);
        rst_n = 1;
        repeat (40) @(posedge clk);
    end
    always @(posedge clk) begin
        cyc++;
        kvw_v <= 1'b0;
        if (kvw_cr) credits++;
        if (rw_v) nret++;
        if (rst_n && cyc > 60 && nsent < NROW && credits > 0 && !(kvw_cr && 0)) begin
            kvw_v <= 1'b1; kvw_vg <= rid[nsent][15:14]; kvw_t <= rid[nsent][13:0]; kvw_layer <= rid[nsent][21:16];
            kvw_d <= rows[nsent]; nsent++; credits--;
        end
        if (nret == NROW || cyc > 60000) begin
            check();
            $finish;
        end
    end
    task check();
        int bad = 0, missing = 0, q, ecc_bad = 0;
        reg [287:0] cw, ex;
        reg [4:0] pc; reg [23:0] sec; reg [13:0] t; reg [1:0] vg; reg [5:0] l;
        reg [65:0] dc;
        for (i = 0; i < NROW; i++) begin
            t = rid[i][13:0]; vg = rid[i][15:14]; l = rid[i][21:16];
            for (q = 0; q < 4; q++) begin
                pc = {q[1:0], t[2:0]};
                sec = {7'd0, l, vg[0], vg[1], t[13:9], t[6:3]};
                if (!mem.exists((int'(pc) << 24) | sec)) begin missing++; continue; end
                cw = mem[(int'(pc) << 24) | sec];
                ex = enc256(rows[i][256*q +: 256]);
                if (cw != ex) bad++;
                for (b = 0; b < 4; b++) begin
                    dc = cor64(cw[b*72 +: 72], syn64(cw[b*72 +: 72]));
                    if (dc[65] || dc[64] || dc[63:0] != rows[i][256*q + 64*b +: 64]) ecc_bad++;
                end
            end
        end
        $display("{\"mut\": %0d, \"rows\": %0d, \"retired\": %0d, \"writes\": %0d, \"missing\": %0d, \"bad_codeword\": %0d, \"ecc_bad\": %0d, \"rewrites\": %0d, \"faults\": %0d, \"cycles\": %0d, \"exact\": %s}",
                 MUT, NROW, nret, nwrites, missing, bad, ecc_bad, bad_key, wq_fault + $countones(c_fault) + $countones(h_fault) + $countones(p_fault), cyc,
                 (nret == NROW && nwrites == 4 * NROW && missing == 0 && bad == 0 && ecc_bad == 0 && bad_key == 0 && !wq_fault
                  && c_fault == 0 && h_fault == 0 && p_fault == 0) ? "true" : "false");
    endtask
endmodule
