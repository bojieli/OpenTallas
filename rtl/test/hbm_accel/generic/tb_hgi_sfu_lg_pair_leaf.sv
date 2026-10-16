`timescale 1ns/1ps
module tb_hgi_sfu_lg_pair_leaf;
 reg clk=0,rst_n=0; always #0.416667 clk=~clk;
 reg [1111:0] din=0; wire [1111:0] dout;
 wire [1111:0] actual_in = din ^ ((mut && n==31) ? (1112'b1 << 405) : 1112'b0);
 reg [1111:0] expected; integer checks=0,errors=0,n,b,mut;
 ot_hgi_sfu_lg_pair_leaf #(.PIN_RST(1)) dut(
 .clk(clk),.rst_n(rst_n),.c_rq(actual_in[33:0]),.c_wq(actual_in[595:34]),
 .lg_rr(actual_in[1109:596]),.lg_w_done(actual_in[1111:1110]),
 .lg_rq(dout[33:0]),.lg_wq(dout[595:34]),.c_rr(dout[1109:596]),.c_w_done(dout[1111:1110]));
 initial begin
 mut=$test$plusargs("MUT_DATA");
 repeat(4) @(negedge clk);rst_n=1;
 repeat(3) @(negedge clk);
 for(n=0;n<1024;n=n+1)begin
  // Independent externally supplied walking/random words across every boundary bit.
  for(b=0;b<1112;b=b+1) din[b]=((n*17+b*13)>>(b%10))&1;
  din[n%1112]=~din[n%1112];expected=din;
  @(posedge clk);#0.001;
  checks=checks+1112;if(dout!==expected)begin errors=errors+1;$display("LEAF_DATA n=%0d",n);end
  @(negedge clk);
 end
 // Registered reset reaches the validity bits after two local edges.
 rst_n=0; repeat(3) @(negedge clk);
 if({dout[16],dout[33],dout[314],dout[595],dout[852],dout[1109],dout[1111:1110]}!==0)errors=errors+1;
 if(errors)begin $display("SFU_PAIR FAIL checks=%0d errors=%0d",checks,errors);$fatal(1);end
 $display("SFU_PAIR PASS checks=%0d transfers=1024 reset_edges=2 normal_edges=1",checks);$finish;
 end
endmodule
