`timescale 1ns/1ps
// MU-QWEN-HOST 10-19: qkd_host_ctl MU 1 (ot_qfd_pkgctl MU 1, the 4-slot static calendar) behavioural bench.
// Main run: 4 users x 100 positions = 400 steps, issued as soon as the user's previous step retired and fewer than
// 4 steps are outstanding.  Every die reports each generation once, in issue order, after its own random latency
// (3..40 edges, monotone per die).  Checks every edge:
//   - hc start: generation = previous + 1, user on hc pos[17:16] = the issuing user (kv_base / 1024), pos[15:0] and
//     token = the issued step;
//   - res done: a ONE-edge pulse per step, in issue order, only after all 8 dies reported it, with that step's
//     token/value, n_steps = retired count, fault 0;
//   - 4 steps outstanding is reached.
// Fault runs (each after reset; fail closed, never a stall: every outstanding step retires once with fault 1):
//   1 a die skips to the next (outstanding) generation -> die_fault;  2 token disagreement -> disagree;  3 a fifth outstanding start ->
//   start_unready;  4 dies stop reporting -> watchdog;  5 a die reports a generation never started -> die_fault.
module tb_qkd_host_ctl_mu;
    localparam integer ND=8, WDOG=400, NU=4, NPOS=100, NS=NU*NPOS;
    reg ck=0,rst_n=0,ready=0;
    always #0.4165 ck=~ck;
    reg [60:0] req=0;
    reg [142:0] pr=0;
    reg [ND*93-1:0] tk=0;
    wire [181:0] hc;
    wire [119:0] res;
    qkd_host_ctl #(.ND(ND),.WDOG(WDOG),.MU(1)) dut(.*);

    integer cyc=0, errors=0, mode=0, nstep=0;
    // issued steps (issue order == start order == generation order)
    integer is_n=0, st_n=0, rt_n=0, max_out=0, faults_seen=0, flush_pulses=0;
    integer s_user[0:NS+8], s_pos[0:NS+8], s_tok[0:NS+8], s_gen[0:NS+8], s_tstart[0:NS+8];
    integer rt[0:ND-1][0:NS+8];
    integer dp[0:ND-1], last_rt[0:ND-1];
    integer u_busy[0:NU-1], u_pos[0:NU-1], u_last[0:NU-1];
    integer rr_u=0, last_gen=0, d, k, u, lat, mx, g;
    reg stop_reports=0;
    integer inj_at=0;
    reg [3:0] first_bits=0;     // res[87:84] at the first fault retire: the CAUSE, not a later secondary fault
    function automatic [17:0] out_tok(input integer uu, input integer pp); out_tok = 18'(32'h20000 + uu*4096 + pp*5 + 3); endfunction
    function automatic [31:0] out_val(input integer uu, input integer pp); out_val = 32'h3f800000 + uu*65536 + pp; endfunction
    function automatic [17:0] in_tok(input integer uu, input integer pp);
        in_tok = (pp < 3) ? 18'(256*(uu+1) + pp + 5) : out_tok(uu, pp-1);
    endfunction

    task automatic clear_model;
        begin
            is_n=0; st_n=0; rt_n=0; max_out=0; faults_seen=0; flush_pulses=0; last_gen=0; rr_u=0; stop_reports=0; inj_at=0; first_bits=0;
            for (d=0; d<ND; d=d+1) begin dp[d]=0; last_rt[d]=0; end
            for (u=0; u<NU; u=u+1) begin u_busy[u]=0; u_pos[u]=0; end
        end
    endtask

    // die model + checkers, at the negedge (DUT outputs are flop outputs)
    always @(negedge ck) if (rst_n) begin
        cyc = cyc + 1;
        req[0] = 1'b0;
        // start seen by the dies
        if (hc[38]) begin
            g = hc[37:36];
            if (st_n >= is_n) begin errors=errors+1; if (errors<6) $display("ERR start without issue"); end
            else begin
                if (g != ((last_gen + 1) & 3) || hc[17:16] != 2'(s_user[st_n]) || hc[15:0] != 16'(s_pos[st_n]) ||
                    hc[35:18] != in_tok(s_user[st_n], s_pos[st_n])) begin
                    errors=errors+1;
                    if (errors<6) $display("ERR start %0d gen %0d/%0d user %0d/%0d pos %0d/%0d tok %h/%h", st_n, g,
                        (last_gen+1)&3, hc[17:16], s_user[st_n], hc[15:0], s_pos[st_n], hc[35:18], in_tok(s_user[st_n], s_pos[st_n]));
                end
                s_gen[st_n] = g; s_tstart[st_n] = cyc; last_gen = g;
                for (d=0; d<ND; d=d+1) begin
                    lat = 3 + ($urandom % 38);
                    rt[d][st_n] = (cyc + lat > last_rt[d]) ? cyc + lat : last_rt[d] + 1;
                    last_rt[d] = rt[d][st_n];
                end
                st_n = st_n + 1;
            end
        end
        if (st_n - rt_n > max_out) max_out = st_n - rt_n;
        // die reports (level words; one new generation per die per report)
        for (d=0; d<ND; d=d+1)
            if (mode==1 && d==3 && dp[d]==9 && rt[d][9] == cyc && st_n <= 10) rt[d][9] = cyc + 1;   // skip onto an OUTSTANDING gen
            else if (!stop_reports && dp[d] < st_n && rt[d][dp[d]] == cyc) begin
                k = dp[d];
                tk[d*93 +: 93] = {1'b1, 2'(s_gen[k]), 1'b1, 1'b0, 6'd0, out_tok(s_user[k], s_pos[k]), out_val(s_user[k], s_pos[k]), 32'(d)};
                if (mode==1 && d==3 && k==9) tk[d*93+90 +: 2] = 2'(s_gen[k]+1);          // skips a generation
                if (mode==2 && d==5 && k==7) tk[d*93+64 +: 18] = tk[d*93+64 +: 18] ^ 18'd1; // disagrees
                if (mode==5 && d==6 && k==4) tk[d*93+90 +: 2] = 2'(s_gen[k]+2);          // never-started generation
                dp[d] = dp[d] + 1;
            end
        // retire pulses
        if (res[0]) begin
            if (rt_n >= st_n) begin errors=errors+1; if (errors<6) $display("ERR done with nothing outstanding"); end
            else if (res[1]) begin
                if (!faults_seen) first_bits = res[87:84];
                faults_seen = 1; flush_pulses = flush_pulses + 1;
                if (mode==0) begin errors=errors+1; if (errors<6) $display("ERR fault in main run res=%h", res); end
                u_busy[s_user[rt_n]] = 0; rt_n = rt_n + 1;
            end else begin
                mx = 0; for (d=0; d<ND; d=d+1) if (rt[d][rt_n] > mx) mx = rt[d][rt_n];
                if (cyc <= mx || res[19:2] !== out_tok(s_user[rt_n], s_pos[rt_n]) || res[51:20] !== out_val(s_user[rt_n], s_pos[rt_n]) ||
                    res[119:88] !== 32'(rt_n+1)) begin
                    errors=errors+1;
                    if (errors<6) $display("ERR retire %0d at %0d (last report %0d) tok %h/%h n %0d", rt_n, cyc, mx, res[19:2],
                                           out_tok(s_user[rt_n], s_pos[rt_n]), res[119:88]);
                end
                u_busy[s_user[rt_n]] = 0; u_pos[s_user[rt_n]] = s_pos[rt_n] + 1;
                rt_n = rt_n + 1;
            end
        end
        // host model: issue the next free user (static: one step a user, at most 4 outstanding)
        // mode 3: with 4 steps outstanding (reports held so none retires), a broken host starts a fifth
        if (mode==3 && inj_at==0 && is_n >= 12 && is_n - rt_n == 4 && st_n == is_n) begin stop_reports = 1; inj_at = cyc + 10; end
        if (mode==3 && cyc == inj_at) req = {24'd0, 18'd777, 18'd777, 1'b1};
        else if (is_n < nstep && ($urandom % 4) != 0 && !(mode==3 && stop_reports)) begin
            for (k=0; k<NU; k=k+1) begin
                u = (rr_u + k) % NU;
                if (!u_busy[u] && u_pos[u] < NPOS && is_n - rt_n < 4 && !req[0]) begin
                    req = {24'(u*1024), 18'(u_pos[u]), in_tok(u, u_pos[u]), 1'b1};
                    s_user[is_n] = u; s_pos[is_n] = u_pos[u]; u_busy[u] = 1; is_n = is_n + 1; rr_u = (u + 1) % NU;
                end
            end
        end
        if (mode==4 && rt_n >= 10) stop_reports = 1;
        if (mode==3 && faults_seen) stop_reports = 0;
    end

    task tick; begin @(negedge ck); end endtask
    task do_reset; begin rst_n=0; req=0; tk=0; ready=0; repeat(4) tick; clear_model; rst_n=1; ready=1; repeat(4) tick; end endtask
    integer n, f_bit, starts_at_fault;
    initial begin
        // main run
        mode=0; nstep=NS; do_reset;
        n=0; while ((rt_n < NS) && n < 200000) begin tick; n=n+1; end
        repeat(50) tick;
        if (rt_n != NS || st_n != NS || max_out != 4 || res[1] || res[87:84] != 0) begin
            errors=errors+1; $display("ERR main run retired %0d started %0d max_out %0d res=%h", rt_n, st_n, max_out, res);
        end
        $display("MAIN users %0d steps %0d retired %0d max_outstanding %0d errors %0d", NU, st_n, rt_n, max_out, errors);
        // fault runs: the named fault, and every started step retires exactly once (fault pulses flush)
        for (mode=1; mode<=5; mode=mode+1) begin
            nstep=40; do_reset;
            n=0; while (!(faults_seen && rt_n == st_n && is_n == st_n) && n < 20000) begin tick; n=n+1; end
            repeat(30) tick;
            f_bit = (mode==1 || mode==5) ? 87 : (mode==2) ? 84 : (mode==3) ? 86 : 85;
            if (!first_bits[f_bit-84] || !faults_seen || rt_n != st_n || st_n == 0) begin
                errors=errors+1; $display("ERR fault mode %0d bit %0d first %b res=%h faults_seen %0d started %0d retired %0d", mode, f_bit, first_bits, res,
                                          faults_seen, st_n, rt_n);
            end else
                $display("FAULT mode %0d cause bit %0d (first fault bits %b); %0d steps started, all retired (%0d flushed with fault)", mode, f_bit, first_bits, st_n, flush_pulses);
        end
        if (errors) begin $display("FAIL qkd_host_ctl MU errors=%0d", errors); $fatal(1); end
        $display("PASS qkd_host_ctl MU users4 steps%0d in-order one-edge retire after all 8 dies, hc user=pos[17:16], max outstanding 4; faults die-skip/disagree/overflow/watchdog/unknown-gen fail closed and flush", NS);
        $finish;
    end
endmodule
