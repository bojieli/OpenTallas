module ot_dp_st #(parameter integer W = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    input  wire         ea,
    output reg  [W-1:0] q,
    output reg          eq
);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
module old(input clk,rst_n,input [1104:0] ft0_i,ft1_i,output [1104:0] ft0_o,ft1_o);
    wire [1104:0] ft0_o_s0;
    wire [1104:0] ft0_o_s1;
    wire [1104:0] ft0_o_s2;
    wire [1104:0] ft1_o_s0;
    wire [1104:0] ft1_o_s1;
    wire [1104:0] ft1_o_s2;
    ot_dp_st #(.W(1104)) u_ft_ft0_o_0 (.clk(clk), .rst_n(rst_n), .d(ft0_i[1103:0]), .ea(ft0_i[1104]), .q(ft0_o_s0[1103:0]), .eq(ft0_o_s0[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft0_o_1 (.clk(clk), .rst_n(rst_n), .d(ft0_o_s0[1103:0]), .ea(ft0_o_s0[1104]), .q(ft0_o_s1[1103:0]), .eq(ft0_o_s1[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft0_o_2 (.clk(clk), .rst_n(rst_n), .d(ft0_o_s1[1103:0]), .ea(ft0_o_s1[1104]), .q(ft0_o_s2[1103:0]), .eq(ft0_o_s2[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft0_o_3 (.clk(clk), .rst_n(rst_n), .d(ft0_o_s2[1103:0]), .ea(ft0_o_s2[1104]), .q(ft0_o[1103:0]), .eq(ft0_o[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_0 (.clk(clk), .rst_n(rst_n), .d(ft1_i[1103:0]), .ea(ft1_i[1104]), .q(ft1_o_s0[1103:0]), .eq(ft1_o_s0[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_1 (.clk(clk), .rst_n(rst_n), .d(ft1_o_s0[1103:0]), .ea(ft1_o_s0[1104]), .q(ft1_o_s1[1103:0]), .eq(ft1_o_s1[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_2 (.clk(clk), .rst_n(rst_n), .d(ft1_o_s1[1103:0]), .ea(ft1_o_s1[1104]), .q(ft1_o_s2[1103:0]), .eq(ft1_o_s2[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_3 (.clk(clk), .rst_n(rst_n), .d(ft1_o_s2[1103:0]), .ea(ft1_o_s2[1104]), .q(ft1_o[1103:0]), .eq(ft1_o[1104]));
endmodule
module candidate(input clk,rst_n,input [1104:0] ft0_i,ft1_i,output [1104:0] ft0_o,ft1_o);
    wire [1104:0] ft0_o_s0;
    wire [1104:0] ft0_o_s1;
    wire [1104:0] ft0_o_s2;
    wire [1104:0] ft0_o_s3;
    wire [1104:0] ft1_o_s0;
    wire [1104:0] ft1_o_s1;
    wire [1104:0] ft1_o_s2;
    wire [1104:0] ft1_o_s3;
    ot_dp_st #(.W(1104)) u_ft_ft0_o_0 (.clk(clk), .rst_n(rst_n), .d(ft0_i[1103:0]), .ea(ft0_i[1104]), .q(ft0_o_s0[1103:0]), .eq(ft0_o_s0[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft0_o_1 (.clk(clk), .rst_n(rst_n), .d(ft0_o_s0[1103:0]), .ea(ft0_o_s0[1104]), .q(ft0_o_s1[1103:0]), .eq(ft0_o_s1[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft0_o_2 (.clk(clk), .rst_n(rst_n), .d(ft0_o_s1[1103:0]), .ea(ft0_o_s1[1104]), .q(ft0_o_s2[1103:0]), .eq(ft0_o_s2[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft0_o_3 (.clk(clk), .rst_n(rst_n), .d(ft0_o_s2[1103:0]), .ea(ft0_o_s2[1104]), .q(ft0_o_s3[1103:0]), .eq(ft0_o_s3[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft0_o_4 (.clk(clk), .rst_n(rst_n), .d(ft0_o_s3[1103:0]), .ea(ft0_o_s3[1104]), .q(ft0_o[1103:0]), .eq(ft0_o[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_0 (.clk(clk), .rst_n(rst_n), .d(ft1_i[1103:0]), .ea(ft1_i[1104]), .q(ft1_o_s0[1103:0]), .eq(ft1_o_s0[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_1 (.clk(clk), .rst_n(rst_n), .d(ft1_o_s0[1103:0]), .ea(ft1_o_s0[1104]), .q(ft1_o_s1[1103:0]), .eq(ft1_o_s1[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_2 (.clk(clk), .rst_n(rst_n), .d(ft1_o_s1[1103:0]), .ea(ft1_o_s1[1104]), .q(ft1_o_s2[1103:0]), .eq(ft1_o_s2[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_3 (.clk(clk), .rst_n(rst_n), .d(ft1_o_s2[1103:0]), .ea(ft1_o_s2[1104]), .q(ft1_o_s3[1103:0]), .eq(ft1_o_s3[1104]));
    ot_dp_st #(.W(1104)) u_ft_ft1_o_4 (.clk(clk), .rst_n(rst_n), .d(ft1_o_s3[1103:0]), .ea(ft1_o_s3[1104]), .q(ft1_o[1103:0]), .eq(ft1_o[1104]));
endmodule
module tb; reg clk=0,rst_n=0; always #5 clk=~clk; reg[1104:0] a,b; wire[1104:0] o0,o1,n0,n1,r0,r1; old O(clk,rst_n,a,b,o0,o1); candidate N(clk,rst_n,a,b,n0,n1); ot_dp_st #(.W(1104)) R0(clk,rst_n,o0[1103:0],o0[1104],r0[1103:0],r0[1104]); ot_dp_st #(.W(1104)) R1(clk,rst_n,o1[1103:0],o1[1104],r1[1103:0],r1[1104]); integer t,k,checks=0,mut=0; initial begin a=0;b=0; for(t=0;t<600;t=t+1)begin @(negedge clk); rst_n=(t%73>2); for(k=0;k<1105;k=k+1)begin a[k]=$random;b[k]=$random;end @(posedge clk);#1; if(t>6)begin if(n0!==r0||n1!==r1)$fatal(1,"MISMATCH %d",t);checks=checks+2; if(n0!==o0||n1!==o1)mut=mut+1;end end if(mut==0)$fatal(1,"MUTANT NOT DETECTED");$display("PASS checks=%0d mutant_cycles=%0d",checks,mut);$finish;end endmodule