`timescale 1ns/1ps
module tb_dsrom_reindex_list_macro;
 reg clk=0;always #0.4166665 clk=~clk;
 reg rst_n=0,w_v=0,active=0,r_re=0;
 reg [2:0] w_slot=0,active_slot=0,r_slot=0;
 reg [10:0] w_addr=0;reg [13:0] w_block=0;
 reg [9:0] r_pair=0;reg [1:0] r_mask=3;
 wire [13:0] r_even,r_odd;wire r_valid,fault,pending;wire [1:0] corrected;wire [11:0] count;
 ot_dsrom_reindex_list_macro dut(.clk(clk),.rst_n(rst_n),.w_v(w_v),.w_slot(w_slot),.w_addr(w_addr),.w_block(w_block),
 .active(active),.active_slot(active_slot),.r_re(r_re),.r_slot(r_slot),.r_pair(r_pair),.r_mask(r_mask),
 .r_even(r_even),.r_odd(r_odd),.r_valid(r_valid),.corrected(corrected),.fault(fault),.active_count(count),.writer_pending(pending));
 function automatic [13:0] value(input integer slot,entry);
  value=14'((slot*977+entry*7)^14'h256a);
 endfunction
 integer n=0,queued=0,received=0;
 reg [13:0] expect_e[0:8191],expect_o[0:8191];
 reg check_stream=0;
 always @(negedge clk)if(check_stream&&r_valid)begin
  if(fault||r_even!==expect_e[received]||r_odd!==expect_o[received])
   $fatal(1,"pair %0d got%h/%h expected%h/%h fault%0d",received,r_even,r_odd,expect_e[received],expect_o[received],fault);
  received=received+1;
 end
 task automatic one_read(input integer slot,pair,ce);
  begin
   @(negedge clk);r_slot=3'(slot);r_pair=10'(pair);r_re=1;
   @(negedge clk);r_re=0;
   do @(negedge clk);while(!r_valid&&!fault);
   if(fault||r_even!==value(slot,2*pair)||r_odd!==value(slot,2*pair+1)||corrected!==2'(ce))
    $fatal(1,"sealed read fault%0d got%h/%h CE%0d expected%0d",fault,r_even,r_odd,corrected,ce);
  end
 endtask
 integer s,a,bitpos;
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(s=0;s<8;s=s+1)for(a=0;a<2048;a=a+1)begin
   @(negedge clk);w_v=1;w_slot=3'(s);w_addr=11'(a);w_block=value(s,a);
  end
  @(negedge clk);w_v=0;
  repeat(3)@(negedge clk);if(fault)$fatal(1,"writer fault");
  for(s=0;s<8;s=s+1)begin active_slot=3'(s);#0.001;if(count!=2048)$fatal(1,"finite prefix count%0d",count);end
  check_stream=1;
  for(s=0;s<8;s=s+1)for(a=0;a<1024;a=a+1)begin
   @(negedge clk);r_re=1;r_slot=3'(s);r_pair=10'(a);
   expect_e[queued]=value(s,2*a);expect_o[queued]=value(s,2*a+1);queued=queued+1;
  end
  @(negedge clk);r_re=0;
  wait(received==8192);@(negedge clk);check_stream=0;
  $display("FULL_SHAPE_PASS lists8 entries16384 pairs8192");
  // Every protected code bit, including all check bits and the full address seal.
  for(bitpos=0;bitpos<35;bitpos=bitpos+1)begin
   dut.g_b[0].u_macro.arr[0][4*bitpos]=~dut.g_b[0].u_macro.arr[0][4*bitpos];
   one_read(0,0,1);
   dut.g_b[0].u_macro.arr[0][4*bitpos]=~dut.g_b[0].u_macro.arr[0][4*bitpos];
  end
  one_read(0,0,0);
  dut.g_b[0].u_macro.arr[0][0]=~dut.g_b[0].u_macro.arr[0][0];
  dut.g_b[0].u_macro.arr[0][4]=~dut.g_b[0].u_macro.arr[0][4];
  @(negedge clk);r_slot=0;r_pair=0;r_re=1;
  @(negedge clk);r_re=0;
  repeat(8)@(negedge clk);
  if(!fault||r_valid)$fatal(1,"double-error release");
  $display("SECDED_PASS single35 double_fail_closed1");
  $display("PASS");$finish;
 end
endmodule
