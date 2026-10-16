`timescale 1ns/1ps
// H-HARDEN 2026-10-15: ONE VM calendar master hfd_hgi_vm_calendar, exact per-quadrant programme playback
// (compiler-generated universal-layout words, every output edge compared) + reset synchroniser release contract:
// asynchronous assert clears outputs at once; a launch inside the two release edges is not seen; a launch after the
// release runs gapless on its exact edges.
module tb_vm_calendar_universal;
    parameter integer RMUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cfg_we=0,start_v=0;
    reg [9:0] cfg_addr=0,start_base=0;
    reg [255:0] cfg_data=0;
    reg [10:0] start_limit=0;
    reg [15:0] start_loops=0;
    wire calendar_v,active,done,fault;
    wire [31:0] ordinal;
    wire [9:0] client_seq; wire [4:0] response_enable; wire [9:0] response_seq; wire [7:0] bank_enable;
    wire [23:0] bank_client; wire [1:0] hub_ring_enable; wire [5:0] hub_ring_client; wire [7:0] rslot_v,wslot_v;
    wire [23:0] rslot,wslot; wire [1:0] ring_tx_enable; wire [5:0] ring_tx_source; wire replay_enable,replay_source;
    wire [23:0] lg_local_read,lg_local_write;
    hfd_hgi_vm_calendar #(.RMUT(RMUT)) dut(.*);
    wire [186:0] got={lg_local_write,lg_local_read,replay_source,replay_enable,ring_tx_source,ring_tx_enable,wslot,rslot,
                      wslot_v,rslot_v,hub_ring_client,hub_ring_enable,bank_client,bank_enable,response_seq,response_enable,client_seq};
    reg [265:0] cfg[0:1023];
    reg [186:0] expect_w[0:65535];
    integer base,limit,loops,nw,edges,fd,r,checked=0;
    task automatic tick; begin @(posedge clk); #1; end endtask
    initial begin
        fd=$fopen("start.txt","r"); r=$fscanf(fd,"%d %d %d %d %d",base,limit,loops,nw,edges); $fclose(fd);
        $readmemh("cfg.hex",cfg); $readmemh("expect.hex",expect_w);
        repeat(3)tick();
        // release; a launch on the first two release edges must not be seen (exceptional initialization window)
        @(negedge clk); rst_n=1; start_v=1; start_base=10'(base); start_limit=11'(limit); start_loops=16'd1;
        tick(); @(negedge clk); start_v=0;
        repeat(8)begin tick(); if(active||calendar_v||fault)$fatal(1,"CALUNI launch inside the reset release window was seen"); end
        // asynchronous assert mid-way clears at once
        @(negedge clk); rst_n=0; #1; if(active||calendar_v||done||fault)$fatal(1,"CALUNI async reset assert");
        @(negedge clk); rst_n=1; tick(); tick();
        for(integer i=0;i<nw;i++)begin @(negedge clk); cfg_we=1; cfg_addr=cfg[i][265:256]; cfg_data=cfg[i][255:0]; end
        @(negedge clk); cfg_we=0; start_v=1; start_loops=16'(loops); tick(); @(negedge clk); start_v=0;
        while(!calendar_v)tick();
        for(integer e=0;e<edges;e++)begin
            if(!calendar_v)$fatal(1,"CALUNI gap at edge %0d",e);
            if(got!==expect_w[e] || ordinal!==32'(e))$fatal(1,"CALUNI word mismatch edge %0d got %h exp %h",e,got,expect_w[e]);
            checked++; if(e==edges-1 && !done)$fatal(1,"CALUNI done missing"); tick();
        end
        if(calendar_v||fault)$fatal(1,"CALUNI trailing edge/fault");
        $display("VM_CALENDAR_UNIVERSAL PASS%0d edges exact, reset window + async assert", checked); $finish;
    end
endmodule
