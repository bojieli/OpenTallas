`timescale 1ns/1ps
module tb_svc7_bmul;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,pad=0; reg [15:0] a=0,b=0;
 wire [31:0] y,ry; wire flt,rf;
 `ifdef BMUL_RESET_MUT
 wire candidate_rst_n=1'b1; // Negative control: drop the real reset obligation.
`else
 wire candidate_rst_n=rst_n;
`endif
 ot_s81svc7_bmul_native dut(.clk(clk),.rst_n(candidate_rst_n),.a(a),.b(b),.pad(pad),.y(y),.flt(flt));
 reg r0,r1; reg [32:0] pins;
 always @(posedge clk) begin r0<=rst_n; r1<=r0; pins<={a,b,pad}; end
 // Independent original full 8x8 product, not the split-product source.
 ot_hdc_v41x_attn_bmul_l #(.ML(6)) golden(.clk(clk),.a(pins[32:17]),.b(pins[16:1]),.pad(pins[0]|!r1),.y(ry),.flt(rf));
 integer cyc=0,checked=0,errors=0;
 always @(negedge clk) begin
   if(cyc>=9) begin
     checked=checked+1;
     if ({flt,y} !== {rf,ry}) begin errors=errors+1; $display("BMUL_DIFF cycle=%0d got=%h expected=%h",cyc,{flt,y},{rf,ry}); end
   end
   rst_n=!((cyc<3)||(cyc==37)||(cyc>=100 && cyc<104)||(cyc>=9000 && cyc<9003));
   a=$urandom; b=$urandom; pad=($urandom_range(0,7)==0);
   case(cyc%16)
   0: a=16'h7f80;
   1: b=16'h7fc1;
   2: a=0;
   3: b=16'h8000;
   4: a=1;
   5: begin a=16'h7f7f; b=16'h7f7f; end
   6: begin a=16'h3f80; b=16'hbf80; end
   7: begin a=16'h0080; b=16'h0080; end
   endcase
   cyc=cyc+1;
   if(cyc==20000) begin
     $display("SVC7_BMUL checked=%0d errors=%0d latency=7 verdict=%s",checked,errors,errors==0?"PASS":"FAIL");
     if(errors) $fatal(1,"BMUL_FAIL"); $finish;
   end
 end
endmodule
