import sys
s = open(sys.argv[1]).read()
def r(a, b, cnt=1):
    global s
    n = s.count(a)
    if n != cnt: raise SystemExit('count %d != %d: %r' % (n, cnt, a[:90]))
    s = s.replace(a, b)
r('''// S81-L20RD2 (10-20): exact + throughput gate of the PAIRED index reader dsdv_idx_rg2 (die plan --idxrd 3) at production
//   shape: 8 x dsdv_idx_rg2 on the query / score chains (reader p = regions 2p, 2p + 1; rqi0/rdi0 = controller 2p,
//   rqi1/rdi1 = controller 2p + 1) -- derived from tb_dsdv_idx_rg (S81-IDXRD 10-18), checks unchanged:
//   16 x dsfd_ctrl_rg2 (UNCHANGED regional HBM''',
'''// S81-IDX3R (10-20, MU.BAL.SX.3): exact + throughput gate of the NON-INLINE paired index reader dsdv_idx_rg3 at the
//   mu7 production shape -- generated from tb_dsdv_idx_rg2 (S81-L20RD3) by results/rtl/s81_idx3r_1020/mk_tb3.py:
//   8 x dsdv_idx_rg3 in two corner-strip groups (W readers 0..3, E readers 4..7) as static-slot clients of
//   16 x dsfd_ctrl_rg3 (rg2 + reader lanes); svc traffic drives the controllers' rq / rd directly.  The die's relay
//   stations are modelled as registered hops: SD[p] stations each way on reader p's 4 request + 4 response lanes
//   (pair distance 1.07 / 3.19 / 5.31 / 7.43 mm at 405 um: 3 / 8 / 13 / 18; +SDX= extra stations on every lane) and
//   XD (21) stations on the query + score chains between the W and E groups (8.5 mm crossing).
//   +SLOTHIT=1: one slice word inside the reader window (a schedule violation) -> the controller fault must FAIL it.
//   +SLICE2=1 (default): the slice phase runs again after the window (svc resumes on the controllers).
//   Former rg2 bench text (checks unchanged):
//   16 x dsfd_ctrl_rg2 (UNCHANGED regional HBM''')
r('module tb_dsdv_idx_rg2;', 'module tb_dsdv_idx_rg3;')
r('''    integer OPEN = 0;                      // S81-L20DIE: spec om (open lanes 1..3 -> no HDR / empty BEAT expected)''',
  '''    integer OPEN = 0;                      // S81-L20DIE: spec om (open lanes 1..3 -> no HDR / empty BEAT expected)
    integer SLOTHIT = 0, SLICE2 = 1;''')
r('''        void'($value$plusargs("SLICE=%d", SLICE)); void'($value$plusargs("OPEN=%d", OPEN));''',
  '''        void'($value$plusargs("SLICE=%d", SLICE)); void'($value$plusargs("OPEN=%d", OPEN));
        void'($value$plusargs("SLOTHIT=%d", SLOTHIT)); void'($value$plusargs("SLICE2=%d", SLICE2));''')
r('''    parameter integer DQC = 8;
    parameter integer DQR = 8;''', '''    parameter integer DQC = 8;
    parameter integer DQR = 24;            // reader budget = controller landing FIFO entries (RFD)
    parameter integer CMUT = 0;            // dsfd_ctrl_rg3 MUT
    parameter integer XD = 21;             // W -> E chain crossing stations
    parameter integer SDX = 0;             // extra lane stations (latency sweep)''')
# DUT chain
r('''    wire [681:0] rq_s [0:R-1], rq_c [0:R-1];
    wire [561:0] rd_c [0:R-1], rd_s [0:R-1];''', '''    wire [561:0] rd_c [0:R-1], rd_s [0:R-1];
    wire [91:0]  lrq_r [0:R-1], lrq_c [0:R-1];      // request lanes at the reader / at the controller
    wire [543:0] lrd_c [0:R-1], lrd_r [0:R-1];      // response lanes at the controller / at the reader
    function automatic integer sd_of(input integer p_); sd_of = SDX + ((p_ < 4) ? 3 + 5 * p_ : 3 + 5 * (7 - p_)); endfunction
    wire [512:0] qx; wire [275:0] sx;              // W -> E crossing outputs''')
r('''        dsdv_idx_rg2 #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .DQ(DQR), .SQD(SQD), .IQD(IQD)) u (
            .ck(ck), .rst(rst), .sid(4'(2 * r)), .qi(qch[r]), .qo(qch[r + 1]), .si(sch[r]), .so(sch[r + 1]),
            .rqi0(rq_tb[2 * r]), .rqo0(rq_c[2 * r]), .rdi0(rd_c[2 * r]), .rdo0(rd_s[2 * r]),
            .rqi1(rq_tb[2 * r + 1]), .rqo1(rq_c[2 * r + 1]), .rdi1(rd_c[2 * r + 1]), .rdo1(rd_s[2 * r + 1]), .st(st[r]));
    end endgenerate''', '''        wire [512:0] qi_ = (r == 4) ? qx : qch[r];
        wire [275:0] si_ = (r == 4) ? sx : sch[r];
        dsdv_idx_rg3 #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .SQD(SQD), .IQD(IQD)) u (
            .ck(ck), .rst(rst), .sid(4'(2 * r)), .qi(qi_), .qo(qch[r + 1]), .si(si_), .so(sch[r + 1]),
            .rqo({lrq_r[2 * r + 1], lrq_r[2 * r]}), .rri({lrd_r[2 * r + 1], lrd_r[2 * r]}), .st(st[r]));
        // relay stations (registered hops) on the lanes of both controllers of the pair
        tb_idx3_dly #(.W(92),  .D(sd_of(r))) u_q0 (.ck(ck), .d(lrq_r[2 * r]),     .q(lrq_c[2 * r]));
        tb_idx3_dly #(.W(92),  .D(sd_of(r))) u_q1 (.ck(ck), .d(lrq_r[2 * r + 1]), .q(lrq_c[2 * r + 1]));
        tb_idx3_dly #(.W(544), .D(sd_of(r))) u_d0 (.ck(ck), .d(lrd_c[2 * r]),     .q(lrd_r[2 * r]));
        tb_idx3_dly #(.W(544), .D(sd_of(r))) u_d1 (.ck(ck), .d(lrd_c[2 * r + 1]), .q(lrd_r[2 * r + 1]));
    end endgenerate
    tb_idx3_dly #(.W(513), .D(XD)) u_xq (.ck(ck), .d(qch[4]), .q(qx));
    tb_idx3_dly #(.W(276), .D(XD)) u_xs (.ck(ck), .d(sch[4]), .q(sx));''')
r('''        dsfd_ctrl_rg2 #(.DQ(DQC)) u_c (.clk(ck), .ckh(ckh), .rst_n(rst), .rq(rq_c[r]), .rd(rd_c[r]), .ck_o(ck_o_unused),''',
  '''        dsfd_ctrl_rg3 #(.DQ(DQC), .RFD(DQR), .MUT(CMUT)) u_c (.clk(ck), .ckh(ckh), .rst_n(rst), .rq(rq_tb[r]), .rd(rd_c[r]),
            .ck_o(ck_o_unused), .rrq(lrq_c[r]), .rrd(lrd_c[r]),''')
r('''            .kr_data(kr_data[512 * r +: 512]));
    end endgenerate''', '''            .kr_data(kr_data[512 * r +: 512]));
        assign rd_s[r] = rd_c[r];
    end endgenerate''')
# qo forwarding check: + XD
r('''    reg [512:0] qdl [0:31];''', '''    reg [512:0] qdl [0:63];''')
r('''        qdl[0] <= qin; for (i = 1; i < 32; i = i + 1) qdl[i] <= qdl[i - 1];
        if (rst && cyc > 40 && qch[NRD][0] !== qdl[2 * NRD - 1][0] || (qch[NRD][0] && qch[NRD] !== qdl[2 * NRD - 1])) qerr = qerr + 1;''',
  '''        qdl[0] <= qin; for (i = 1; i < 64; i = i + 1) qdl[i] <= qdl[i - 1];
        if (rst && cyc > 80 && qch[NRD][0] !== qdl[2 * NRD + XD - 1][0] || (qch[NRD][0] && qch[NRD] !== qdl[2 * NRD + XD - 1])) qerr = qerr + 1;''')
# slice phase -> task, run before and after
r('''        // slice phase: NS reads per PC, tags [16:15] = 0
        if (SLICE != 0) begin''', '''        // slice phase: NS reads per PC, tags [16:15] = 0
        if (SLICE != 0) slice_phase();
        job_on = 1;
        // a non-index frame (type 1, len 3): skipped by every region, forwarded
        if (0) begin''')
r('''        job_on = 1;
        // a non-index frame (type 1, len 3): skipped by every region, forwarded
        @(negedge ck); qin = {512'd0, 1'b1};''', '''        end
        @(negedge ck); qin = {512'd0, 1'b1};''')
r('''        @(negedge ck); qin = 0; t_end = cyc;''', '''        @(negedge ck); qin = 0; t_end = cyc;
        // SLOTHIT: one slice read on controller 0 PC 0 inside the reader window (its rq is a reader slot there now)
        if (SLOTHIT != 0) begin
            repeat (40) @(negedge ck);
            rq_tb[0][340:0] = {256'd0, 32'd0, 17'h00123, 4'd1, 30'(SL0), 1'b0, 1'b1};
            @(negedge ck); rq_tb[0] = 682'd0;
        end''')
r('''        if (vin_f) begin fail = 1; $display("TB_IDXRD selector V-ingress protocol fault"); end''',
  '''        if (vin_f) begin fail = 1; $display("TB_IDXRD selector V-ingress protocol fault"); end
        for (a = 0; a < R; a = a + 1) if (rd_c[a][561] || !rd_c[a][560]) begin
            fail = 1; $display("TB_IDXRD controller %0d status {fault, live} %b", a, rd_c[a][561:560]);
        end
        job_on = 0;
        if (SLICE != 0 && SLICE2 != 0) slice_phase();''')
# the slice phase body becomes a task: extract text between 'if (0) begin' and its end marker is messy; define task explicitly
task = '''    task automatic slice_phase();
        integer k_, a, b, ln_;
        for (k_ = 0; k_ < NS; k_ = k_ + 1) begin
            @(negedge ck);
            for (a = 0; a < R; a = a + 1) for (b = 0; b < 2; b = b + 1) begin
                ln_ = 1 + (k_ % 4);
                rq_tb[a][341 * b +: 341] = {256'd0, 32'd0, {2'b00, 4'(a), 1'(b), 10'(k_)}, 4'(ln_), 30'(SL0 + 8 * k_), 1'b0, 1'b1};
                s_exp[a][b] = s_exp[a][b] + ln_;
                s_rkx[a][b] = s_rkx[a][b] + 1;
            end
            @(negedge ck); for (a = 0; a < R; a = a + 1) rq_tb[a] = 682'd0;
        end
        repeat (1500) @(posedge ck);
        for (a = 0; a < R; a = a + 1) for (b = 0; b < 2; b = b + 1)
            if (s_rv[a][b] != s_exp[a][b] || s_rk[a][b] != s_rkx[a][b]) begin
                s_err = s_err + 1;
                if (s_err <= 8) $display("TB_IDXRD SLICE-COUNT-ERR r %0d pc %0d rv %0d/%0d rk %0d/%0d", a, b, s_rv[a][b], s_exp[a][b], s_rk[a][b], s_rkx[a][b]);
            end
    endtask
'''
r('''    // ------------------------------------------------------------------ stimulus''', task + '''    // ------------------------------------------------------------------ stimulus''')
r('''    integer s_rv [0:R-1][0:1], s_rk [0:R-1][0:1], s_exp [0:R-1][0:1], s_err = 0;''',
  '''    integer s_rv [0:R-1][0:1], s_rk [0:R-1][0:1], s_exp [0:R-1][0:1], s_rkx [0:R-1][0:1], s_err = 0;''')
r('''        for (int b = 0; b < 2; b++) begin s_rv[a][b] = 0; s_rk[a][b] = 0; s_exp[a][b] = 0; end''',
  '''        for (int b = 0; b < 2; b++) begin s_rv[a][b] = 0; s_rk[a][b] = 0; s_exp[a][b] = 0; s_rkx[a][b] = 0; end''')
r('''        $display("TB_IDXRD_STATS gather %0d N %0d''', '''        $display("TB_IDXRD_STATS3 sdx %0d xd %0d dqr %0d cmut %0d slothit %0d", SDX, XD, DQR, CMUT, SLOTHIT);
        $display("TB_IDXRD_STATS gather %0d N %0d''')
s += '''
// registered hops (relay stations) of the bench's die-link model; D = 0 is a wire
module tb_idx3_dly #(parameter integer W = 1, parameter integer D = 1) (input wire ck, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if (D == 0) begin : g_w
        assign q = d;
    end else begin : g_r
        reg [W-1:0] sr [0:D-1];
        integer i;
        initial for (i = 0; i < D; i = i + 1) sr[i] = '0;
        always @(posedge ck) begin sr[0] <= d; for (i = 1; i < D; i = i + 1) sr[i] <= sr[i - 1]; end
        assign q = sr[D-1];
    end endgenerate
endmodule
'''
open(sys.argv[2], 'w').write(s)
