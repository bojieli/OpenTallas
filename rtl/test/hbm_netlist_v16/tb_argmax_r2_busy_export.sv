`timescale 1ns/1ps
`default_nettype none
// Lockstep bench (HBM-NATIVE 10-17): ot_hbm_argmax_static_sw_vm_r2 (busy export flop) vs the CLOSED e4dc0b651 RTL
// (ot_hbm_argmax_static_sw_vm_r2_ref). Both get the SAME random stimulus on every input (go pulses with legal and
// illegal records, both modes, random VM response / ack words, random mid-run resets) and EVERY output pin
// (vm_rq, cq, cq_seq, busy, done, fault, nan_flag) is compared on every edge. PASS needs 0 mismatches and coverage:
// busy rises, busy falls on the legal-record end (done or fault) and on the illegal-record (E_CHK) path, and resets.
module tb_argmax_r2_busy_export;
`ifndef SEED
`define SEED 1
`endif
`ifndef NCYC
`define NCYC 8000
`endif
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0, go = 0, mode = 0, a_mirror = 0; reg [7:0] die_id = 8'd3;
    reg [17:0] imm_a = 0, a_base = 0, n = 0, o_base = 0; reg [15:0] o_is = 0;
    reg [263:0] vm_rr = 0; reg [273:0] cr = 0;
    wire [135:0] rq0, rq1; wire [337:0] cq0, cq1; wire [1:0] s0, s1; wire b0, b1, d0, d1, f0, f1, n0, n1;
    ot_hbm_argmax_static_sw_vm_r2_ref #(.TP(192)) ref_(.clk(clk), .rst_n(rst_n), .die_id(die_id), .go(go), .mode(mode),
        .imm_a(imm_a), .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq0), .vm_rr(vm_rr),
        .cq(cq0), .cq_seq(s0), .cr(cr), .busy(b0), .done(d0), .fault(f0), .nan_flag(n0));
    ot_hbm_argmax_static_sw_vm_r2 #(.TP(192)) dut(.clk(clk), .rst_n(rst_n), .die_id(die_id), .go(go), .mode(mode),
        .imm_a(imm_a), .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq1), .vm_rr(vm_rr),
        .cq(cq1), .cq_seq(s1), .cr(cr), .busy(b1), .done(d1), .fault(f1), .nan_flag(n1));
    integer seed = `SEED, cyc = 0, mism = 0, rises = 0, falls_end = 0, falls_chk = 0, resets = 0, dones = 0, faults = 0;
    reg b_prev = 0; reg cyc_was_chk = 0;
    function automatic [31:0] rnd; input integer dummy; rnd = $random(seed); endfunction
    integer k;
    always @(negedge clk) begin
        cyc = cyc + 1;
        // stimulus (changes at negedge, sampled by both at the next posedge)
        if (cyc < 4) rst_n = 0;
        else if ((rnd(0) % 1000) == 0) begin rst_n = 0; resets = resets + 1; end
        else rst_n = 1;
        go = (rnd(0) % 23) == 0;
        mode = (rnd(0) % 9) == 0;
        a_mirror = rnd(0); die_id = rnd(0);
        if ((rnd(0) % 4) != 0) begin                 // mostly legal records (sid 0, small n, output in slice 0)
            a_base = {2'd0, 16'(rnd(0))}; n = 18'(1 + (rnd(0) % 40)); o_base = {2'd0, 16'(rnd(0) % 16'hF000)};
            o_is = 16'(rnd(0) % 256); imm_a = 18'(rnd(0) % 262143);
        end else begin
            a_base = rnd(0); n = (rnd(0) % 8 == 0) ? 18'd0 : rnd(0); o_base = rnd(0); o_is = rnd(0); imm_a = rnd(0);
        end
        for (k = 0; k < 9; k = k + 1) vm_rr[32*k +: 32] = rnd(0);
        vm_rr[263:256] = (rnd(0) % 3 == 0) ? 8'(rnd(0)) : 8'd0;
        for (k = 0; k < 9; k = k + 1) cr[32*k +: 32] = rnd(0);
        cr[273] = (rnd(0) % 5) == 0;
        // compare every output (sampled after the previous posedge settled)
        if (cyc > 4 && rst_n !== 1'bx) begin
            if ({rq0, cq0, s0, b0, d0, f0, n0} !== {rq1, cq1, s1, b1, d1, f1, n1}) begin
                mism = mism + 1;
                if (mism <= 5) $display("MISMATCH cyc %0d busy %b/%b done %b/%b fault %b/%b seq %b/%b rq %0d cq %0d", cyc,
                    b0, b1, d0, d1, f0, f1, s0, s1, rq0 !== rq1, cq0 !== cq1);
            end
            if (b0 && !b_prev) rises = rises + 1;
            if (!b0 && b_prev && rst_n) begin if (d0 || f0) falls_end = falls_end + (cyc_was_chk ? 0 : 1); if (cyc_was_chk) falls_chk = falls_chk + 1; end
            if (d0) dones = dones + 1; if (f0) faults = faults + 1;
            b_prev = b0; cyc_was_chk = (ref_.st == 4'd1);
        end
        if (cyc == `NCYC) begin
            $display("BUSY_EXPORT seed %0d cycles %0d busy_rises %0d falls_end %0d falls_chk %0d resets %0d dones %0d faults %0d mismatches %0d",
                `SEED, cyc, rises, falls_end, falls_chk, resets, dones, faults, mism);
            if (mism == 0 && rises > 50 && falls_end > 10 && falls_chk > 10 && resets > 3) $display("ARGMAX_R2_BUSY_EXPORT PASS");
            else $display("ARGMAX_R2_BUSY_EXPORT FAIL");
            $finish;
        end
    end
endmodule
`default_nettype wire
