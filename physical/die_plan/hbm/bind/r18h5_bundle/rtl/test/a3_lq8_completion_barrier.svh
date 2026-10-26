    wire core_busy,core_done,lifetime_clear,compute_abort,transport_cancel;
    wire lifetime_ready,lifetime_done;
    wire [31:0] completion_generation,transport_generation;
    wire [7:0] lifetime_error;
    reg [3:0] transport_wait=0,write_wait=0;
    wire transport_ack=transport_cancel && transport_wait==5;
    wire writes_drained=write_wait==9;
    ot_a3_runtime_operation_lifetime lifetime(
        .clk(clk),.rst_n(rst_n),.start( start_dut ),.start_ready(lifetime_ready),
        .command_generation(generation+1'b1),.compute_done(core_done),.compute_error(dut_error_code),
        .service_fault(protocol_error || (geometry_error && operand_request)),.abort_valid(1'b0),
        .transport_ack(transport_ack),.writes_drained(writes_drained),
        .transport_cancel(transport_cancel),.transport_generation(transport_generation),
        .service_clear(lifetime_clear),.compute_abort(compute_abort),.busy(dut_busy),
        .completion_valid(lifetime_done),.completion_ready(1'b1),
        .completion_generation(completion_generation),.completion_error(lifetime_error));
    assign dut_done=lifetime_done;
    always @(posedge clk)begin
        if(!rst_n || start_dut)begin transport_wait<=0;write_wait<=0;end
        else begin
            if(transport_cancel && transport_wait!=5)transport_wait<=transport_wait+1'b1;
            if(lifetime_clear && write_wait!=9)write_wait<=write_wait+1'b1;
            if(dut_done && (!writes_drained || transport_wait!=5 || completion_generation!=generation || lifetime_error!=dut_error_code))
                $fatal(1,"completion preceded generation drain or write acknowledgement");
            if(start_dut && !lifetime_ready)$fatal(1,"command while previous lifetime owned");
            // Corpus faults arrive from compute; service-fault abort behavior
            // is exercised separately by the controller lifecycle unit test.
            if(compute_abort)$fatal(1,"unexpected runtime protocol abort");
        end
    end
