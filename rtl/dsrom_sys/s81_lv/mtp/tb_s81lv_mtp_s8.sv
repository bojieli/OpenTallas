`timescale 1ns/1ps
// tb_s81lv_mtp_s8 (s81lv/C-mtp, 2026-10-12): seam S8 bench of the S81 layer vehicle on the head run.
// DUT: ot_s81lv_mtp_s8 (real dsfd_mtp_hrow_src x3, dsfd_mtp_hrow_tc / dsfd_mtp_hrow, dsfd_cap_mtp_ep,
// dsfd_mtp_seq_rtt, dsfd_coll_mtp_ep, dsfd_vm_mtp_ep).
// Stimulus (tools/s81_lv/mtp_stim.py, golden = su_cases_v2_ildr.pkl 'head.final_norm' h, the 1M token's final layer
// output): the 640 H_STORE rows in HC-master format (S_WR slots a cycle, lane masks, unmasked lanes carry garbage),
// in a permuted order with idle cycles; the head RESULT flit {user, pos, argmax} is offered EARLY (during H_STORE).
// Checks:
//   C1 hrow readback through its real read port, addressed from the SEED's own {epoch, user, pos}: 2 positions x 240
//      beats; beats of h == golden rows bit-exact (640 rows), pad beats == 0;
//   C2 the seed handshake (collective end) happens after every hidden-lane flit landed at the hrow (and after the
//      last H_STORE row), never before; the RESULT is accepted only then;
//   C3 seed fields: user, closing pos = head pos, epoch = the hrow row's epoch, token = head argmax, nrow = pos + 1;
//   C4 draft chain: rows-ready -> 5 draft-head steps j = 1..5 (step 1 carries the bonus = argmax, step j > 1 the
//      previous draft) -> token return: DRAFT flit {user, base pos+1, epoch, n 5, drafts} then the held RESULT;
//   C5 no fault: hrow store / window / hrow_src / sequencer.
module tb_s81lv_mtp_s8;
    parameter integer TILES = 1;
    localparam integer NW = 21, UW = 10, FLIT = 512, AW = 24, S_WR = 8, S_BASE = 6144, HROWS = 640;
    localparam integer SW = UW + 3 * NW + 4, DW = UW + 3 + NW;
    localparam integer HDR_TYPE = 16, HDR_USER = 32, HDR_POS = 40, HDR_IDX = 61, HDR_VAL = 82, HDR_ADDR = 135;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;

    reg [511:0] hrow_g [0:HROWS-1];
    reg [29:0]  wr [0:4095];
    reg [31:0]  meta [0:15];
    integer nwr;
    reg [UW-1:0] user; reg [NW-1:0] pos; reg [3:0] ep; reg [NW-1:0] glen, plen, idx; reg [31:0] val;
    integer seed_v;
    initial begin
        $readmemh("hstore.mem", hrow_g);
        $readmemh("meta.mem", meta);
        nwr = meta[0]; user = meta[1]; pos = meta[2]; ep = meta[3]; glen = meta[4]; plen = meta[5];
        idx = meta[6]; val = meta[7]; seed_v = meta[8];
        $readmemh("writes.mem", wr, 0, nwr - 1);
    end

    reg [S_WR-1:0] wq_v = 0; reg [S_WR*14-1:0] wq_row = 0; reg [S_WR*16-1:0] wq_mask = 0; reg [S_WR*512-1:0] wq_d = 0;
    reg c_rv = 0; wire c_rr; reg [FLIT-1:0] c_rd = 0;
    wire c_sv; wire [SW-1:0] c_sd; wire c_tv; wire [FLIT-1:0] c_td;
    wire c_hv; wire [DW-1:0] c_hd; reg c_wv = 0; wire c_wr; reg [UW-1:0] c_wd = 0;
    reg c_qv = 0; wire c_qr; reg [DW-1:0] c_qd = 0;
    wire [AW:0] vrq; wire vrg; wire [1024:0] vrs;
    wire h_done, hrow_landed; wire [3:0] hrow_flt; wire [5:0] src_flt; wire [2*NW+UW+4:0] t_acc;
    ot_s81lv_mtp_s8 #(.TILES(TILES)) dut (.ck(clk), .rst(rst), .cfg_user(user), .cfg_pos(pos), .cfg_ep(ep),
        .cfg_seq({glen, plen}), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d),
        .c_rv(c_rv), .c_rr(c_rr), .c_rd(c_rd), .c_sv(c_sv), .c_sr(1'b1), .c_sd(c_sd), .c_tv(c_tv), .c_tr(1'b1), .c_td(c_td),
        .c_hv(c_hv), .c_hr(1'b1), .c_hd(c_hd), .c_wv(c_wv), .c_wr(c_wr), .c_wd(c_wd), .c_qv(c_qv), .c_qr(c_qr), .c_qd(c_qd),
        .f_vrq(vrq), .t_vrq(vrg), .t_vrs(vrs), .h_done(h_done), .hrow_landed(hrow_landed), .hrow_flt(hrow_flt),
        .src_flt(src_flt), .t_acc(t_acc));
    // seed-client read link (bench transmitter = the real grant-protocol sender)
    reg q_v = 0; wire q_r; reg [AW-1:0] q_a = 0;
    ot_dsrom_mtp_ltx #(.W(AW)) u_q (.clk(clk), .rst_n(rst), .c_valid(q_v), .c_ready(q_r), .c_data(q_a),
        .l_valid(vrq[0]), .l_ready(vrg), .l_data(vrq[AW:1]));

    // ---------------- event cycles
    integer cyc_hs_last = -1, cyc_done = -1, cyc_landed = -1, cyc_res = -1, cyc_seed = -1;
    always @(posedge clk) begin
        if (h_done && cyc_done < 0) cyc_done = cyc;
        if (hrow_landed && cyc_landed < 0) cyc_landed = cyc;
    end

    // ---------------- H_STORE driver: k writes a cycle (1..S_WR), idle cycles, lane masks; garbage in masked-off lanes
    integer wi = 0, k, s, l, n;
    initial begin
        wait (rst);
        repeat (20) @(posedge clk);
        while (wi < nwr) begin
            @(negedge clk);
            wq_v = 0;
            if (($urandom % 5) != 0) begin
                n = 1 + ($urandom % S_WR);
                for (s = 0; s < n && wi < nwr; s = s + 1) begin
                    wq_v[s] = 1'b1;
                    wq_row[14*s +: 14] = S_BASE + wr[wi][29:16];
                    wq_mask[16*s +: 16] = wr[wi][15:0];
                    for (l = 0; l < 16; l = l + 1)
                        wq_d[512*s + 32*l +: 32] = wr[wi][l] ? hrow_g[wr[wi][29:16]][32*l +: 32]
                                                             : ~hrow_g[wr[wi][29:16]][32*l +: 32];
                    wi = wi + 1;
                end
                if (wi == nwr) cyc_hs_last = cyc;
            end
        end
        @(negedge clk) wq_v = 0;
    end

    // ---------------- head RESULT, offered early (after ~1/4 of the H_STORE writes)
    initial begin
        wait (wi > nwr / 4);
        @(negedge clk);
        c_rd = 0; c_rd[15:0] = 16'h3a00; c_rd[HDR_TYPE +: 4] = 4'd2; c_rd[HDR_USER +: 8] = user[7:0];
        c_rd[HDR_POS +: NW] = pos; c_rd[HDR_IDX +: NW] = idx; c_rd[HDR_VAL +: 32] = val;
        c_rv = 1;
        @(posedge clk); while (!c_rr) @(posedge clk);
        cyc_res = cyc;
        @(negedge clk) c_rv = 0;
    end

    // ---------------- seed capture, hrow readback, draft chain
    reg [SW-1:0] seedd; reg seen_seed = 0;
    always @(posedge clk) if (c_sv && !seen_seed) begin seen_seed <= 1; seedd <= c_sd; cyc_seed = cyc; end
    wire [UW-1:0] s_user = seedd[SW-1 -: UW];
    wire [NW-1:0] s_pos = seedd[3*NW+3 -: NW];
    wire [NW-1:0] s_nrow = seedd[2*NW+3 -: NW];
    wire [NW-1:0] s_tok = seedd[NW+3 -: NW];
    wire [3:0] s_ep = seedd[3:0];
    integer nrsp = 0, rows_ok = 0, rows_bad = 0, pad_ok = 0, pad_bad = 0, first_bad = -1, nseeds = 0;
    always @(posedge clk) if (c_sv) nseeds = nseeds + 1;
    always @(posedge clk) if (vrs[0]) begin : chk
        integer pn, b, gb;
        pn = nrsp / 240; b = nrsp % 240; gb = pn * 240 + b;
        if (gb < HROWS / 2) begin
            if (vrs[512:1] === hrow_g[2*gb]) rows_ok = rows_ok + 1; else begin rows_bad = rows_bad + 1; if (first_bad < 0) first_bad = 2*gb; end
            if (vrs[1024:513] === hrow_g[2*gb+1]) rows_ok = rows_ok + 1; else begin rows_bad = rows_bad + 1; if (first_bad < 0) first_bad = 2*gb+1; end
        end else begin
            if (vrs[1024:1] === 1024'd0) pad_ok = pad_ok + 1; else pad_bad = pad_bad + 1;
        end
        nrsp = nrsp + 1;
    end
    integer nreq = 0, j;
    reg [NW-1:0] dr [1:5]; reg [NW-1:0] prev;
    integer steps_ok = 0, steps_bad = 0;
    initial begin
        wait (seen_seed);
        @(negedge clk);
        while (nreq < 480) begin
            q_v = 1; q_a = {1'b0, s_ep, s_user[2:0], 8'(s_pos + nreq / 240), 8'(nreq % 240)};
            @(posedge clk); if (q_r) nreq = nreq + 1;
            @(negedge clk);
        end
        q_v = 0;
        wait (nrsp == 480);
        // rows on the head die -> draft-head steps
        @(negedge clk); c_wv = 1; c_wd = s_user;
        @(posedge clk); while (!c_wr) @(posedge clk);
        @(negedge clk) c_wv = 0;
        prev = idx;
        for (j = 1; j <= 5; j = j + 1) begin
            @(posedge clk); while (!c_hv) @(posedge clk);
            if (c_hd[DW-1 -: UW] == user && c_hd[NW +: 3] == j && c_hd[NW-1:0] == prev) steps_ok = steps_ok + 1;
            else steps_bad = steps_bad + 1;
            dr[j] = (idx * 3 + 17 * j) & 21'h1FFFFF; prev = dr[j];
            @(negedge clk); c_qv = 1; c_qd = {user, 3'(j), dr[j]};
            @(posedge clk); while (!c_qr) @(posedge clk);
            @(negedge clk) c_qv = 0;
        end
    end
    // token return
    integer ntok = 0, tok_ok = 0, tok_bad = 0;
    always @(posedge clk) if (c_tv) begin : tk
        reg ok; integer m;
        ok = 1;
        if (ntok == 0) begin
            if (c_td[HDR_TYPE +: 4] != 4'd4 || c_td[HDR_USER +: 8] != user[7:0] || c_td[HDR_POS +: NW] != pos + 1 ||
                c_td[HDR_ADDR +: 4] != ep || c_td[248 +: 3] != 3'd5) ok = 0;
            for (m = 1; m <= 5; m = m + 1) if (c_td[256 + (m-1)*NW +: NW] != dr[m]) ok = 0;
        end else if (ntok == 1) begin
            if (c_td[HDR_TYPE +: 4] != 4'd2 || c_td[HDR_POS +: NW] != pos || c_td[HDR_IDX +: NW] != idx ||
                c_td[HDR_VAL +: 32] != val) ok = 0;
        end else ok = 0;
        if (ok) tok_ok = tok_ok + 1; else tok_bad = tok_bad + 1;
        ntok = ntok + 1;
    end

    // ---------------- finish
    integer t0;
    initial begin
        repeat (5) @(posedge clk); rst = 1;
        t0 = 0;
        while (!(ntok >= 2 && nrsp == 480) && t0 < 200000) begin @(posedge clk); t0 = t0 + 1; end
        repeat (50) @(posedge clk);
        begin : fin
            integer c1, c2, c3, c4, c5, pass;
            c1 = (rows_ok == HROWS && rows_bad == 0 && pad_ok == 160 && pad_bad == 0);
            c2 = (cyc_seed > cyc_landed && cyc_landed >= 0 && cyc_seed > cyc_hs_last && cyc_res > cyc_landed && nseeds == 1);
            c3 = (seen_seed && s_user == user && s_pos == pos && s_ep == ep && s_tok == idx && s_nrow == pos + 1);
            c4 = (steps_ok == 5 && steps_bad == 0 && tok_ok == 2 && tok_bad == 0 && ntok == 2);
            c5 = (hrow_flt == 0 && src_flt == 0 && t_acc[2*NW+UW+4] == 0);
            pass = c1 && c2 && c3 && c4 && c5;
            $display("S8 rows_ok=%0d rows_bad=%0d first_bad_row=%0d pad_ok=%0d pad_bad=%0d beats=%0d hs_last=%0d h_done=%0d landed=%0d res_acc=%0d seed=%0d nseeds=%0d seed_user=%0d seed_pos=%0d seed_ep=%0d seed_tok=%0d seed_nrow=%0d steps_ok=%0d steps_bad=%0d tok_ok=%0d tok_bad=%0d hrow_flt=%0d src_flt=%0d seq_fault=%0d C1=%0d C2=%0d C3=%0d C4=%0d C5=%0d TILES=%0d timeout=%0d",
                rows_ok, rows_bad, first_bad, pad_ok, pad_bad, nrsp, cyc_hs_last, cyc_done, cyc_landed, cyc_res, cyc_seed, nseeds,
                s_user, s_pos, s_ep, s_tok, s_nrow, steps_ok, steps_bad, tok_ok, tok_bad, hrow_flt, src_flt, t_acc[2*NW+UW+4],
                c1, c2, c3, c4, c5, TILES, t0 >= 200000);
            $display("S8_RESULT %s", pass ? "PASS" : "FAIL");
        end
        $finish;
    end
endmodule
