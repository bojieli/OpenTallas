`timescale 1ns/1ps
module tb_native_attention_record;
    parameter integer MUT=0;
    parameter integer SIDE=1;
    reg ck=0;always #1 ck=~ck;
    reg rst_n=0,tx_event=0,tx_expected=0,rx_event=0,rx_expected=0;
    reg [3:0] tx_kind=3,tx_expected_kind=3,rx_expected_kind=2;
    reg [15:0] tx_epoch=16'hfe12,tx_expected_epoch=16'hfe12,rx_expected_epoch=16'hfe12;
    reg [5:0] tx_layer=0,tx_expected_layer=0,rx_expected_layer=0;
    reg [4:0] tx_beat=0,tx_expected_beat=0,rx_expected_beat=0;
    reg [511:0] tx_data=0;reg [547:0] rx_payload=0;
    wire tv,rv,fault;wire [547:0] tp;wire [3:0] rk,cause;
    wire [15:0] re;wire [5:0] rl;wire [4:0] rb;wire [511:0] rd;
    qkd_native_attention_record #(.KV_SIDE(SIDE),.MUT(MUT)) dut(.*,
        .tx_valid(tv),.tx_payload(tp),.rx_valid(rv),.rx_kind(rk),.rx_epoch(re),.rx_layer(rl),.rx_beat(rb),.rx_data(rd),.fault_cause(cause));
    task reset;
        begin
            @(negedge ck);rst_n=0;tx_event=0;tx_expected=0;rx_event=0;rx_expected=0;
            @(negedge ck);rst_n=1;
        end
    endtask
    task check(input bit good);
        begin
            @(posedge ck);#0.1;
            if(good)begin
                if(fault||tv!==tx_event||rv!==rx_event)$fatal(1,"event mismatch");
                if(tx_event&&tp!=={5'd0,tx_kind,tx_layer,tx_epoch,tx_beat,tx_data})$fatal(1,"TX corrupt");
                if(rx_event&&{rk,rl,re,rb,rd}!==rx_payload[542:0])$fatal(1,"RX corrupt");
            end else if(!fault||tv||rv)$fatal(1,"timing/context violation escaped cause=%b",cause);
        end
    endtask
    integer l,b,w;
    initial begin
        reset;
        // Actual boundary shape32Q+32results across all36layers, one/edge.
        for(l=0;l<36;l=l+1)for(b=0;b<32;b=b+1)begin
            @(negedge ck);
            tx_event=1;tx_expected=1;rx_event=1;rx_expected=1;
            tx_kind=SIDE?3:2;tx_expected_kind=tx_kind;rx_expected_kind=SIDE?2:3;
            tx_layer=l;tx_expected_layer=l;rx_expected_layer=l;
            tx_beat=b;tx_expected_beat=b;rx_expected_beat=b;
            for(w=0;w<16;w=w+1)tx_data[w*32+:32]=(l<<24)^(b<<16)^(w*32'h01010101);
            rx_payload={5'd0,rx_expected_kind,rx_expected_layer,rx_expected_epoch,rx_expected_beat,~tx_data};
            check(1);
        end
        // True command and true status observations are transported unchanged.
        @(negedge ck);tx_kind=SIDE?4:1;tx_expected_kind=tx_kind;tx_beat=0;tx_expected_beat=0;tx_data=SIDE?512'h19:512'h3fff;
        rx_expected_kind=SIDE?1:4;rx_expected_beat=0;rx_payload={5'd0,rx_expected_kind,rx_expected_layer,rx_expected_epoch,5'd0,(SIDE?512'h3fff:512'h19)};check(1);
        reset;@(negedge ck);tx_expected=1;tx_event=0;check(0);
        reset;@(negedge ck);rx_expected=1;rx_event=0;check(0);
        reset;@(negedge ck);tx_expected=0;tx_event=1;check(0);
        reset;@(negedge ck);rx_expected=0;rx_event=1;check(0);
        // Late identity is fatal; never retag a prior token/beat.
        for(w=0;w<32;w=w+1)begin
            reset;@(negedge ck);rx_expected=1;rx_event=1;
            rx_expected_kind=SIDE?2:3;rx_expected_beat=0;
            rx_payload={5'd0,rx_expected_kind,rx_expected_layer,rx_expected_epoch,5'd0,512'd0}^(548'd1<<(512+w));check(0);
        end
        reset;@(negedge ck);rx_expected=1;rx_event=1;
        rx_expected_kind=SIDE?2:3;rx_payload={5'd1,rx_expected_kind,rx_expected_layer,rx_expected_epoch,5'd0,512'd0};check(0);
        @(negedge ck);rx_expected=0;rx_event=0;tx_expected=0;tx_event=0;
        @(posedge ck);#0.1;if(!fault||tv||rv)$fatal(1,"fault not sticky");
        $display("PASS native attention record:1152 Q/result pairs,command/status,37 timing/identity/reserved faults");$finish;
    end
endmodule
