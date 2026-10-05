`timescale 1ns/1ps
module tb_hdc_qwen_dflash_step_ctrl;
    reg clk=0, rst_n=0, step_start=0, draft_tok_v=0, draft_done=0;
    always #5 clk=~clk;
    reg [15:0] start_token=0, start_pos=0, draft_token=0, verify_token=0;
    reg [2:0] draft_slot=0, verify_slot=0;
    reg verify_tok_v=0, verify_done=0, verify_kv_drained=0;
    wire draft_start, verify_start, kv_commit_v, step_done, fault, busy;
    wire [15:0] kv_commit_pos, next_token, next_pos;
    wire [2:0] accepted_drafts, emitted_tokens;
    integer cases=0;
    ot_hdc_qwen_dflash_step_ctrl dut (
        .clk(clk),.rst_n(rst_n),.step_start(step_start),
        .start_token(start_token),.start_pos(start_pos),.draft_start(draft_start),
        .draft_tok_v(draft_tok_v),.draft_slot(draft_slot),.draft_token(draft_token),.draft_done(draft_done),
        .verify_start(verify_start),.verify_tok_v(verify_tok_v),.verify_slot(verify_slot),
        .verify_token(verify_token),.verify_done(verify_done),.verify_kv_drained(verify_kv_drained),
        .kv_commit_v(kv_commit_v),.kv_commit_pos(kv_commit_pos),.step_done(step_done),
        .next_token(next_token),.next_pos(next_pos),.accepted_drafts(accepted_drafts),
        .emitted_tokens(emitted_tokens),.fault(fault),.busy(busy)
    );
    task automatic send_draft(input integer slot, input integer token);
        begin
            @(negedge clk); draft_tok_v=1; draft_slot=slot; draft_token=token;
            @(negedge clk); draft_tok_v=0;
        end
    endtask
    task automatic send_verify(input integer slot, input integer token);
        begin
            @(negedge clk); verify_tok_v=1; verify_slot=slot; verify_token=token;
            @(negedge clk); verify_tok_v=0;
        end
    endtask
    task automatic run_case(input integer base, input integer accept_count);
        integer i, expect_token, target;
        begin
            @(negedge clk); start_pos=base; start_token=7; step_start=1;
            @(negedge clk); step_start=0;
            if (!draft_start || !busy) $fatal(1,"draft phase did not start");
            for (i=1;i<5;i=i+1) send_draft(i,10+i);
            @(negedge clk); draft_done=1;
            @(negedge clk); draft_done=0;
            if (!verify_start) $fatal(1,"verify phase did not start");
            for (i=0;i<5;i=i+1) begin
                target = (i < accept_count) ? 11+i : (90+base%10+i);
                send_verify(i,target);
            end
            @(negedge clk); verify_done=1;
            @(negedge clk); verify_done=0;
            repeat (3) @(negedge clk);
            if (step_done || kv_commit_v) $fatal(1,"committed before KV drain");
            verify_kv_drained=1;
            wait (step_done);
            @(negedge clk);
            expect_token=90+base%10+accept_count;
            if (fault || accepted_drafts!=accept_count || emitted_tokens!=accept_count+1 ||
                next_token!=expect_token || next_pos!=base+accept_count+1 ||
                kv_commit_pos!=base+accept_count+1 || !kv_commit_v)
                $fatal(1,"commit mismatch base=%0d accept=%0d got a=%0d emit=%0d tok=%0d pos=%0d kv=%0d fault=%b",
                       base,accept_count,accepted_drafts,emitted_tokens,next_token,next_pos,kv_commit_pos,fault);
            cases=cases+1;
            verify_kv_drained=0;
            @(negedge clk);
        end
    endtask
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        run_case(100,0);
        run_case(200,2);
        run_case(300,4);
        @(negedge clk); step_start=1; start_pos=400;
        @(negedge clk); step_start=0;
        @(negedge clk); draft_done=1;
        @(negedge clk); draft_done=0;
        if (!fault) $fatal(1,"incomplete draft passed");
        $display("PASS Qwen DFlash controller: %0d accepted-prefix cases, KV drain barrier, early-done fault",cases);
        $finish;
    end
    initial begin #200000; $fatal(1,"DFlash controller timeout"); end
endmodule
