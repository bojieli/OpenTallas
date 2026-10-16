`timescale 1ps/1fs
module tb_static_boot_cdc #(parameter integer MUT=0);
 reg ck=0,hck=0,rst=0,hrst=0;
 always #312.5 ck=~ck;always #384 hck=~hck;
 reg we=0,last=0;reg[7:0]addr=0;reg[63:0]data=0;
 wire sw,seal,applied,fc,fh;wire[7:0]sa;wire[63:0]sd;
 qkd_static_kv_boot_cdc #(.HAS_SEAL(1),.MUT(MUT))dut(.ck(ck),.rst_n(rst),.hck(hck),.hrst_n(hrst),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),.cfg_last(last),.sink_we(sw),.sink_addr(sa),.sink_data(sd),.sink_seal(seal),.applied_hbm(applied),.fault_core(fc),.fault_hbm(fh));
 integer seen=0,seals=0,a;reg[31:0]age=0;
 always @(posedge hck)begin
  #1;if(sw)begin
   if(sa!=8'(seen)||sd!=(64'h1234567800000000^64'(seen)))$fatal(1,"actual CDC word differs");
   if(seen>=32||seals!=0)$fatal(1,"late/duplicate boot word");seen=seen+1;
  end
  if(seal)begin if(seen!=32||seals!=0)$fatal(1,"seal before actual final word");seals=seals+1;age=0;end
  else if(seals!=0)age=age+1;
  if(applied&&(seen!=32||seals!=1||age<2))$fatal(1,"applied before actual child seal acceptance age");
 end
 initial begin
  repeat(4)@(negedge ck);rst=1;hrst=1;repeat(20)@(negedge ck);
  for(a=0;a<32;a=a+1)begin we=1;addr=8'(a);data=64'h1234567800000000^64'(a);last=a==31;@(negedge ck);end
  we=0;last=0;repeat(60)@(negedge ck);
  if(seen!=32||seals!=1||!applied||fc||fh)$fatal(1,"actual CDC did not apply exact complete image");
  we=1;@(negedge ck);we=0;repeat(3)@(negedge ck);if(!fc)$fatal(1,"post-seal write not rejected");
  $display("PASS actual boot FIFO32consecutive words core625/HBM768 exact, seal/application age, postseal rejection MUT%0d",MUT);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
