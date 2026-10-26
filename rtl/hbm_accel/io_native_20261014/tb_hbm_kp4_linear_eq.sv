`timescale 1ns/1ps
// tb_s81_kp4 (s81-die-rtl-bind 2026-10-14, F10): KP4 RS(544,514) transmit + receive FEC of the S81 die link,
// exact against the reference tools/s81_link/rs544.py.
//   * encoder: the first NV frames carry the vector file's beats (+vec=<file>, rs544.py vectors); every PMA codeword's
//     parity must equal the reference parity bit for bit;
//   * channel: per frame f, n(f) random symbol errors (random nonzero 10-b values at distinct positions): frames cycle
//     n = 0..15 (correctable), every 8th frame n = 16..22 (beyond t);
//   * decoder: after lock, every frame <= t comes out EXACT (all 10 beats, sequence, q_nerr = n, q_unc = 0); every
//     frame > t is flagged q_unc = 1 or comes out exact (a miscorrection = FAIL).
// PASS line: TB_S81_KP4 ... PASS.  Mutants: enc MUT 1 (parity symbol inverted), dec MUT 2 (Forney value) must FAIL.
module tb_hbm_kp4_linear_eq;
    parameter integer NF = 280, NV = 16, EMUT = 0, DMUT = 0;
    reg clk = 0, rst_n = 0;
    always #0.41667 clk = ~clk;
    reg tx_v = 0; reg [511:0] tx_d = 0;
    wire p_v; wire [543:0] p_d; wire efault;
    ot_s81_kp4_enc #(.MUT(0)) u_e (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(p_v), .p_d(p_d), .fault(efault));
    reg [543:0] ch_d; reg ch_v;
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_relock;
    ot_s81_kp4_dec #(.MUT(0)) u_d (.clk(clk), .rst_n(rst_n), .p_v(ch_v), .p_d(ch_d), .q_v(q_v), .q_d(q_d), .q_first(q_first),
        .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock), .n_corr(n_corr), .n_unc(n_unc), .n_relock(n_relock));
    wire lpv,lef;wire[543:0]lpd;
    ot_hbm_kp4_enc_linear #(.MUT(EMUT))le(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(lpv),.p_d(lpd),.fault(lef));
    wire lqv,lqfirst,lqunc,llock;wire[511:0]lqd;wire[4:0]lqerr;wire[7:0]lseq;wire[31:0]lcorr,lunc,lrl;
    ot_hbm_kp4_dec_linear #(.MUT(DMUT))ld(.clk(clk),.rst_n(rst_n),.p_v(ch_v),.p_d(ch_d),.q_v(lqv),.q_d(lqd),.q_first(lqfirst),.q_unc(lqunc),.q_nerr(lqerr),.q_seq(lseq),.lock(llock),.n_corr(lcorr),.n_unc(lunc),.n_relock(lrl));
    integer enc_edges=0,dec_edges=0;
    always @(posedge clk)begin #0.001;if(rst_n)begin
      enc_edges=enc_edges+1;dec_edges=dec_edges+1;
      if({p_v,p_d,efault}!=={lpv,lpd,lef})$fatal(1,"HBM_KP4_LINEAR_EQ_FAIL encoder edge%0d MUT%0d",enc_edges,EMUT);
      if({q_v,q_d,q_first,q_unc,q_nerr,q_seq,lock,n_corr,n_unc,n_relock}!=={lqv,lqd,lqfirst,lqunc,lqerr,lseq,llock,lcorr,lunc,lrl})$fatal(1,"HBM_KP4_LINEAR_EQ_FAIL decoder edge%0d MUT%0d",dec_edges,DMUT);
    end end
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
            // An explicitly uncorrectable frame carries invalid metadata. Require
            // exact sequence for corrected/clean frames; compare ALL metadata
            // against unchanged legacy RTL every edge above, including unc.
            // Frame order fixes the expected index independently of bad metadata.
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
            $display("TB_S81_KP4 frames_out=%0d exact=%0d beyond_t_flagged=%0d bad=%0d miscorrected=%0d nerr_bad=%0d parity_checked=%0d parity_bad=%0d lock=%0d relocks=%0d n_corr=%0d n_unc=%0d EMUT=%0d DMUT=%0d %s",
                frames_out, ok_fr, unc_ok, bad, miscorr, nerr_bad, par_chk, par_bad, lock, n_relock, n_corr, n_unc, EMUT, DMUT, pass ? "PASS" : "FAIL");
            $display("HBM_KP4_LINEAR_EQ_%s enc_edges%0d dec_edges%0d no_added_edges EMUT%0d DMUT%0d",pass?"PASS":"FAIL",enc_edges,dec_edges,EMUT,DMUT);
            $finish;
        end
    end
endmodule
