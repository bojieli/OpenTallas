`timescale 1ns/1ps
module tb_native59_qseat_sram;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,clear=0,read_v=0;reg[7:0]write_v=0;
 reg[71:0]write_element=0;reg[255:0]write_data=0;reg[4:0]read_beat=0;
 wire[511:0]read_data;
 qfd_native59_qseat_sram #(.MUT(MUT)) dut(.ck_mem(ck),.element_copies(1152'd0),.valid_copies(128'd0),.*);
 reg[31:0]gold[0:511];reg[511:0]valid=0;reg[511:0]expected;
 integer errors=0,checks=0,cycle=0,k,e;reg[31:0]rng=32'h59c0ffee;
 task tick;
 begin
  @(negedge ck);
  for(integer j=0;j<8;j=j+1)if(write_v[j]&&!clear)begin
   gold[write_element[9*j+:9]]=write_data[32*j+:32];valid[write_element[9*j+:9]]=1;
  end
  for(integer j=0;j<16;j=j+1)expected[32*j+:32]=gold[16*read_beat+j];
  @(posedge ck);#1;
  if(read_v)for(integer j=0;j<16;j=j+1)if(valid[16*read_beat+j])begin
   checks=checks+1;
   if(read_data[32*j+:32]!==expected[32*j+:32])begin
    if(errors<8)$display("QSEAT_ERR c=%0d seat=%0d got=%h want=%h",cycle,16*read_beat+j,read_data[32*j+:32],expected[32*j+:32]);
    errors=errors+1;
   end
  end
  cycle=cycle+1;
 end
 endtask
 initial begin
  tick();rst_n=1;
  // Populate every seat with a permuted scatter: eight different rows per edge.
  for(integer n=0;n<64;n=n+1)begin
   write_v=8'hff;read_v=1;read_beat=5'(n);
   for(k=0;k<8;k=k+1)begin e=((8*n+k)*37+11)%512;write_element[9*k+:9]=9'(e);write_data[32*k+:32]=32'h59000000+32'(e);end
   tick();
  end
  // Exhaustive reads cover retained lanes, with no active writers.
  write_v=0;for(integer n=0;n<32;n=n+1)begin read_beat=5'(n);tick();end
  // Consecutive arbitrary writes, repeated seats, highest-writer priority,
  // same-edge read-after-write bypass, clear suppression, and warm reset.
  for(integer n=0;n<1024;n=n+1)begin
   rng=rng*32'd1664525+32'd1013904223;write_v=rng[7:0];read_beat=rng[12:8];clear=(n%71==0);rst_n=(n%83!=0);
   for(k=0;k<8;k=k+1)begin
    rng=rng*32'd1664525+32'd1013904223;e=rng[8:0];
    if(n%3==0)e=16*int'(read_beat)+(k%4); // duplicate pairs on current read row
    write_element[9*k+:9]=9'(e);write_data[32*k+:32]=rng^32'(n*8+k);
   end
   tick();
  end
  write_v=0;clear=0;rst_n=1;
  for(integer n=0;n<32;n=n+1)begin read_beat=5'(n);tick();end
  if(errors)begin $display("QSEAT_FAIL errors=%0d checks=%0d",errors,checks);$fatal(1);end
  $display("QSEAT_PASS checks=%0d cycles=%0d physical_banks=8 logical_bits=16384 capacity_bits=131072",checks,cycle);$finish;
 end
endmodule
