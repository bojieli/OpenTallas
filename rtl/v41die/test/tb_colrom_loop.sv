`timescale 1ns/1ps
// tb_colrom_loop (FABLE-FIX-S81-COLROM-R2 2026-11-21, COORD functional gate of the S81 col ROM-input stage, lever 1).
// Closed loop of one col pair exactly as the bound RTL of col_h10_r1__t1__cld01bb4ae wires it (u_s6 / u_c6_0..6 / u_bs6 / u_e6.u_w + u_e6.u_e):
//   lc -> ot_s81_cfg7_seq (PQ1 PINREG1 LAYOUT1 RD_EXTRA from +define+OT_S81_CFG7_RDX) -> a/ce -> 7 x ot_rom_4096x72_m8 -> [q stage] -> seq q
//   seq cfg/go_e -> dsfd_qbank_S (with x0/x1) ; seq go_tag direct -> w_u_e6_0_Y bus -> [ROM-input stage on the 13 element inputs] ->
//   ot_v41_rom_elem_q_qxpq_w10_gb_hw / _he (bound parameters) ; ef = {u_w.bank_free, u_w.sh_free} -> seq, UNCHANGED (no stage).
// Two loops share one stimulus (the hub calendar is fixed, it cannot see the stage): A = no ROM-input stage (candC3g + RDX only),
// B = with the stage (the colrom delta).  The hub is adaptive on A's seq status only (st.ld_busy) and A's element state, i.e. the
// schedule is as tight as A allows, then B must: raise no fault (seq st.fault, element fault), and emit the same partial records
// (pv/pval/prow/pseg/pnseg/perr/ppos of both halves) in the same order, each exactly STG cycles later.
//   +K=n   : 0 = serial ops (next broadcast after the op drained); n > 0 = preload, the next cfg_go n cycles after go (pend path:
//            held on bank_free / sh_free).  The sweep of K measures the stale-ef window (go -> seq sees bank_free low).
//   +GQ=n  : quiet cycles the hub waits after A is ready before go.
// Mutants (must FAIL): +define+MUT_CFGONLY (B: stage on cfg_v/cfg_a/cfg_d only: go/go_tag/xs one edge early relative to cfg),
//                      +define+MUT_EFSTUCK (B: seq ef tied 2'b11: the held load is not held).
module colrom_loop #(parameter integer STG = 0, parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire [14:0] lc, input wire [282:0] x0, input wire [265:0] x1,
    output wire [1:0] st, output wire [1:0] ef, output wire w_fault, output wire e_fault,
    output wire [63:0] rec_w, output wire [63:0] rec_e, output wire [53:0] s_cfg, output wire s_go, output wire [1:0] s_tag);
    wire [11:0] a; wire [6:0] ce; wire [71:0] rq [0:6]; reg [47:0] lq [0:6];
    wire [53:0] cfg; wire go_e; wire [1:0] go_tag;
    wire bank_free, sh_free;
    assign ef = {bank_free, sh_free};
    wire [1:0] ef_s = (MUT == 2) ? 2'b11 : ef;
    genvar j;
    generate for (j = 0; j < 7; j = j + 1) begin : g_rom
        ot_rom_4096x72_m8 u_rom (.clk(clk), .ce_in(ce[j]), .addr_in(a), .rd_out(rq[j]));
        always @(posedge clk) lq[j] <= rq[j][47:0];            // u_y_xd_u_s6_q<j>: relay_depth sink row, D = 1 (RD_EXTRA = 1)
    end endgenerate
    ot_s81_cfg7_seq #(.AW(15), .CW(25), .LAYOUT(1), .NROM(7), .NSEG(8), .PHW(10), .PINREG(1), .PQ(1), .RD_EXTRA(1)) u_s (
        .clk(clk), .rst_n(rst_n), .lc(lc), .a(a), .ce0(ce[0]), .ce1(ce[1]), .ce2(ce[2]), .ce3(ce[3]), .ce4(ce[4]), .ce5(ce[5]), .ce6(ce[6]),
        .q0(lq[0]), .q1(lq[1]), .q2(lq[2]), .q3(lq[3]), .q4(lq[4]), .q5(lq[5]), .q6(lq[6]),
        .cfg(cfg), .go_e(go_e), .st(st), .ef(ef_s), .go_tag(go_tag));
    assign s_cfg = cfg; assign s_go = go_e; assign s_tag = go_tag;
    wire [53:0] b_cfg; wire b_go; wire [282:0] b_x0; wire [265:0] b_x1;
    dsfd_qbank_S u_bs (.ck(clk), .i_cfg(cfg), .i_go(go_e), .i_x0(x0), .i_x1(x1), .o_cfg(b_cfg), .o_go(b_go), .o_x0(b_x0), .o_x1(b_x1), .rs(rst_n));
    // the bound bus (col_h10_r1 line 3872/3876): bit 604 is the reset, not used here
    wire [603:0] y = {b_cfg[53], b_cfg[4:0], b_cfg[52:5], b_go, go_tag[1:0], b_x0[282], b_x0[276:266], b_x0[255:0], b_x0[265:256],
                      b_x1[255:0], b_x1[265:256], b_x0[279:277]};
    reg [603:0] yd;
    always @(posedge clk) yd <= y;                              // u_y_xd_u_e6_u_{w,e}_*: relay_depth sink rows, D = 1 on all 13 ports
    wire [603:0] ys = (STG == 0) ? y : (MUT == 1) ? {yd[603:550], y[549:0]} : yd;
`define EP .CGR(0), .EARLY(1), .FAST(1), .FRONT_PAR(0), .GO_BOUNDARY(1), .IFN(0), .MTP(1), .OLAT(1), .PP(1), .PQ(1), .QM(5), .QPIPE(1), .QP_CAP(0), .QP_CSAM(10), .QP_P1(1), .QP_XS(1), .QS(5), .QTIMING_FIX(1), .QW(0), .QX(10), .QY(1), .QZ(1), .QZ_NE(4), .QZ_NS(8), .RSTP(1)
`define EC .clk(clk), .rst_n(rst_n), .cfg_v(ys[603]), .cfg_a(ys[602:598]), .cfg_d(ys[597:550]), .go(ys[549]), .go_tag(ys[548:547]), \
           .xs_v(ys[546]), .xs_p(ys[545:538]), .xs_b(ys[537:535]), .xs_q0(ys[534:279]), .xs_e0(ys[278:269]), .xs_q1(ys[268:13]), .xs_e1(ys[12:3]), .xs_pos(ys[2:0])
    wire wpv, wperr, epv, eperr; wire [31:0] wpval, epval; wire [15:0] wprow, eprow; wire [4:0] wpseg, wpnseg, epseg, epnseg; wire [2:0] wppos, eppos;
    ot_v41_rom_elem_q_qxpq_w10_gb_hw #(`EP, .INSTANCE("w")) u_w (`EC, .walking(), .bank_free(bank_free), .sh_free(sh_free),
        .pv(wpv), .pval(wpval), .prow(wprow), .pseg(wpseg), .pnseg(wpnseg), .perr(wperr), .ppos(wppos), .busy(), .fault(w_fault));
    ot_v41_rom_elem_q_qxpq_w10_gb_he #(`EP, .INSTANCE("e")) u_e (`EC, .walking(), .bank_free(), .sh_free(),
        .pv(epv), .pval(epval), .prow(eprow), .pseg(epseg), .pnseg(epnseg), .perr(eperr), .ppos(eppos), .busy(), .fault(e_fault));
    assign rec_w = {1'b0, wpv, wperr, wppos, wpnseg, wpseg, wprow, wpval};
    assign rec_e = {1'b0, epv, eperr, eppos, epnseg, epseg, eprow, epval};
endmodule

module tb_colrom_loop;
    integer SEED = 1, K = 0, GQ = 10, NOPS = 40;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst = 0;
    reg go = 0, cfg_go = 0; reg [9:0] ph = 0; reg [2:0] np = 0;
    reg xs_v = 0; reg [7:0] xs_p = 0; reg [2:0] xs_b = 0, xs_pos = 0; reg [255:0] xs_q0 = 0, xs_q1 = 0; reg [9:0] xs_e0 = 10'd127, xs_e1 = 10'd127;
    // hub / lane sender flops (every input launches from a rising-edge flop)
    reg [14:0] lc = 0; reg [282:0] x0 = 0; reg [265:0] x1 = 0;
    always @(posedge clk) begin
        lc <= {np, ph, cfg_go, go};
        x0 <= {xs_v, 2'b00, xs_pos, xs_p, xs_b, xs_e0, xs_q0};
        x1 <= {xs_e1, xs_q1};
    end
`ifdef MUT_CFGONLY
    localparam integer MUTB = 1;
`elsif MUT_EFSTUCK
    localparam integer MUTB = 2;
`else
    localparam integer MUTB = 0;
`endif
    wire [1:0] a_st, b_st, a_ef, b_ef, a_tag, b_tag; wire a_wf, a_ef_, b_wf, b_ef_, a_go, b_go; wire [63:0] a_rw, a_re, b_rw, b_re; wire [53:0] a_cfg, b_cfg;
    colrom_loop #(.STG(0), .MUT(0)) A (.clk(clk), .rst_n(rst), .lc(lc), .x0(x0), .x1(x1), .st(a_st), .ef(a_ef), .w_fault(a_wf), .e_fault(a_ef_),
        .rec_w(a_rw), .rec_e(a_re), .s_cfg(a_cfg), .s_go(a_go), .s_tag(a_tag));
    colrom_loop #(.STG(1), .MUT(MUTB)) B (.clk(clk), .rst_n(rst), .lc(lc), .x0(x0), .x1(x1), .st(b_st), .ef(b_ef), .w_fault(b_wf), .e_fault(b_ef_),
        .rec_w(b_rw), .rec_e(b_re), .s_cfg(b_cfg), .s_go(b_go), .s_tag(b_tag));
    // ---- cfg ROM image (both loops): phase p, word k at macro k % 7, row 4p + k / 7 (LAYOUT 1); element words as tb_qxpq_split.configure
    localparam integer NPH = 64;
    reg [47:0] payload [0:NPH*25-1];
    task automatic mkphase(input integer p);
        integer c, nu, base, mode; reg [47:0] d;
        mode = p % 2;                                   // 0: 3 valid classes, 2 positions (np = 2); 1: 8 classes of 1 unit
        for (c = 0; c < 8; c = c + 1) begin
            d = 48'(c + 1) | (48'(1 + $urandom % 3) << 16) | (48'd1 << 21) | (48'(mode != 1) << 26) | (48'd1 << 27) | (48'd1 << 28) | (48'($urandom % 8192) << 29);
            payload[p*25 + c] = d;
            if (mode == 0) nu = (c == 0) ? 9 : ((c == 3) ? 3 : ((c == 7) ? 2 : 0)); else nu = 1;
            base = (c == 0) ? 252 : (32 * c);
            payload[p*25 + 8 + c] = 48'(nu != 0) | (48'(base) << 1) | (48'(nu) << 9) | (48'(c) << 16) | (48'(c) << 19);
            payload[p*25 + 17 + c] = 48'(c + 101);
        end
        payload[p*25 + 16] = 48'(mode == 0) | (48'(2 * ($urandom % 64)) << 6);      // plast comes from cfg_np (the sequencer ORs it in)
    endtask
    task automatic load_roms;
        integer g, b, m, r;
        for (g = 0; g < NPH * 25; g = g + 1) begin
            m = (g % 25) % 7; r = 4 * (g / 25) + (g % 25) / 7;
            for (b = 0; b < 48; b = b + 1) begin
                case (m)
                    0: begin A.g_rom[0].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; B.g_rom[0].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; end
                    1: begin A.g_rom[1].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; B.g_rom[1].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; end
                    2: begin A.g_rom[2].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; B.g_rom[2].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; end
                    3: begin A.g_rom[3].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; B.g_rom[3].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; end
                    4: begin A.g_rom[4].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; B.g_rom[4].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; end
                    5: begin A.g_rom[5].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; B.g_rom[5].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; end
                    default: begin A.g_rom[6].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; B.g_rom[6].u_rom.arr[r/8][b*8 + r%8] = payload[g][b]; end
                endcase
            end
        end
    endtask
    // ---- A-side observation (the hub is tight on A)
    wire a_run   = A.u_w.u_h.u_e.n_run;
    wire a_shful = A.u_w.u_h.u_e.u_pq.sh_full;
    wire a_walk  = A.u_w.u_h.u_e.pq_walking;
    wire [2:0] a_settle = A.u_w.u_h.u_e.u_pq.settle;
    wire a_pend = A.u_s.u_impl.pend, b_pend = B.u_s.u_impl.pend;
    wire a_lds = A.u_s.u_impl.ld_start, b_lds = B.u_s.u_impl.ld_start;
    // ---- scoreboard
    integer cyc = 0;
    reg [63:0] qa_w [0:65535]; integer ta_w [0:65535]; integer na_w = 0, nb_w = 0;
    reg [63:0] qa_e [0:65535]; integer ta_e [0:65535]; integer na_e = 0, nb_e = 0;
    integer rec_mism = 0, shift_bad = 0, a_fault_c = 0, b_fault_c = 0, a_fault_first = -1, b_fault_first = -1;
    integer pend_a = 0, pend_b = 0, lds_a = 0, lds_b = 0, lds_shift_max = 0, seq_diff = 0, a_lds_t = 0, go_cnt = 0, cfg_cnt = 0, xs_cnt = 0, go_a = 0, go_b = 0;
    reg a_pend_d = 0, b_pend_d = 0;
    always @(negedge clk) begin
        cyc = cyc + 1;
        if (rst) begin
            if (a_rw[62]) begin if (na_w < 65536) begin qa_w[na_w] = a_rw; ta_w[na_w] = cyc; end na_w = na_w + 1; end
            if (a_re[62]) begin if (na_e < 65536) begin qa_e[na_e] = a_re; ta_e[na_e] = cyc; end na_e = na_e + 1; end
            if (b_rw[62]) begin
                if (nb_w >= na_w || nb_w >= 65536 || qa_w[nb_w] !== b_rw) begin rec_mism = rec_mism + 1; if (rec_mism <= 3) $display("REC_MISMATCH w #%0d cyc %0d B %h A %h", nb_w, cyc, b_rw, nb_w < na_w ? qa_w[nb_w] : 64'hx); end
                else if (cyc - ta_w[nb_w] != 1) shift_bad = shift_bad + 1;
                nb_w = nb_w + 1;
            end
            if (b_re[62]) begin
                if (nb_e >= na_e || nb_e >= 65536 || qa_e[nb_e] !== b_re) begin rec_mism = rec_mism + 1; if (rec_mism <= 3) $display("REC_MISMATCH e #%0d cyc %0d B %h A %h", nb_e, cyc, b_re, nb_e < na_e ? qa_e[nb_e] : 64'hx); end
                else if (cyc - ta_e[nb_e] != 1) shift_bad = shift_bad + 1;
                nb_e = nb_e + 1;
            end
            if (a_st[1] || a_wf || a_ef_) begin a_fault_c = a_fault_c + 1; if (a_fault_first < 0) begin a_fault_first = cyc; $display("A_FAULT cyc %0d st %b wf %b ef %b (go %0d cfg %0d)", cyc, a_st, a_wf, a_ef_, go_cnt, cfg_cnt); end end
            if (b_st[1] || b_wf || b_ef_) begin b_fault_c = b_fault_c + 1; if (b_fault_first < 0) begin b_fault_first = cyc; $display("B_FAULT cyc %0d st %b wf %b ef %b (go %0d cfg %0d)", cyc, b_st, b_wf, b_ef_, go_cnt, cfg_cnt); end end
            if (a_pend && !a_pend_d) pend_a = pend_a + 1;
            if (b_pend && !b_pend_d) pend_b = pend_b + 1;
            if (a_lds) begin lds_a = lds_a + 1; a_lds_t = cyc; end
            if (b_lds) begin lds_b = lds_b + 1; if (cyc - a_lds_t > lds_shift_max) lds_shift_max = cyc - a_lds_t; end
            if ({a_cfg, a_go, a_tag, a_st} !== {b_cfg, b_go, b_tag, b_st}) seq_diff = seq_diff + 1;
            if (a_go) go_a = go_a + 1;
            if (b_go) go_b = go_b + 1;
        end
        a_pend_d = a_pend; b_pend_d = b_pend;
    end
    // first cycle the sequencer of each loop sees bank_free low after a go at the lc pin (the stale-ef window)
    integer go_t = -1, la = -1, lb = -1, la_max = 0, lb_max = 0;
    always @(negedge clk) if (rst) begin
        if (lc[0]) begin go_t = cyc; la = -1; lb = -1; end
        if (go_t >= 0 && la < 0 && !A.u_s.u_impl.ef_i[1]) begin la = cyc - go_t; if (la > la_max && la < 64) la_max = la; end
        if (go_t >= 0 && lb < 0 && !B.u_s.u_impl.ef_i[1]) begin lb = cyc - go_t; if (lb > lb_max && lb < 64) lb_max = lb; end
    end
    task automatic tick(input integer n); repeat (n) @(posedge clk); endtask
    task automatic rnd_x;
        for (integer i = 0; i < 8; i = i + 1) begin xs_q0[32*i +: 32] = $urandom; xs_q1[32*i +: 32] = $urandom; end
        xs_e0 = 10'd100 + 10'($urandom % 50); xs_e1 = 10'd100 + 10'($urandom % 50);
    endtask
    task automatic beat(input integer gap);
        @(negedge clk); #0.01; rnd_x;
        xs_v = 1; xs_p = A.u_w.u_h.u_e.n_pair; xs_b = A.u_w.u_h.u_e.n_b; xs_pos = A.u_w.u_h.u_e.n_pos; xs_cnt = xs_cnt + 1;
        tick(1); @(negedge clk); #0.01; xs_v = 0; rnd_x; tick(gap);
    endtask
    task automatic bcast(input integer p);
        @(negedge clk); #0.01; cfg_go = 1; ph = 10'(p % NPH); np = (p % 2 == 0) ? 3'd2 : 3'd0; cfg_cnt = cfg_cnt + 1; tick(1);
        @(negedge clk); #0.01; cfg_go = 0;
    endtask
    // preload: the next broadcast K cycles after go (lc time).  pre_cnt: >0 count down, 0 assert, -2 deassert, -1 idle
    integer pre_cnt = -1, pre_ph = 0;
    always @(negedge clk) begin
        if (pre_cnt > 0) pre_cnt = pre_cnt - 1;
        else if (pre_cnt == 0) begin #0.01; cfg_go = 1; ph = 10'(pre_ph % NPH); np = (pre_ph % 2 == 0) ? 3'd2 : 3'd0; cfg_cnt = cfg_cnt + 1; pre_cnt = -2; end
        else if (pre_cnt == -2) begin #0.01; cfg_go = 0; pre_cnt = -1; end
    end
    task automatic wait_loaded;          // A: the load reached the element, the shadow was copied and settled, sequencer idle
        integer w, q; w = 0; q = 0;
        while (q < GQ + 1 && w < 60000) begin
            if (a_run) begin beat(16); q = 0; end
            else begin @(negedge clk); w = w + 1; if (!a_st[0] && !a_shful && !a_walk && a_settle == 0 && !a_pend && seen_full) q = q + 1; else q = 0; end
        end
        if (w >= 60000) begin $display("TIMEOUT wait_loaded cyc %0d", cyc); timeouts = timeouts + 1; end
    endtask
    integer timeouts = 0; reg seen_full = 0;
    always @(negedge clk) if (a_shful) seen_full = 1;
    integer n, sent, w;
    initial begin
        void'($value$plusargs("seed=%d", SEED)); void'($value$plusargs("K=%d", K)); void'($value$plusargs("GQ=%d", GQ)); void'($value$plusargs("nops=%d", NOPS));
        void'($urandom(SEED));
        for (n = 0; n < NPH; n = n + 1) mkphase(n);
        #0.1 load_roms;
        tick(8); @(negedge clk); rst = 1; tick(40);
        seen_full = 0; bcast(0);
        for (n = 0; n < NOPS; n = n + 1) begin
            wait_loaded;
            @(negedge clk); #0.01; go = 1; go_cnt = go_cnt + 1; seen_full = 0; tick(1);
            @(negedge clk); #0.01; go = 0;
            if (K == 1 && n + 1 < NOPS) begin cfg_go = 1; ph = 10'((n + 1) % NPH); np = ((n + 1) % 2 == 0) ? 3'd2 : 3'd0; cfg_cnt = cfg_cnt + 1; pre_cnt = -2; end
            else if (K > 1 && n + 1 < NOPS) begin pre_ph = n + 1; pre_cnt = K - 2; end
            w = 0; while (!a_run && w < 60) begin @(negedge clk); w = w + 1; end
            sent = 0; while (a_run && sent < 4000) begin beat(16); sent = sent + 1; end
            if (K == 0 && n + 1 < NOPS) begin
                w = 0; while (!(a_ef == 2'b11 && !a_walk) && w < 4000) begin @(negedge clk); w = w + 1; end
                tick(8); bcast(n + 1);
            end
        end
        tick(600);
        $display("COLROM_LOOP K %0d GQ %0d seed %0d: ops go %0d (A go_e %0d, B go_e %0d) cfg %0d xs %0d | recs A w/e %0d/%0d B w/e %0d/%0d mism %0d shift!=1 %0d | faults A %0d (first %0d) B %0d (first %0d) | pend A %0d B %0d, ld_start A %0d B %0d, B-A ld_start max %0d, seq cycles differing %0d | go->seq bank_free low: A %0d B %0d | timeouts %0d",
            K, GQ, SEED, go_cnt, go_a, go_b, cfg_cnt, xs_cnt, na_w, na_e, nb_w, nb_e, rec_mism, shift_bad, a_fault_c, a_fault_first, b_fault_c, b_fault_first,
            pend_a, pend_b, lds_a, lds_b, lds_shift_max, seq_diff, la_max, lb_max, timeouts);
        if (a_fault_c != 0) $display("COLROM_LOOP A_ILLEGAL (the schedule is not legal without the stage either)");
        if (a_fault_c == 0 && b_fault_c == 0 && rec_mism == 0 && shift_bad == 0 && na_w == nb_w && na_e == nb_e && na_w + na_e > 0 && go_a == NOPS && go_b == NOPS && timeouts == 0 && lds_a == lds_b)
            $display("COLROM_LOOP PASS");
        else $display("COLROM_LOOP FAIL");
        $finish;
    end
    initial begin #3000000; $display("COLROM_LOOP FAIL (global timeout)"); $finish; end
endmodule
