`timescale 1ns/1ps
module tb_hdc_qwen_kv_tail_read_mux;
    parameter integer SW=8;
    localparam integer AW=24;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [1:0] rd_v=0;
    reg [2*AW-1:0] rd_word=0;
    wire [2*SW-1:0] bank_re;
    wire [2*SW*AW-1:0] bank_row;
    reg [2*SW*128-1:0] bank_q=0;
    wire [1:0] rd_valid;
    wire [255:0] rd_data;
    wire addr_error;
    reg [127:0] mem [0:2*SW-1][0:31];
    integer b, r;
    ot_hdc_qwen_kv_tail_read_mux #(.SW(SW), .AW(AW), .LOG_HD(7), .LOG_TW(2)) dut (.*);
    always @(posedge clk) begin
        for (integer n=0;n<2*SW;n=n+1)
            if (bank_re[n]) bank_q[n*128 +: 128] <= mem[n][bank_row[n*AW +: AW]];
    end
    initial begin
        for (b=0;b<2*SW;b=b+1)
            for (r=0;r<32;r=r+1) mem[b][r]=0;
        // Layer/head zero: tile 2 (parity 0), d=3; tile 1 (parity 1), d=7.
        mem[3][0] = {16{8'h23}};
        mem[SW+7][0] = {16{8'h17}};
        // Layer/head one: tile 2 and tile 1 must use row 128/SW, not new tile rows.
        mem[3][128/SW] = {16{8'h43}};
        mem[SW+7][128/SW] = {16{8'h37}};
        repeat (2) @(negedge clk); rst_n=1;
        rd_v=2'b11;
        rd_word[0 +: AW]=2*128+3;
        rd_word[AW +: AW]=1*128+7;
        #1;
        if (bank_re !== ((1 << 3) | (1 << (SW+7)))) $fatal(1,"two parity reads collided");
        @(posedge clk); #1;
        if (rd_valid !== 2'b11 || rd_data[0 +: 128] !== {16{8'h23}} ||
            rd_data[128 +: 128] !== {16{8'h17}}) $fatal(1,"one-cycle mux result");
        @(negedge clk);
        rd_word[0 +: AW]=(4+2)*128+3;
        rd_word[AW +: AW]=(4+1)*128+7;
        #1;
        if (bank_row[3*AW +: AW] !== 128/SW ||
            bank_row[(SW+7)*AW +: AW] !== 128/SW) $fatal(1,"head row address");
        @(posedge clk); #1;
        if (rd_data[0 +: 128] !== {16{8'h43}} ||
            rd_data[128 +: 128] !== {16{8'h37}}) $fatal(1,"head word mux");
        @(negedge clk); rd_v=0;
        @(posedge clk); #1;
        if (rd_valid !== 0 || addr_error) $fatal(1,"idle/read parity check");
        $display("PASS READ SW=%0d",SW); $finish;
    end
endmodule
