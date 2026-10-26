`timescale 1ns/1ps
module tb_hbm_ep_calendar_host;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cfg_we=0,start_v=0;
    reg [9:0] cfg_addr=0,start_base=0;
    reg [255:0] cfg_data=0;
    reg [10:0] start_limit=0;
    reg [15:0] start_loops=0;
    wire [186:0] calendar;
    wire calendar_v,active,done,fault;
    // Actual F20 host programme collar and mapped SRAM, as host_completion.json.
    reg desc_v=0,launch_v=0;
    reg [11:0] desc_base=0;
    reg [12:0] desc_limit=0;
    reg [15:0] desc_loops=0;
    wire p_we,p_start,configured,target_fault;
    wire [9:0] p_addr,p_base;
    wire [255:0] p_data;
    wire [10:0] p_limit;
    wire [15:0] p_loops;
    ot_static_program_target #(.TARGET(132),.PCW(10)) collar(
        .clk(clk),.rst_n(rst_n),.cfg_v(cfg_we),.cfg_target(8'd132),.cfg_addr({2'b0,cfg_addr}),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .program_active(active),.program_cfg_we(p_we),.program_cfg_addr(p_addr),.program_cfg_data(p_data),
        .program_start_v(p_start),.program_start_base(p_base),.program_start_limit(p_limit),
        .program_start_loops(p_loops),.configured(configured),.fault(target_fault));
    wire [31:0] ordinal;
    wire [9:0] client_seq,response_seq;
    wire [4:0] response_enable;
    wire [7:0] bank_enable,rslot_v,wslot_v;
    wire [23:0] bank_client,rslot,wslot,lg_local_read,lg_local_write;
    wire [1:0] hub_ring_enable,ring_tx_enable;
    wire [5:0] hub_ring_client,ring_tx_source;
    wire replay_enable,replay_source;
    hfd_hgi_vm_calendar dut(.clk(clk),.rst_n(rst_n),.cfg_we(p_we),.cfg_addr(p_addr),.cfg_data(p_data),
        .start_v(p_start),.start_base(p_base),.start_limit(p_limit),.start_loops(p_loops),
        .calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault),
        .client_seq(client_seq),.response_seq(response_seq),.response_enable(response_enable),
        .bank_enable(bank_enable),.bank_client(bank_client),.hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client),
        .rslot_v(rslot_v),.wslot_v(wslot_v),.rslot(rslot),.wslot(wslot),.ring_tx_enable(ring_tx_enable),
        .ring_tx_source(ring_tx_source),.replay_enable(replay_enable),.replay_source(replay_source),
        .lg_local_read(lg_local_read),.lg_local_write(lg_local_write));
    assign calendar={lg_local_write,lg_local_read,replay_source,replay_enable,ring_tx_source,ring_tx_enable,wslot,rslot,
                     wslot_v,rslot_v,hub_ring_client,hub_ring_enable,bank_client,bank_enable,response_seq,response_enable,client_seq};
    integer count=0,cycle=0,launch=-1;
    reg watching=0;
    function automatic [186:0] pattern(input integer pc_);
        pattern={66'h23456781234567890,64'h19283746aa55cc99,64'hf0ef1e2d3c4b5a69} ^ (187'(pc_)*187'h178951178951178951178951178951178951);
    endfunction
    task automatic step;
        begin
            @(posedge clk);#1;cycle++;
            if(watching)begin
                if(count<1536 && cycle>=launch+6)begin
                    if(!calendar_v)$fatal(1,"CALENDAR missing fixed edge %0d",count);
                    if(calendar!==pattern(5+count%3) || ordinal!==32'(count))$fatal(1,"CALENDAR wrong fixed word %0d",count);
                    count++;
                end else if(calendar_v)$fatal(1,"CALENDAR unexpected edge");
                if(done && count!=1536)$fatal(1,"CALENDAR early done");
            end
        end
    endtask
    initial begin
        step();@(negedge clk);rst_n=1;repeat(3)step();
        for(integer p=5;p<8;p++)begin
            @(negedge clk);cfg_we=1;cfg_addr=10'(p);cfg_data=0;
            cfg_data[255:240]=16'hc7a1;cfg_data[233:224]=10'(p);cfg_data[186:0]=pattern(p);if(MUT==1 && p==6)cfg_data[2]=~cfg_data[2];step();
        end
        @(negedge clk);cfg_we=0;repeat(5)step();
        desc_v=1;desc_base=5;desc_limit=8;desc_loops=(MUT==2)?511:512;step();@(negedge clk);desc_v=0;
        repeat(8)step();if(!configured||target_fault)$fatal(1,"host descriptor install failed");
        launch_v=1;launch=cycle+1;watching=1;step();@(negedge clk);launch_v=0;
        while(count<1536)step();
        if(!done || fault)$fatal(1,"CALENDAR completion/fault");
        step();if(calendar_v || calendar!=0)$fatal(1,"CALENDAR repeated last active slot");
        watching=0;
        // A non-programmed range still consumes its exact reserved cycles and
        // faults rather than waiting for memory initialization or replaying.
        @(negedge clk);desc_v=1;desc_base=64;desc_limit=65;desc_loops=1;step();
        @(negedge clk);desc_v=0;repeat(8)step();
        if(configured || !target_fault)$fatal(1,"uninstalled programme range advertised ready");
        launch_v=1;step();@(negedge clk);launch_v=0;repeat(6)step();
        if(calendar_v || calendar!=0 || !target_fault)$fatal(1,"host calendar uninstalled range not fail closed");
        $display("EP_CALENDAR_HOST PASS1536 gapless slots512 wraps actual host target and programme SRAM startup6edges missing-row rejection");$finish;
    end
endmodule
