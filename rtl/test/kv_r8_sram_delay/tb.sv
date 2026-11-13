`timescale 1ns/1ps
module coupon #(parameter integer W=291, BASE=2, COUNT=0, MAX=24, CW=5, PREFACE=0)(
    input wire clk, input wire [W-1:0] d, input wire [31:0] age, output wire mismatch
);
    localparam integer D=PREFACE+BASE+((COUNT>MAX)?MAX:COUNT);
    wire [W-1:0] di;
    generate if(PREFACE==2) begin:g_prefix
        reg [W-1:0] a,b; always @(posedge clk) begin a<=d;b<=a;end
        assign di=b;
    end else begin:g_direct
        assign di=d;
    end endgenerate
    wire [W-1:0] q;
    ot_dp_dly_cnt_sram #(.W(W),.DMAX(MAX),.BASE(BASE),.CW(CW)) u (
        .clk(clk),.strap_cnt(CW'(COUNT)),.d(di),.q(q));
    wire [W-1:0] gold;
    generate if (D==0) begin : g_zero
        assign gold=d;
    end else begin : g_delay
        reg [W-1:0] r [0:D-1];
        always @(posedge clk) begin
            r[0]<=d;
            for (integer j=1;j<D;j=j+1) r[j]<=r[j-1];
        end
        assign gold=r[D-1];
    end endgenerate
    // ORIGINAL reset-less history is undefined before D clocks. From its
    // first defined word onward compare EVERY payload/control bit, continuously.
    assign mismatch=(age>=32'(D)) && (q!==gold);
endmodule
module tb;
    reg clk=0; always #0.4165 clk=~clk;
    reg [290:0] d;
    reg [31:0] age=0;
    reg warm_reset=1;
    wire [3:0] full_bad;
    coupon #(.COUNT(0)) f0(clk,d,age,full_bad[0]);
    coupon #(.COUNT(4)) f4(clk,d,age,full_bad[1]);
    coupon #(.COUNT(19)) f19(clk,d,age,full_bad[2]);
    coupon #(.COUNT(24)) f24(clk,d,age,full_bad[3]);
    wire [3:0] prefix_bad;
    coupon #(.BASE(0),.PREFACE(2),.COUNT(0)) p0(clk,d,age,prefix_bad[0]);
    coupon #(.BASE(0),.PREFACE(2),.COUNT(4)) p4(clk,d,age,prefix_bad[1]);
    coupon #(.BASE(0),.PREFACE(2),.COUNT(19)) p19(clk,d,age,prefix_bad[2]);
    coupon #(.BASE(0),.PREFACE(2),.COUNT(24)) p24(clk,d,age,prefix_bad[3]);
    wire [24:0] thin_bad;
    for (genvar k=0;k<=24;k=k+1) begin : g_all
        coupon #(.W(17),.COUNT(k)) c(clk,d[16:0],age,thin_bad[k]);
    end
    wire [4:0] edge_bad;
    coupon #(.W(17),.BASE(0),.COUNT(0),.MAX(2),.CW(2)) e0(clk,d[16:0],age,edge_bad[0]);
    coupon #(.W(17),.BASE(0),.COUNT(1),.MAX(2),.CW(2)) e1(clk,d[16:0],age,edge_bad[1]);
    coupon #(.W(17),.BASE(0),.COUNT(2),.MAX(2),.CW(2)) e2(clk,d[16:0],age,edge_bad[2]);
    coupon #(.W(17),.BASE(0),.COUNT(32),.MAX(32),.CW(6)) e32(clk,d[16:0],age,edge_bad[3]);
    coupon #(.W(17),.BASE(2),.COUNT(31),.MAX(24),.CW(5)) eclip(clk,d[16:0],age,edge_bad[4]);
    reg [63:0] rnd=64'h9e3779b97f4a7c15;
    integer checks=0;
    initial begin
        d='0; #0.1;
        $display("POINTER_INIT %0d %0d %0d %0d",f0.u.g_ring.wp,f4.u.g_ring.wp,f19.u.g_ring.wp,f24.u.g_ring.wp);
        for (integer n=1;n<=4096;n=n+1) begin
            if (n>1) @(negedge clk);
            warm_reset=!((n>=128&&n<139)||(n>=777&&n<793)||(n>=2048&&n<2059));
            for (integer b=0;b<291;b=b+1) begin
                rnd={rnd[62:0],rnd[63]^rnd[62]^rnd[60]^rnd[59]};
                d[b]=rnd[0] ^ ((n%29)==0) ^ (!warm_reset && ((b%7)==0));
            end
            @(posedge clk);age=32'(n);#0.001;
            if ((|full_bad)||(|prefix_bad)||(|thin_bad)||(|edge_bad)) begin
                $display("LOCKSTEP FAIL n=%0d warm=%0d full=%b prefix=%b thin=%h edge=%b",n,warm_reset,full_bad,prefix_bad,thin_bad,edge_bad);
                $fatal(1,"MEMORY_DELAY_MISMATCH");
            end
            checks=checks+38;
        end
        $display("LOCKSTEP PASS checks=%0d cycles=4096 fullwidth=291 counts=0,4,19,24 fused_and_prefix2 all0to24=17b warm_resets=3",checks);
        $finish;
    end
endmodule
