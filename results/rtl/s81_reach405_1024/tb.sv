`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg arst_n=0;reg[32:0] x0=0;reg[45:0] x1=0;
wire[32:0] r0,n0;wire[45:0] r1,n1;
reg[32:0] d00,d01;reg[45:0] d10,d11;
integer cyc=0;
ref_t7 ref0 (.clk(clk), .clk_t1(clk), .clk_t2(clk), .clk_t3(clk), .clk_t4(clk), .clk_t5(clk), .clk_t6(clk), .clk_t7(clk), .clk_t8(clk), .clk_t9(clk), .clk_t10(clk), .clk_t11(clk), .clk_t12(clk), .clk_t13(clk), .clk_t14(clk), .clk_t15(clk),.arst_n(arst_n),.ft0_i(x0),.ft1_i(x1),.ft0_o(r0),.ft1_o(r1));
new_t7 new0 (.clk(clk), .clk_t1(clk), .clk_t2(clk), .clk_t3(clk), .clk_t4(clk), .clk_t5(clk), .clk_t6(clk), .clk_t7(clk), .clk_t8(clk), .clk_t9(clk), .clk_t10(clk), .clk_t11(clk), .clk_t12(clk), .clk_t13(clk), .clk_t14(clk), .clk_t15(clk),.arst_n(arst_n),.ft0_i(x0),.ft1_i(x1),.ft0_o(n0),.ft1_o(n1));
initial begin #2;arst_n=1;end
always @(negedge clk) begin x0={$random,$random};x1={$random,$random};end
always @(posedge clk) begin
 d00<=r0;d01<=d00;d10<=r1;d11<=d10;cyc=cyc+1;
 #1;
 if(cyc>12 && (n0!==d01 || n1!==d11)) $fatal(1,"MISMATCH cycle%0d",cyc);
 if(cyc==2000) begin $display("LOCKSTEP_PASS 1988 checked cycles two FT buses incl epoch; added_cycles=2");$finish;end
end
endmodule
