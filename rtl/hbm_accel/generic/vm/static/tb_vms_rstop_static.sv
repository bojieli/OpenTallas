`timescale 1ns/1ps
module tb_vms_rstop_static;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,tx_enable=0,dir=0,ack_i=0;
    reg [1:0] sid=0;
    reg [2:0] tx_source=0,wki=0;
    reg [2223:0] l_in=0;
    wire [2223:0] l_out;
    reg [289:0] pi=0;
    reg [2207:0] eg=0;
    wire [2207:0] xq;
    reg [7:0] xq_done=0;
    wire [287:0] rce;
    reg [265:0] ri=0;
    wire [2:0] wko;
    wire [263:0] cco;
    wire ack_o,mirror_busy,fault;
    ot_vms_rstop_static #(.MUT(MUT)) dut(.*);
    integer checks=0;
    task automatic tick;
        begin @(posedge clk);#1; end
    endtask
    task automatic idle;
        begin l_in=0;pi=0;eg=0;ri=0;wki=0;tx_enable=0; end
    endtask
    task automatic check(input bit ok,input string label_);
        begin checks++;if(!ok)$fatal(1,"STATIC_RING mismatch %s",label_);end
    endtask
    reg [2223:0] f;
    initial begin
        repeat(2)tick();@(negedge clk);rst_n=1;
        // Bank mirror egress injection keeps every byte and physical CW map.
        for(integer n=0;n<16;n++)begin
            @(negedge clk);idle();tx_enable=1;tx_source=2;
            for(integer b=0;b<8;b++)eg[b*276+:276]={1'b1,11'(n),256'(32'h15240000+n*8+b),8'hff};
            tick();@(negedge clk);idle();tick();
            check(l_out[2223] && l_out[2222:2221]==1,"WBC valid kind");
            check(l_out[2220:2217]==4'b1010,"physical CW destinations SW->SE/NE");
            for(integer b=0;b<8;b++)check(l_out[b*276+8+:256]==256'(32'h15240000+n*8+b),"mirror payload");
        end
        // Transit and local ejection share a fixed edge, remaining mask clears.
        @(negedge clk);idle();f=0;f[2223]=1;f[2222:2221]=0;f[2220:2217]=4'b0011;
        f[2216:2215]=2;f[2214:2211]=3;f[2210:2209]=1;f[2208]=1;
        f[4*276+:276]={1'b1,11'd12,256'hfeedbeef,8'hf0};l_in=f;tx_enable=1;tx_source=0;
        tick();@(negedge clk);idle();tick();
        check(l_out[2220:2217]==2 && l_out[2223],"transit destination clear");
        check(rce=={1'b1,2'd2,4'd3,2'd1,1'b1,3'd4,11'd12,8'hf0,256'hfeedbeef},"PREQ replay ABI");
        // Response eject (no replay queue) and WACK return observation.
        @(negedge clk);idle();f=0;f[2223]=1;f[2222:2221]=2;f[2220:2217]=1;
        f[2214:2211]=7;f[2210:2209]=2;f[2208]=1;f[263:8]=256'habc123;l_in=f;
        tick();@(negedge clk);idle();tick();
        check(cco=={1'b1,4'd7,2'd2,1'b1,256'habc123},"PRSP ABI");
        // Local mirror ejection, fixed macro-commit observation five edges later.
        @(negedge clk);idle();f=0;f[2223]=1;f[2222:2221]=1;f[2220:2217]=1;f[2216:2215]=2;
        for(integer b=0;b<8;b++)f[b*276+:276]={1'b1,11'd32,256'(b),8'hff};l_in=f;
        tick();@(negedge clk);idle();tick();
        check(xq==f[2207:0],"mirror ejection");
        repeat(4)tick();@(negedge clk);xq_done=8'hff;tick();
        check(wko=={1'b1,2'd2},"ack after actual commit observation");
        @(negedge clk);xq_done=0;tick();check(!fault,"legal fixed reservations");
        // Missing a reserved output is a sticky schedule error, never a stall.
        @(negedge clk);pi[289]=1;tick();@(negedge clk);idle();tick();
        check(fault,"unreserved injection faults");
        $display("VMS_STATIC_RING PASS %0d checks",checks);$finish;
    end
endmodule
