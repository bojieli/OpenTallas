`timescale 1ns/1ps
module tb_phase;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cmd_v=0,cmd_short=0,cmd_fault=0,event_v=0,den_v=0;
    reg [15:0] cmd_tag=0,event_tag=0,den_tag=0;
    reg [2:0] event_kind=0;
    wire cmd_ready,event_ready,bf16_upper_half,busy,fault;
    wire [2:0] expected_kind;
    wire [6:0] memory_row;
    wire [15:0] active_tag;
    integer checks=0,cycle=0;
    always @(posedge clk)cycle<=cycle+1;
    ot_dsrom_softmax_phase dut(.*);
    task automatic reset;
        @(negedge clk);rst_n=0;cmd_v=0;event_v=0;den_v=0;cmd_fault=0;
        repeat(2)@(negedge clk);rst_n=1;
        @(posedge clk);#1;if(fault || !cmd_ready || busy)$fatal(1,"RESET");
    endtask
    task automatic command(input short_t,input [15:0] tag_t);
        @(negedge clk);cmd_short=short_t;cmd_tag=tag_t;cmd_v=1;
        @(posedge clk);#1;if(fault || !busy || active_tag!=tag_t)$fatal(1,"COMMAND");
        @(negedge clk);cmd_v=0;event_tag=tag_t;
    endtask
    task automatic inject_event(input [2:0] kind_t);
        @(negedge clk);event_kind=kind_t;event_v=1;
        @(posedge clk);#1;
        event_v=0;
    endtask
    task automatic positive(input short_t,input [15:0] tag_t);
        integer n,base,expected_address,start_cycle;
        command(short_t,tag_t);start_cycle=cycle;
        for(integer phase=0;phase<8;phase=phase+1)begin
            n=(phase<4)?(short_t?8:40):32;
            if(phase==5)begin
                repeat(4)@(negedge clk);
                if(event_ready)$fatal(1,"PV_WITHOUT_DEN");
                den_v=1;den_tag=tag_t;
                @(posedge clk);#1;
                @(negedge clk);den_v=0;
            end
            for(integer i=0;i<n;i=i+1)begin
                // Bound is derived from the controller's two-edge write barrier.
                if(!event_ready)begin repeat(2)begin @(posedge clk);#1;end end
                if(!event_ready || fault || expected_kind!=phase)$fatal(1,"PHASE_READY");
                case(phase)
                  0,1:expected_address=i;
                  2,3:expected_address=72+i;
                  4,5:expected_address=40+i;
                  6,7:expected_address=112+i/2;
                endcase
                if(memory_row!=expected_address || (phase>=6 && bf16_upper_half!=(i%2)))$fatal(1,"ADDRESS");
                if(phase==3 || phase==7)begin
                    repeat(i%4)@(negedge clk);
                    if(active_tag!=tag_t || !busy)$fatal(1,"OWNERSHIP_STALL");
                end
                inject_event(3'(phase));checks=checks+1;
                if(fault)$fatal(1,"POSITIVE_FAULT phase=%0d i=%0d",phase,i);
            end
        end
        if(busy || !cmd_ready)$fatal(1,"RELEASE");
        $display("ROW short=%0d events=%0d elapsed_fixture_cycles=%0d",short_t,short_t?160:288,cycle-start_cycle);
    endtask
    initial begin
        reset();positive(0,16'h3210);positive(1,16'h3211);
        command(0,16'h5555);
        event_tag=16'h5554;inject_event(0);
        if(!fault)$fatal(1,"WRONG_TAG_ESCAPED");checks=checks+1;
        reset();command(0,16'h5556);inject_event(4);
        if(!fault)$fatal(1,"EARLY_PV_ESCAPED");checks=checks+1;
        reset();command(0,16'h5557);
        force dut.count=6'd1;#1;if(!fault)$fatal(1,"COUNTER_UPSET_ESCAPED");
        @(posedge clk);#1;release dut.count;
        if(!fault)$fatal(1,"FAULT_NOT_STICKY");checks=checks+1;
        reset();command(0,16'h5558);
        force dut.state_n=10'd0;#1;if(!fault)$fatal(1,"STATE_UPSET_ESCAPED");
        @(posedge clk);#1;release dut.state_n;checks=checks+1;
        reset();command(0,16'h5559);reset();command(0,16'h555a);
        event_tag=16'h5559;inject_event(0);
        if(!fault)$fatal(1,"STALE_RESET_TAG_ESCAPED");checks=checks+1;
        reset();command(0,16'h555b);
        @(negedge clk);den_v=1;den_tag=16'h555b;
        @(posedge clk);#1;if(!fault)$fatal(1,"EARLY_DEN_ESCAPED");checks=checks+1;
        $display("PASS checks=%0d full128/640 phases, memory addresses, ownership, denominator gate, wrong/stale tags and state/counter upsets",checks);
        $finish;
    end
endmodule
