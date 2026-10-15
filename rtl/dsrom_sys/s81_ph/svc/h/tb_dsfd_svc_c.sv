`timescale 1ns/1ps
// CLAUDE s81die-1011/ctrl svch: SLAB-PIN exact gate of the HIERARCHICAL dsfd_svc_c (4 x dsfd_svc_quad + dsfd_svc_idx
// + relay stations + the closed job / IO hub / PC tiles; die DIE, stack ST), adapted from tb_s81_svcq_slab: the job
// descriptor j arms the slab (arg = q frames of the job, END sources {0}); q enters at the die pin; results are read at
// the ad (a0) / od pins (valid-only); the 32 PC faces run the same ctrl + HBM model.  Additional checks: one job done
// on jd, no jd / hub / quadrant / index fault.
// (Original description of the gate, unchanged:) the window rows travel OWN_ROW frames -> the window writer ->
// HBM -> the 32-PC window load -> the merger, the selected rows the owned-row fetch through the arbiter.  On the
// golden vectors of tools/v41_ckv_sel_attn_vectors.py (tools/hdc_golden_v41.py chunk8: window rows qdq_fp8, selected
// rows qdq_fp4_e4m3 stored in the HBM image of their owner die/stack, q / p, expected scores sc.hex and p.v pv.hex).
// The bench is the VM + peers + HBM: it sends the job's q frames (WIN_LOAD, SEL_IDS, ATTN_Q x2, ROWS for every pair the
// slab needs from elsewhere, in a seeded random order, and PV after the last expected score), valid-only with random
// gaps; serves the slab's P fetch ports from the image (random latency); streams the window rows; and scores
// every result frame:
//   a0 SCORE   exactly the rows this slab holds, each once, every word bit-exact and its 16 fault flags as expected;
//   a0 PV      the 8 beats of the owned 128 dims, every word bit-exact, flags as expected; END on the last only;
//   od ROWX    every row this slab owns, once, eight words equal to the image row;
//   no frame after END, no fault.
// Prints  SVCQATTN ...  (PASS = all checks zero errors).
module tb_dsfd_svc_c (input wire clk);
    parameter integer DIE = 0;
    parameter integer ST = 0;
    parameter bit SRAM_MACRO = 0;
    parameter bit NATIVE_FP32_PV = 0;
    parameter integer P = 8;
    parameter integer NHBM = 32768;
    parameter integer MAXCYC = 900000;
    parameter integer DR = 64;
    localparam integer WBASE = 32 * 4096, WUSER = 3, WFIRST = 1000;
    localparam integer H = 16, D = 512, TD = 32, NL = 4, KW = 10, ROWW = 16 * 265, HAW = 30, S = 16, TAGW = 8;
    reg [31:0] cfg [0:31];
    reg [31:0] selm [0:511];
    reg [4223:0] winm [0:127];
    reg [63:0] hkey [0:NHBM-1];
    reg [255:0] hdat [0:NHBM-1];
    reg [D*16-1:0] qm [0:H-1];
    reg [TD*16-1:0] pm [0:639];
    reg [511:0] em [0:639];
    reg [H*33-1:0] scm [0:639];
    reg [H*33-1:0] pvm [0:D-1];
    reg [255:0] hbm [longint];
    reg [1023:0] dir;
    integer seed = 1, lat = 60, gap = 10;
    integer static_inputs = 0, pv_cycle = -1, expected_end = -1, schedule_errors = 0;
    // Optional component trace: capture actual pin results, never the expected
    // arrays. A consumer can use these to drive the real SU and compare the
    // service/SU boundary without substituting golden attention results.
    string trace_dir, p_file, e_file;
    integer trace_sc = 0, trace_pv = 0, trace_q = 0, trace_pc = 0;
    integer wcount, nsel, npub, nh, T;
    longint hk;
    integer i, j, k, h;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("lat=%d", lat)) ;
        if ($value$plusargs("gap=%d", gap)) ;
        if ($value$plusargs("static_inputs=%d", static_inputs)) ;
        if ($value$plusargs("pv_cycle=%d", pv_cycle)) ;
        if ($value$plusargs("expected_end=%d", expected_end)) ;
        if (static_inputs != 0 && (pv_cycle < 41 || expected_end < pv_cycle))
            $fatal(1, "static_inputs requires assigned pv_cycle and expected_end");
        if ($value$plusargs("trace=%s", trace_dir)) begin
            trace_sc = $fopen({trace_dir, "/scores.tsv"}, "w");
            trace_pv = $fopen({trace_dir, "/pv.tsv"}, "w");
            trace_q = $fopen({trace_dir, "/q.tsv"}, "w");
            trace_pc = $fopen({trace_dir, "/pc.tsv"}, "w");
            if (!trace_sc || !trace_pv || !trace_q || !trace_pc)
                $fatal(1, "cannot open native service pin traces");
        end
        $readmemh({dir, "/cfg.hex"}, cfg);
        $readmemh({dir, "/sel.hex"}, selm);
        $readmemh({dir, "/win.hex"}, winm);
        $readmemh({dir, "/hkey.hex"}, hkey);
        $readmemh({dir, "/hdat.hex"}, hdat);
        $readmemh({dir, "/q.hex"}, qm);
        $readmemh({dir, "/p.hex"}, pm);
        // The native SU bridge may supply actual SE/BF16 probabilities. The
        // expected PV remains checker-only; no DUT result comes from it.
        if ($value$plusargs("p_file=%s", p_file)) $readmemh(p_file, pm);
        if (NATIVE_FP32_PV) begin
            if (!$value$plusargs("e_file=%s", e_file)) $fatal(1, "native FP32 probabilities require actual SU +e_file");
            $readmemh(e_file, em);
        end
        $readmemh({dir, "/sc.hex"}, scm);
        $readmemh({dir, "/pv.hex"}, pvm);
        wcount = cfg[0]; nsel = cfg[1]; npub = cfg[2]; nh = cfg[3]; T = cfg[4];
        for (i = 0; i < nh; i = i + 1) hbm[hkey[i]] = hdat[i];
        void'($urandom(seed));
    end
    function automatic [1:0] odie(input integer g); odie = g[5:4]; endfunction
    function automatic [1:0] ostk(input integer g); ostk = g[7:6]; endfunction
    function automatic integer olocal(input integer g); olocal = ((g >> 8) << 4) | (g & 15); endfunction
    function automatic [2303:0] imgrow(input integer g);
        integer kk; longint key;
        imgrow = 0;
        for (kk = 0; kk < 9; kk = kk + 1) begin
            key = (longint'(odie(g)) << 32) | (longint'(ostk(g)) << 30) | longint'(cfg[9 + ostk(g)] + 9 * olocal(g) + kk);
            imgrow[256*kk +: 256] = hbm.exists(key) ? hbm[key] : 256'hx;
        end
    endfunction
    function automatic bit held_sel(input integer r); held_sel = ostk(selm[r]) == 2'(ST); endfunction
    function automatic bit own_sel(input integer r); own_sel = odie(selm[r]) == 2'(DIE) && ostk(selm[r]) == 2'(ST); endfunction
    function automatic bit held_row(input integer t);
        held_row = (t < wcount) ? (t % 4 == ST) : held_sel(t - wcount);
    endfunction

    reg rst_n = 0;
    integer cyc = 0;
    // ---------------- DUT ----------------
    reg q_v = 0; reg [511:0] q_d = 0;
    wire a0_v, od_v; wire [511:0] a0_d, od_d; reg a0_r = 1, od_r = 1;
    wire [32*341-1:0] rq; reg [31:0] rk = 0, rv = 0, wd = 0; reg [32*17-1:0] r_tag = 0; reg [32*4-1:0] r_beat = 0;
    reg [32*256-1:0] r_data = 0;
    reg [32:0] jcmd = 0; wire [1:0] jd;
    reg [291:0] hw = 0; wire [8:0] hc;
    wire [513:0] od, xd; wire [1025:0] ad; wire of, xf, af, hub_fault;
    dsfd_svc_c #(.DIE_ID(DIE), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .NATIVE_FP32_PV(NATIVE_FP32_PV)) dut (
        .ck(clk), .rst(rst_n), .j(jcmd), .jd(jd), .q({1'b0, 1'b1, q_d, q_v}),
        .od(od), .of(of), .xd(xd), .xf(xf), .ad(ad), .af(af), .fault(hub_fault),
        .rq(rq), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hw(hw), .hc(hc), .hs(2'b01));
    // ---------------- host writes (dsfd_host_sd hw / hc contract: 8 credits, cr per word, ack per completed sector) ----
    // NHW sector writes (KV class, then RoPE class) to a region no job touches, one KV marker (no write, no ack),
    // interleaved with the job; at the end every written sector must hold its data in the HBM image and the acks must
    // equal the sector writes.
    localparam integer NHW = 96;
    integer h_cred = 8, h_sent = 0, h_ack = 0, h_err = 0, h_mark = 0;
    reg [255:0] h_dat [0:NHW-1]; reg [31:0] h_adr [0:NHW-1];
    initial for (i = 0; i < NHW; i = i + 1) begin
        h_adr[i] = (i < NHW / 2) ? 32'h0300_0000 + 32'(i * 5) : 32'h8300_0000 + 32'(i * 7);
        for (k = 0; k < 8; k = k + 1) h_dat[i][32*k +: 32] = 32'h1234_5678 * (i + 1) + k;
    end
    always @(posedge clk) begin
        hw <= 0;
        h_cred = h_cred + hc[0]; h_ack = h_ack + hc[8:1];
        if (static_inputs == 0 && rst_n && cyc > 30 && h_cred > 0 && ($urandom % 4) == 0) begin
            if (h_sent < NHW) begin
                hw <= {(h_adr[h_sent][31] ? 2'd1 : 2'd0), 1'b1, h_adr[h_sent], h_dat[h_sent], 1'b1}; h_sent = h_sent + 1; h_cred = h_cred - 1;
            end else if (h_mark == 0) begin
                hw <= {2'd0, 1'b1, 32'hffffffff, 256'h0b007_e2d, 1'b1}; h_mark = 1; h_cred = h_cred - 1;
            end
        end
    end
    task automatic host_check();
        integer ii; longint kk;
        for (ii = 0; static_inputs == 0 && ii < NHW; ii = ii + 1) begin
            kk = (longint'(DIE) << 32) | (longint'(ST) << 30) | longint'(h_adr[ii][29:0]);
            if (!hbm.exists(kk) || hbm[kk] !== h_dat[ii]) h_err = h_err + 1;
        end
        if ((static_inputs == 0 && h_ack != NHW) || h_cred != 8) h_err = h_err + 1;
    endtask
    assign a0_v = ad[0]; assign a0_d = ad[512:1];
    assign od_v = od[1]; assign od_d = od[513:2];
    wire [4:0] cflt = {dut.u_x.fo[0], dut.g_q[3].u_q.fo[0], dut.g_q[2].u_q.fo[0], dut.g_q[1].u_q.fo[0], dut.g_q[0].u_q.fo[0]};
    wire fault = hub_fault | jd[1] | (|cflt);
    wire [63:0] fault_code = {57'd0, jd[1], hub_fault, cflt};
    integer n_done = 0, done_early = 0;
    always @(posedge clk) if (jd[0]) begin
        n_done <= n_done + 1;
        if(n_end==0)done_early <= done_early + 1;
    end
    // ---------------- q frame list (built once) ----------------
    localparam integer QMAX = 8192;
    reg [511:0] qw [0:QMAX-1];
    integer nq = 0, nq_pre = 0, nq_own = 0;        // frames before PV end at nq_pre
    integer order [0:1023];
    integer npair_in = 0;
    integer nframes = 0, last_hdr = 0;
    function automatic [511:0] hdr(input [3:0] typ, input [11:0] len, input [448:0] spec);
        hdr = {typ, 1'b0, 4'b0001, 8'h5a, 3'd0, len, 21'd777, 10'd3, spec};
        nframes = nframes + 1; last_hdr = nq;
    endfunction
    task automatic build_frames();
        reg [448:0] sp; integer r, t, n, b, pr, cnt, base, sz;
        reg [2303:0] row;
        // CFG: window ring region (user WUSER's ring at WBASE + WUSER * 2176)
        sp = 0; sp[29:0] = WBASE; sp[59:30] = 8 * 2176;
        qw[nq] = hdr(4'd12, 0, sp); nq = nq + 1;
        // OWN_ROW: the window rows, oldest first (as the tokens wrote them), 16 blocks each
        for (r = 0; r < wcount; r = r + 1) begin
            qw[nq] = hdr(4'd3, 12'd16, 449'd0); qw[nq][479:459] = WFIRST + r; qw[nq][458:449] = WUSER; nq = nq + 1;
            for (b = 0; b < 16; b = b + 1) begin
                qw[nq] = 0; qw[nq][255:0] = winm[r][256*b +: 256]; qw[nq][263:256] = winm[r][4096 + 8*b +: 8]; nq = nq + 1;
            end
        end
        nq_own = nq;
        // WIN_LOAD
        sp = 0; sp[29:0] = cfg[9 + ST]; sp[59:30] = cfg[13 + ST]; sp[80:60] = npub; sp[88:81] = wcount; sp[98:89] = nsel;
        sp[119:99] = WFIRST;
        qw[nq] = hdr(4'd2, 0, sp); qw[nq][458:449] = WUSER; nq = nq + 1;
        // SEL_IDS: one frame, 16 ids a word
        n = (nsel + 15) / 16;
        sp = 0; sp[9:0] = 0; sp[19:10] = nsel;
        if (nsel > 0) begin
            qw[nq] = hdr(4'd7, 12'(n), sp); nq = nq + 1;
            for (b = 0; b < n; b = b + 1) begin
                qw[nq] = 0;
                for (r = 0; r < 16; r = r + 1) if (16 * b + r < nsel) qw[nq][32*r +: 32] = selm[16 * b + r];
                nq = nq + 1;
            end
        end
        // ATTN_Q
        for (b = 0; b < 2; b = b + 1) begin
            sp = 0; sp[448] = b[0];
            qw[nq] = hdr(4'd1, 12'd128, sp); nq = nq + 1;
            for (r = 0; r < 128; r = r + 1) begin qw[nq] = qm[8 * b + r / 16][512 * (r % 16) +: 512]; nq = nq + 1; end
        end
        // ROWS: every (rank, pair) this slab needs from elsewhere, shuffled, frames of <= 200 words
        cnt = 0;
        for (r = 0; r < nsel; r = r + 1) if (!own_sel(r))
            for (pr = 0; pr < 8; pr = pr + 1) if (held_sel(r) || pr / 2 == ST) begin order[cnt] = r * 8 + pr; cnt = cnt + 1; end
        if (static_inputs == 0)
            for (r = cnt - 1; r > 0; r = r - 1) begin t = $urandom % (r + 1); b = order[r]; order[r] = order[t]; order[t] = b; end
        npair_in = cnt;
        base = 0;
        while (base < cnt) begin
            sz = (cnt - base > 200) ? 200 : cnt - base;
            qw[nq] = hdr(4'd6, 12'(sz), 449'd0); nq = nq + 1;
            for (b = 0; b < sz; b = b + 1) begin
                r = order[base + b] / 8; pr = order[base + b] % 8; row = imgrow(selm[r]);
                qw[nq] = 0; qw[nq][9:0] = r; qw[nq][30:10] = selm[r]; qw[nq][33:31] = pr;
                qw[nq][289:34] = row[256*pr +: 256]; qw[nq][321:290] = row[2048 + 32*pr +: 32];
                nq = nq + 1;
            end
            base = base + sz;
        end
        nq_pre = nq;
        // PV: ceil(T / 2) words in frames of <= 250
        n = NATIVE_FP32_PV ? T : (T + 1) / 2; base = 0;
        while (base < n) begin
            sz = (n - base > 250) ? 250 : n - base;
            // Native FP32-PV conversion resets its row pairing at each
            // frame; all intermediate chunks are even (250), and only
            // the final chunk may contain an odd row.
            qw[nq] = hdr(NATIVE_FP32_PV ? 4'd14 : 4'd5, 12'(sz), 449'd0); nq = nq + 1;
            for (b = 0; b < sz; b = b + 1) begin
                qw[nq] = NATIVE_FP32_PV ? em[base + b] : pm[base + b]; nq = nq + 1;
            end
            base = base + sz;
        end
        qw[last_hdr][507] = 1'b1;      // protocol v1.1: END on the job's last q frame
    endtask

    // ---------------- expected counts ----------------
    integer exp_scores = 0, exp_own = 0;
    reg [639:0] got_row;
    reg [511:0] got_own;
    integer sc_err = 0, sc_chk = 0, pv_err = 0, pv_chk = 0, x_err = 0, x_rows = 0, n_end = 0, after_end = 0, fmt_err = 0;
    integer pv_beats = 0, sc_rows = 0;
    integer qi = 0, wi = 0;
    integer last_score_cyc = -1, end_cyc = -1, first_q_cyc = -1;
    // ctrl + HBM model state
    localparam integer PQ = 64;
    integer pq_t [0:31][0:PQ-1];
    reg [340:0] pq_w [0:31][0:PQ-1];
    integer pq_h [0:31], pq_n [0:31], pq_b [0:31];
    integer cred_err = 0, pc_err = 0;
    reg [340:0] w341; reg [255:0] old;
    longint key;
    initial for (i = 0; i < 32; i = i + 1) begin pq_h[i] = 0; pq_n[i] = 0; pq_b[i] = 0; end
    // a0 / od frame parsers
    integer a_left = 0, a_sub = 0, a_row = 0, a_k = 0, a_endf = 0; reg [3:0] a_mask; reg [255:0] a_fl; integer a_pvc = 0;
    integer o_left = 0, o_rank = 0, o_gid = 0, o_k = 0; reg [2303:0] o_row;
    integer pv_sent = 0;
    reg built = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1;
        jcmd <= 0;
        if (cyc == 8) jcmd <= {1'b1, 9'd0, 8'(nframes), 2'b00, 5'b00001, 8'h5a};
        if (cyc == 1) begin
            build_frames(); built = 1;
            if (nframes > 255) $display("TOO MANY Q FRAMES %0d", nframes);
            got_row = 0; got_own = 0;
            for (i = 0; i < T; i = i + 1) if (held_row(i)) exp_scores = exp_scores + 1;
            for (i = 0; i < nsel; i = i + 1) if (own_sel(i)) exp_own = exp_own + 1;
        end
        // q stream (valid-only, gaps); PV frames only after the last expected score
        q_v <= 0;
        if (q_v && trace_q) $fdisplay(trace_q, "%0d\t%0128x", cyc, q_d);
        // In static mode PV launches at its reserved cycle; score completion is
        // checked and cannot gate or postpone input issue. External PC service
        // has a declared fixed latency. The legacy random mode is diagnostic.
        if (static_inputs != 0 && cyc == pv_cycle && (qi != nq_pre || sc_rows != exp_scores))
            schedule_errors = schedule_errors + 1;
        if (rst_n && built && cyc > 40 && qi < nq &&
            (static_inputs != 0 || ($urandom % 100) >= gap) &&
            (qi < nq_pre || (static_inputs != 0 ? cyc >= pv_cycle : sc_rows >= exp_scores))) begin
            q_v <= 1; q_d <= qw[qi]; qi = qi + 1;
            if (first_q_cyc < 0) first_q_cyc = cyc;
        end
        // ctrl + HBM model: per PC a request queue (credit returned when the PHY takes it, one a cycle), each sector
        // returned lat + rand cycles later in order, valid-only; writes land in the image and pulse wd
        rk <= 0; rv <= 0; wd <= 0;
        for (i = 0; i < 32; i = i + 1) begin
            if (rq[i*341]) begin
                if (trace_pc) $fdisplay(trace_pc, "%0d\t%0d\t%086x", cyc, i, rq[i*341 +: 341]);
                pq_t[i][(pq_h[i] + pq_n[i]) % PQ] = cyc + lat + (static_inputs != 0 ? 0 : ($urandom % 16));
                pq_w[i][(pq_h[i] + pq_n[i]) % PQ] = rq[i*341 +: 341];
                pq_n[i] = pq_n[i] + 1;
                if (pq_n[i] > 8) begin cred_err = cred_err + 1; end
            end
            if (pq_n[i] > 0 && pq_t[i][pq_h[i]] <= cyc) begin
                w341 = pq_w[i][pq_h[i]];
                if (w341[1]) begin
                    key = (longint'(DIE) << 32) | (longint'(ST) << 30) | longint'(w341[31:2]);
                    old = hbm.exists(key) ? hbm[key] : 256'd0;
                    for (j = 0; j < 32; j = j + 1) if (w341[53 + j]) old[8*j +: 8] = w341[85 + 8*j +: 8];
                    hbm[key] = old; wd[i] <= 1;
                    pq_h[i] = (pq_h[i] + 1) % PQ; pq_n[i] = pq_n[i] - 1; rk[i] <= 1;
                end else begin
                    key = (longint'(DIE) << 32) | (longint'(ST) << 30) | longint'(w341[31:2] + pq_b[i]);
                    if (((w341[31:2] + pq_b[i]) >> 2 ^ (w341[31:2] + pq_b[i]) >> 7 ^ (w341[31:2] + pq_b[i]) >> 12) % 32 != i) pc_err = pc_err + 1;
                    rv[i] <= 1; r_tag[i*17 +: 17] <= w341[52:36]; r_beat[i*4 +: 4] <= pq_b[i];
                    r_data[i*256 +: 256] <= hbm.exists(key) ? hbm[key] : 256'd0;
                    if (pq_b[i] + 1 == w341[35:32]) begin pq_b[i] = 0; pq_h[i] = (pq_h[i] + 1) % PQ; pq_n[i] = pq_n[i] - 1; rk[i] <= 1; end
                    else pq_b[i] = pq_b[i] + 1;
                end
            end
        end
        // ---- a0 checker ----
        if (a0_v && a0_r) begin
            if (n_end > 0) after_end = after_end + 1;
            if (a_left == 0) begin
                if (a0_d[511:508] != 4'd8 || a0_d[502:495] != 8'h5a || a0_d[479:459] != 21'd777 || a0_d[458:449] != 10'd3)
                    fmt_err = fmt_err + 1;
                a_sub = a0_d[448:447]; a_row = a0_d[446:431]; a_mask = a0_d[430:427]; a_fl = a0_d[255:0];
                a_left = a0_d[491:480]; a_k = 0; a_endf = a0_d[507];
                if (a_sub == 1 && a_left != 16) fmt_err = fmt_err + 1;
                if (a_endf) begin
                    if (pv_beats != 7) fmt_err = fmt_err + 1;
                    // END describes the whole frame. Its payload is still
                    // legal traffic, and job retirement must wait for it.
                    if(a_left==0) begin
                        n_end=n_end+1;end_cyc=cyc;
                        if(static_inputs!=0&&cyc!=expected_end)schedule_errors=schedule_errors+1;
                    end
                end
                if (a_sub == 0) for (j = 0; j < 4; j = j + 1) begin
                    if (a_mask[j]) begin
                        if (!held_row(a_row + j) || got_row[a_row + j]) begin sc_err = sc_err + 1; $display("SC ROW %0d not held/dup", a_row + j); end
                        got_row[a_row + j] = 1;
                    end
                end
            end else begin
                if (a_sub == 0) begin
                    while (!a_mask[a_k]) a_k = a_k + 1;
                    for (h = 0; h < H; h = h + 1) begin
                        if (trace_sc) $fdisplay(trace_sc, "%0d\t%0d\t%0d\t%08x\t%0d", cyc,
                                               a_row + a_k, h, a0_d[32*h +: 32], a_fl[16*a_k + h]);
                        sc_chk = sc_chk + 1;
                        if (a0_d[32*h +: 32] !== scm[a_row + a_k][h*33 +: 32] && !scm[a_row + a_k][h*33 + 32] ||
                            a_fl[16*a_k + h] !== scm[a_row + a_k][h*33 + 32]) begin
                            sc_err = sc_err + 1;
                            if (sc_err < 8) $display("SC MISMATCH row %0d head %0d got %08x f%0d exp %08x f%0d", a_row + a_k, h,
                                                     a0_d[32*h +: 32], a_fl[16*a_k + h], scm[a_row + a_k][h*33 +: 32], scm[a_row + a_k][h*33 + 32]);
                        end
                    end
                    a_k = a_k + 1; sc_rows = sc_rows + 1; last_score_cyc = cyc;
                end else begin
                    k = 128 * ST + 8 * a_k + a_row;
                    for (h = 0; h < H; h = h + 1) begin
                        if (trace_pv) $fdisplay(trace_pv, "%0d\t%0d\t%0d\t%08x\t%0d", cyc,
                                               k, h, a0_d[32*h +: 32], a_fl[16*a_k + h]);
                        pv_chk = pv_chk + 1;
                        if (a0_d[32*h +: 32] !== pvm[k][h*33 +: 32] && !pvm[k][h*33 + 32] || a_fl[16*a_k + h] !== pvm[k][h*33 + 32]) begin
                            pv_err = pv_err + 1;
                            if (pv_err < 8) $display("PV MISMATCH dim %0d head %0d got %08x f%0d exp %08x", k, h, a0_d[32*h +: 32],
                                                     a_fl[16*a_k + h], pvm[k][h*33 +: 32]);
                        end
                    end
                    a_k = a_k + 1;
                    if (a_k == 16) pv_beats = pv_beats + 1;
                end
                a_left = a_left - 1;
                if(a_left==0&&a_endf) begin
                    n_end=n_end+1;end_cyc=cyc;
                    if(static_inputs!=0&&cyc!=expected_end)schedule_errors=schedule_errors+1;
                end
            end
        end
        // ---- od checker ----
        if (od_v && od_r) begin
            if (n_end > 0) after_end = after_end + 1;
            if (o_left == 0) begin
                if (od_d[511:508] != 4'd11 || od_d[491:480] != 12'd8) fmt_err = fmt_err + 1;
                o_rank = od_d[9:0]; o_gid = od_d[30:10]; o_left = 8; o_k = 0;
                if (o_rank >= nsel || !own_sel(o_rank) || selm[o_rank] != o_gid || got_own[o_rank]) begin
                    x_err = x_err + 1; $display("ROWX bad rank %0d gid %0d", o_rank, o_gid);
                end else got_own[o_rank] = 1;
            end else begin
                o_row = imgrow(o_gid);
                if (od_d[9:0] != o_rank || od_d[30:10] != o_gid || od_d[33:31] != o_k ||
                    od_d[289:34] !== o_row[256*o_k +: 256] || od_d[321:290] !== o_row[2048 + 32*o_k +: 32] || od_d[511:322] != 0) begin
                    x_err = x_err + 1; if (x_err < 8) $display("ROWX word mismatch rank %0d pair %0d", o_rank, o_k);
                end
                o_k = o_k + 1; o_left = o_left - 1;
                if (o_left == 0) x_rows = x_rows + 1;
            end
        end
        if ((n_end > 0 && n_done > 0 && cyc > end_cyc + 200) || (n_end > 0 && cyc > end_cyc + 5000) || cyc >= MAXCYC || (fault && cyc > 20 && n_end == 0 && cyc > MAXCYC / 2)) begin
            for (i = 0; i < T; i = i + 1) if (held_row(i) && !got_row[i]) sc_err = sc_err + 1;
            host_check();
            $display("SVCC_SCHEDULE static_inputs=%0d pv_cycle=%0d expected_end=%0d errors=%0d",
                     static_inputs, pv_cycle, expected_end, schedule_errors);
            $display("SVCC_DONE_BOUNDARY early=%0d",done_early);
            $display("SVCC_HOST sent=%0d acks=%0d credits=%0d errors=%0d", h_sent, h_ack, h_cred, h_err);
            $display("SVCC done=%0d die=%0d st=%0d T=%0d window=%0d nsel=%0d held_rows=%0d score_rows=%0d sc_checked=%0d sc_errors=%0d pv_beats=%0d pv_checked=%0d pv_errors=%0d own_rows=%0d rowx=%0d rowx_errors=%0d pairs_in=%0d ends=%0d after_end=%0d fmt_errors=%0d fault=%0d fault_code=%016x cred_err=%0d pc_err=%0d first_q=%0d last_score=%0d end=%0d cycles=%0d timeout=%0d verdict=%s",
                     n_done, DIE, ST, T, wcount, nsel, exp_scores, sc_rows, sc_chk, sc_err, pv_beats, pv_chk, pv_err, exp_own, x_rows, x_err,
                     npair_in, n_end, after_end, fmt_err, fault, fault_code, cred_err, pc_err, first_q_cyc, last_score_cyc, end_cyc, cyc, cyc >= MAXCYC,
                     (schedule_errors == 0 && done_early == 0 && n_done == 1 && h_err == 0 && sc_err == 0 && pv_err == 0 && x_err == 0 && fmt_err == 0 && after_end == 0 && n_end == 1 && pv_beats == 8 &&
                      sc_rows == exp_scores && x_rows == exp_own && !fault && cred_err == 0 && pc_err == 0 && cyc < MAXCYC) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
