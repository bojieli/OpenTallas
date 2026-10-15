`timescale 1ns/1ps
module tb_smh_calendar_static;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cfg_we=0,start_v=0;
    reg [9:0] cfg_addr=0,start_base=0;
    reg [255:0] cfg_data=0;
    reg [10:0] start_limit=0;
    reg [15:0] start_loops=0;
    wire [82:0] calendar;
    wire calendar_v,active,done,fault;
    wire [31:0] ordinal;
    ot_smh_calendar_static #(.W(83),.MUT(MUT)) dut(.*);
    integer count=0,cycle=0,launch=-1;
    reg watching=0;
    function automatic [82:0] pattern(input integer pc_);
        pattern=83'h567812345678901234569 ^ (83'(pc_)*83'h178951178951178951178951178951178951);
    endfunction
    task automatic step;
        begin
            @(posedge clk);#1;cycle++;
            if(watching)begin
                if(count<1536 && cycle>=launch+4)begin
                    if(!calendar_v)$fatal(1,"CALENDAR missing fixed edge %0d",count);
                    if(calendar!==pattern(5+count%3) || ordinal!==32'(count))$fatal(1,"CALENDAR wrong fixed word %0d",count);
                    count++;
                end else if(calendar_v)$fatal(1,"CALENDAR unexpected edge");
                if(done && count!=1536)$fatal(1,"CALENDAR early done");
            end
        end
    endtask
    initial begin
        step();@(negedge clk);rst_n=1;
        for(integer p=5;p<8;p++)begin
            @(negedge clk);cfg_we=1;cfg_addr=10'(p);cfg_data=0;
            cfg_data[255:240]=16'hc7a1;cfg_data[233:224]=10'(p);cfg_data[82:0]=pattern(p);step();
        end
        @(negedge clk);cfg_we=0;start_v=1;start_base=5;start_limit=8;start_loops=512;
        launch=cycle+1;watching=1;step();@(negedge clk);start_v=0;
        while(count<1536)step();
        if(!done || fault)$fatal(1,"CALENDAR completion/fault");
        step();if(calendar_v || calendar!=0)$fatal(1,"CALENDAR repeated last active slot");
        watching=0;
        // A non-programmed range still consumes its exact reserved cycles and
        // faults rather than waiting for memory initialization or replaying.
        @(negedge clk);start_v=1;start_base=64;start_limit=65;start_loops=1;step();
        @(negedge clk);start_v=0;step();step();step();step();
        if(!calendar_v || calendar!=0 || !fault || !done)$fatal(1,"CALENDAR invalid word not fail closed");
        $display("SMH_STATIC_CALENDAR PASS1536 gapless slots512 wraps actual programme SRAM startup4edges invalidword fault");$finish;
    end
endmodule
