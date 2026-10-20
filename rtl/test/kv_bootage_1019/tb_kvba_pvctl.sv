`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19: lockstep bench ot_qwen_tp8_pv_wide_ctl_tb (boot age cfg_fia) vs the closed pair control
// ot_qwen_tp8_pv_wide_ctl_t #(.FIRST_INPUT_AGE(A)) (kit qkd_pv_ctl_t_d54f58a95: RESET_PIN 1, TRUNK_D 54, FLAG_D 58).
// V path model: in_* = req_* delayed L edges (the ports + die relays, one fixed latency), in_epoch = the command epoch;
// columns: col_valid = the reference's column-flag slot (its JOIN wage, one edge ahead of the pin register), col_fault 0.
//   calibrate  L is searched (A - 12 .. A + 4) for a fault-free reference command (the model must exercise the real
//              arrival / output checks, not only the fault path)
//   phase B    commands at several context lengths and both pair straps: every output identical every edge, the
//              reference fault-free, out_age identical
//   phase A    the same with random single-bit corruptions of in_t / in_valid / col_valid: identical fault behaviour
//   phase C    invalid boot ages (0, > bound): a start must set the successor's fault
// Prints "KVBA_PVCTL PASS A=.. mut=.. checks=N" or "KVBA_PVCTL FAIL ...".
module tb_kvba_pvctl;
    parameter integer A = 95, MUT = 0, SEED = 1;
    localparam integer AB = 127, TD = 54, FD = 58, LMAX = 160;
    localparam integer COL_CHK = (2 + 3 + 3 * 7 + 3 + 1) + TD + FD;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg [7:0] cfg; reg pair_id = 0, start = 0; reg [13:0] ctx = 0; reg [15:0] epoch = 0;
    reg [7:0] in_valid; reg [111:0] in_t; reg [127:0] in_epoch; reg [31:0] col_valid, col_fault;
    wire [7:0] a_rv, b_rv; wire [111:0] a_rt, b_rt; wire [59:0] a_cmd, b_cmd;
    wire [15:0] a_oe, b_oe, a_oa, b_oa; wire a_f, b_f, a_busy, b_busy;
    ot_qwen_tp8_pv_wide_ctl_t #(.FIRST_INPUT_AGE(A), .RESET_PIN(1), .TRUNK_D(TD), .FLAG_D(FD)) u_ref (
        .clk(clk), .rst_n(rst_n), .pair_id(pair_id), .start(start), .context_len(ctx), .epoch(epoch),
        .in_valid(in_valid), .in_t(in_t), .in_epoch(in_epoch), .req_valid(a_rv), .req_t(a_rt), .cmd(a_cmd),
        .col_valid(col_valid), .col_fault(col_fault), .out_epoch(a_oe), .fault(a_f), .busy(a_busy), .out_age(a_oa));
    ot_qwen_tp8_pv_wide_ctl_tb #(.FIRST_INPUT_AGE(AB), .RESET_PIN(1), .MUT(MUT), .TRUNK_D(TD), .FLAG_D(FD)) u_dut (
        .clk(clk), .rst_n(rst_n), .cfg_fia(cfg), .pair_id(pair_id), .start(start), .context_len(ctx), .epoch(epoch),
        .in_valid(in_valid), .in_t(in_t), .in_epoch(in_epoch), .req_valid(b_rv), .req_t(b_rt), .cmd(b_cmd),
        .col_valid(col_valid), .col_fault(col_fault), .out_epoch(b_oe), .fault(b_f), .busy(b_busy), .out_age(b_oa));
    // V path delay line (reference requests; identical to the successor's while lockstep holds)
    reg [7:0] dv [0:LMAX]; reg [111:0] dt [0:LMAX];
    integer L = 0, i, j, checks = 0, errs = 0, seed, refault = 0, cmds = 0, corrupt = 0, flip = 0;
    always @(posedge clk) begin
        dv[0] <= rst_n ? a_rv : 8'd0; dt[0] <= a_rt;
        for (i = 1; i <= LMAX; i = i + 1) begin dv[i] <= rst_n ? dv[i-1] : 8'd0; dt[i] <= dt[i-1]; end
    end
    reg pf = 0; integer nf = 0;
    always @(posedge clk) begin
        pf <= a_f;
        if (a_f && !pf && nf < 4) begin nf = nf + 1;
            $display("DBG ref fault t=%0t L=%0d pa=%0d state=%0d iv_r=%h pexp_v=%h cv0=%b out_slot=%b", $time, L, u_ref.pa,
                     u_ref.state, u_ref.iv_r, u_ref.pexp_v, u_ref.cv_r[0], u_ref.out_slot); end
    end
    wire join_slot = (u_ref.state == 4'd7) && (u_ref.wage == 8'(COL_CHK));
    always @* begin
        in_valid = (L > 0) ? dv[L-1] : a_rv; in_t = (L > 0) ? dt[L-1] : a_rt; in_epoch = {8{epoch}};
        col_valid = {32{join_slot}}; col_fault = 32'd0;
        if (corrupt != 0 && flip == 1) in_t[0] = ~in_t[0];
        if (corrupt != 0 && flip == 2) in_valid[3] = ~in_valid[3];
        if (corrupt != 0 && flip == 3) col_valid[7] = ~col_valid[7];
    end
    task cmp; begin
        checks = checks + 1;
        if ({a_rv, a_rt, a_cmd, a_oe, a_f, a_busy, a_oa} !== {b_rv, b_rt, b_cmd, b_oe, b_f, b_busy, b_oa}) begin
            errs = errs + 1;
            if (errs < 6) $display("MISMATCH t=%0t req %h/%h cmd %h/%h fault %b/%b busy %b/%b out_age %0d/%0d", $time,
                                   a_rv, b_rv, a_cmd, b_cmd, a_f, b_f, a_busy, b_busy, a_oa, b_oa);
        end
    end endtask
    task do_reset; begin
        rst_n = 0; start = 0; repeat (6) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
    end endtask
    // one command; returns when both are idle again (or after a bound)
    task run_cmd(input [13:0] c, input [15:0] e, input integer chk, input integer cor); integer n; begin
        ctx = c; epoch = e; corrupt = cor; flip = 0;
        start = 1; @(negedge clk); start = 0;
        for (n = 0; n < 4000; n = n + 1) begin
            if (cor != 0 && n == 20 + ($unsigned($random(seed)) % 200)) flip = 1 + ($unsigned($random(seed)) % 3); else flip = 0;
            @(posedge clk); #0.1 if (chk) cmp; @(negedge clk);
            if (n > 8 && !a_busy && !b_busy) n = 4000;
        end
        flip = 0; corrupt = 0; repeat (4) begin @(posedge clk); #0.1 if (chk) cmp; @(negedge clk); end
    end endtask
    integer found, k, ok_c; reg [13:0] cl [0:5];
    initial begin
        seed = SEED; cfg = 8'(A);
        cl[0] = 14'd1; cl[1] = 14'd129; cl[2] = 14'd300; cl[3] = 14'd1000; cl[4] = 14'd2049; cl[5] = 14'd700;
        for (i = 0; i <= LMAX; i = i + 1) begin dv[i] = 0; dt[i] = 0; end
        // ---- calibrate the V path latency on the reference
        found = 0;
        for (L = A - 12; L <= A + 4 && !found; L = L + 1) begin
            do_reset; run_cmd(14'd300, 16'h0b0b, 0, 0);
            if (!a_f && a_oa != 0) found = L;
        end
        if (!found) begin
            $display("KVBA_PVCTL FAIL A=%0d mut=%0d calibrate: no V latency in [%0d, %0d] gives a fault-free reference", A, MUT, A - 12, A + 4);
            $finish;
        end
        L = found;
        // ---- phase B: clean commands, both pairs
        for (j = 0; j < 2; j = j + 1) begin
            pair_id = j[0]; do_reset;
            for (k = 0; k < 6; k = k + 1) begin
                run_cmd(cl[k], 16'h0b0b + 16'(k), 1, 0); cmds = cmds + 1;
                if (a_f) refault = refault + 1;
            end
        end
        // ---- phase A: corrupted arrivals / column flags (identical fault behaviour)
        for (k = 0; k < 6; k = k + 1) begin
            pair_id = k[0]; do_reset; run_cmd(cl[k], 16'h0c0c, 1, 1);
        end
        // ---- phase C: invalid boot ages
        ok_c = 0;
        for (k = 0; k < 2; k = k + 1) begin
            cfg = (k == 0) ? 8'd0 : 8'(AB + 1); do_reset;
            start = 1; ctx = 300; @(negedge clk); start = 0; repeat (6) @(negedge clk);
            if (b_f) ok_c = ok_c + 1; else $display("PHASE_C cfg=%0d: start accepted with an invalid boot age", cfg);
        end
        if (errs == 0 && refault == 0 && cmds == 12 && ok_c == 2)
            $display("KVBA_PVCTL PASS A=%0d mut=%0d L=%0d checks=%0d cmds=%0d", A, MUT, L, checks, cmds);
        else
            $display("KVBA_PVCTL FAIL A=%0d mut=%0d L=%0d checks=%0d errors=%0d ref_faults=%0d cmds=%0d invalid_caught=%0d/2",
                     A, MUT, L, checks, errs, refault, cmds, ok_c);
        $finish;
    end
endmodule
