`timescale 1ns/1ps
// Actual two-tile, two-epoch4352b store. Identical request stream into flat
// and banked hardware: banked answer must match exactly one edge later.
module tb_qfd_xs_leaf_banked;
 parameter integer MUT=0;
 reg clk=0,rst_n=0;
 always #1 clk=~clk;
 reg w_v=0,w_ep=0,c_v=0,c_ep=0,r_v=0,r_t=0,r_ep=0;
 reg [5:0] w_off=0;
 reg [63:0] w_m=0;
 reg [1023:0] w_d=0;
 reg [71:0] w_ctl=0;
 reg [27:0] r_p=0;
 wire fv,bv,fb,bb;
 wire [63:0] fq,bq;
 ot_qfd_xs_leaf #(.BANK_PIPE(0)) ref_leaf
  (.clk,.rst_n,.w_v,.w_ep,.w_off,.w_m,.w_d,.w_ctl,.c_v,.c_ep,
   .r_v,.r_t,.r_ep,.r_p,.q_v(fv),.q(fq),.q_bad(fb));
 ot_qfd_xs_leaf #(.BANK_PIPE(1),.MUT(MUT)) dut
  (.clk,.rst_n,.w_v,.w_ep,.w_off,.w_m,.w_d,.w_ctl,.c_v,.c_ep,
   .r_v,.r_t,.r_ep,.r_p,.q_v(bv),.q(bq),.q_bad(bb));
 reg pv=0,pb=0;reg [63:0] pq=0;
 integer checked=0,good=0,bad=0;
 always @(negedge clk)if(rst_n)begin
  if(bv!==pv)$fatal(1,"FAIL banked valid alignment checked=%0d",checked);
  if(bv)begin
   if(bq!==pq || bb!==pb)$fatal(1,"FAIL banked payload got=%h/%b expected=%h/%b",bq,bb,pq,pb);
   checked=checked+1;if(bb)bad=bad+1;else good=good+1;
  end
  pv=fv;pq=fq;pb=fb;
 end
 task tick;begin @(negedge clk);#0.1;end endtask
 integer ep,t,l,i,j;
 initial begin
  repeat(3)tick();rst_n=1;
  for(ep=0;ep<2;ep=ep+1)begin
   c_v=1;c_ep=ep;tick();c_v=0;tick();
   for(t=0;t<2;t=t+1)begin
    w_v=1;w_ep=ep;w_m=~64'd0;w_ctl=0;w_ctl[9*t+8]=1;
    for(l=0;l<64;l=l+1)w_d[16*l+:16]=16'h1000+ep*1024+t*256+l;
    tick();w_v=0;tick();
   end
  end
  repeat(4)tick();
  // II4 alternating tiles => each tile requested every8edges; includes all
  // bank boundaries, both epochs and disabled elements in arbitrary positions.
  for(i=0;i<128;i=i+1)begin
   r_v=1;r_t=i%2;r_ep=(i/2)%2;
   for(j=0;j<4;j=j+1)begin r_p[7*j+:6]=(i*13+j*31)%64;r_p[7*j+6]=((i+j)%5!=0);end
   tick();r_v=0;repeat(3)tick();
  end
  repeat(12)tick();
  // Clear epoch0 validity, then read it: the candidate must retain fail-loud
  // per-element invalid tracking as well as matching the successful reads.
  c_v=1;c_ep=0;tick();c_v=0;repeat(3)tick();
  r_v=1;r_t=1;r_ep=0;r_p={7'h7f,7'h60,7'h5f,7'h40};tick();r_v=0;
  repeat(12)tick();
  if(checked!=129 || good!=128 || bad!=1)$fatal(1,"FAIL coverage checked=%0d good=%0d bad=%0d",checked,good,bad);
  $display("PASS banked leaf checks=%0d good=%0d invalid=%0d added_read_edges=1 same_tile_II=8",checked,good,bad);$finish;
 end
endmodule
