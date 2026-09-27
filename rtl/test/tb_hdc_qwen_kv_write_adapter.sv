`timescale 1ns/1ps
module tb_hdc_qwen_kv_write_adapter;
    parameter integer SW = 8;
    localparam integer AW=24, V0=4096;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, in_v=0, fl_v=0, flush=0, mem_r_ready=0, mem_r_resp_v=0, mem_w_ready=0;
    reg [SW-1:0] in_we=0;
    reg [SW*AW-1:0] in_addr=0;
    reg [SW*8-1:0] in_data=0;
    reg [AW-1:0] fl_word_addr=0;
    reg [127:0] fl_word_data=0;
    reg [255:0] mem_r_resp_data=0;
    wire in_ready, fl_ready, idle, mem_r_v, mem_w_v, fault;
    wire [2*SW-1:0] tl_we;
    wire [2*SW*AW-1:0] tl_row;
    wire [2*SW*16-1:0] tl_mask;
    wire [2*SW*128-1:0] tl_data;
    wire [AW-1:0] mem_r_sector, mem_w_sector;
    wire [255:0] mem_w_data;
    ot_hdc_qwen_kv_write_adapter #(.SW(SW), .AW(AW), .LOG_HD(7), .V0_ELEMENT(V0)) dut (.*);
    integer i, base;
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        in_v=1; in_we={SW{1'b1}};
        for (i=0;i<SW;i=i+1) begin
            in_addr[i*AW +: AW]=i*16;
            in_data[i*8 +: 8]=i+1;
        end
        #1;
        if (!in_ready || tl_we[SW-1:0] !== {SW{1'b1}} || tl_we[2*SW-1:SW] !== 0)
            $fatal(1,"K beat was not routed to distinct tail banks");
        for (i=0;i<SW;i=i+1)
            if (tl_mask[i*16 +: 16] !== 16'hffff || tl_data[i*128 +: 8] !== i+1)
                $fatal(1,"K bank %0d data or new-tile mask",i);
        @(negedge clk); in_v=0; in_we=0;
        for (base=0;base<32;base=base+SW) begin
            in_v=1; in_we={SW{1'b1}};
            for (i=0;i<SW;i=i+1) begin
                in_addr[i*AW +: AW]=V0+base+i;
                in_data[i*8 +: 8]=base+i;
            end
            #1; if (!in_ready) $fatal(1,"V vector backpressured within sector");
            @(negedge clk);
        end
        in_v=0; in_we=0;
        repeat (2) @(negedge clk);
        if (!mem_w_v || mem_w_sector !== V0/32) $fatal(1,"full sector not written");
        for (i=0;i<32;i=i+1)
            if (mem_w_data[i*8 +: 8] !== i) $fatal(1,"full sector byte %0d",i);
        mem_w_ready=1; @(negedge clk); mem_w_ready=0;
        if (!idle) $fatal(1,"write did not retire");

        // One byte of a pre-existing sector must read-modify-write its other 31 bytes.
        in_v=1; in_we=2; in_addr[AW +: AW]=V0+64+3; in_data[8 +: 8]=8'haa;
        #1; if (!in_ready) $fatal(1,"partial V beat not accepted");
        @(negedge clk);
        // A different sector is backpressured while the first partial one
        // drains through an explicit read/modify/write.
        in_addr[AW +: AW]=V0+96;
        #1; if (in_ready) $fatal(1,"sector switch was not backpressured");
        @(negedge clk); in_v=0; in_we=0;
        if (!mem_r_v || mem_r_sector !== (V0+64)/32) $fatal(1,"RMW read absent");
        mem_r_ready=1; @(negedge clk); mem_r_ready=0;
        mem_r_resp_data={32{8'h11}}; mem_r_resp_v=1;
        @(negedge clk); mem_r_resp_v=0;
        if (!mem_w_v || mem_w_data[3*8 +: 8] !== 8'haa ||
            mem_w_data[2*8 +: 8] !== 8'h11 || mem_w_data[4*8 +: 8] !== 8'h11)
            $fatal(1,"RMW failed to preserve untouched bytes");
        mem_w_ready=1; @(negedge clk); mem_w_ready=0;
        if (!idle || fault) $fatal(1,"adapter did not finish cleanly");

        // Two completed 16-byte K-tail words become one 32-byte HBM write.
        fl_v=1; fl_word_addr=0; fl_word_data={16{8'h22}};
        #1; if (!fl_ready) $fatal(1,"first tail word not accepted");
        @(negedge clk); fl_word_addr=1; fl_word_data={16{8'h33}};
        #1; if (!fl_ready) $fatal(1,"second tail word not accepted");
        @(negedge clk); fl_v=0;
        repeat (2) @(negedge clk);
        if (!mem_w_v || mem_w_sector !== 0 ||
            mem_w_data[127:0] !== {16{8'h22}} || mem_w_data[255:128] !== {16{8'h33}})
            $fatal(1,"K-tail sector assembly failed");
        mem_w_ready=1; @(negedge clk); mem_w_ready=0;
        if (!idle) $fatal(1,"tail write did not retire");
        $display("PASS SW=%0d",SW); $finish;
    end
endmodule
