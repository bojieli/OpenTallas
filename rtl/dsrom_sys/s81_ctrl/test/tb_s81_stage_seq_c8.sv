`timescale 1ns/1ps
// tb_s81_stage_seq_c8 (s81-die-rtl-bind 2026-10-14, die item F4): the S81 layer1 stage sequencer MASTER dsfd_stage_seq_c8
// (engines 0..7 on die pins, 8..11 absent) at its die pins, two clocks (ck 1.2 GHz stream, ckv 0.9 GHz serial), running
// a real stage program (tools/s81_ctrl/stage_programs.py hex, +prog=<hex> +nops=<n>) for NJOB kit jobs.
//   program load: f_pw / f_plen on ckv (as the host cfg path, one write every 8 ckv cycles); kit start f_ks (ckv); done t_kd (ckv); status t_st (ckv).
//   engines 0..7: behavioural dataflow ports on the stream clock -- a descriptor c<e> = {v, {slot, user 10, tok 21,
//   pos 21, arg 24, op 7}} is queued; the op starts when its in-stage predecessors have ended (actual ends), runs dur
//   cycles, and its done {v, tag {slot, op}} returns on d<e> (one per port per cycle); s<e> = {online 1, fault 0}.
// PASS (default): NJOB t_kd done pulses, every op of every job started exactly once, every descriptor on the port the
//   program names with the job's context, no fault in t_st.
// +expect_fault=8: PASS iff t_st reports fault with code 8 (an op routed to an engine this die has no pins for) and no
//   job completes -- the fail-closed check of a program that is wrong for this die.
module tb_s81_stage_seq_c8;
    parameter integer NOPS = 128, NJOB = 2;
    localparam integer OPW = 7, NE = 8, CMDW = 84;
    reg ck = 0, ckv = 0, rst = 0, rsv = 0;
    always #0.41667 ck = ~ck;
    always #0.55556 ckv = ~ckv;
    reg  [52:0] f_ks = 0; wire [53:0] t_kd; reg [35:0] f_pw = 0; reg [7:0] f_plen = 0; wire [5:0] t_st;
    wire [84:0] c [0:NE-1]; reg [8:0] d [0:NE-1]; wire [1:0] s [0:NE-1];
    genvar g;
    generate for (g = 0; g < NE; g = g + 1) begin : g_s assign s[g] = 2'b10; end endgenerate
    dsfd_stage_seq_c8 #(.NOPS(NOPS)) dut (.ckv(ckv), .rsv(rsv), .ck(ck), .rst(rst), .f_ks(f_ks), .t_kd(t_kd), .f_pw(f_pw),
        .f_plen(f_plen), .t_st(t_st),
        .c0(c[0]), .c1(c[1]), .c2(c[2]), .c3(c[3]), .c4(c[4]), .c5(c[5]), .c6(c[6]), .c7(c[7]),
        .d0(d[0]), .d1(d[1]), .d2(d[2]), .d3(d[3]), .d4(d[4]), .d5(d[5]), .d6(d[6]), .d7(d[7]),
        .s0(s[0]), .s1(s[1]), .s2(s[2]), .s3(s[3]), .s4(s[4]), .s5(s[5]), .s6(s[6]), .s7(s[7]));

    reg [159:0] img [0:NOPS-1];
    integer n, port [0:NOPS-1], dur [0:NOPS-1], np [0:NOPS-1], pr [0:NOPS-1][0:7];
    integer i, j, e, k, expect_fault = 0;
    string prog;
    // per (slot, op) state of the job currently in that slot
    integer st_ [0:1][0:NOPS-1], en_ [0:1][0:NOPS-1], has_ [0:1][0:NOPS-1];
    integer slotjob [0:1];
    integer q [0:NE-1][0:255], qh [0:NE-1], qt [0:NE-1];          // queued {slot*NOPS + op}
    integer dq [0:NE-1][0:255], dh [0:NE-1], dt [0:NE-1];
    integer fseen = -1;
    integer cyc = 0, started = 0, ctx_bad = 0, dup = 0, kd_n = 0, nxt = 0, loaded = 0, kd_prev = 0;

    initial begin
        if (!$value$plusargs("prog=%s", prog)) $fatal(1, "+prog=<hex> required");
        if (!$value$plusargs("nops=%d", n)) $fatal(1, "+nops=<n> required");
        if (!$value$plusargs("expect_fault=%d", expect_fault)) expect_fault = 0;
        for (i = 0; i < NOPS; i = i + 1) img[i] = 0;
        $readmemh(prog, img);
        for (i = 0; i < n; i = i + 1) begin
            port[i] = img[i][143:140]; dur[i] = img[i][139:116]; np[i] = img[i][91:88];
            for (j = 0; j < 8; j = j + 1) pr[i][j] = img[i][87 - 8*j -: 8];
        end
        for (k = 0; k < 2; k = k + 1) begin slotjob[k] = -1; for (i = 0; i < NOPS; i = i + 1) begin st_[k][i] = -1; en_[k][i] = -1; has_[k][i] = 0; end end
        for (e = 0; e < NE; e = e + 1) begin qh[e] = 0; qt[e] = 0; dh[e] = 0; dt[e] = 0; d[e] = 0; end
        repeat (6) @(posedge ckv);
        rst = 1; rsv = 1;
        repeat (8) @(posedge ckv);
        f_plen = n[7:0];
        for (i = 0; i < n; i = i + 1) begin
            @(negedge ckv); f_pw = {1'b1, 7'(i), 4'(port[i]), 24'(i) ^ 24'h5A0000};
            @(negedge ckv); f_pw = 0;                     // the host paces program writes (f_pw has no ready: the
            repeat (6) @(negedge ckv);                    // sequencer's 4-deep crossing FIFO overflow is a fault)
        end
        @(negedge ckv); f_pw = 0;
        repeat (40) @(posedge ckv);
        loaded = 1;
    end
    // kit side (serial clock): offer job nxt once the previous job's done came back (one job in flight); count dones
    integer clr = -1, rt_n = 0, hop_bad = 0, hops = 0;
    integer kdc [0:7], hope [0:7], nhe [0:7];
    initial for (i = 0; i < 8; i = i + 1) begin kdc[i] = -1; hope[i] = -1; nhe[i] = -1; end
    always @(negedge ckv) if (loaded) begin
        f_ks <= 0;
        if (t_kd[53]) begin kd_n = kd_n + 1; kdc[kd_n - 1] = cyc; end
        else if (nxt < NJOB && nxt == kd_n) begin
            f_ks <= {1'b1, 10'(nxt + 3), 21'(1000 + nxt), 21'(1048575 - nxt)};
            nxt = nxt + 1;
        end
    end
    // engines (stream clock)
    function integer ready(input integer sl, input integer op);
        integer m, r;
        begin
            r = 1;
            for (m = 0; m < np[op]; m = m + 1) if (en_[sl][pr[op][m]] < 0 || en_[sl][pr[op][m]] > cyc) r = 0;
            ready = r;
        end
    endfunction
    always @(negedge ck) if (loaded) begin
        cyc = cyc + 1;
        for (e = 0; e < NE; e = e + 1) if (c[e][84]) begin : rx
            reg [CMDW-1:0] cd; integer sl, op;
            cd = c[e][83:0]; sl = cd[CMDW-1]; op = cd[OPW-1:0];
            if (op >= n || port[op] != e || cd[OPW +: 24] != (24'(op) ^ 24'h5A0000)) ctx_bad = ctx_bad + 1;
            else begin
                if (has_[sl][op]) dup = dup + 1;
                has_[sl][op] = 1; q[e][qt[e] % 256] = sl * NOPS + op; qt[e] = qt[e] + 1;
            end
        end
        for (e = 0; e < NE; e = e + 1) begin : eng
            integer go, x, sl2, op2;
            go = 1;
            while (go && qh[e] != qt[e]) begin
                x = q[e][qh[e] % 256]; sl2 = x / NOPS; op2 = x % NOPS;
                if (ready(sl2, op2)) begin st_[sl2][op2] = cyc; en_[sl2][op2] = cyc + dur[op2]; started = started + 1; qh[e] = qh[e] + 1; end
                else go = 0;
            end
        end
        for (k = 0; k < 2; k = k + 1) for (i = 0; i < n; i = i + 1)
            if (has_[k][i] && en_[k][i] == cyc) begin dq[port[i]][dt[port[i]] % 256] = k * NOPS + i; dt[port[i]] = dt[port[i]] + 1; end
        for (e = 0; e < NE; e = e + 1) begin
            d[e] <= 9'd0;
            if (dh[e] != dt[e]) begin : rep
                integer y;
                y = dq[e][dh[e] % 256]; dh[e] = dh[e] + 1;
                d[e] <= {1'b1, 1'(y / NOPS), 7'(y % NOPS)};
                // the job of slot y / NOPS: the oldest unretired job or the next one.  KDX 7: the kit done follows the job's
                // last NON-hop completion by a fixed latency (it never waits for the hop op)
                if (e == 7) hope[(rt_n + (((y / NOPS) != (rt_n % 2)) ? 1 : 0))] = cyc;
                else nhe[(rt_n + (((y / NOPS) != (rt_n % 2)) ? 1 : 0))] = cyc;
            end
        end
        // a slot is cleared when its job RETIRES (every op incl. the hop done), not at the kit done (KDX: the kit done
        // comes before the hop op completes)
        if (dut.u_s.u_seq.job_done) begin rt_n = rt_n + 1; clr = (rt_n - 1) % 2; end
        if (clr >= 0) begin for (i = 0; i < NOPS; i = i + 1) begin has_[clr][i] = 0; en_[clr][i] = -1; st_[clr][i] = -1; end clr = -1; end
        if (t_st[5] && fseen < 0) fseen = cyc;           // status word: fault bit and first code settle within a few ckv
        if ((kd_n == NJOB && rt_n == NJOB) || (expect_fault != 0 && fseen >= 0 && cyc > fseen + 24) || cyc > 600000) begin : fin
            integer pass, j;
            // KDX 7: every job's kit done precedes its hop op's completion (the kit sends the HIDDEN after its done)
            // (LAT 40 stream cycles: done pin flops + the ck -> ckv crossing; the hop is >= 1,006 cycles in every program)
            for (j = 0; j < NJOB; j = j + 1) if (hope[j] >= 0) begin
                hops = hops + 1;
                if (!(kdc[j] >= 0 && ((nhe[j] >= 0) ? (kdc[j] <= nhe[j] + 40) : (kdc[j] < hope[j])))) begin
                    hop_bad = hop_bad + 1; $display("KD job %0d kd=%0d last_non_hop_end=%0d hop_end=%0d", j, kdc[j], nhe[j], hope[j]);
                end
            end
            if (expect_fault != 0)
                pass = t_st[5] && t_st[4:1] == 4'(expect_fault) && kd_n == 0;
            else
                pass = kd_n == NJOB && rt_n == NJOB && started == n * NJOB && ctx_bad == 0 && dup == 0 && !t_st[5] && hop_bad == 0;
            $display("TB_S81_STAGE_SEQ_C8 prog=%s nops=%0d jobs=%0d/%0d retired=%0d started=%0d/%0d ctx_bad=%0d dup=%0d hops=%0d kd_waited=%0d fault=%0d code=%0d expect_fault=%0d cyc=%0d %s",
                     prog, n, kd_n, NJOB, rt_n, started, n * NJOB, ctx_bad, dup, hops, hop_bad, t_st[5], t_st[4:1], expect_fault, cyc, pass ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
