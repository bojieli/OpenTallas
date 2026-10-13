`timescale 1ns/1ps
`default_nettype none
// tb_hgi_b2_swap_rec ([mtp-rtl] 2026-10-13): the native B2 MTP swap-out from REAL PROGRAM RECORDS.
//   DUT chain: program image (HGI-1 16-byte words in the HBM image, encoded HERE from the field layout of
//   tools/hbm_generic_iface.py D_UOP_FIELDS / D_MDESC_FIELDS) -> the REAL ot_hgi_seq (fetch, TOKEN x dyn_mul resolve,
//   in-order dispatch) -> ot_hgi_b2_swap_rec (the REAL ot_hgi_dma_record inside) -> ot_hgi_b2_swap_disp -> relays ->
//   four REAL ot_hgi_dma_back NS 1 / NB 8 engines.
//   Program = [mtp-rtl] ENCODING: 4 x DMA.STORE h (param GRP, the last GRP | GLAST; HBM O base (q << 35) | COLB + 64 q,
//   dyn_sel TOKEN, dyn_mul 131072), DMA.STORE PRE (GRP | GLAST), CTL.FENCE, CTL.END.  The doorbell token = the column slot.
//   Oracle = the LOGICAL native slot image only (as tb_hgi_b2_swap_grp): h row 80q + j on stack q at stack-local
//   COLB + slot x CSTR + 64 q + 256 j; PRE on stack 0 at COLB + slot x CSTR + 81920.
//   PASS = every expected HBM word exact, no stray word, completion status 0 with 5 DMA retires, no retire before its
//   engine's src, wr_quiet / the completion never before the last acknowledged sector, and first DMA dispatch ->
//   wr_quiet (the CTL.FENCE answer at the unit pin) <= LIMIT in every run; then two NEGATIVE programs (a duplicate
//   cluster in a group; a dropped GLAST) must each end in the sticky unit fault with no HBM word written.
//   ONE OWNER A RULE: the fence answer is S's (the adapter keeps no outstanding count), so the wr_quiet / completion
//   checks observe S's join directly (MUT 3 = S's join ignores its outstanding count -> EARLY FENCE here); the
//   duplicate-cluster fault is S's (the adapter has no such check), so the bench requires S's own fault to be the
//   origin of the unit fault in both negative programs (a dropped GLAST makes the PRE record a second record for
//   cluster 0 in the still-open group) -- MUT 6 = S's fault report dropped -> no unit fault.
//   MUT: 1 2 3 5 (S) / 6 (composition) / 7 9 (adapter) / 8 (bench: the doorbell token is slot ^ 1 = a wrong TOKEN
//   resolve) must FAIL; 4 (serialized group) must fail the throughput check.
module tb_hgi_b2_swap_rec;
    parameter integer MUT = 0;
    parameter integer DHOPS = 10;
    parameter integer LAT = 6;
    parameter integer JIT = 5;
    parameter integer HOPS = 3;
    parameter integer ALAT = 40;
    parameter integer VCR = 8;
    parameter integer LIMIT = 272;       // 1.10 x 248 (immutable price)
    parameter integer SEED = 1;
    localparam integer NB = 8, NL = 8, SBIT = 35;
    localparam longint COLB = 64'h510000000, CSTR = 64'd131072;
    localparam integer VMW = 98304;
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    wire [4*129-1:0] vr2q; reg [4*2065-1:0] vr2r = 0; wire [4*2312-1:0] wd; wire [31:0] wd_cr; reg [15:0] wa = 0;
    wire rec_v, rec_rdy, ret_done, ret_fault, wr_quiet, fault, s_done, s_fault_o; wire [3:0] e_src, e_acc;
    longint t_sf = 0, t_uf = 0;          // first cycle of S's fault / of the unit fault in a run
    // ---------------------------------------------------------------- the sequencer
    reg db_v = 0; reg [17:0] db_token = 0; wire db_rdy, sq_busy;
    wire f_req_v; wire [39:0] f_req_addr; reg f_rsp_v = 0; reg [255:0] f_rsp_data = 0;
    wire vr_v; wire [17:0] vr_addr; reg vr_p1 = 0, vr_rsp_v = 0;
    wire [15:0] u_v; wire [127:0] d_hdr; wire [255:0] d_sut; wire [1791:0] d_desc; wire [146:0] d_n;
    wire [20:0] d_pos1, d_pslot1; wire [15:0] d_L, d_L1;
    wire cpl_v; reg cpl_rdy = 0; wire [17:0] cpl_token; wire [19:0] cpl_pos; wire [31:0] cpl_job, cpl_cycles; wire [3:0] cpl_gen, cpl_status; wire cpl_tokx;
    localparam [31:0] PAGE = 32'd16;
    localparam [39:0] IMG = 40'd65536;
    ot_hgi_seq u_seq (.clk(clk), .rst_n(rst_n), .md_d({32'd1, PAGE, 32'd0, 32'd0, 32'd0}), .cfg_vocab(18'd4096), .cfg_ctx_max(21'd4096),
        .rank(8'd0), .hold(1'b0), .busy(sq_busy), .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(20'd0), .db_job(32'h1234),
        .db_gen(4'h5), .db_entry(2'd0), .db_ncol(4'd0), .db_kernel(4'd0), .db_loff(32'd0), .md_k(352'd0),
        .f_req_v(f_req_v), .f_req_rdy(1'b1), .f_req_addr(f_req_addr), .f_rsp_v(f_rsp_v), .f_rsp_data(f_rsp_data),
        .vr_v(vr_v), .vr_rdy(1'b1), .vr_addr(vr_addr), .vr_rsp_v(vr_rsp_v), .vr_rsp_data(32'd5),
        .u_v(u_v), .u_rdy({7'd0, rec_rdy, 8'd0}), .d_hdr(d_hdr), .d_sut(d_sut), .d_desc(d_desc), .d_n(d_n), .d_pos1(d_pos1),
        .d_pslot1(d_pslot1), .d_L(d_L), .d_L1(d_L1), .u_done({7'd0, ret_done, 8'd0}), .u_fault({7'd0, ret_fault, 8'd0}),
        .wr_quiet(wr_quiet), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy), .cpl_token(cpl_token), .cpl_pos(cpl_pos), .cpl_job(cpl_job),
        .cpl_gen(cpl_gen), .cpl_status(cpl_status), .cpl_cycles(cpl_cycles), .cpl_tokx(cpl_tokx));
    assign rec_v = u_v[8];
    ot_hgi_b2_swap_rgrp #(.DHOPS(DHOPS), .VCR(VCR), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(d_hdr), .rec_a(d_desc[255:0]), .rec_o(d_desc[4*256 +: 256]), .rec_n_a(d_n[20:0]), .rec_n_o(d_n[4*21 +: 21]),
        .ret_done(ret_done), .ret_fault(ret_fault), .wr_quiet(wr_quiet), .fault(fault), .s_done(s_done), .s_fault_o(s_fault_o), .e_src(e_src),
        .e_acc(e_acc), .vr2q(vr2q), .vr2r(vr2r), .wd(wd), .wd_cr(wd_cr), .wa(wa));
    // ---------------------------------------------------------------- HBM image fetch / the END token read
    reg [127:0] img [0:255]; integer iw = 0;
    function automatic [127:0] word_at(input [39:0] a);
        longint w; begin w = (longint'(a) - longint'(IMG)) / 16; word_at = (a >= IMG && w < 256) ? img[w] : 128'hDEAD; end
    endfunction
    reg [39:0] fq [0:255]; integer fqh = 0, fqn = 0, fdel = 0;
    always @(posedge clk) begin
        vr_p1 <= vr_v; vr_rsp_v <= vr_p1;
        f_rsp_v <= 1'b0;
        if (!rst_n) begin fqh = 0; fqn = 0; fdel = 0; end
        else begin
            if (f_req_v) begin fq[(fqh + fqn) % 256] = f_req_addr; fqn = fqn + 1; end
            if (fqn > 0) begin
                if (fdel > 0) fdel = fdel - 1;
                else begin f_rsp_v <= 1'b1; f_rsp_data <= {word_at(fq[fqh] + 40'd16), word_at(fq[fqh])}; fqh = (fqh + 1) % 256; fqn = fqn - 1; fdel = 1; end
            end
        end
    end
    longint cyc = 0;
    // ---------------------------------------------------------------- VM slice models (one a cluster)
    reg [31:0] vm [0:3][0:VMW-1];
    integer rq_s [0:3][0:7][0:255]; longint rq_due [0:3][0:7][0:255]; integer rq_h [0:3][0:7], rq_t [0:3][0:7]; longint ldue [0:3][0:7];
    reg [3:0] gnt = 0;
    integer errors = 0;
    initial for (integer c = 0; c < 4; c++) for (integer b = 0; b < 8; b++) begin rq_h[c][b] = 0; rq_t[c][b] = 0; ldue[c][b] = 0; end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        for (integer c = 0; c < 4; c++) begin : vc
            reg [128:0] rq; reg [2064:0] rr;
            rq = vr2q[c*129 +: 129]; rr = '0;
            rr[2064] = gnt[c]; gnt[c] <= rst_n && rq[128];
            if (rst_n) for (integer b = 0; b < NB; b++) begin
                if (rq[b*16 + 15]) begin : rd
                    integer sec; longint du;
                    sec = int'(rq[b*16 +: 15]);
                    if (sec % NB != b) begin $display("TB FAIL: cluster %0d VM lane %0d got sector %0d", c, b, sec); errors++; end
                    if (!gnt[c]) begin $display("TB FAIL: cluster %0d VM read without the grant", c); errors++; end
                    du = cyc + LAT + ((JIT > 0) ? $urandom_range(0, JIT) : 0); if (du < ldue[c][b]) du = ldue[c][b]; ldue[c][b] = du;
                    rq_s[c][b][rq_t[c][b] % 256] = sec; rq_due[c][b][rq_t[c][b] % 256] = du; rq_t[c][b] = rq_t[c][b] + 1;
                    rr[NB*257 + b] = 1'b1;
                    // (as tb_hgi_dma_back: the credit is back at the bank pop = the next edge; the response pipeline holds <= 32)
                    if (rq_t[c][b] - rq_h[c][b] > 32) begin $display("TB FAIL: cluster %0d VM lane %0d over 32 in flight", c, b); errors++; end
                end
                if (rq_h[c][b] < rq_t[c][b] && rq_due[c][b][rq_h[c][b] % 256] <= cyc) begin : rs
                    integer sc; sc = rq_s[c][b][rq_h[c][b] % 256];
                    for (integer w = 0; w < 8; w++) rr[b*257 + w*32 +: 32] = vm[c][(sc * 8 + w) % VMW];
                    rr[b*257 + 256] = 1'b1; rq_h[c][b] = rq_h[c][b] + 1;
                end
            end
            vr2r[c*2065 +: 2065] <= rr;
        end
    end
    // ---------------------------------------------------------------- svc WRITE models (one a stack)
    reg [4*2312-1:0] wdh [0:HOPS]; reg [31:0] crh [0:HOPS]; reg [31:0] cr0 = 0;
    always @* begin wdh[0] = wd; crh[0] = cr0; end
    always @(posedge clk) for (integer k = 1; k <= HOPS; k++) begin wdh[k] <= wdh[k-1]; crh[k] <= crh[k-1]; end
    assign wd_cr = crh[HOPS];
    reg [31:0] hbm [longint]; reg wr [longint];
    integer ackq [0:3][0:1023]; longint ackt [0:3][0:1023]; integer aq_h [0:3], aq_t [0:3];
    longint nwrit = 0, nack = 0, t_lastw = 0, t_lastack = 0;
    initial for (integer s = 0; s < 4; s++) begin aq_h[s] = 0; aq_t[s] = 0; end
    always @(posedge clk) begin
        cr0 <= '0; wa <= '0;
        for (integer s = 0; s < 4; s++) begin : st
            integer c; c = 0;
            for (integer l = 0; l < NL; l++) begin : ln
                reg [288:0] bt; longint a;
                bt = wdh[HOPS][(s*NL + l)*289 +: 289];
                if (bt[288]) begin
                    a = longint'(bt[287:256]) * 32;
                    if (((a >> SBIT) & 3) != s) begin $display("TB FAIL: stack %0d lane %0d got address %h", s, l, a); errors++; end
                    for (integer w = 0; w < 8; w++) begin
                        if (wr.exists(a / 4 + w)) begin $display("TB FAIL: HBM word %h written twice", a + w * 4); errors++; end
                        hbm[a / 4 + w] = bt[w*32 +: 32]; wr[a / 4 + w] = 1'b1;
                    end
                    cr0[s*NL + l] <= 1'b1; c = c + 1; nwrit = nwrit + 1; t_lastw = cyc;
                end
            end
            if (c > 0) begin ackq[s][aq_t[s] % 1024] = c; ackt[s][aq_t[s] % 1024] = cyc + ALAT; aq_t[s] = aq_t[s] + 1; end
            if (aq_h[s] < aq_t[s] && ackt[s][aq_h[s] % 1024] <= cyc) begin
                wa[s*4 +: 4] <= 4'(ackq[s][aq_h[s] % 1024]); nack = nack + ackq[s][aq_h[s] % 1024]; aq_h[s] = aq_h[s] + 1;
                t_lastack = cyc;
            end
        end
    end
    // ---------------------------------------------------------------- program encoding (HGI-1 field layout)
    function automatic [127:0] mkhdr(input integer unit, input integer op, input integer opnd, input integer param, input integer wt);
        mkhdr = {4'(unit), 6'(op), 16'(wt), 2'd0, 7'(opnd), 1'b0, 3'd0, 25'(param), 32'd0, 32'd0};
    endfunction
    function automatic [255:0] mkdesc(input integer space, input integer fmt, input longint base, input integer n, input integer m,
                                      input longint stride, input integer dsel, input integer dmul);
        reg [255:0] d;
        begin d = '0; d[1:0] = 2'(space); d[4:2] = 3'(fmt); d[47:8] = 40'(base); d[67:48] = 20'(n); d[87:68] = 20'(m);
              d[119:88] = 32'(stride); d[173:168] = 6'(dsel); d[200:174] = 27'(dmul); mkdesc = d; end
    endfunction
    task automatic put(input [127:0] w); begin img[iw] = w; iw = iw + 1; end endtask
    task automatic put_store(input integer param, input integer vb, input integer vst, input longint hb, input longint hst, input integer m, input integer n);
        reg [255:0] a, o;
        begin
            a = mkdesc(1, 0, longint'(vb), n, m, longint'(vst), 0, 0);
            o = mkdesc(0, 0, hb, n, m, hst, 3, 131072);                    // dyn_sel TOKEN, dyn_mul = the column pitch
            put(mkhdr(8, 1, 7'h11, param, 0)); put(a[127:0]); put(a[255:128]); put(o[127:0]); put(o[255:128]);
        end
    endtask
    // ---------------------------------------------------------------- stimulus / oracle
    reg [31:0] h [0:319][0:63]; reg [31:0] pre [0:7];
    reg [31:0] exp_w [longint];
    integer sv_b [0:3][0:1], sv_s [0:3][0:1], sv_m [0:3][0:1], sv_n [0:3][0:1]; integer sv_k [0:3], sv_t [0:3];
    integer nret = 0, nsrc = 0, nflt = 0;
    always @(posedge clk) if (rst_n) begin
        for (integer c = 0; c < 4; c++) if (e_src[c]) begin
            if (sv_k[c] < sv_t[c])
                for (integer o = 0; o < sv_m[c][sv_k[c]]; o++) for (integer i = 0; i < sv_n[c][sv_k[c]]; i++)
                    vm[c][sv_b[c][sv_k[c]] + o * sv_s[c][sv_k[c]] + i] = 32'hDEAD0000 ^ 32'(i);
            sv_k[c] = sv_k[c] + 1; nsrc = nsrc + 1;
        end
        if (ret_done) begin
            nret = nret + 1;
            if (nret > nsrc && errors < 8) begin $display("TB FAIL: DMA retire %0d with only %0d sources consumed", nret, nsrc); errors++; end
        end
        if (ret_fault) nflt = nflt + 1;
        if (s_fault_o && t_sf == 0) t_sf = cyc;
        if (fault && t_uf == 0) t_uf = cyc;
    end
    integer exp_sec = 0; reg armed = 0; longint t_first = 0, t_q = 0, t_cpl = 0, t_db = 0, t_lastrec = 0;
    always @(posedge clk) if (rst_n && armed) begin
        if (rec_v && rec_rdy) begin if (t_first == 0) t_first = cyc; t_lastrec = cyc; end
        if (t_first != 0 && cyc > t_first + 2) begin
            if (wr_quiet && nret >= 5 && t_q == 0) t_q = cyc;
            if ((wr_quiet || cpl_v) && nack < exp_sec && errors < 8) begin
                $display("TB FAIL: wr_quiet %0d cpl %0d at +%0d with %0d of %0d sectors acknowledged", wr_quiet, cpl_v, cyc - t_first, nack, exp_sec);
                errors++;
            end
        end
    end
    longint tp, tp_max = 0, te_max = 0;
    // kind 0: the production program; 1: cluster 2's h record on stack 1 (duplicate cluster); 2: no GLAST on the h group
    task automatic run(input integer slot, input bit mirror, input integer kind);
        integer to; longint loc;
        to = 0; loc = COLB + slot * CSTR;
        rst_n = 0; repeat (4) @(negedge clk); rst_n = 1; repeat (40 + 2 * DHOPS) @(negedge clk);
        exp_w.delete(); wr.delete(); hbm.delete(); nwrit = 0; nack = 0; t_lastw = 0; t_lastack = 0; nret = 0; nsrc = 0; nflt = 0;
        t_first = 0; t_q = 0; t_lastrec = 0; t_sf = 0; t_uf = 0;
        for (integer c = 0; c < 4; c++) begin sv_k[c] = 0; sv_t[c] = 0; for (integer i = 0; i < VMW; i++) vm[c][i] = $urandom; end
        for (integer o = 0; o < 320; o++) for (integer i = 0; i < 64; i++) h[o][i] = $urandom;
        for (integer i = 0; i < 8; i++) pre[i] = $urandom;
        // ORACLE: the NATIVE slot image (logical row 80q + j on stack q at slot row q + 4j), from the logical h / PRE and the slot only
        for (integer o = 0; o < 320; o++) for (integer i = 0; i < 64; i++)
            exp_w[((longint'(o / 80) << SBIT) | (loc + 64 * (o / 80) + 256 * (o % 80))) / 4 + i] = h[o][i];
        for (integer i = 0; i < 8; i++) exp_w[(loc + 81920) / 4 + i] = pre[i];
        exp_sec = 4 * 640 + 1;
        for (integer c = 0; c < 4; c++) begin
            sv_b[c][0] = mirror ? 65536 + 5120 * c : 128 + 1024 * c; sv_s[c][0] = 64; sv_m[c][0] = 80; sv_n[c][0] = 64; sv_t[c] = 1;
            if (mirror) begin for (integer o = 0; o < 320; o++) for (integer i = 0; i < 64; i++) vm[c][65536 + 64 * o + i] = h[o][i]; end
            else for (integer j = 0; j < 80; j++) for (integer i = 0; i < 64; i++) vm[c][sv_b[c][0] + 64 * j + i] = h[80 * c + j][i];
        end
        sv_b[0][1] = mirror ? 65536 + 20480 : 8192; sv_s[0][1] = 64; sv_m[0][1] = 1; sv_n[0][1] = 8; sv_t[0] = 2;
        for (integer i = 0; i < 8; i++) vm[0][sv_b[0][1] + i] = pre[i];
        // the PROGRAM (bases WITHOUT the slot: the sequencer adds TOKEN x 131072)
        for (integer i = 0; i < 256; i++) img[i] = '0;
        iw = 0;
        for (integer c = 0; c < 4; c++)
            put_store(((c == 3 && kind != 2) ? 3 : 1), sv_b[c][0], sv_s[c][0],
                      (longint'((kind == 1 && c == 2) ? 1 : c) << SBIT) | (COLB + 64 * c), 256, 80, 64);
        put_store(3, sv_b[0][1], 64, COLB + 81920, 0, 1, 8);
        put(mkhdr(0, 4, 0, 0, 0));                                                           // CTL.FENCE
        begin : endr reg [255:0] a; a = mkdesc(1, 5, 256, 1, 1, 0, 0, 0); put(mkhdr(0, 3, 1, 0, 16'h0100)); put(a[127:0]); put(a[255:128]); end
        if (!wr_quiet) begin $display("TB FAIL: not quiet before the group"); errors++; end
        armed = 1;
        while (!db_rdy) @(negedge clk);
        db_token = 18'((MUT == 8) ? (slot ^ 1) : slot); db_v = 1; @(negedge clk); db_v = 0; t_db = cyc;
        while (!cpl_v && !(kind != 0 && fault && to > 400) && to < 20000) begin @(negedge clk); to++; end
        t_cpl = cyc; armed = 0;
        if (kind != 0) begin
            if (!fault || nflt != 1 || nwrit != 0 || (cpl_v && cpl_status == 4'd0))
                begin $display("TB FAIL: negative program %0d: fault %0d ret_fault %0d HBM sectors written %0d cpl %0d status %0d", kind, fault, nflt, nwrit, cpl_v, cpl_status); errors++; end
            // the owner of the rule is S in BOTH programs: 1 sends cluster 1 twice in the h group; 2 leaves the h group
            // open, so the PRE record (cluster 0) is a second record for cluster 0 in it.  S's fault must precede the unit's.
            else if (!(t_sf != 0 && t_sf < t_uf))
                begin $display("TB FAIL: negative program %0d: the unit fault (cycle %0d) did not come from S's own fault (cycle %0d)", kind, t_uf, t_sf); errors++; end
            else $display("TB negative program %0d (%s): sticky unit fault, 0 HBM sectors written, completion %0d status %0d",
                          kind, kind == 1 ? "duplicate cluster" : "dropped GLAST", cpl_v, cpl_status);
        end else begin
            tp = t_q - t_first;
            if (!cpl_v) begin $display("TB FAIL: no completion (slot %0d mirror %0d): retires %0d fault %0d", slot, mirror, nret, fault); errors++; end
            else if (cpl_status != 4'd0 || nret != 5 || fault) begin $display("TB FAIL: completion status %0d retires %0d fault %0d", cpl_status, nret, fault); errors++; end
            if (cpl_v && nack < exp_sec) begin $display("TB FAIL: EARLY FENCE: completion with %0d of %0d sectors acknowledged", nack, exp_sec); errors++; end
            repeat (ALAT + 2 * HOPS + 30) @(negedge clk);
            begin : chk
                integer bad, extra; bad = 0; extra = 0;
                foreach (exp_w[a]) if (!wr.exists(a) || hbm[a] !== exp_w[a]) begin
                    if (bad < 3) $display("  HBM word %h = %h expected %h", a * 4, wr.exists(a) ? hbm[a] : 32'hx, exp_w[a]);
                    bad++;
                end
                foreach (wr[a]) if (!exp_w.exists(a)) extra++;
                if (bad || extra) begin $display("TB slot %0d %s: %0d wrong, %0d stray words", slot, mirror ? "MIRROR" : "LOCAL", bad, extra); errors++; end
                else $display("TB slot %0d %s: %0d words exact, 0 stray; first DMA dispatch -> wr_quiet %0d cycles (last record +%0d, last ack +%0d); doorbell -> completion %0d (doorbell -> first dispatch %0d)",
                              slot, mirror ? "MIRROR" : "LOCAL", exp_w.size(), tp, t_lastrec - t_first, t_lastack - t_first, t_cpl - t_db, t_first - t_db);
            end
            if (tp > tp_max) tp_max = tp;
            if (t_cpl - t_db > te_max) te_max = t_cpl - t_db;
        end
        cpl_rdy = 1; @(negedge clk); cpl_rdy = 0;
    endtask
    initial begin
        void'($urandom(SEED));
        begin : runs
            integer sl [0:5]; bit mi [0:5];
            sl = '{0, 0, 5, 12, 12, 7}; mi = '{0, 1, 0, 0, 1, 1};
            for (integer k = 0; k < 6 && errors == 0; k++) run(sl[k], mi[k], 0);
            if (errors == 0) run(3, 0, 1);
            if (errors == 0) run(9, 1, 2);
        end
        if (errors == 0 && tp_max > LIMIT) $display("TB THROUGHPUT FAIL: %0d cycles > limit %0d (price 248)", tp_max, LIMIT);
        if (errors == 0 && tp_max <= LIMIT)
            $display("TB_HGI_B2_SWAP_REC PASS (MUT %0d DHOPS %0d LAT %0d JIT %0d HOPS %0d ALAT %0d) exact from program records, worst first dispatch -> fence answer %0d cycles (price 248, limit %0d, ratio %0.3f); worst doorbell -> completion %0d",
                     MUT, DHOPS, LAT, JIT, HOPS, ALAT, tp_max, LIMIT, real'(tp_max) / 248.0, te_max);
        else $display("TB_HGI_B2_SWAP_REC FAIL (MUT %0d) errors %0d worst %0d cycles", MUT, errors, tp_max);
        $finish;
    end
    initial begin #4000000; $display("TB_HGI_B2_SWAP_REC FAIL: global timeout"); $finish; end
    // verilator lint_off UNUSEDSIGNAL
    wire unused_ok = &{1'b0, sq_busy, vr_addr, u_v, d_sut, d_desc, d_n, d_pos1, d_pslot1, d_L, d_L1, cpl_token, cpl_pos, cpl_job, cpl_cycles, cpl_gen, cpl_tokx, s_done, e_acc};
    // verilator lint_on UNUSEDSIGNAL
endmodule
`default_nettype wire
