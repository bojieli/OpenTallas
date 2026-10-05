`timescale 1ns/1ps
// Lockstep bench (Verilator --binary): the hardened commit/rollback/visibility element
// ot_qwen_kv_mp_commit against the expressions of ot_qwen_rt_kv_stream4_mp_service (lane decode:
// E4M3 encode, block visibility, K tile select, V block row; commit / start checks), on random
// steps (np 1..4 incl. illegal 0/5, positions near tile edges and the 8192 window end), lanes inside,
// just outside and far outside the block, non-E4M3 values, and commits with legal / illegal commit_n
// and with / without ack debt.  Prints MP_COMMIT_LOCKSTEP PASS/FAIL.
module tb_qwen_kv_mp_commit;
    localparam integer SW = 64, AW = 24, NW = 18, VPMAX = 4, N = 100000, KVB = 131072;
    reg clk = 0, rst_n = 1;
    reg start; reg [NW-1:0] pos; reg [3:0] npos; reg [SW-1:0] kv_we; reg [SW*AW-1:0] kv_waddr; reg [SW*32-1:0] kv_wdata;
    reg commit_v; reg [3:0] commit_n; reg ack_debt;
    wire [SW-1:0] lane_v, lane_bad, lane_isk, lane_sel; wire [SW*2-1:0] lane_j; wire [SW*8-1:0] lane_code;
    wire [127:0] tail_lm; wire [NW-1:0] P, committed_len; wire [3:0] NPr; wire committed_v; wire [15:0] fault_code;
    ot_qwen_kv_mp_commit #(.VPMAX(VPMAX)) dut (.clk(clk), .rst_n(rst_n), .start(start), .pos(pos), .npos(npos), .kv_we(kv_we),
        .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .commit_v(commit_v), .commit_n(commit_n), .ack_debt(ack_debt),
        .lane_v(lane_v), .lane_bad(lane_bad), .lane_isk(lane_isk), .lane_sel(lane_sel), .lane_j(lane_j), .lane_code(lane_code),
        .tail_lm(tail_lm), .P(P), .committed_len(committed_len), .NPr(NPr), .committed_v(committed_v), .fault_code(fault_code));
    // ---- reference: the service's expressions ----
    function automatic [8:0] f32_e4m3(input [31:0] b);
        reg [7:0] e; reg [22:0] m;
        begin
            e = b[30:23]; m = b[22:0];
            if (e == 0 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd0};
            else if (e >= 8'd121 && e <= 8'd135 && m[19:0] == 0) f32_e4m3 = {1'b0, b[31], e[3:0] - 4'd8, m[22:20]};
            else if (e == 8'd120 && m[20:0] == 0) f32_e4m3 = {1'b0, b[31], 4'd0, 1'b1, m[22:21]};
            else if (e == 8'd119 && m[21:0] == 0) f32_e4m3 = {1'b0, b[31], 5'd0, 1'b1, m[22]};
            else if (e == 8'd118 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd1};
            else f32_e4m3 = {1'b1, 8'd0};
        end
    endfunction
    reg [NW-1:0] rP, rCL; reg [3:0] rNP; reg rCV; reg [15:0] rF;
    reg [SW-1:0] eb, es, ek; reg [SW*2-1:0] ej; reg [SW*8-1:0] ec;
    reg [SW-1:0] d_eb = 0, d_es = 0, d_ek = 0, d_ev = 0, q_eb, q_es, q_ek, q_ev; reg [SW*2-1:0] d_ej = 0, q_ej; reg [SW*8-1:0] d_ec = 0, q_ec;
    task automatic ref_lanes();
        integer li; reg [NW-1:0] PE;
        PE = rP + {{(NW-4){1'b0}}, rNP};
        for (li = 0; li < SW; li = li + 1) begin
            reg [AW-1:0] e; reg [AW-5:0] a; reg [8:0] fc; reg [16:0] w; reg [12:0] pp; reg [8:0] t; reg bad;
            e = kv_waddr[li*AW +: AW]; a = e[AW-1:4]; fc = f32_e4m3(kv_wdata[li*32 +: 32]);
            bad = 1'b0; if (fc[8]) bad = 1'b1;
            ec[li*8 +: 8] = fc[7:0]; ek[li] = a < KVB; es[li] = 1'b0; ej[li*2 +: 2] = 0;
            if (a < KVB) begin
                t = a[15:7];
                if (a[19:17] != 0 || {t, e[3:0]} < rP[12:0] || {t, e[3:0]} >= PE[13:0]) bad = 1'b1;
                es[li] = (a[15:7] != rP[12:4]);
            end else begin
                w = a - KVB; pp = w[15:3];
                if (a >= KVB + 131072 || pp < rP[12:0] || {1'b0, pp} >= PE[13:0]) bad = 1'b1;
                ej[li*2 +: 2] = 2'(w[15:3] - rP[12:0]);
            end
            eb[li] = kv_we[li] && bad;
        end
    endtask
    task automatic ref_seq();
        if (start) begin
            if (npos > VPMAX) rF[12] = 1'b1;
            if (pos + ((npos == 0) ? 1 : npos) > 8192) rF[1] = 1'b1;
            if (rCV) begin if (pos != rCL) rF[14] = 1'b1; end
        end
        if (commit_v) begin
            if (commit_n == 0 || commit_n > rNP) rF[12] = 1'b1;
            if (ack_debt) rF[13] = 1'b1;
        end
        // state update in the service's order: start (clears committed_v) then commit (sets it)
        if (start) begin rCV = 1'b0; end
        if (commit_v) begin rCL = rP + {{(NW-4){1'b0}}, commit_n}; rCV = 1'b1; end
        if (start) begin rP = pos; rNP = (npos == 0) ? 4'd1 : npos; end
    endtask
    integer t, li, bad, nbad, ncommit, nstart;
    reg [SW-1:0] pb, ps, pk, pv; reg [SW*2-1:0] pj; reg [SW*8-1:0] pc; reg [SW*AW-1:0] pa; reg [SW*32-1:0] pd;
    initial begin
        bad = 0; nbad = 0; ncommit = 0; nstart = 0;
        rP = 0; rCL = 0; rNP = 1; rCV = 0; rF = 0;
        start = 0; commit_v = 0; kv_we = 0; ack_debt = 0; pos = 0; npos = 1; commit_n = 0; kv_waddr = 0; kv_wdata = 0;
        #1 rst_n = 0; #1 rst_n = 1;                              // a real reset edge
        for (t = 0; t < N; t = t + 1) begin
            start = ($urandom % 50) == 0;
            pos = ($urandom % 4 == 0) ? NW'(8188 + $urandom % 6) : ($urandom % 3 == 0 && rCV) ? rCL : NW'($urandom % 8192);
            npos = 4'($urandom % 6);
            commit_v = !start && ($urandom % 40) == 0; commit_n = 4'($urandom % 6); ack_debt = ($urandom % 4) == 0;
            for (li = 0; li < SW; li = li + 1) begin
                reg [23:0] e; reg [31:0] v; integer p0, sh;
                kv_we[li] = ($urandom % 2);
                p0 = integer'(rP[12:0]) + integer'($urandom % 7) - 1;          // around the block
                if ($urandom % 8 == 0) p0 = integer'($urandom % 8192);
                if (p0 < 0) p0 = 0;
                if ($urandom % 2) e = 24'((((($urandom % 2) * 512 + (p0 >> 4)) * 128 + ($urandom % 128)) * 16) + (p0 & 15));     // K
                else e = 24'(2097152 + (($urandom % 2) * 8192 + p0) * 128 + ($urandom % 128));                                 // V
                if ($urandom % 64 == 0) e = 24'($urandom);
                kv_waddr[li*AW +: AW] = e;
                sh = $urandom % 16;
                v = {1'($urandom), 8'(118 + $urandom % 18), 3'($urandom), 20'd0};
                if ($urandom % 10 == 0) v = $urandom;
                kv_wdata[li*32 +: 32] = v;
            end
            #1;
            ref_lanes(); pv = kv_we; pa = kv_waddr; pd = kv_wdata;
            // the element's lane outputs are two edges after the lane: compare against the previous lane
            q_eb = d_eb; q_es = d_es; q_ek = d_ek; q_ej = d_ej; q_ec = d_ec; q_ev = d_ev;
            d_eb = eb; d_es = es; d_ek = ek; d_ej = ej; d_ec = ec; d_ev = kv_we;
            clk = 1; #1; clk = 0;
            ref_seq();
            nstart += start; ncommit += commit_v; nbad += $countones(eb);
            if ((t > 0 && (lane_bad !== q_eb || lane_sel !== q_es || lane_isk !== q_ek || lane_code !== q_ec || lane_v !== q_ev ||
                (VPMAX > 1 && lane_j !== q_ej))) || P !== rP || NPr !== rNP || committed_len !== rCL || committed_v !== rCV ||
                fault_code !== rF) begin
                bad = bad + 1;
                if (bad < 5) $display("MISMATCH t=%0d bad %h/%h sel %h/%h F %h/%h CL %0d/%0d", t, lane_bad, eb, lane_sel, es, fault_code, rF, committed_len, rCL);
            end
        end
        $display("%s cycles=%0d starts=%0d commits=%0d bad_lanes=%0d faults=%h mismatches=%0d",
                 bad == 0 ? "MP_COMMIT_LOCKSTEP PASS" : "MP_COMMIT_LOCKSTEP FAIL", N, nstart, ncommit, nbad, rF, bad);
        if (bad != 0) $fatal(1, "EQUIVALENCE_TERMINAL_FAIL");
        $finish;
    end
endmodule
