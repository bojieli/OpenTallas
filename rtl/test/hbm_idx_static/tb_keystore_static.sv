`timescale 1ns/1ps
module tb_keystore_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,key_v=0,store_slot=0;reg[1:0]store_part=0;
 reg[543:0]key_data=0;reg[36:0]key_address=0;
 wire write_v;wire[36:0]write_address;wire[255:0]write_data;wire[31:0]write_mask;wire fault;
 ot_hbm_idx_keystore_static dut(.*);
 // Declared off-chip PHY sink only. This is an external-memory oracle, not an
 // on-chip substituted SRAM or production service qualification.
 reg[7:0]phy[0:1023],expected[0:1023];integer errors=0,sectors=0,bytes=0;
 always @(negedge clk)if(write_v)begin
  sectors++;
  for(integer b=0;b<32;b=b+1)if(write_mask[b])begin phy[int'(write_address)+b]=write_data[b*8+:8];bytes++;end
 end
 initial begin
  for(integer b=0;b<1024;b=b+1)begin phy[b]=8'ha5;expected[b]=8'ha5;end
  repeat(4)@(negedge clk);rst_n=1;
  for(integer k=0;k<8;k=k+1)begin
   key_v=1;key_address=37'(k*68);
   for(integer b=0;b<68;b=b+1)begin key_data[b*8+:8]=8'(k*71+b);expected[k*68+b]=8'(k*71+b);end
   if(MUT==2&&k==3)key_data[11]=~key_data[11];
   @(negedge clk);key_v=0;
   for(integer p=0;p<4;p=p+1)begin store_slot=1;store_part=2'((MUT==1&&k==3&&p==2)?1:p);@(negedge clk);end
   store_slot=0;repeat(2)@(negedge clk);
  end
  repeat(3)@(negedge clk);
  for(integer b=0;b<1024;b=b+1)if(phy[b]!==expected[b])errors++;
  $display("IDX_KEYSTORE_STATIC MUT%0d sectors%0d bytes%0d errors%0d fault%0d",MUT,sectors,bytes,errors,fault);
  if(errors||fault||bytes!=544)$fatal(1,"fixed physicalbyte-mask write mismatch");$finish;
 end
endmodule
