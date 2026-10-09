`timescale 1ns/1ps
// tb_s81_stage_seq (stream ds-control, 2026-10-08): exactness bench of ot_s81_stage_seq against the golden program
// trace of one S81 stage (tools/s81_ctrl/stage_programs.py hex image, +prog=<file> +nops=<n>).
//
// The engines are behavioural dataflow ports: a port receives descriptors (after L_CMD cycles of die wire / stations),
// keeps them in order, and starts its oldest queued job at the first cycle at which (a) its descriptor is there and
// (b) its inputs are present: the stage input + cross-stage inputs (t0 + ext) and the end of every in-stage
// predecessor (its ACTUAL end, so any lateness propagates).  Several queued jobs may start in one cycle (the
// composition overlaps them); a job ends dur cycles later; completions return one per port per cycle after L_DN cycles.
// NJOB jobs (users 0..NJOB-1) run back to back: job k's HIDDEN header (job_v) is offered as soon as the sequencer
// takes it, its stage input lands HLEAD cycles later or one cycle after job k-1's job_done (the package controller
// starts a job only on a free core), whichever is later.
// PASS: every job of every stage job starts exactly at t0 + its golden start (zero cycles added by the sequencer),
// every descriptor carries its job's context and op, job_done fires DONE_LAT after the job's last completion arrives
// (reported, constant), no fault.
module tb_s81_stage_seq;
    parameter integer NOPS = 128, NENG = 12, QD = 4, FQ = 4, MUT = 0;
    parameter integer L_CMD = 4, L_DN = 4, HLEAD = 640, NJOB = 3;
    localparam integer OPW = $clog2(NOPS), ARGW = 24, USER_W = 10, NW = 21;
    localparam integer CMDW = 1 + USER_W + 2 * NW + ARGW + OPW, TAGW = 1 + OPW, PEW = 4 + ARGW;

    reg clk = 0, rst_n = 0, loaded = 0;
    always #0.4166 clk = ~clk;

    reg              pw_v = 0; reg [OPW-1:0] pw_a = 0; reg [PEW-1:0] pw_d = 0;
    reg  [OPW:0]     prog_len = 0;
    reg              job_v = 0; wire job_rdy;
    reg  [USER_W-1:0] job_user = 0; reg [NW-1:0] job_pos = 0, job_tok = 0;
    wire             job_done;
    wire [NENG-1:0]  cmd_v; wire [NENG*CMDW-1:0] cmd_d;
    reg  [NENG-1:0]  dn_v = 0; reg [NENG*TAGW-1:0] dn_tag = 0;
    wire             busy, fault; wire [3:0] fault_code; wire [31:0] st_jobs, st_cmds, st_cs;

    ot_s81_stage_seq #(.NOPS(NOPS), .NENG(NENG), .QD(QD), .FQ(FQ), .MUT(MUT)) dut (
        .clk(clk), .rst_n(rst_n), .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d), .prog_len(prog_len),
        .job_v(job_v), .job_rdy(job_rdy), .job_user(job_user), .job_pos(job_pos), .job_tok(job_tok), .job_done(job_done),
        .cmd_v(cmd_v), .cmd_d(cmd_d), .dn_v(dn_v), .dn_tag(dn_tag), .busy(busy), .fault(fault), .fault_code(fault_code),
        .st_jobs(st_jobs), .st_cmds(st_cmds), .st_credit_stall(st_cs));

    // ---- program (golden trace) ----
    reg [159:0] img [0:NOPS-1];
    integer n, port [0:NOPS-1], dur [0:NOPS-1], ext [0:NOPS-1], np [0:NOPS-1], pr [0:NOPS-1][0:7], gst [0:NOPS-1];
    string prog;
    integer i, j, k, e;
    // ---- per job state ----
    integer t0 [0:NJOB-1], hdr_t [0:NJOB-1], done_t [0:NJOB-1], last_end [0:NJOB-1], last_dn [0:NJOB-1];
    integer ast [0:NJOB-1][0:NOPS-1], aend [0:NJOB-1][0:NOPS-1], cmd_at [0:NJOB-1][0:NOPS-1];
    integer slotjob [0:1];
    integer cyc = 0, late = 0, early_bad = 0, ctx_bad = 0, started = 0, jobs_acc = 0, jobs_done = 0;
    integer worst_margin = 1 << 30;      // min over jobs of (golden start - descriptor arrival)
    // ---- port models ----
    integer q [0:NENG-1][0:NOPS*NJOB-1];     // queued {job*NOPS+op}
    integer qh [0:NENG-1], qt [0:NENG-1];
    integer dq [0:NENG-1][0:NOPS*NJOB-1];    // completions to report
    integer dh [0:NENG-1], dt [0:NENG-1];
    // delay lines
    reg [NENG-1:0] cv_d [0:L_CMD]; reg [NENG*CMDW-1:0] cd_d [0:L_CMD];
    reg [NENG-1:0] dv_d [0:L_DN];  reg [NENG*TAGW-1:0] dtg_d [0:L_DN];

    function integer ready_at(input integer jb, input integer op);
        integer r, m;
        begin
            r = (t0[jb] < 0) ? (1 << 30) : t0[jb] + ext[op];
            for (m = 0; m < np[op]; m = m + 1)
                r = (aend[jb][pr[op][m]] < 0) ? (1 << 30) : ((aend[jb][pr[op][m]] > r) ? aend[jb][pr[op][m]] : r);
            ready_at = r;
        end
    endfunction

    initial begin
        if (!$value$plusargs("prog=%s", prog)) $fatal(1, "+prog=<hex> required");
        if (!$value$plusargs("nops=%d", n)) $fatal(1, "+nops=<n> required");
        for (i = 0; i < NOPS; i = i + 1) img[i] = 0;
        $readmemh(prog, img);
        for (i = 0; i < n; i = i + 1) begin
            port[i] = img[i][143:140]; dur[i] = img[i][139:116]; ext[i] = img[i][115:92]; np[i] = img[i][91:88];
            for (j = 0; j < 8; j = j + 1) pr[i][j] = img[i][87 - 8*j -: 8];
            gst[i] = img[i][23:0];
        end
        for (k = 0; k < NJOB; k = k + 1) begin
            t0[k] = -1; hdr_t[k] = -1; done_t[k] = -1; last_end[k] = -1; last_dn[k] = -1;
            for (i = 0; i < NOPS; i = i + 1) begin ast[k][i] = -1; aend[k][i] = -1; cmd_at[k][i] = -1; end
        end
        for (e = 0; e < NENG; e = e + 1) begin qh[e] = 0; qt[e] = 0; dh[e] = 0; dt[e] = 0; end
        for (i = 0; i <= L_CMD; i = i + 1) begin cv_d[i] = 0; cd_d[i] = 0; end
        for (i = 0; i <= L_DN; i = i + 1) begin dv_d[i] = 0; dtg_d[i] = 0; end
        slotjob[0] = -1; slotjob[1] = -1;
        prog_len = n[OPW:0];
        repeat (4) @(posedge clk);
        rst_n = 1;
        // program load through the cfg path
        for (i = 0; i < n; i = i + 1) begin
            @(negedge clk); pw_v = 1; pw_a = i[OPW-1:0]; pw_d = {port[i][3:0], 24'(i) ^ 24'h5A0000};
        end
        @(negedge clk); pw_v = 0;
        repeat (4) @(posedge clk);
        loaded = 1;
    end

    // ---- everything below runs on the falling edge: DUT outputs are stable, inputs are set up for the next edge ----
    integer nxt = 0;
    always @(negedge clk) if (loaded) begin
        cyc = cyc + 1;
        // job offer: one-cycle job_v when the sequencer is ready (taken at the next rising edge)
        job_v = 0;
        if (nxt < NJOB && job_rdy && cyc > 4) begin
            job_v = 1; job_user = nxt[USER_W-1:0] + 10'd3; job_pos = 21'd1048575 - nxt[20:0]; job_tok = 21'(1000 + nxt);
            hdr_t[nxt] = cyc; slotjob[nxt % 2] = nxt; jobs_acc = jobs_acc + 1; nxt = nxt + 1;
        end
        // stage input: HLEAD after the header, and after the previous job's job_done (core free)
        for (k = 0; k < NJOB; k = k + 1)
            if (t0[k] < 0 && hdr_t[k] >= 0 && cyc >= hdr_t[k] + HLEAD && (k == 0 || (done_t[k-1] >= 0 && cyc > done_t[k-1])))
                t0[k] = cyc;
        // descriptors arriving after L_CMD
        for (e = 0; e < NENG; e = e + 1) if (cv_d[L_CMD][e]) begin : rx
            reg [CMDW-1:0] c; integer s_, op_, jb_;
            c = cd_d[L_CMD][e*CMDW +: CMDW];
            s_ = c[CMDW-1]; op_ = c[OPW-1:0]; jb_ = slotjob[s_];
            if (jb_ < 0 || op_ >= n || port[op_] != e) begin ctx_bad = ctx_bad + 1; end
            else begin
                if (c[CMDW-2 -: USER_W] != USER_W'(jb_ + 3) || c[CMDW-2-USER_W -: NW] != NW'(1048575 - jb_) ||
                    c[OPW +: ARGW] != (24'(op_) ^ 24'h5A0000)) ctx_bad = ctx_bad + 1;
                cmd_at[jb_][op_] = cyc;
                q[e][qt[e]] = jb_ * NOPS + op_; qt[e] = qt[e] + 1;
            end
        end
        // engines: start in order whatever is ready
        for (e = 0; e < NENG; e = e + 1) begin : eng
            integer go, x, jb2, op2, r;
            go = 1;
            while (go && qh[e] != qt[e]) begin
                x = q[e][qh[e]]; jb2 = x / NOPS; op2 = x % NOPS;
                r = ready_at(jb2, op2);
                if (r <= cyc) begin
                    ast[jb2][op2] = cyc; aend[jb2][op2] = cyc + dur[op2]; started = started + 1;
                    if (cyc != t0[jb2] + gst[op2]) late = late + 1;
                    if (t0[jb2] + gst[op2] - cmd_at[jb2][op2] < worst_margin) worst_margin = t0[jb2] + gst[op2] - cmd_at[jb2][op2];
                    if (aend[jb2][op2] > last_end[jb2]) last_end[jb2] = aend[jb2][op2];
                    qh[e] = qh[e] + 1;
                end else go = 0;
            end
        end
        // completions: any job that ends now goes to its port's report queue
        for (k = 0; k < NJOB; k = k + 1)
            for (i = 0; i < n; i = i + 1)
                if (aend[k][i] == cyc) begin dq[port[i]][dt[port[i]]] = k * NOPS + i; dt[port[i]] = dt[port[i]] + 1; end
        for (e = 0; e < NENG; e = e + 1) begin
            dv_d[0][e] = 0;
            if (dh[e] != dt[e]) begin : rep
                integer y;
                y = dq[e][dh[e]]; dh[e] = dh[e] + 1;
                dv_d[0][e] = 1; dtg_d[0][e*TAGW +: TAGW] = {1'((y / NOPS) % 2), OPW'(y % NOPS)};
                if (cyc > last_dn[y / NOPS]) last_dn[y / NOPS] = cyc;
            end
        end
        if (job_done) begin
            for (k = 0; k < NJOB; k = k + 1) if (done_t[k] < 0 && t0[k] >= 0) begin done_t[k] = cyc; jobs_done = jobs_done + 1; k = NJOB; end
        end
        // delay lines (descriptor from the sequencer's command register; completion to the sequencer's pins)
        for (i = L_CMD; i > 0; i = i - 1) begin cv_d[i] = cv_d[i-1]; cd_d[i] = cd_d[i-1]; end
        cv_d[0] = cmd_v; cd_d[0] = cmd_d;
        dn_v = dv_d[L_DN]; dn_tag = dtg_d[L_DN];
        for (i = L_DN; i > 0; i = i - 1) begin dv_d[i] = dv_d[i-1]; dtg_d[i] = dtg_d[i-1]; end
        if (jobs_done == NJOB || cyc > 400000) begin : fin
            integer dl, pass;
            dl = (jobs_done == NJOB) ? done_t[NJOB-1] - last_end[NJOB-1] : -1;
            pass = (jobs_done == NJOB) && started == n * NJOB && late == 0 && ctx_bad == 0 && !fault;
            $display("TB_S81_STAGE_SEQ prog=%s nops=%0d jobs=%0d/%0d started=%0d/%0d late=%0d ctx_bad=%0d fault=%0d code=%0d done_lat=%0d worst_margin=%0d credit_stall=%0d makespan0=%0d t0=%0d,%0d,%0d %s",
                     prog, n, jobs_done, NJOB, started, n * NJOB, late, ctx_bad, fault, fault_code, dl, worst_margin, st_cs,
                     last_end[0] - t0[0], t0[0], (NJOB > 1) ? t0[1] : -1, (NJOB > 2) ? t0[2] : -1, pass ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
