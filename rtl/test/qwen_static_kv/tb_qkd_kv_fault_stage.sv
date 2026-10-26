`timescale 1ns/1ps
module tb_qkd_kv_fault_stage;
 reg ck=0;always #0.416667 ck=~ck;
 reg[0:0]a=0;wire[0:0]b;
 reg[31:0]rng=32'h3498a78b;reg previous;
 qkd_kv_fault_stage dut(.ck(ck),.a(a),.b(b));
 initial begin
  for(integer n=0;n<20000;n=n+1)begin
   @(negedge ck);
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   a=(n<32)?!(n%2):rng[0];
   #0.001;
   if(n>0&&b!==previous)$fatal(1,"KV_FAULT_STAGE FAIL changed before observation edge word%0d",n);
   @(posedge ck);#0.001;
   if(b!==a)$fatal(1,"KV_FAULT_STAGE FAIL observation mismatch word%0d",n);
   previous=a;
  end
  $display("KV_FAULT_STAGE PASS 20000 words one fault observation edge zero normal payload edges");$finish;
 end
 initial begin #20000;$fatal(1,"KV_FAULT_STAGE FAIL timeout");end
endmodule
