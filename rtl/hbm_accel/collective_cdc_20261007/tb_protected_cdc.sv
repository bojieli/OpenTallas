`timescale 1ps/1fs
module tb_protected_cdc;
 reg wclk=0,rclk=0;always #416.666667 wclk=~wclk;always #512.3 rclk=~rclk;
 reg por_stream=1,por_link=1;wire wrst_n,rrst_n;
 ot_hbm_collective_reset_entry #(.ENABLE(1)) resets(.clk_stream(wclk),.clk_link(rclk),.por_stream(por_stream),.por_link(por_link),.rst_n(wrst_n),.prst_n(rrst_n));
 reg in_v=0,out_r=0;reg [544:0]in_d=0;wire in_r,out_v,wempty,rempty,fault;wire[544:0]out_d;
 ot_hbm_collective_protected_cdc #(.ENABLE(1)) dut(.*);
 reg[544:0]expectation[0:2047];integer writes=0,reads=0;reg checking=1;
 function automatic[544:0]payload(input integer x);
  for(integer i=0;i<17;i=i+1)payload[i*32+:32]=(x*32'h753adb19)^(i*32'hfe345917);
  payload[544]=x[0];
 endfunction
 always @(posedge wclk)if(wrst_n&&checking&&in_v&&in_r)begin expectation[writes]=in_d;writes=writes+1;end
 always @(posedge rclk)if(rrst_n&&checking&&out_r&&out_v)begin
  if(reads>=writes||out_d!==expectation[reads])$fatal(1,"CDC_DATA mismatch %0d",reads);
  reads=reads+1;
 end
 task send(input integer x);begin
  @(negedge wclk);while(!in_r)@(negedge wclk);in_d=payload(x);in_v=1;
  @(negedge wclk);in_v=0;
 end endtask
 task cold;begin
  por_stream=1;por_link=1;in_v=0;out_r=0;
  repeat(3)@(negedge wclk);por_stream=0;
  repeat(4)@(negedge rclk);por_link=0;
  wait(wrst_n&&rrst_n);@(negedge wclk);
 end endtask
 initial begin
  cold();
  for(integer i=0;i<64;i=i+1)send(i);
  if(in_r||wempty||rempty)$fatal(1,"CDC_FULL or quiet failed");
  // Corrupt an unread stored code; protected head corrects before retirement.
  dut.g_on.mem[5][3]=~dut.g_on.mem[5][3];
  out_r=1;
  for(integer i=64;i<512;i=i+1)begin send(i);out_r=(i%7!=0);repeat(i%3)@(negedge wclk);out_r=1;end
  wait(reads==writes);repeat(6)@(negedge wclk);
  if(fault||!wempty||!rempty)$fatal(1,"CDC drain failed");
  // Incoherent synchronized pointer rails suppress authorization.
  @(negedge wclk);dut.g_on.rgi_sync1[0]=~dut.g_on.rgi_sync1[0];#0.1;
  if(in_r||wempty)$fatal(1,"CDC rail corruption granted permission");
  repeat(3)@(negedge wclk);
  if(!in_r||fault)$fatal(1,"CDC rail coherence did not recover");
  // Cold reset with outstanding traffic invalidates old generation.
  send(1001);send(1002);out_r=0;checking=0;cold();writes=0;reads=0;checking=1;
  send(771);out_r=1;wait(reads==1);
  // Double-error control corruption must fail closed, never fabricate a credit.
  @(negedge wclk);dut.g_on.u_write_pointer.code[0][0]=~dut.g_on.u_write_pointer.code[0][0];
  dut.g_on.u_write_pointer.code[0][1]=~dut.g_on.u_write_pointer.code[0][1];#0.1;
  if(!fault||in_r||wempty)$fatal(1,"CDC pointer double error escaped");
  checking=0;cold();send(990);wait(out_v);@(negedge rclk);
  dut.g_on.u_head.code[0][0]=~dut.g_on.u_head.code[0][0];
  dut.g_on.u_head.code[0][1]=~dut.g_on.u_head.code[0][1];#0.1;
  if(!fault||out_v||rempty)$fatal(1,"CDC payload double error escaped");
  $display("PASS_CDC full545x64 independent_clocks512flits wrap/stalls/full/correction/rails/drain/coordinated_reset/control_double/payload_double");$finish;
 end
endmodule
