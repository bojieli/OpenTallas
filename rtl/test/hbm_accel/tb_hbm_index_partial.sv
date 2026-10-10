`timescale 1ps/1ps
// Minimum actual assembler partial final group; no full-controller surrogate.
module tb_hbm_index_partial #(parameter integer BLOCKS=1);
 reg clk=0;always #512 clk=~clk;
 reg rst_n=0,start=0;reg[31:0]sector_v=0;reg[383:0]sector_j=0;
 wire[8791:0]lines;wire[63:0]pop;wire done,fault,retained;
 wire[7:0]credit;
 for(genvar p=0;p<8;p=p+1)assign credit[p]=lines[p*1099]&&lines[p*1099+1+:10]<BLOCKS*4;
 ot_hbm_index_lines #(.ENABLE(1),.DEPTH(64),.CRED(64)) dut(.clk(clk),.rst_n(rst_n),.start(start),.blocks(9'(BLOCKS)),
 .sector_v(sector_v),.sector_j(sector_j),.sector_data(8192'd0),.credit(credit),.lines(lines),.pop(pop),.done(done),.fault(fault),.retained(retained));
 integer seen=0,wave,p;
 always@(posedge clk)if(rst_n)begin
  if(fault)$fatal(1,"assembler fault");
  for(integer l=0;l<8;l=l+1)if(lines[l*1099])begin
   if(lines[l*1099+1+:10]>=BLOCKS*4)$fatal(1,"SPURIOUS_PARTIAL_LINE blocks=%0d tag=%0d",BLOCKS,lines[l*1099+1+:10]);
   seen=seen+1;
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;
  for(wave=0;wave<(BLOCKS*17+31)/32;wave=wave+1)begin
   sector_v=0;
   for(p=0;p<32;p=p+1)begin sector_v[p]=wave*32+p<BLOCKS*17;sector_j[p*12+:12]=12'(wave);end
   @(negedge clk);
  end
  sector_v=0;repeat(20)@(negedge clk);
  if(seen!=BLOCKS*4||retained)$fatal(1,"PARTIAL_CREDIT_DEBT blocks=%0d seen=%0d retained=%0b",BLOCKS,seen,retained);
  $display("PASS_INDEX_PARTIAL blocks=%0d lines=%0d no_credit_debt=1",BLOCKS,seen);$finish;
 end
endmodule
