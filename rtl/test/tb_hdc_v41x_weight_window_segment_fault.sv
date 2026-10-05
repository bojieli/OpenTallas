`timescale 1ns/1ps
module tb_hdc_v41x_weight_window_segment_fault;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0,start=0,hr_v=0;
    reg [2:0] hr_tag=0;
    reg [4:0] hr_beat=0;
    wire hq_v,hr_rdy,ready,fault;
    wire [3:0] fault_why;
    wire fetched;
    wire [31:0] received;
    integer req=0;
    ot_hdc_v41x_weight_window #(.WB(66*256),.SB(256),.WORDS(1),
        .AW(8),.HAW(28),.NPC(1),.LENW(6),.BURST_MAX(32)) dut (
        .clk(clk),.rst_n(rst_n),.start(start),.release_window(1'b0),
        .rom_base(8'd4),.hbm_base(28'h100000),.nwords(1'b1),
        .ready(ready),.hq_v(hq_v),.hq_rdy(1'b1),.hq_addr(),
        .hq_len(),.hq_tag(),.hr_v(hr_v),.hr_rdy(hr_rdy),
        .hr_tag(hr_tag),.hr_beat(hr_beat),.hr_data(256'd0),
        .rom_re(1'b0),.rom_addr(8'd0),.rom_q(),
        .fault(fault),.fault_why(fault_why),.fetched_words(fetched),
        .received_sectors(received)
    );
    always @(posedge clk) if (hq_v) req <= req+1;
    task automatic reset_and_issue;
        begin
            @(negedge clk); rst_n=0; hr_v=0; req=0;
            repeat (2) @(negedge clk);
            rst_n=1; start=1;
            @(negedge clk); start=0;
            wait(req==3);
            @(negedge clk);
            if (fetched!==1 || ready || fault) $fatal(1,"request issue failed");
        end
    endtask
    initial begin
        reset_and_issue();
        hr_v=1; hr_tag=3'd2; hr_beat=5'd31; // final segment has only two beats
        @(posedge clk); #1;
        if (!fault || !fault_why[1] || ready || received!=0)
            $fatal(1,"out-of-range final beat accepted");
        reset_and_issue();
        hr_v=1; hr_tag=3'd3; hr_beat=0; // unused fourth segment
        @(posedge clk); #1;
        if (!fault || !fault_why[1] || ready || received!=0)
            $fatal(1,"unused segment accepted");
        $display("FULLSHAPE_WEIGHT_SEGMENT_FAULT_PASS");
        $finish;
    end
    initial begin repeat (1000) @(posedge clk); $fatal(1,"timeout"); end
endmodule
