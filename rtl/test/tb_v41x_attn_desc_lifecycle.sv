`timescale 1ns/1ps
module tb_v41x_attn_desc_lifecycle;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, desc_v=0, stage_v=0, beat_v=0, beat_ready=0, engine_idle=1;
    reg issue_v=0, service_fault=0, wrap_drained=1;
    reg [9:0] desc_user=7;
    reg [20:0] desc_pos=199999, desc_tiles=1, desc_k=512, desc_nout=128;
    reg [29:0] desc_wbase=10, desc_ts=1, desc_ks=1, desc_js=0;
    reg [1:0] desc_hg=0;
    reg desc_mmode=1;
    reg [15:0] stage_gen=0, beat_gen=0;
    reg [10:0] stage_rows=128;
    reg [3:0] beat_mask=4'hf;
    wire desc_accept, issue_ok, done, fault;
    wire [15:0] desc_gen;
    wire [10:0] desc_rows, beats_accepted;
    wire [3:0] fault_code;
    ot_chip_v41x_attn_desc_lifecycle #(.RESET_GEN(16'hffff)) dut (.*);
    task automatic tick;
        begin @(posedge clk); #1; end
    endtask
    task automatic reset_gate;
        begin
            @(negedge clk); rst_n=0; desc_v=0; stage_v=0; beat_v=0;
            beat_ready=0; engine_idle=1; issue_v=0; service_fault=0;
            wrap_drained=1;
            tick(); @(negedge clk); rst_n=1; tick();
        end
    endtask
    task automatic run_job(input bit pv, input [15:0] generation,
                           input [10:0] staged_prefix);
        integer n;
        begin
            @(negedge clk);
            desc_k=pv ? 128 : 512; desc_nout=pv ? 512 : 128;
            desc_ks=pv ? 16 : 1; desc_v=1;
            #1;
            if (desc_gen !== generation || !desc_accept)
                $fatal(1,"new descriptor generation/accept mismatch");
            tick();
            if (issue_ok || fault || desc_rows != 128)
                $fatal(1,"descriptor issued before staged");
            // Repeated S_DEC emits the same descriptor. No fixed-wait release.
            repeat (7) begin tick(); if (issue_ok || fault) $fatal(1,"unstaged descriptor released"); end
            @(negedge clk); desc_v=0; stage_v=1; stage_gen=generation;
            stage_rows=staged_prefix;
            tick();
            if (!issue_ok || fault) $fatal(1,"staged descriptor did not release");
            @(negedge clk); stage_v=0; issue_v=1;
            tick();
            @(negedge clk); issue_v=0; engine_idle=0;
            tick();
            // A valid beat may wait; count changes only on valid && ready.
            @(negedge clk); beat_v=1; beat_ready=0; beat_gen=generation; beat_mask=4'hf;
            repeat (3) begin tick(); if (beats_accepted != 0 || fault) $fatal(1,"backpressure counted beat"); end
            @(negedge clk); beat_ready=1;
            for (n=0;n<32;n=n+1) begin
                tick();
                if (beats_accepted != n+1 || fault) $fatal(1,"beat %0d not accepted",n);
                @(negedge clk);
            end
            beat_v=0; beat_ready=0;
            repeat (4) begin tick(); if (done || fault) $fatal(1,"premature completion"); end
            @(negedge clk); engine_idle=1;
            tick();
            if (!done || fault) $fatal(1,"drained descriptor did not complete");
            tick(); if (done || fault || !desc_accept && desc_v) $fatal(1,"completion not one cycle");
        end
    endtask
    initial begin
        reset_gate();
        run_job(0,16'd1,11'd128); // current L0 source stages all 128 rows
        run_job(1,16'd2,11'd4);   // synthetic future refill under backpressure
        reset_gate();
        @(negedge clk); wrap_drained=0; desc_v=1;
        tick(); if (!fault || fault_code != 10) $fatal(1,"undrained wrap accepted");
        reset_gate();
        @(negedge clk); stage_v=1; stage_gen=16'd1;
        tick(); if (!fault || fault_code != 3) $fatal(1,"unsolicited stage accepted");
        reset_gate();
        @(negedge clk); desc_v=1; desc_k=512; desc_nout=128; desc_ks=1;
        tick();
        @(negedge clk); desc_v=0; stage_v=1; stage_gen=16'd2;
        tick(); if (!fault || fault_code != 4) $fatal(1,"stale generation accepted");
        reset_gate();
        @(negedge clk); stage_v=0; desc_v=1; desc_k=512; desc_nout=128; desc_ks=1;
        tick();
        @(negedge clk); desc_pos=200000;
        tick(); if (!fault || fault_code != 2) $fatal(1,"changed repeated S_DEC accepted");
        reset_gate();
        @(negedge clk); desc_pos=199999; desc_v=1;
        tick();
        @(negedge clk); desc_v=0; service_fault=1;
        tick(); if (!fault || fault_code != 9) $fatal(1,"service fault not latched");
        reset_gate();
        @(negedge clk); desc_v=1;
        tick();
        @(negedge clk); desc_v=0; stage_v=1; stage_gen=16'd1; stage_rows=128;
        tick();
        @(negedge clk); stage_v=0; issue_v=1;
        tick();
        @(negedge clk); issue_v=0; engine_idle=0;
        tick();
        @(negedge clk); engine_idle=1;
        tick(); if (!fault || fault_code != 7) $fatal(1,"early engine idle not caught");
        $display("PASS lifecycle: QK/PV replay 32 beats each, wrap, backpressure, drain, stale/unsolicited/changed faults");
        $finish;
    end
endmodule
