`timescale 1ns/1ps
module tb_sysface_reset32;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0; wire[111:0] leaf;
 qfd_sysface_reset32 #(.LEAVES(112)) dut(ck,rst_n,leaf);
 reg [1:0] old_s;reg old_q;reg prior_old;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin old_s<=0;old_q<=0;end
  else begin old_s<={old_s[0],1'b1};old_q<=old_s[1];end
 always @(posedge ck) begin prior_old=old_q;#1;
  if(rst_n && leaf!=={112{prior_old}}) $fatal(1,"SYSFACE_RESET32 release skew");
  if(!rst_n && leaf!==0) $fatal(1,"SYSFACE_RESET32 asserted");
 end
 initial begin
  #1;rst_n=1;#2;rst_n=0;#1;
  if(leaf!==0)$fatal(1,"SYSFACE_RESET32 async clear");
  for(integer r=0;r<32;r=r+1)begin
   @(negedge ck);rst_n=1;repeat(8)@(negedge ck);
   #2;rst_n=0;#1;if(leaf!==0)$fatal(1,"SYSFACE_RESET32 reassert");
   repeat(2)@(negedge ck);
  end
  $display("SYSFACE_RESET32_PASS epochs=32 leaves=112 extra_boot_edges=1");$finish;
 end
endmodule
