`timescale 1ns/1ps
module tb_stage_top;
    reg aon_clk=0, core_clk=0, aon_rst_n=0, core_rst_n=0;
    always #7 aon_clk=~aon_clk;
    always #5 core_clk=~core_clk;
    integer failures=0;
    reg host_cmd_valid=0; reg [255:0] host_cmd_record=0;
    wire host_cmd_ready; wire host_rsp_valid; reg host_rsp_ready=1; wire [127:0] host_rsp_record;
    reg csr_req_valid=0; reg [127:0] csr_req_record=0; wire csr_req_ready;
    wire csr_rsp_valid; wire [127:0] csr_rsp_record; reg csr_rsp_ready=1;
    wire telemetry_valid; wire [127:0] telemetry_record; reg telemetry_ready=1;
    wire service_start_valid; reg service_start_ready=0;
    wire [15:0] service_transaction_id; wire [23:0] service_session_id;
    wire [6:0] service_first_layer, service_last_layer; wire [15:0] service_batch_minus_one;
    wire [3:0] service_draft_tokens; wire service_poison;
    reg service_done_valid=0; reg [7:0] service_done_status=0, service_done_error_source=0; reg [3:0] service_done_syndrome=0;
    reg power_good=1, clock_stable=1, hbm_ready=1, link_ready=1, bist_done=1, bist_pass=1;
    reg thermal_warning=0, thermal_fatal=0, fatal_error=0, requalify=0, test_enable=0;
    reg abort_valid=0; reg [15:0] abort_transaction_id=0;
    wire [3:0] power_state; wire safe_state, stage_idle, admission_block;
    reg schedule_wr_valid=0; reg [7:0] schedule_wr_slot=0; reg [15:0] schedule_wr_data=0;
    reg schedule_commit_req=0, schedule_manifest_crc_ok=1;
    wire schedule_wr_ready, schedule_wr_ack, schedule_wr_error;
    wire schedule_commit_ready, schedule_commit_ack, schedule_commit_error, schedule_valid;

    ot_stage_top #(.SESSION_ENTRIES(4),.CREDIT_SINKS(2),.CREDIT_DEPTH(4),
                   .SCHEDULE_SLOTS(4),.SCHEDULE_PORTS(8)) dut (
        .aon_clk(aon_clk),.core_clk(core_clk),.aon_rst_n(aon_rst_n),.core_rst_n(core_rst_n),
        .host_cmd_valid(host_cmd_valid),.host_cmd_ready(host_cmd_ready),.host_cmd_record(host_cmd_record),
        .host_rsp_valid(host_rsp_valid),.host_rsp_ready(host_rsp_ready),.host_rsp_record(host_rsp_record),
        .telemetry_valid(telemetry_valid),.telemetry_ready(telemetry_ready),.telemetry_record(telemetry_record),
        .csr_req_valid(csr_req_valid),.csr_req_ready(csr_req_ready),.csr_req_record(csr_req_record),
        .csr_rsp_valid(csr_rsp_valid),.csr_rsp_ready(csr_rsp_ready),.csr_rsp_record(csr_rsp_record),
        .image_slot_valid(256'b1),.service_start_valid(service_start_valid),.service_start_ready(service_start_ready),
        .service_transaction_id(service_transaction_id),.service_session_id(service_session_id),
        .service_first_layer(service_first_layer),.service_last_layer(service_last_layer),
        .service_batch_minus_one(service_batch_minus_one),.service_draft_tokens(service_draft_tokens),
        .service_poison(service_poison),.service_done_valid(service_done_valid),.service_done_status(service_done_status),
        .service_done_error_source(service_done_error_source),.service_done_syndrome(service_done_syndrome),
        .power_good(power_good),.clock_stable(clock_stable),.hbm_ready(hbm_ready),.link_ready(link_ready),
        .bist_done(bist_done),.bist_pass(bist_pass),.thermal_warning(thermal_warning),.thermal_fatal(thermal_fatal),
        .fatal_error(fatal_error),.requalify(requalify),.test_enable(test_enable),.abort_valid(abort_valid),
        .abort_transaction_id(abort_transaction_id),.power_state(power_state),.safe_state(safe_state),
        .stage_idle(stage_idle),.admission_block(admission_block),.schedule_wr_valid(schedule_wr_valid),
        .schedule_wr_slot(schedule_wr_slot),.schedule_wr_data(schedule_wr_data),
        .schedule_wr_ready(schedule_wr_ready),.schedule_wr_ack(schedule_wr_ack),
        .schedule_wr_error(schedule_wr_error),.schedule_commit_req(schedule_commit_req),
        .schedule_commit_ready(schedule_commit_ready),
        .schedule_manifest_crc_ok(schedule_manifest_crc_ok),.schedule_commit_ack(schedule_commit_ack),
        .schedule_commit_error(schedule_commit_error),.schedule_valid(schedule_valid));

    function automatic [15:0] crc16_112;
        input [111:0] d; integer by,bi; reg [15:0] c; reg fb;
        begin c=16'hffff; for(by=0;by<14;by=by+1) for(bi=7;bi>=0;bi=bi-1) begin fb=c[15]^d[by*8+bi]; c={c[14:0],1'b0}; if(fb)c=c^16'h1021; end crc16_112=c; end
    endfunction
    function automatic [15:0] crc16_240;
        input [239:0] d; integer by,bi; reg [15:0] c; reg fb;
        begin c=16'hffff; for(by=0;by<30;by=by+1) for(bi=7;bi>=0;bi=bi-1) begin fb=c[15]^d[by*8+bi]; c={c[14:0],1'b0}; if(fb)c=c^16'h1021; end crc16_240=c; end
    endfunction

    task automatic csr_write_control;
        reg [111:0] b;
        begin
            b=112'b0; b[1:0]=2'd1; b[4:2]=3'd3; b[23:8]=16'h0020; b[31:24]=8'hff; b[95:32]=64'h1; b[111:96]=16'h55;
            csr_req_record={crc16_112(b),b};
            @(negedge aon_clk); csr_req_valid=1;
            while(!csr_req_ready) @(negedge aon_clk);
            @(negedge aon_clk); csr_req_valid=0;
            wait(csr_rsp_valid); @(negedge aon_clk);
            if(csr_rsp_record[7:0]!==8'h00) begin $display("FAIL CSR status %h",csr_rsp_record[7:0]); failures=failures+1; end
        end
    endtask

    reg [7:0] command_epoch=0;
    task automatic send_cmd;
        input [7:0] op; input [23:0] sid; input [31:0] ck;
        reg [239:0] b;
        begin
            b=240'b0; b[7:0]=op; b[15:8]=8'h04; b[23:16]=8'h01; b[31:24]=0; b[39:32]=command_epoch;
            b[47:40]=0; b[71:48]=sid; b[91:72]=0; b[111:92]=20'd8191; b[127:112]=0;
            b[134:128]=0; b[141:135]=0; b[145:142]=0; b[153:146]=0; b[201:154]=0; b[233:202]=ck;
            host_cmd_record={crc16_240(b),b};
            @(negedge aon_clk); host_cmd_valid=1;
            while(!host_cmd_ready) @(negedge aon_clk);
            @(negedge aon_clk); host_cmd_valid=0;
        end
    endtask

    integer schedule_wr_acks=0, schedule_wr_errors=0;
    integer schedule_commit_acks=0, schedule_commit_errors=0;
    always @(posedge aon_clk) begin
        if (schedule_wr_ack) schedule_wr_acks= schedule_wr_acks + 1;
        if (schedule_wr_error) schedule_wr_errors = schedule_wr_errors + 1;
        if (schedule_commit_ack) schedule_commit_acks = schedule_commit_acks + 1;
        if (schedule_commit_error) schedule_commit_errors = schedule_commit_errors + 1;
    end

    task automatic schedule_write;
        input [7:0] slot;
        input [15:0] data;
        input expect_error;
        integer ack_before, error_before, wait_cycles;
        begin
            ack_before=schedule_wr_acks; error_before=schedule_wr_errors;
            @(negedge aon_clk);
            schedule_wr_slot=slot; schedule_wr_data=data; schedule_wr_valid=1;
            while(!schedule_wr_ready) @(negedge aon_clk);
            @(negedge aon_clk); schedule_wr_valid=0;
            wait_cycles=0;
            while(schedule_wr_acks==ack_before && schedule_wr_errors==error_before && wait_cycles<80) begin
                @(negedge aon_clk); wait_cycles=wait_cycles+1;
            end
            if(expect_error) begin
                if(schedule_wr_errors!=error_before+1 || schedule_wr_acks!=ack_before) begin
                    $display("FAIL schedule write expected error"); failures=failures+1;
                end
            end else if(schedule_wr_acks!=ack_before+1 || schedule_wr_errors!=error_before) begin
                $display("FAIL schedule write expected ack"); failures=failures+1;
            end
        end
    endtask

    task automatic schedule_commit;
        input crc_ok;
        input expect_error;
        integer ack_before, error_before, wait_cycles;
        begin
            ack_before=schedule_commit_acks; error_before=schedule_commit_errors;
            @(negedge aon_clk);
            schedule_manifest_crc_ok=crc_ok; schedule_commit_req=1;
            while(!schedule_commit_ready) @(negedge aon_clk);
            @(negedge aon_clk); schedule_commit_req=0;
            wait_cycles=0;
            while(schedule_commit_acks==ack_before && schedule_commit_errors==error_before && wait_cycles<120) begin
                @(negedge aon_clk); wait_cycles=wait_cycles+1;
            end
            if(expect_error) begin
                if(schedule_commit_errors!=error_before+1 || schedule_commit_acks!=ack_before) begin
                    $display("FAIL schedule commit expected error"); failures=failures+1;
                end
            end else if(schedule_commit_acks!=ack_before+1 || schedule_commit_errors!=error_before) begin
                $display("FAIL schedule commit expected ack"); failures=failures+1;
            end
        end
    endtask

    task automatic launch_schedule_commit;
        input crc_ok;
        begin
            @(negedge aon_clk);
            schedule_manifest_crc_ok=crc_ok; schedule_commit_req=1;
            while(!schedule_commit_ready) @(negedge aon_clk);
            @(negedge aon_clk); schedule_commit_req=0;
        end
    endtask

    integer responses=0; reg service_pending=0; reg allow_service_done=1;
    always @(posedge core_clk) begin
        service_start_ready <= service_start_valid;
        if(service_start_valid) service_pending <= 1;
        if(service_pending && allow_service_done) begin
            service_done_valid <= 1; service_done_status<=0; service_done_error_source<=0; service_done_syndrome<=0; service_pending<=0;
        end else service_done_valid<=0;
    end
    always @(posedge aon_clk) if(host_rsp_valid && host_rsp_ready) begin
        responses=responses+1; $display("host response %0d status=%h opcode=%h cookie=%h",responses,host_rsp_record[7:0],host_rsp_record[15:8],host_rsp_record[107:76]);
        if(host_rsp_record[7:0]!==8'h00) failures=failures+1;
    end

    initial begin
        repeat(5) @(negedge aon_clk); aon_rst_n=1; core_rst_n=1;
        repeat(12) @(negedge aon_clk);

        // An out-of-range write returns an error but does not poison the bank.
        schedule_write(8'd7,16'h0009,1'b1);
        schedule_write(8'd0,16'h0009,1'b0);
        schedule_commit(1'b0,1'b1);
        if(schedule_valid) begin
            $display("FAIL bad-manifest commit made schedule valid"); failures=failures+1;
        end
        schedule_commit(1'b1,1'b0);
        repeat(8) @(negedge aon_clk);
        if(!schedule_valid || dut.active_epoch!==8'd1) begin
            $display("FAIL first schedule activation valid=%b epoch=%0d",schedule_valid,dut.active_epoch);
            failures=failures+1;
        end

        command_epoch=8'd1;
        csr_write_control();
        repeat(12) @(negedge aon_clk); send_cmd(8'h01,24'h1,32'hcafe0001);
        while(responses<1) @(negedge aon_clk);

        // Prepare the next shadow bank, then issue its commit while a real
        // service transaction holds the stage non-quiescent.
        schedule_write(8'd1,16'h000a,1'b0);
        allow_service_done=0;
        send_cmd(8'h10,24'h1,32'hcafe0002);
        while(!service_pending || stage_idle) @(negedge core_clk);
        launch_schedule_commit(1'b1);
        while(!dut.schedule.commit_pending) @(negedge core_clk);
        repeat(12) @(negedge aon_clk);
        if(schedule_commit_acks!=1 || schedule_commit_errors!=1 || dut.active_epoch!==8'd1) begin
            $display("FAIL commit did not remain blocked while stage busy"); failures=failures+1;
        end
        allow_service_done=1;
        while(schedule_commit_acks<2) @(negedge aon_clk);
        while(responses<2) @(negedge aon_clk);
        repeat(20) @(negedge aon_clk);
        if(dut.active_epoch!==8'd2 || schedule_commit_acks!=2) begin
            $display("FAIL commit duplicated or epoch mismatch epoch=%0d acks=%0d",dut.active_epoch,schedule_commit_acks);
            failures=failures+1;
        end
        if(responses<2) begin $display("FAIL expected responses got %0d",responses); failures=failures+1; end
        if(schedule_wr_acks!=2 || schedule_wr_errors!=1 || schedule_commit_errors!=1) begin
            $display("FAIL schedule response accounting wa=%0d we=%0d ca=%0d ce=%0d",
                     schedule_wr_acks,schedule_wr_errors,schedule_commit_acks,schedule_commit_errors);
            failures=failures+1;
        end
        if(failures==0) begin $display("PASS: stage top command/session/service and schedule CDC integration"); $finish; end
        $fatal(1,"%0d failures",failures);
    end
endmodule
