`timescale 1ns/1ps
module tb_hdc_v41x_weight_window;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0, start = 0, release_window = 0;
    reg [7:0] rom_base = 0, hbm_base = 0;
    reg [2:0] nwords = 0;
    wire ready, hq_v;
    reg hq_rdy = 1;
    wire [7:0] hq_addr;
    wire [3:0] hq_len;
    wire [1:0] hq_tag;
    reg [1:0] hr_v = 0;
    wire [1:0] hr_rdy;
    reg [3:0] hr_tag = 0;
    reg [1:0] hr_beat = 0;
    reg [511:0] hr_data = 0;
    reg rom_re = 0;
    reg [7:0] rom_addr = 0;
    wire [511:0] rom_q;
    wire fault;
    wire [3:0] fault_why;
    wire [2:0] fetched_words;
    wire [31:0] received_sectors;
    ot_hdc_v41x_weight_window #(.WB(512), .SB(256), .WORDS(4),
        .AW(8), .HAW(8), .NPC(2)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .release_window(release_window),
        .rom_base(rom_base), .hbm_base(hbm_base), .nwords(nwords), .ready(ready),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .rom_re(rom_re), .rom_addr(rom_addr), .rom_q(rom_q),
        .fault(fault), .fault_why(fault_why), .fetched_words(fetched_words),
        .received_sectors(received_sectors));

    task automatic send_pair(input [1:0] tag0, input beat0,
                             input [255:0] data0, input [1:0] tag1,
                             input beat1, input [255:0] data1);
        begin
            @(negedge clk);
            hr_v = 2'b11;
            hr_tag[0 +: 2] = tag0; hr_beat[0] = beat0;
            hr_tag[2 +: 2] = tag1; hr_beat[1] = beat1;
            hr_data[0 +: 256] = data0; hr_data[256 +: 256] = data1;
            @(posedge clk); #1;
            @(negedge clk); hr_v = 0;
        end
    endtask

    initial begin
        repeat (2) @(negedge clk);
        rst_n = 1;
        start = 1; rom_base = 8'h10; hbm_base = 8'h20; nwords = 2;
        @(negedge clk); start = 0;
        if (!hq_v || hq_addr !== 8'h20 || hq_len !== 4'd2 || hq_tag !== 0)
            $fatal(1, "first HBM request");
        @(negedge clk);
        if (!hq_v || hq_addr !== 8'h22 || hq_tag !== 1)
            $fatal(1, "second HBM request");
        @(negedge clk);
        if (hq_v || fetched_words !== 2) $fatal(1, "request completion");
        // Two pseudo-channels respond out of order, including the two halves
        // of each word on different cycles.
        send_pair(1, 1, 256'hdd, 0, 0, 256'haa);
        if (ready || received_sectors !== 2) $fatal(1, "premature ready");
        send_pair(1, 0, 256'hcc, 0, 1, 256'hbb);
        if (!ready || received_sectors !== 4 || fault) $fatal(1, "window not ready");
        rom_re = 1; rom_addr = 8'h10;
        @(posedge clk); #1;
        if (rom_q !== {256'hbb, 256'haa}) $fatal(1, "word 0 mismatch");
        @(negedge clk); rom_addr = 8'h11;
        @(posedge clk); #1;
        if (rom_q !== {256'hdd, 256'hcc}) $fatal(1, "word 1 mismatch");
        @(negedge clk); rom_re = 0; release_window = 1;
        @(negedge clk); release_window = 0;
        if (ready || fault) $fatal(1, "release failed");

        // A duplicate beat returned simultaneously on two channels fails
        // closed even before the rest of the window has arrived.
        start = 1; rom_base = 8'h40; hbm_base = 8'h60; nwords = 1;
        @(negedge clk); start = 0;
        @(negedge clk);
        send_pair(0, 0, 256'h1, 0, 0, 256'h2);
        if (!fault || !fault_why[2] || ready) $fatal(1, "duplicate response accepted");

        @(negedge clk); rst_n = 0;
        @(negedge clk); rst_n = 1;
        start = 1; rom_base = 8'h70; hbm_base = 8'h80; nwords = 1;
        @(negedge clk); start = 0;
        @(negedge clk);
        send_pair(0, 0, 256'h11, 0, 1, 256'h22);
        if (!ready || fault) $fatal(1, "single-word refill");
        rom_re = 1; rom_addr = 8'h71;
        @(posedge clk); #1;
        if (!fault || !fault_why[3] || ready) $fatal(1, "out-of-range ROM read accepted");
        $display("PASS v41x bounded HBM weight window");
        $finish;
    end
endmodule
