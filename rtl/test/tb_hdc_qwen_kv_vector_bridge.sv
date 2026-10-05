`timescale 1ns/1ps
module tb_hdc_qwen_kv_vector_bridge;
    parameter integer SW = 8;
    localparam integer AW = 16, V0 = 4096;
    reg clk=0, rst_n=0, fl_v=0, flush=0, mem_r_ready=0, mem_r_resp_v=0, mem_w_ready=0;
    always #5 clk=~clk;
    reg [SW-1:0] core_we=0;
    reg [SW*AW-1:0] core_addr=0;
    reg [SW*32-1:0] core_data=0;
    reg [AW-1:0] fl_word_addr=0;
    reg [127:0] fl_word_data=0;
    reg [255:0] mem_r_resp_data=0;
    wire drained, fl_ready, mem_r_v, mem_w_v, fault;
    wire [AW-1:0] mem_r_sector, mem_w_sector;
    wire [255:0] mem_w_data;
    wire [2*SW-1:0] tl_we;
    wire [2*SW*AW-1:0] tl_row;
    wire [2*SW*16-1:0] tl_mask;
    wire [2*SW*128-1:0] tl_data;
    integer writes=0, tail=0, i, beat;
    ot_hdc_qwen_kv_vector_bridge #(.SW(SW), .AW(AW), .LOG_HD(7), .LOG_TW(2),
                                    .V0_ELEMENT(V0), .FIFO_BEATS(128)) dut (
        .clk(clk), .rst_n(rst_n), .core_we(core_we), .core_addr(core_addr), .core_data(core_data),
        .drained(drained), .tl_we(tl_we), .tl_row(tl_row), .tl_mask(tl_mask), .tl_data(tl_data),
        .fl_v(fl_v), .fl_ready(fl_ready), .fl_word_addr(fl_word_addr), .fl_word_data(fl_word_data),
        .flush(flush), .mem_r_v(mem_r_v), .mem_r_ready(mem_r_ready),
        .mem_r_sector(mem_r_sector), .mem_r_resp_v(mem_r_resp_v),
        .mem_r_resp_data(mem_r_resp_data), .mem_w_v(mem_w_v), .mem_w_ready(mem_w_ready),
        .mem_w_sector(mem_w_sector), .mem_w_data(mem_w_data), .fault(fault));
    always @(posedge clk) if (rst_n) begin
        if (mem_w_v && mem_w_ready) begin
            if (mem_w_sector !== (V0/32 + writes)) $fatal(1,"sector %0d", mem_w_sector);
            for (i=0;i<32;i=i+1)
                if (mem_w_data[i*8 +: 8] !== 8'h38) $fatal(1,"FP8 byte %0d",i);
            writes <= writes+1;
        end
        if (|tl_we) begin
            if (tl_we[SW-1:0] !== {SW{1'b1}} || tl_we[2*SW-1:SW] !== 0)
                $fatal(1,"K bank dispatch");
            for (i=0;i<SW;i=i+1)
                if (tl_mask[i*16 +: 16] !== 16'hffff ||
                    tl_data[i*128 +: 8] !== 8'h40) $fatal(1,"K bank byte %0d",i);
            tail <= tail+1;
        end
        if (fault || mem_r_v) $fatal(1,"bridge fault or unexpected RMW");
    end
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        // A full shipped-shape 1,024-element V instruction arrives while HBM
        // refuses writes. The FIFO must hold the entire stream without loss.
        for (beat=0;beat<(1024/SW);beat=beat+1) begin
            core_we={SW{1'b1}};
            for (integer j=0;j<SW;j=j+1) begin
                core_addr[j*AW +: AW]=V0+beat*SW+j;
                core_data[j*32 +: 32]=32'h3f800000;
            end
            @(negedge clk);
        end
        core_we=0;
        repeat(5) @(negedge clk);
        if (drained || writes != 0) $fatal(1,"backpressure missing");
        mem_w_ready=1;
        wait(writes==32);
        @(negedge clk); mem_w_ready=0;
        // Each K dimension uses a distinct tail-word bank in one vector beat.
        core_we={SW{1'b1}};
        for (integer j=0;j<SW;j=j+1) begin
            core_addr[j*AW +: AW]=j*16;
            core_data[j*32 +: 32]=32'h40000000;
        end
        @(negedge clk); core_we=0;
        wait(tail==1);
        repeat(3) @(negedge clk);
        if (!drained) $fatal(1,"bridge failed to drain");
        $display("PASS VECTOR_BRIDGE SW=%0d writes=%0d Kbeats=%0d",SW,writes,tail);
        $finish;
    end
endmodule
