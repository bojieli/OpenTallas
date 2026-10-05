`timescale 1ns/1ps
module tb_wf_stage_completion_join;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,request_v=0,request_binding_valid=0;
    wire request_ready;
    reg [46:0] request_identity=47'h12345;
    reg [13:0] request_terminal_entry=21,request_producer_pc=4,request_end_pc=8;
    reg native_active=1,native_producer_take=0,native_end_take=0,native_done=0,native_am_any=1;
    reg [46:0] native_identity=47'h12345;
    reg [13:0] native_entry=21,native_pc=0;
    reg [20:0] native_next_token=0;
    reg [31:0] native_next_value=0;
    reg coverage_valid=0,coverage_wholeplan_complete=0;
    reg [46:0] coverage_identity=47'h12345;
    reg visibility_valid=0,visibility_fault=0;
    reg [46:0] visibility_identity=47'h12345;
    reg [4:0] visibility=0;
    reg c8_write_quiet=1,c8_quarantine=0,c8_fault=0;
    reg capture_live=0,capture_drained=1,capture_fault=0;
    reg collective_busy=0,collective_fault=0,native_fault=0,stage_accepted=0;
    wire stage_done,pending,fault;
    wire [20:0] stage_next_token;
    wire [31:0] stage_next_value;
    ot_dsrom_wf_stage_completion_join #(.ENABLE(1)) dut(.*);
    wire off_ready,off_done,off_pending,off_fault;
    wire [20:0] off_token; wire [31:0] off_value;
    ot_dsrom_wf_stage_completion_join disabled(
        .request_ready(off_ready),.stage_done(off_done),.stage_next_token(off_token),
        .stage_next_value(off_value),.pending(off_pending),.fault(off_fault),.*);
    // Actual END response ordering: raw native done and result change AFTER
    // the terminal edge, exactly as the selected native core's registers do.
    always @(posedge clk) if(native_end_take) begin
        native_done<=1;native_next_token<=21'h13579;native_next_value<=32'hdeadbeef;
    end
    task step; begin @(posedge clk); #1;
        if(off_ready||off_done||off_pending||off_fault||off_token||off_value)
            $fatal(1,"default-off join active");
    end endtask
    task idle_check; begin #1;if(stage_done)$fatal(1,"premature whole-stage completion");step;end endtask
    task request; begin
        request_v=1;#1;if(!request_ready)$fatal(1,"bound request not ready");step;request_v=0;
        if(!pending)$fatal(1,"accepted request lost");
    end endtask
    task producer(input [13:0] pc); begin
        native_pc=pc;native_producer_take=1;step;native_producer_take=0;
    end endtask
    task terminal; begin native_pc=8;native_end_take=1;step;native_end_take=0;end endtask
    integer testcase;
    initial begin
        testcase=0; if($value$plusargs("case=%d",testcase)) begin end
        step;step;rst_n=1;
        request_v=1;step;
        if(request_ready||pending)$fatal(1,"unbound source admitted");
        request_v=0;request_binding_valid=1;request;
        if(testcase!=0) begin
            coverage_valid=1;coverage_wholeplan_complete=1;
            visibility_valid=1;visibility=5'b11111;
            if(testcase==1) begin
                producer(5);terminal;
                if(!fault||!pending||stage_done)$fatal(1,"foreign producer accepted or debt erased");
            end else begin
                producer(4);terminal;
                if(!stage_done)$fatal(1,"native completion bypass missing");
                native_fault=1;#1;
                if(stage_done)$fatal(1,"fault did not suppress unaccepted completion");step;
                if(!fault||!pending)$fatal(1,"fault failed to preserve debt");
            end
        end else begin
            native_done=1;repeat(3)idle_check;
            native_entry=99;native_end_take=1;step;native_end_take=0;
            if(stage_done||fault)$fatal(1,"fragment END treated as terminal");
            native_entry=21;native_done=0;producer(4);terminal;
            if(stage_done)$fatal(1,"END substituted for coverage/visibility");
            step;native_next_token=21'h777;native_next_value=32'h11111111;
            coverage_valid=1;coverage_wholeplan_complete=1;coverage_identity=47'h999;
            idle_check;coverage_identity=request_identity;coverage_wholeplan_complete=0;idle_check;
            coverage_wholeplan_complete=1;idle_check;
            visibility_valid=1;visibility=5'b11110;idle_check;
            visibility=5'b11111;visibility_identity=47'h999;idle_check;
            visibility_identity=request_identity;c8_write_quiet=0;idle_check;
            c8_write_quiet=1;capture_live=1;idle_check;
            capture_live=0;capture_drained=0;idle_check;
            capture_drained=1;collective_busy=1;idle_check;collective_busy=0;#1;
            if(!stage_done||stage_next_token!=21'h13579||stage_next_value!=32'hdeadbeef)
                $fatal(1,"held exact native result lost");
            // Stall keeps the captured old result despite changing raw ports.
            repeat(4) begin step;
                if(!stage_done||stage_next_value!=32'hdeadbeef)$fatal(1,"stalled result overwritten");
            end
            // Actual old acceptance and new request share an edge.
            stage_accepted=1;request_v=1;request_identity=47'h23456;#1;
            if(!request_ready||stage_next_value!=32'hdeadbeef)$fatal(1,"old/new edge ownership");
            step;request_v=0;stage_accepted=0;
            native_identity=request_identity;coverage_identity=request_identity;visibility_identity=request_identity;
            native_done=0;if(!pending||stage_done)$fatal(1,"same-edge new request lost");
            producer(4);terminal;
            if(!stage_done||stage_next_value!=32'hdeadbeef)$fatal(1,"added completion response edge");
            stage_accepted=1;step;stage_accepted=0;
            if(pending||stage_done)$fatal(1,"accepted result retained as new debt");
            request_identity=47'h34567;native_identity=request_identity;
            coverage_identity=request_identity;visibility_identity=request_identity;native_done=0;
            request;producer(4);terminal;step;
            rst_n=0;step;rst_n=1;step;
            if(!fault||!pending||stage_done||request_ready||stage_next_value!=32'hdeadbeef)
                $fatal(1,"warm reset erased retained debt/result or permitted retirement");
        end
        $display("WF_COMPLETION_JOIN PASS case=%0d defaultoff/missingauthority/identity/nativeEND/result/hold/accept/reissue/reset/fault",testcase);
        $finish;
    end
endmodule
