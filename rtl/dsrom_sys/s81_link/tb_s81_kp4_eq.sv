`timescale 1ns/1ps
// tb_s81_kp4_eq (S81-TILES2 2026-10-17): bit-exact equivalence of the four-tile KP4 decoder re-split (dsyn / ddly /
// dchn / dout, ot_s81_kp4_dec) against the frozen two-tile decoder of 33a35eb7d (ref/ot_s81_kp4_dec_r33.sv), on the
// tb_s81_kp4 stimulus (encoder + random symbol errors, frames <= t and > t).
//   * RTL: every output of u_d (DMUT) equals the reference u_r (MUT 0) on every cycle after reset (same latency, 60);
//   * HW: kp4_dec_hw = the four tiles with every tile pin registered (cluster in / out + both pins of every seam)
//     PLUS the hardened 2x2 parent's own pin registers (s81lk_kp4_dec pin_regs, SMHKP4 2026-10-18: +1 in, +1 out);
//     its q_* equal the reference delayed by DLY_Q = 8 cycles and lock by DLY_L = 4 (n_* counters are not cycle-aligned in this model, as before) (pin registers of the
//     33a35eb7d cluster: 4 on q_*) -> the re-split adds 2 cycles and the parent landing 2 more in hardware;
//   * the original tb_s81_kp4 exactness checks against tools/s81_link/rs544.py still run on u_d.
// PASS line: TB_S81_KP4_EQ ... PASS.  A mutant (DMUT 2 / 3, SEAMMUT 1: the word seam one register short, or PREGMUT 1:
// the parent's input landing register missing) must FAIL.
module tb_s81_kp4_eq;
    parameter integer NF = 120, NV = 16, EMUT = 0, DMUT = 0, SEAMMUT = 0, PREGMUT = 0;
    reg clk = 0, rst_n = 0;
    always #0.41667 clk = ~clk;
    reg tx_v = 0; reg [511:0] tx_d = 0;
    wire p_v; wire [543:0] p_d; wire efault;
    ot_s81_kp4_enc #(.MUT(EMUT)) u_e (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(p_v), .p_d(p_d), .fault(efault));
    reg [543:0] ch_d; reg ch_v;
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_relock;
    ot_s81_kp4_dec #(.MUT(DMUT)) u_d (.clk(clk), .rst_n(rst_n), .p_v(ch_v), .p_d(ch_d), .q_v(q_v), .q_d(q_d), .q_first(q_first),
        .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock), .n_corr(n_corr), .n_unc(n_unc), .n_relock(n_relock));
    // ---- reference (33a35eb7d) and hardware-view composition
    wire r_v, r_first, r_unc, r_lock; wire [511:0] r_d; wire [4:0] r_nerr; wire [7:0] r_seq; wire [31:0] r_corr, r_unc_n, r_relock;
    ot_s81_kp4_dec_r33 u_r (.clk(clk), .rst_n(rst_n), .p_v(ch_v), .p_d(ch_d), .q_v(r_v), .q_d(r_d), .q_first(r_first),
        .q_unc(r_unc), .q_nerr(r_nerr), .q_seq(r_seq), .lock(r_lock), .n_corr(r_corr), .n_unc(r_unc_n), .n_relock(r_relock));
    wire h_v, h_first, h_unc, h_lock; wire [511:0] h_d; wire [4:0] h_nerr; wire [7:0] h_seq; wire [31:0] h_corr, h_unc_n, h_relock;
    kp4_dec_hw #(.MUT(DMUT), .SEAMMUT(SEAMMUT), .PREGMUT(PREGMUT)) u_h (.clk(clk), .rst_n(rst_n), .p_v(ch_v), .p_d(ch_d), .q_v(h_v), .q_d(h_d), .q_first(h_first),
        .q_unc(h_unc), .q_nerr(h_nerr), .q_seq(h_seq), .lock(h_lock), .n_corr(h_corr), .n_unc(h_unc_n), .n_relock(h_relock));
    localparam integer DLY_Q = 8, DLY_L = 4;
    reg [530:0] rq_dl [0:DLY_Q]; reg rl_dl [0:DLY_L]; reg [95:0] rn_dl [0:DLY_L];
    integer k_, eq_rtl_bad = 0, eq_hw_bad = 0, eq_cyc = 0, eq_qv = 0;
    always @(posedge clk) begin
        rq_dl[0] <= {r_v, r_first, r_unc, r_nerr, r_seq, r_d}; rl_dl[0] <= r_lock; rn_dl[0] <= {r_corr, r_unc_n, r_relock};
        for (k_ = 1; k_ <= DLY_Q; k_ = k_ + 1) rq_dl[k_] <= rq_dl[k_ - 1];
        for (k_ = 1; k_ <= DLY_L; k_ = k_ + 1) begin rl_dl[k_] <= rl_dl[k_ - 1]; rn_dl[k_] <= rn_dl[k_ - 1]; end
    end
    always @(posedge clk) if (rst_n) begin
        eq_cyc = eq_cyc + 1; if (r_v) eq_qv = eq_qv + 1;
        if ({q_v, q_first, q_unc, q_nerr, q_seq, q_d, lock, n_corr, n_unc, n_relock} !==
            {r_v, r_first, r_unc, r_nerr, r_seq, r_d, r_lock, r_corr, r_unc_n, r_relock}) begin
            eq_rtl_bad = eq_rtl_bad + 1; if (eq_rtl_bad < 4) $display("ERR rtl mismatch cycle %0d", eq_cyc); end
        if (eq_cyc > DLY_Q + 2 && ({h_v, h_first, h_unc, h_nerr, h_seq, h_d} !== rq_dl[DLY_Q - 1] || h_lock !== rl_dl[DLY_L - 1])) begin
            eq_hw_bad = eq_hw_bad + 1; if (eq_hw_bad < 4) $display("ERR hw mismatch cycle %0d", eq_cyc); end
    end
    // ---- frames sent
    reg [511:0] sent [0:(NF+64)*10];
    reg [299:0] vpar [0:NV-1];
    reg [511:0] vbeat [0:NV*10-1];
    integer nerr_of [0:NF+64];
    integer i, f, b, fd, r, nb = 0;
    string vec;
    reg [4*5+4*1280+4*360+40:0] line;
    initial begin
        if (!$value$plusargs("vec=%s", vec)) $fatal(1, "+vec=<rs544 vectors> required");
        fd = $fopen(vec, "r");
        for (f = 0; f < NV; f = f + 1) begin : rd
            reg [19:0] h; reg [511:0] bt [0:9]; reg [299:0] pr;
            r = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h %h %h\n", h, bt[0], bt[1], bt[2], bt[3], bt[4], bt[5], bt[6], bt[7], bt[8], bt[9], pr);
            for (b = 0; b < 10; b = b + 1) vbeat[10 * f + b] = bt[b];
            vpar[f] = pr;
        end
        $fclose(fd);
        for (f = 0; f <= NF + 64; f = f + 1) nerr_of[f] = (f % 8 == 7) ? 16 + (f / 8) % 7 : f % 16;
        repeat (5) @(posedge clk); rst_n = 1;
        repeat (3) @(posedge clk);
        for (f = 0; f < NF + 8; f = f + 1)
            for (b = 0; b < 10; b = b + 1) begin
                @(negedge clk);
                tx_v = 1;
                tx_d = (f < NV) ? vbeat[10 * f + b] : {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                                                     $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                sent[nb] = tx_d; nb = nb + 1;
            end
        // keep the stream running (the PMA never stops) until the pipeline drains
        forever begin @(negedge clk); tx_d = 0; if (nb < (NF + 64) * 10) begin sent[nb] = 0; nb = nb + 1; end end
    end
    // ---- encoder parity vs reference (frame index = PMA frame count)
    integer pw = 0, pf = 0, par_bad = 0, par_chk = 0;
    reg [5439:0] cwb;
    always @(posedge clk) if (p_v) begin
        cwb[5439 - 544 * (pw % 10) -: 544] = p_d;
        if (pw % 10 == 9) begin
            if (pf < NV) begin par_chk = par_chk + 1; if (cwb[299:0] !== vpar[pf]) begin par_bad = par_bad + 1; if (par_bad < 4) $display("ERR parity frame %0d", pf); end end
            pf = pf + 1;
        end
        pw = pw + 1;
    end
    // ---- channel: symbol errors per codeword
    integer cw_i = 0, wi = 0;
    reg [5439:0] emask;
    task automatic draw(input integer n);
        integer m, p, used [0:543], ok;
        reg [9:0] ev;
        begin
            emask = 0;
            for (m = 0; m < 544; m = m + 1) used[m] = 0;
            m = 0;
            while (m < n) begin
                p = $urandom % 544;
                if (!used[p]) begin used[p] = 1; ev = 10'($urandom % 1023 + 1); emask[5439 - 10 * p -: 10] = ev; m = m + 1; end
            end
        end
    endtask
    always @(negedge clk) begin
        ch_v <= p_v;
        if (p_v) begin
            if (wi % 10 == 0) draw(nerr_of[cw_i]);
            ch_d <= p_d ^ emask[5439 - 544 * (wi % 10) -: 544];
            if (wi % 10 == 9) cw_i = cw_i + 1;
            wi = wi + 1;
        end else ch_d <= 544'd0;
    end
    // ---- decoder output check (frames identified by their sequence number = frame index mod 256)
    integer of = -1, ob_ = 0, ok_fr = 0, unc_ok = 0, bad = 0, miscorr = 0, nerr_bad = 0, frames_out = 0, base = -1;
    reg cur_unc; reg [4:0] cur_ne; integer cur_f, cur_bad;
    always @(posedge clk) if (q_v) begin
        if (q_first) begin
            if (of >= 0) begin : close
                if (nerr_of[cur_f] <= 15) begin if (cur_bad || cur_unc) bad = bad + 1; else ok_fr = ok_fr + 1; if (cur_ne != nerr_of[cur_f] && !cur_unc) nerr_bad = nerr_bad + 1; end
                else if (cur_unc) unc_ok = unc_ok + 1; else if (cur_bad) miscorr = miscorr + 1; else ok_fr = ok_fr + 1;
            end
            // frame index from the sequence (frames go out in order; the first decoded frame fixes the 256-window); a
            // flagged (q_unc) frame's header is uncorrected, so its sequence is not checked (S81-KP4 10-17)
            if (base < 0) base = q_seq;
            cur_f = (of < 0) ? q_seq : cur_f + 1;
            if (of >= 0 && !q_unc && (cur_f % 256) != q_seq) begin bad = bad + 1; $display("ERR sequence %0d expected %0d", q_seq, cur_f % 256); end
            of = of + 1; ob_ = 0; cur_unc = q_unc; cur_ne = q_nerr; cur_bad = 0; frames_out = frames_out + 1;
        end
        if (q_d !== sent[10 * cur_f + ob_]) cur_bad = 1;
        ob_ = ob_ + 1;
    end
    integer cyc = 0;
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc > (NF + 8) * 10 + 200) begin : fin
            integer pass, expect_unc;
            expect_unc = 0;
            pass = (par_bad == 0) && (par_chk == NV) && (bad == 0) && (miscorr == 0) && (nerr_bad == 0) && (frames_out >= NF - 4) && (unc_ok > 0) && !efault;
            pass = pass && (eq_rtl_bad == 0) && (eq_hw_bad == 0) && (eq_qv >= (NF - 4) * 10);
            $display("TB_S81_KP4_EQ cycles=%0d ref_beats=%0d rtl_mismatch=%0d hw_mismatch=%0d SEAMMUT=%0d", eq_cyc, eq_qv, eq_rtl_bad, eq_hw_bad, SEAMMUT);
            $display("TB_S81_KP4 frames_out=%0d exact=%0d beyond_t_flagged=%0d bad=%0d miscorrected=%0d nerr_bad=%0d parity_checked=%0d parity_bad=%0d lock=%0d relocks=%0d n_corr=%0d n_unc=%0d EMUT=%0d DMUT=%0d %s",
                frames_out, ok_fr, unc_ok, bad, miscorr, nerr_bad, par_chk, par_bad, lock, n_relock, n_corr, n_unc, EMUT, DMUT, pass ? "PASS" : "FAIL");
            $display("TB_S81_KP4_EQ %s", pass ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule

// four tiles with every tile pin registered (the pin_regs of the kits): cluster in (1) / out (1), each seam 2; plus the
// hardened parent's own pin registers (s81lk_kp4_dec pin_regs): p_* in (1), every output out (1)
module kp4_dec_hw #(parameter integer MUT = 0, parameter integer SEAMMUT = 0, parameter integer PREGMUT = 0) (
    input wire clk, input wire rst_n, input wire p_v, input wire [543:0] p_d,
    output wire q_v, output wire [511:0] q_d, output wire q_first, output wire q_unc, output wire [4:0] q_nerr, output wire [7:0] q_seq,
    output wire lock, output wire [31:0] n_corr, n_unc, n_relock);
    reg pv0, pv1; reg [543:0] pd0, pd1;
    always @(posedge clk) begin pv0 <= p_v; pd0 <= p_d; pv1 <= PREGMUT ? p_v : pv0; pd1 <= PREGMUT ? p_d : pd0; end
    wire [543:0] x_q, d_q, cw; wire [3:0] k_v; wire [309:0] k_lo; wire [4:0] k_L, o_ne; wire k_any, o_unc, fs, lk; wire [7:0] apply;
    wire [31:0] nrl, nco, nun;
    ot_s81_kp4_dsyn #(.MUT(MUT)) u_syn (.clk(clk), .rst_n(rst_n), .p_v(pv1), .p_d(pd1), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lk), .n_relock(nrl));
    reg [543:0] xq1, xq2, dq1, dq2; reg [319:0] k1, k2;
    always @(posedge clk) begin xq1 <= x_q; xq2 <= xq1; k1 <= {k_v, k_lo, k_L, k_any}; k2 <= k1; end
    wire [543:0] xq_s = SEAMMUT ? xq1 : xq2;
    ot_s81_kp4_ddly u_dly (.clk(clk), .rst_n(rst_n), .w_d(xq_s), .r_d(d_q));
    ot_s81_kp4_dchn #(.MUT(MUT)) u_chn (.clk(clk), .rst_n(rst_n), .k_v(k2[319:316]), .k_lo(k2[315:6]), .k_L(k2[5:1]), .k_any(k2[0]),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(nco), .n_unc(nun));
    reg [558:0] c1, c2;
    always @(posedge clk) begin dq1 <= d_q; dq2 <= dq1; c1 <= {cw, apply, o_unc, o_ne, fs}; c2 <= c1; end
    wire v_, f_, u_; wire [511:0] d_; wire [4:0] ne_; wire [7:0] sq_;
    ot_s81_kp4_dout u_out (.clk(clk), .rst_n(rst_n), .d_q(dq2), .cw(c2[558:15]), .apply(c2[14:7]), .o_unc(c2[6]), .o_ne(c2[5:1]), .fs(c2[0]),
        .q_v(v_), .q_d(d_), .q_first(f_), .q_unc(u_), .q_nerr(ne_), .q_seq(sq_));
    reg [529:0] o1; reg l1; reg [95:0] n1;
    always @(posedge clk) begin o1 <= {v_, f_, u_, ne_, sq_, d_}; l1 <= lk; n1 <= {nco, nun, nrl}; end
    reg [529:0] o2; reg l2; reg [95:0] n2;
    always @(posedge clk) begin o2 <= o1; l2 <= l1; n2 <= n1; end
    assign {q_v, q_first, q_unc, q_nerr, q_seq, q_d} = o2;
    assign lock = l2; assign {n_corr, n_unc, n_relock} = n2;
endmodule
