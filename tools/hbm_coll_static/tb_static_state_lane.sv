`timescale 1ns/1ps
module tb_static_state_lane;
 parameter integer MUT_READ_SOURCE=0;
 reg clk=0; always #5 clk=~clk;
 reg lp_we=0,acc_we=0;
 reg [2:0] lp_tag=0,acc_tag=0,c0_tag=0,c1_tag=0;
 reg [31:0] lp_data=0,acc_data=0,c0_data=0,c1_data=0;
 reg [1:0] carry_we=0,c0_src=0,c1_src=0;
 reg read_add=0,read_tx=0,read_rr=0,read_rhs_acc=0,read_tx_acc=0;
 reg [2:0] add_tag=0,tx_tag=0,rr_tag=0;
 reg [1:0] add_src=0;
 wire [31:0] rhs,carry,tx,rr;
 wire [1:0] actual_add_src=add_src ^ (MUT_READ_SOURCE!=0 ? 2'b01 : 2'b00);
 ot_hgi_coll_pring_static_state_lane dut(
  .clk(clk),.lp_we(lp_we),.lp_tag(lp_tag),.lp_data(lp_data),
  .acc_we(acc_we),.acc_tag(acc_tag),.acc_data(acc_data),
  .carry_we(carry_we),.carry0_tag(c0_tag),.carry1_tag(c1_tag),
  .carry0_src(c0_src),.carry1_src(c1_src),.carry0_data(c0_data),.carry1_data(c1_data),
  .read_add(read_add),.read_tx(read_tx),.read_rr(read_rr),
  .read_rhs_acc(read_rhs_acc),.read_tx_acc(read_tx_acc),
  .add_tag(add_tag),.add_src(actual_add_src),.tx_tag(tx_tag),.rr_tag(rr_tag),
  .rhs_add(rhs),.carry_add(carry),.tx_data(tx),.acc_rr(rr));
 function automatic [31:0] lval(input integer t);lval=32'h01234567 ^ (32'h1020304*t);endfunction
 function automatic [31:0] aval(input integer t);aval=32'h89abcdef ^ (32'h1102031*t);endfunction
 function automatic [31:0] cval(input integer t,input integer s);cval=32'h13579bdf ^ (32'h1020305*t) ^ (32'h1000804*s);endfunction
 integer checks=0;
 task automatic check(input reg [31:0] got,input reg [31:0] want,input integer field);
  if(got!==want)$fatal(1,"STATE_LANE mismatch field=%0d got=%h expected=%h",field,got,want);
  checks=checks+1;
 endtask
 task automatic edge_sample;@(posedge clk);#1;endtask
 initial begin
  for(integer t=0;t<8;t=t+1)begin
   @(negedge clk);lp_we=1;acc_we=1;lp_tag=3'(t);acc_tag=3'(t);lp_data=lval(t);acc_data=aval(t);edge_sample();
  end
  @(negedge clk);lp_we=0;acc_we=0;
  for(integer t=0;t<8;t=t+1)for(integer s=0;s<4;s=s+2)begin
   @(negedge clk);carry_we=3;c0_tag=3'(t);c1_tag=3'(t);c0_src=2'(s);c1_src=2'(s+1);c0_data=cval(t,s);c1_data=cval(t,s+1);edge_sample();
  end
  @(negedge clk);carry_we=0;
  for(integer t=0;t<8;t=t+1)for(integer s=0;s<4;s=s+1)for(integer a=0;a<2;a=a+1)begin
   @(negedge clk);read_add=1;read_tx=1;read_rr=1;add_tag=3'(t);tx_tag=3'(t);rr_tag=3'(t);add_src=2'(s);read_rhs_acc=1'(a);read_tx_acc=1'(a);
   edge_sample();check(rhs,a?aval(t):lval(t),0);check(carry,cval(t,s),1);check(tx,a?aval(t):lval(t),2);check(rr,aval(t),3);
  end
  // Read faces hold their previous values without a compiler reservation.
  @(negedge clk);read_add=0;read_tx=0;read_rr=0;add_tag=0;tx_tag=0;rr_tag=0;edge_sample();
  check(rhs,aval(7),4);check(carry,cval(7,3),5);check(tx,aval(7),6);check(rr,aval(7),7);
  // A simultaneous write and read observes the prior stored word at this edge.
  @(negedge clk);acc_we=1;acc_tag=0;acc_data=32'hfedcba98;read_add=1;read_rr=1;read_rhs_acc=1;add_tag=0;rr_tag=0;add_src=0;edge_sample();
  check(rhs,aval(0),8);check(rr,aval(0),9);
  @(negedge clk);acc_we=0;edge_sample();check(rhs,32'hfedcba98,10);check(rr,32'hfedcba98,11);
  $display("STATE_LANE PASS checked=%0d tags=8 sources=4 data_bits=32 reserved_reads=64 hold=1 read_before_write=1",checks);$finish;
 end
endmodule
