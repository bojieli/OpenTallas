`timescale 1ns/1fs
module tb_h2_ecc_column;
 import ot_gpu_w6_secded_pkg::*;
 reg clk=0;always #0.8333335 clk=~clk;
 reg rst_n=0,w_ce=0,r_ce=0;reg[31:0]generation=42;
 reg[5:0]w_addr=0,r_addr=0;reg[511:0]w_data=0;
 wire ov,fault;wire[511:0]od;
 ot_hbm_h2_ecc_column #(.ENABLE(1),.COLUMN(3)) dut(clk,rst_n,generation,w_ce,w_addr,w_data,r_ce,r_addr,ov,od,fault);
 wire off_v,off_f;wire[511:0]off_d;
 ot_hbm_h2_ecc_column off(clk,rst_n,generation,w_ce,w_addr,w_data,r_ce,r_addr,off_v,off_d,off_f);
 function automatic[511:0]data(input integer a);
  for(integer i=0;i<8;i=i+1)data[i*64+:64]=64'h4a372b6500000000^(64'(a)<<24)^64'(i*1234567);
 endfunction
 integer sent=0,got=0,cechecks=0,uechecks=0,concurrent=0;
 reg checking=1;reg[511:0]expected[0:2047];
 always @(posedge clk)begin
  if(rst_n&&checking&&r_ce&&!fault)begin expected[sent]=data(r_addr);sent=sent+1;end
  if(w_ce&&r_ce&&w_addr!=r_addr)concurrent=concurrent+1;
  #0.000001;
  if(off_v!==0||off_f!==0||off_d!==0)$fatal(1,"default-off mismatch");
  if(rst_n&&checking)begin
   if(fault!==0)$fatal(1,"unexpected column fault");
   if(ov)begin
    if(got>=sent||od!==expected[got])$fatal(1,"DATA order mismatch got=%0d sent=%0d",got,sent);
    got=got+1;
   end
  end
 end
 task automatic reset;
  @(negedge clk);rst_n=0;w_ce=0;r_ce=0;repeat(3)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
 endtask
 task automatic flip(input integer b);
  case(b/256)
   0:dut.g_on.g_mem[0].u_storage.arr[7][b%256]=~dut.g_on.g_mem[0].u_storage.arr[7][b%256];
   1:dut.g_on.g_mem[1].u_storage.arr[7][b%256]=~dut.g_on.g_mem[1].u_storage.arr[7][b%256];
   2:dut.g_on.g_mem[2].u_storage.arr[7][b%256]=~dut.g_on.g_mem[2].u_storage.arr[7][b%256];
  endcase
 endtask
 task automatic read7;
  @(negedge clk);r_addr=7;r_ce=1;
  @(negedge clk);r_ce=0;repeat(4)@(negedge clk);
 endtask
 initial begin
  reset();
  for(integer a=0;a<64;a=a+1)begin @(negedge clk);w_ce=1;w_addr=6'(a);w_data=data(a);end
  @(negedge clk);w_ce=0;
  for(integer a=0;a<64;a=a+1)begin
   @(negedge clk);r_ce=1;r_addr=6'(a);
   w_ce=a<32;w_addr=6'(a+32);w_data=data(a+32);
  end
  @(negedge clk);r_ce=0;w_ce=0;repeat(5)@(negedge clk);
  if(got!=64||sent!=64||concurrent!=32)$fatal(1,"full row/concurrency coverage");
  for(integer b=0;b<648;b=b+1)begin
   @(negedge clk);flip(b);read7();flip(b);cechecks=cechecks+1;
  end
  if(got!=712||sent!=712)$fatal(1,"CE coverage transfer count");
  checking=0;
  for(integer word=0;word<9;word=word+1)begin
   @(negedge clk);flip(word*72);flip(word*72+1);read7();
   if(fault!==1||ov!==0)$fatal(1,"UE did not quarantine word=%0d",word);
   flip(word*72);flip(word*72+1);uechecks=uechecks+1;reset();
  end
  // Correctly encoded but wrong transaction identity must still be rejected.
  @(negedge clk);dut.g_on.g_mem[2].u_storage.arr[7][64+:72]=encode64({22'd0,1'b1,32'd42,3'd4,6'd7});
  read7();if(fault!==1||ov!==0)$fatal(1,"column identity laundering");
  @(negedge clk);dut.g_on.g_mem[2].u_storage.arr[7][64+:72]=encode64({22'd0,1'b1,32'd42,3'd3,6'd7});reset();
  generation=43;read7();if(fault!==1||ov!==0)$fatal(1,"stale generation not rejected");generation=42;reset();
  @(negedge clk);w_ce=1;r_ce=1;w_addr=7;r_addr=7;w_data=data(7);#0.000001;
  if(fault!==1||ov!==0)$fatal(1,"same-address collision not quarantined");reset();
  @(negedge clk);dut.g_on.request2=dut.g_on.request2^72'd3;#0.000001;
  if(fault!==1||ov!==0)$fatal(1,"request control UE not quarantined");reset();
  checking=1;read7();
  if(got!=713||sent!=713)$fatal(1,"reset recovery mismatch");
  $display("PASS_H2_ECC_COLUMN rows64 concurrent%0d CE%0d UE%0d accepted%0d identity_generation_collision_requestUE_defaultoff",concurrent,cechecks,uechecks,got);$finish;
 end
endmodule
