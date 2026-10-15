`timescale 1ns/1ps
// Actual two-tile, two-epoch4352b store. Identical request stream into flat
// and banked hardware: banked answer must match exactly one edge later.
module tb_qfd_xs_leaf_capture;
 parameter integer MUT=0;
 parameter integer EARLY=0;
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
 reg suppress_capture1=0;
 wire capture1_clk=clk&&!suppress_capture1;
 always @(negedge clk)suppress_capture1<=$test$plusargs("drop_clock")&&(age==25);
 wire fault,wo_v,wo_ep,co_v,co_ep;
 wire [5:0] wo_off;wire [63:0]wo_m;wire[1023:0]wo_d;wire[71:0]wo_ctl;
 reg[1169:0]fill1=0,fill2=0;integer fillchecks=0,age=0;
 always @(posedge clk)if(!rst_n)age<=0;else begin
  age<=age+1;
  fill1<={c_ep,c_v,18'd0,w_ctl[71:18],w_d,w_m,w_off,w_ep,w_v};
  fill2<=fill1;
 end
 always @(negedge clk)if(rst_n&&age>8&&EARLY==0)begin
  if($test$plusargs("drop_clock")&&fault)begin $display("PASS external capture dropped-clock epoch fault detected");$finish;end
  if({co_ep,co_v,wo_ctl,wo_d,wo_m,wo_off,wo_ep,wo_v}!==fill2)$fatal(1,"FAIL external capture forwarding age/bits check=%0d",fillchecks);
  if(fault)$fatal(1,"FAIL external capture protocol fault");
  fillchecks=fillchecks+1;
 end
 qfd_xs_leaf_capture_parent #(.MUT(MUT)) dut
  (.clk,.clk_wd0(clk),.clk_wd1(capture1_clk),.rst_n,.w_v,.w_ep,.w_off,.w_m,.w_d,.w_ctl,.c_v,.c_ep,
   .r_v,.r_t,.r_ep,.r_p,.q_v(bv),.q(bq),.q_bad(bb),.fault,
   .wo_v,.wo_ep,.wo_off,.wo_m,.wo_d,.wo_ctl,.co_v,.co_ep);
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
  if(EARLY!=0||$test$plusargs("early"))begin w_v=1;tick();w_v=0;repeat(6)tick();if(!fault)$fatal(1,"FAIL early fill not rejected");$display("PASS external capture early fill rejected");$finish;end
  repeat(8)tick();
  for(ep=0;ep<2;ep=ep+1)begin
   c_v=1;c_ep=ep;tick();c_v=0;tick();
   for(t=0;t<2;t=t+1)begin
    w_v=1;w_ep=ep;w_m=~64'd0;w_ctl=0;w_ctl[9*t+8]=1;
    for(l=0;l<64;l=l+1)w_d[16*l+:16]=16'h1000+ep*1024+t*256+l;
    tick();w_v=0;w_d=~w_d;tick();
   end
  end
  // Full64-word payload on128 consecutive edges, no gap/backpressure.
  w_ctl=0;w_ctl[8]=1;w_ctl[17]=1;w_m=~64'd0;
  for(i=0;i<128;i=i+1)begin
   w_v=1;w_ep=i%2;
   for(l=0;l<64;l=l+1)w_d[16*l+:16]=16'h2000+i*64+l;
   tick();
  end
  w_v=0;w_d=~w_d;repeat(4)tick();
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
  $display("PASS external capture leaf checks=%0d good=%0d invalid=%0d same_read_age=1 fill_II=1 burst_words=128 payload_bytes_per_edge=128",checked,good,bad);$finish;
 end
endmodule
