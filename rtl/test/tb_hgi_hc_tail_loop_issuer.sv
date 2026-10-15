`timescale 1ns/1ps
module tb_hgi_hc_tail_loop_issuer;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cfg_we=0,start_v=0;
    reg [10:0] cfg_addr=0;
    reg [255:0] cfg_data=0;
    reg [15:0] loops=6;
    wire [50:0] c,legacy;
    wire [2:0] status,legacy_status;
    reg [255:0] image[0:496];
    integer cycle=0,valid_edges=0,idle_edges=0,launches=0,sinks=0,captures=0,starts=0;
    integer ordinal=0,run_first=0,run_launches=0;
    reg mutant=0;
    always @(negedge clk)if(mutant&&dut.v&&dut.ordinal==496)force dut.current_tail=3'd6;
    ot_hgi_hc_programme_mtp_static #(.TAIL_LOOP(1)) dut(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(11'd0),.start_limit(12'd497),.start_loops(loops),
        .clear(c[0]),.row_launch(c[1]),.row_raw_read(c[2]),.row_weight_slot(c[3]),.row_id(c[8:4]),
        .tail_launch(c[9]),.sink_launch(c[10]),.sink_capture(c[11]),.norm_eps(c[43:12]),.row_npos(c[47:44]),.tail_position(c[50:48]),
        .active(status[0]),.done(status[1]),.fault(status[2]));
    ot_hgi_hc_programme_mtp_static #(.TAIL_LOOP(0)) old_(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(11'd0),.start_limit(12'd497),.start_loops(loops),
        .clear(legacy[0]),.row_launch(legacy[1]),.row_raw_read(legacy[2]),.row_weight_slot(legacy[3]),.row_id(legacy[8:4]),
        .tail_launch(legacy[9]),.sink_launch(legacy[10]),.sink_capture(legacy[11]),.norm_eps(legacy[43:12]),.row_npos(legacy[47:44]),.tail_position(legacy[50:48]),
        .active(legacy_status[0]),.done(legacy_status[1]),.fault(legacy_status[2]));
    task tick;
        reg [50:0] expected;
        begin
            @(posedge clk);
            // Consumer clocks: fixed seven-core-edge phase, not tail-done feedback.
            if(rst_n&&dut.v&&c[10]&&(cycle%7)!=0)$fatal(1,"sink phase error");
            #1;
            if(rst_n)begin
                if(status!==legacy_status||status[2])$fatal(1,"status/PC fault");
                if(dut.v!==old_.v||dut.ordinal!==old_.ordinal||dut.raw!==old_.raw)$fatal(1,"raw programme control mismatch");
                if(dut.v)begin
                    expected=image[ordinal%497][50:0];
                    if(ordinal%497==0)expected[50:48]=3'(ordinal/497);
                    if(c!==expected)$fatal(1,"tail counter/slot mismatch ordinal=%0d got=%h expected=%h",ordinal,c,expected);
                    if((c&51'h0ffffffffffff)!==(legacy&51'h0ffffffffffff))$fatal(1,"non-position control changed");
                    if(dut.ordinal!=32'(ordinal))$fatal(1,"ordinal identity mismatch");
                    if(c[9])begin launches=launches+1;run_launches=run_launches+1;end
                    if(c[10])sinks=sinks+1;
                    if(c[11])captures=captures+1;
                    ordinal=ordinal+1;valid_edges=valid_edges+1;
                end else begin
                    if(c!==0)$fatal(1,"nonzero idle51pins");idle_edges=idle_edges+1;
                end
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    task execute(input integer n);
        begin
            // Align first HC consumer edge start+5 to phase0 modulo7.
            while((cycle+5)%7!=0)tick();
            ordinal=0;run_launches=0;loops=16'(n);start_v=1;starts=starts+1;tick();start_v=0;
            while(!status[1])tick();
            if(ordinal!=n*497||run_launches!=n)$fatal(1,"incomplete repeated tail");
        end
    endtask
    initial begin
        mutant=$test$plusargs("MUTANT");$readmemh("tail_n8.mem",image,0,496);
        repeat(8)tick();rst_n=1;
        for(integer i=0;i<497;i=i+1)begin cfg_we=1;cfg_addr=11'(i);cfg_data=image[i];tick();end
        cfg_we=0;repeat(3)tick();
        execute(6);execute(8);
        rst_n=0;repeat(6)tick();rst_n=1;repeat(3)tick();execute(8);execute(6);
        repeat(8)tick();
        if(launches!=28||sinks!=28||captures!=28||starts!=4)$fatal(1,"missing production events");
        $display("HC_TAIL_LOOP PASS valid51_edges=%0d launches=%0d sink_slots=%0d capture_slots=%0d idle_zero_edges=%0d starts=%0d period497 sink_phase7 reset=1 consecutive_starts=1",valid_edges,launches,sinks,captures,idle_edges,starts);
        $finish;
    end
endmodule
