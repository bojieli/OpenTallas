`timescale 1ns/1ps
module check_tag #(parameter W=13, D=8, G=16) (input wire clk, rst_n, input wire [31:0] stimulus, input wire check_now);
    wire [W-1:0] gold;
    wire [16*W-1:0] actual;
    ot_hdc_delay #(.W(W),.D(D)) u_gold (.clk(clk),.rst_n(rst_n),.d(stimulus[W-1:0]),.q(gold));
    ot_v41_bf_tag_delay #(.W(W),.D(D),.GROUPS(G)) u_new (.clk(clk),.rst_n(rst_n),.d(stimulus[W-1:0]),.q(actual));
    integer l;
    always @(negedge clk) if (check_now)
        for (l=0;l<16;l=l+1) if (actual[l*W+:W] !== gold)
            $fatal(1,"tag difference W=%0d D=%0d G=%0d lane=%0d",W,D,G,l);
endmodule
module tb;
    reg root=0, run=1, rst_n=0, check_now=0;
    wire clk=root & run;
    reg [31:0] s=32'h7a0513cc;
    integer n;
    always #5 root=~root;
    check_tag #(.W(13),.D(8),.G(16)) a(clk,rst_n,s,check_now);
    check_tag #(.W(13),.D(8),.G(4)) b(clk,rst_n,s,check_now);
    check_tag #(.W(8),.D(5),.G(16)) c(clk,rst_n,s,check_now);
    check_tag #(.W(8),.D(5),.G(4)) d(clk,rst_n,s,check_now);
    initial begin
        for(n=0;n<8192;n=n+1) begin
            @(negedge root); #1;
            s={s[30:0],s[31]^s[21]^s[1]^s[0]};
            run=(n<32 || s[6:4]!=0);
            rst_n=(n>12 && n%311>5);
            check_now=(n>32);
        end
        $display("PASS 8192 cycles, 4 shapes, 16 lanes, clock holds and repeated reset");
        $finish;
    end
endmodule
