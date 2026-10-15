`timescale 1ns/1ps
module tb_hgi_hc_row_loop_counter;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cfg_we=0,start_v=0;
    reg [10:0] cfg_addr=0;
    reg [255:0] cfg_data=0;
    reg [11:0] start_limit=0;
    reg [15:0] start_loops=24;
    reg [255:0] image[0:2047];
    wire [50:0] actual,reference;
    wire [2:0] actual_status,reference_status;
    integer cycle=0,compared=0,starts=0,idles=0,leaks=0;
    reg mutant=0;
    // Fault-inject the actual row-identity state, not the checker output.
    always @(negedge clk)
        if(mutant && dut.v && dut.ordinal==1400)force dut.current_row=5'd7;
    wire [50:0] observed=actual;
    ot_hgi_hc_programme_mtp_static #(.ROW_LOOP(1)) dut(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(11'd0),.start_limit(start_limit),.start_loops(start_loops),
        .clear(actual[0]),.row_launch(actual[1]),.row_raw_read(actual[2]),.row_weight_slot(actual[3]),
        .row_id(actual[8:4]),.tail_launch(actual[9]),.sink_launch(actual[10]),.sink_capture(actual[11]),
        .norm_eps(actual[43:12]),.row_npos(actual[47:44]),.tail_position(actual[50:48]),
        .active(actual_status[0]),.done(actual_status[1]),.fault(actual_status[2]));
    ot_hgi_hc_programme_mtp_static_div_reference #(.ROW_LOOP(1)) ref_(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(11'd0),.start_limit(start_limit),.start_loops(start_loops),
        .clear(reference[0]),.row_launch(reference[1]),.row_raw_read(reference[2]),.row_weight_slot(reference[3]),
        .row_id(reference[8:4]),.tail_launch(reference[9]),.sink_launch(reference[10]),.sink_capture(reference[11]),
        .norm_eps(reference[43:12]),.row_npos(reference[47:44]),.tail_position(reference[50:48]),
        .active(reference_status[0]),.done(reference_status[1]),.fault(reference_status[2]));
    task tick;
        begin
            @(posedge clk);#1;
            if(rst_n)begin
                if(actual_status!==reference_status || actual_status[2])$fatal(1,"status/PC identity fault cycle=%0d",cycle);
                if(dut.v!==ref_.v || dut.ordinal!==ref_.ordinal || dut.raw!==ref_.raw)$fatal(1,"programme controls differ cycle=%0d",cycle);
                if(dut.v)begin
                    if(observed!==reference)$fatal(1,"valid51 mismatch cycle=%0d ordinal=%0d got=%h expected=%h",cycle,dut.ordinal,observed,reference);
                    compared=compared+1;
                end else begin
                    if(actual!==0)$fatal(1,"nonzero idle51 cycle=%0d",cycle);
                    idles=idles+1;
                    if(reference!==0)begin
                        if(leaks<4)$display("PRESERVED_DIV_IDLE_LEAK cycle=%0d ordinal=%0d raw=%h oldpins=%h newpins=%h",cycle,ref_.ordinal,ref_.raw,reference,actual);
                        leaks=leaks+1;
                    end
                end
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    task load(input integer n);
        integer period;
        begin
            period=n==6?1080:1400;
            if(n==6)$readmemh("n6.mem",image,0,period-1);else $readmemh("n8.mem",image,0,period-1);
            for(integer i=0;i<period;i=i+1)begin cfg_we=1;cfg_addr=11'(i);cfg_data=image[i];tick();end
            cfg_we=0;tick();tick();start_limit=12'(period);
        end
    endtask
    task run24;
        begin
            start_v=1;starts=starts+1;tick();start_v=0;tick();
            while(!actual_status[1])tick();
            if(dut.ordinal!=24*int'(start_limit)-1)$fatal(1,"last ordinal mismatch");
        end
    endtask
    initial begin
        mutant=$test$plusargs("MUTANT");
        repeat(8)tick();rst_n=1;repeat(5)tick();
        load(6);run24();run24();repeat(6)tick();
        // Reset interrupts an actual running programme, then restart full shape.
        start_v=1;starts=starts+1;tick();start_v=0;repeat(1500)tick();
        rst_n=0;repeat(6)tick();rst_n=1;repeat(6)tick();
        load(8);run24();run24();repeat(8)tick();
        if(compared!=2*24*(1080+1400)+1497)$fatal(1,"coverage differs valid=%0d",compared);
        if(leaks==0)$fatal(1,"idle leak diagnostic missing");
        $display("HC_ROW_COUNTER PASS valid51_cycles=%0d full24row_programmes=4 starts=%0d idle_zero_cycles=%0d preserved_idle_leaks=%0d reset_during_programme=1 back_to_back=1",compared,starts,idles,leaks);
        $finish;
    end
endmodule
