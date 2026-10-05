`timescale 1ns/1ps
module tb_hdc_qwen_kv_tail_bank_port;
    parameter integer SW=8;
    localparam integer AW=24, LOG_HD=4, LOG_TW=2, LLG=3, TAW=LLG+LOG_HD;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg [1:0] tl_re=0;
    reg [2*TAW-1:0] tl_raddr=0;
    wire [511:0] tl_q;
    wire [2*SW-1:0] bank_re;
    wire [2*SW*AW-1:0] bank_row;
    reg [2*SW*128-1:0] bank_q=0;
    reg [127:0] mem [0:2*SW-1][0:15];
    wire addr_error;
    integer b,r;
    ot_hdc_qwen_kv_tail_bank_port #(.SW(SW),.AW(AW),.LOG_HD(LOG_HD),.LOG_TW(LOG_TW),.LLG(LLG)) dut (
        .clk(clk),.rst_n(rst_n),.tl_re(tl_re),.tl_raddr(tl_raddr),.tl_q(tl_q),
        .bank_re(bank_re),.bank_row(bank_row),.bank_q(bank_q),.addr_error(addr_error));
    always @(posedge clk) begin
        for (integer i=0;i<2*SW;i=i+1)
            if (bank_re[i]) bank_q[i*128 +: 128] <= mem[i][bank_row[i*AW +: AW]];
    end
    initial begin
        for (b=0;b<2*SW;b=b+1)
            for (r=0;r<16;r=r+1) mem[b][r]=0;
        // Head 3, dimensions 7 and 14, tiles of opposite parity.
        mem[7][(3 << (LOG_HD-$clog2(SW))) | (7 >> $clog2(SW))] = {16{8'h38}};
        mem[SW+(14 % SW)][(3 << (LOG_HD-$clog2(SW))) | (14 >> $clog2(SW))] = {16{8'hb8}};
        repeat (2) @(negedge clk);
        rst_n=1;
        tl_re=2'b11;
        tl_raddr[0 +: TAW]=(3 << LOG_HD) | 7;
        tl_raddr[TAW +: TAW]=(3 << LOG_HD) | 14;
        @(posedge clk); #1;
        if (tl_q[15:0] !== 16'h3f80 || tl_q[271:256] !== 16'hbf80 || addr_error)
            $fatal(1,"tail read mismatch SW=%0d got %h %h error=%b",SW,tl_q[15:0],tl_q[271:256],addr_error);
        $display("PASS TAIL_BANK_PORT SW=%0d",SW);
        $finish;
    end
endmodule
