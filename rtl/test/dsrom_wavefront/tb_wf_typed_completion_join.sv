`timescale 1ns/1ps
module tb_wf_typed_completion_join;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,request_v=0,request_binding_valid=1;
    reg [46:0] request_identity=47'h12345,native_identity=47'h12345;
    reg [13:0] request_terminal_entry=21,request_producer_pc=24,request_end_pc=28;
    reg native_active=1,native_end_take=0,native_done=1,good_producer=0;
    reg [13:0] native_entry=21,native_pc=0;
    reg [20:0] native_next_token=21'h123;
    reg [31:0] native_next_value=32'h76543210;
    reg coverage_valid=0,coverage_wholeplan_complete=0;
    reg [46:0] coverage_identity=47'h12345,visibility_identity=47'h12345;
    reg visibility_valid=0,visibility_fault=0;
    reg [4:0] visibility=0;
    reg c8_write_quiet=1,c8_quarantine=0,c8_fault=0;
    reg capture_live=0,capture_drained=1,capture_fault=0;
    reg collective_busy=0,collective_fault=0,native_fault=0,stage_accepted=0;
    wire request_ready,stage_done,pending,fault,terminal_kind,token_result_valid,stage_handoff_done;
    wire [20:0] stage_next_token;wire [31:0] stage_next_value;
    ot_dsrom_wf_typed_completion_join #(.ENABLE(1)) handoff(
        .request_kind(1'b1),.native_producer_take(1'b0),.native_am_any(1'b0),.*);
    wire head_ready,head_done,head_pending,head_fault,head_kind,head_valid,head_handoff;
    wire [20:0] head_token;wire [31:0] head_value;
    ot_dsrom_wf_typed_completion_join #(.ENABLE(1)) no_argmax_head(
        .request_kind(1'b0),.native_producer_take(1'b0),.native_am_any(1'b0),
        .request_ready(head_ready),.stage_done(head_done),.pending(head_pending),.fault(head_fault),
        .terminal_kind(head_kind),.token_result_valid(head_valid),.stage_handoff_done(head_handoff),
        .stage_next_token(head_token),.stage_next_value(head_value),.stage_accepted(1'b0),.*);
    wire good_ready,good_done,good_pending,good_fault,good_kind,good_valid,good_handoff;
    wire [20:0] good_token;wire [31:0] good_value;
    ot_dsrom_wf_typed_completion_join #(.ENABLE(1)) actual_argmax_head(
        .request_kind(1'b0),.native_producer_take(good_producer),.native_am_any(1'b1),
        .request_ready(good_ready),.stage_done(good_done),.pending(good_pending),.fault(good_fault),
        .terminal_kind(good_kind),.token_result_valid(good_valid),.stage_handoff_done(good_handoff),
        .stage_next_token(good_token),.stage_next_value(good_value),.*);
    wire off_ready,off_done,off_pending,off_fault,off_kind,off_valid,off_handoff;
    wire [20:0] off_token;wire [31:0] off_value;
    ot_dsrom_wf_typed_completion_join disabled(
        .request_kind(1'b1),.native_producer_take(1'b0),.native_am_any(1'b0),
        .request_ready(off_ready),.stage_done(off_done),.pending(off_pending),.fault(off_fault),
        .terminal_kind(off_kind),.token_result_valid(off_valid),.stage_handoff_done(off_handoff),
        .stage_next_token(off_token),.stage_next_value(off_value),.*);
    // Real native result registers update after END, not from a host timer.
    always @(posedge clk) if(native_end_take) begin
        native_done<=1;native_next_token<=21'h13579;native_next_value<=32'hdeadbeef;
    end
    task step;begin @(posedge clk);#1;
        if(off_ready||off_done||off_pending||off_fault||off_kind||off_valid||off_handoff||off_token||off_value)
            $fatal(1,"typed successor default off changed");
    end endtask
    initial begin
        step;step;rst_n=1;request_v=1;#1;
        if(!request_ready||!head_ready||!good_ready)$fatal(1,"typed bound admission missing");
        step;request_v=0;
        repeat(2)begin step;if(stage_done||head_done||good_done)$fatal(1,"stale done bypassed real END");end
        native_done=0;native_pc=24;good_producer=1;step;good_producer=0;
        native_pc=28;native_end_take=1;step;native_end_take=0;
        if(!head_fault||head_done||head_valid||head_handoff||!head_pending)
            $fatal(1,"HEAD without fresh argmax not refused");
        if(fault||good_fault||stage_done||good_done)$fatal(1,"END substituted for wholeplan/fences");
        step;native_next_token=21'h777;native_next_value=32'h11111111;
        coverage_valid=1;coverage_wholeplan_complete=1;visibility_valid=1;visibility=5'b11110;
        step;if(stage_done||good_done)$fatal(1,"missing real fence admitted");
        visibility=5'b11111;#1;
        if(!stage_done||!stage_handoff_done||!terminal_kind||token_result_valid)
            $fatal(1,"legitimate no-argmax handoff refused or claimed token validity");
        if(!good_done||!good_valid||good_kind||good_handoff||good_fault)
            $fatal(1,"strict real HEAD result unavailable");
        if(stage_next_token!=21'h13579||stage_next_value!=32'hdeadbeef||
           good_token!=21'h13579||good_value!=32'hdeadbeef)
            $fatal(1,"native raw payload fabricated or overwritten");
        repeat(2)begin step;if(!stage_handoff_done||token_result_valid||!good_valid)$fatal(1,"typed hold lost");end
        stage_accepted=1;step;stage_accepted=0;
        if(pending||good_pending||stage_done||good_done||token_result_valid||good_valid)
            $fatal(1,"typed acceptance failed to retire exact old request");
        if(!head_fault||!head_pending)$fatal(1,"HEAD refusal debt erased");
        $display("WF_TYPED_COMPLETION PASS handoff_without_argmax/head_refusal/strict_head/missing_coverage_fence/native_payload/hold/accept/defaultoff");
        $finish;
    end
endmodule
