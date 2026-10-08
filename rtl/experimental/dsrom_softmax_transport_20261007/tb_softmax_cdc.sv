`timescale 1ps/1fs
module tb_softmax_cdc;
 reg wclk=0,rclk=0;
`ifdef SOFTMAX_CDC_REVERSE
 always #416.666666667 wclk=~wclk;always #555.555555556 rclk=~rclk;
`else
 always #555.555555556 wclk=~wclk;always #416.666666667 rclk=~rclk;
`endif
 reg por_stream=1,por_link=1;wire wrst_n,rrst_n;
 ot_hbm_collective_reset_entry #(.ENABLE(1)) resets(.clk_stream(wclk),.clk_link(rclk),.por_stream(por_stream),.por_link(por_link),.rst_n(wrst_n),.prst_n(rrst_n));
 reg in_v=0,out_r=0;reg [1049:0]in_d=0;wire in_r,out_v,wempty,rempty,fault;wire[1049:0]out_d;
 ot_hbm_collective_protected_cdc #(.ENABLE(1),.W(1050),.AW(6)) dut(.*);
 wire [1049:0] observed = out_d
`ifdef SOFTMAX_CDC_CORRUPT_HEADER
 ^ (1050'b1 << 1049)
`endif
 ;
 reg[1049:0]expectation[0:2047];integer writes=0,reads=0;reg checking=1;integer redges=0,last_read_edge=0;always @(negedge rclk)redges=redges+1;
 function automatic[1049:0]payload(input integer x);
  for(integer i=0;i<32;i=i+1)payload[i*32+:32]=(x*32'h753adb19)^(i*32'hfe345917);
  payload[1049:1024]={16'(x+17),7'(x/8),3'(x%8)};
 endfunction
 always @(posedge wclk)if(wrst_n&&checking&&in_v&&in_r)begin expectation[writes]=in_d;writes=writes+1;end
 always @(posedge rclk)if(rrst_n&&checking&&out_r&&out_v)begin
  if(reads>=writes||observed!==expectation[reads])$fatal(1,"CDC_DATA mismatch %0d",reads);
  if(reads>0&&reads<4&&redges-last_read_edge!=3)$fatal(1,"CDC_II expected3 got%0d",redges-last_read_edge);
  last_read_edge=redges;reads=reads+1;
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
  dut.g_on.mem[5][1210]=~dut.g_on.mem[5][1210];
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
  dut.g_on.u_head.code[16][0]=~dut.g_on.u_head.code[16][0];
  dut.g_on.u_head.code[16][1]=~dut.g_on.u_head.code[16][1];#0.1;
  if(!fault||out_v||rempty)$fatal(1,"CDC payload double error escaped");
  $display("PASS_CDC full1050x64 ratio3to4_512flits wrap/stalls/full/correction/rails/drain/coordinated_reset/control_double/payload_double");$finish;
 end
endmodule
