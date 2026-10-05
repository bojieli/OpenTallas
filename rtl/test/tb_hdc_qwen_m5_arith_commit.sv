`timescale 1ns/1ps
module tb_hdc_qwen_m5_arith_commit;
    reg clk=0, rst_n=0, valid=0, first=0, last_k=0;
    always #5 clk=~clk;
    reg step_start=0, draft_tok_v=0, draft_done=0, kv_drained=0;
    reg [2:0] draft_slot=0;
    reg [15:0] draft_token=0;
    wire draft_start, verify_start, commit_v, step_done, ctrl_fault, ctrl_busy;
    wire [15:0] commit_pos, next_token, next_pos;
    wire [2:0] accepted, emitted;
    wire out_valid, mac_fault, tok_valid, tok_done, bridge_fault, bridge_busy;
    wire [639:0] result;
    wire [2:0] tok_slot;
    wire [15:0] tok;
    integer result_beats=0, token_beats=0, i;
    function automatic [31:0] fbits(input integer x);
        integer e, mantissa;
        begin
            e=0;
            while ((1 << (e+1)) <= x) e=e+1;
            mantissa=(x << (23-e)) - (1 << 23);
            fbits={1'b0, (8'd127+e), mantissa[22:0]};
        end
    endfunction
    ot_hdc_qwen_m5_mac_reduce #(.G(2),.W(2),.IL(8)) u_arith (
        .clk(clk),.rst_n(rst_n),.valid(valid),.first(first),.last_k(last_k),
        .split_log2(2'd1),.weight_fp32({4{32'h3f800000}}),
        .activation_fp32({fbits(5),fbits(5),fbits(4),fbits(4),fbits(3),fbits(3),
                          fbits(2),fbits(2),fbits(1),fbits(1)}),
        .row_scale_bf16({16'h4000,16'h3f00,16'h4000,16'h3f00}),
        .out_valid(out_valid),.result(result),.fault(mac_fault));
    ot_hdc_qwen_m5_result_tokens #(.G(2),.W(2),.NW(16)) u_tokens (
        .clk(clk),.rst_n(rst_n),.arm(verify_start),
        .result_valid(out_valid),.result_last(out_valid && result_beats==7),
        .result(result),.row_base(16'd100),.tok_valid(tok_valid),
        .tok_slot(tok_slot),.tok(tok),.done(tok_done),.fault(bridge_fault),.busy(bridge_busy));
    ot_hdc_qwen_dflash_step_ctrl u_ctrl (
        .clk(clk),.rst_n(rst_n),.step_start(step_start),.start_token(16'd7),
        .start_pos(16'd200),.draft_start(draft_start),
        .draft_tok_v(draft_tok_v),.draft_slot(draft_slot),
        .draft_token(draft_token),.draft_done(draft_done),
        .verify_start(verify_start),.verify_tok_v(tok_valid),
        .verify_slot(tok_slot),.verify_token(tok),.verify_done(tok_done),
        .verify_kv_drained(kv_drained),.kv_commit_v(commit_v),.kv_commit_pos(commit_pos),
        .step_done(step_done),.next_token(next_token),.next_pos(next_pos),
        .accepted_drafts(accepted),.emitted_tokens(emitted),.fault(ctrl_fault),.busy(ctrl_busy));
    always @(posedge clk) begin
        if (out_valid) result_beats<=result_beats+1;
        if (tok_valid) begin
            if (tok_slot!==token_beats || tok!==16'd101)
                $fatal(1,"slot/token mismatch slot=%0d token=%0d beat=%0d",tok_slot,tok,token_beats);
            token_beats<=token_beats+1;
        end
    end
    task automatic send_draft(input integer slot, input integer token);
        begin
            @(negedge clk); draft_tok_v=1; draft_slot=slot; draft_token=token;
            @(negedge clk); draft_tok_v=0;
        end
    endtask
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        @(negedge clk); step_start=1;
        @(negedge clk); step_start=0;
        if (!draft_start) $fatal(1,"draft did not start");
        send_draft(1,101); send_draft(2,101); send_draft(3,0); send_draft(4,0);
        @(negedge clk); draft_done=1;
        @(negedge clk); draft_done=0;
        if (!verify_start) $fatal(1,"verify did not start");
        $display("verify started at %0t",$time);
        repeat (8) begin @(negedge clk); valid=1; first=1; end
        repeat (8) begin @(negedge clk); valid=1; first=0; last_k=1; end
        @(negedge clk); valid=0; last_k=0;
        $display("arithmetic issued at %0t",$time);
        wait(tok_done);
        repeat (4) @(negedge clk);
        if (step_done || commit_v) $fatal(1,"commit before KV drain");
        kv_drained=1;
        wait(step_done);
        @(negedge clk);
        if (ctrl_fault || bridge_fault || mac_fault || result_beats!=8 || token_beats!=5 ||
            accepted!=2 || emitted!=3 || next_token!=101 || next_pos!=203 ||
            commit_pos!=203 || !commit_v)
            $fatal(1,"integration mismatch faults=%b%b%b result=%0d token=%0d accept=%0d emit=%0d next=%0d pos=%0d commit=%b",
                   ctrl_fault,bridge_fault,mac_fault,result_beats,token_beats,accepted,emitted,next_token,next_pos,commit_v);
        $display("PASS Qwen m5 arithmetic-to-commit: 8 result beats, 5 exact argmax tokens, accepted 2, KV drain barrier");
        $finish;
    end
    initial begin #5000; $fatal(1,"m5 arithmetic-to-commit timeout result=%0d token=%0d ctrl=%b bridge=%b",result_beats,token_beats,ctrl_busy,bridge_busy); end
endmodule
