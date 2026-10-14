`timescale 1ns/1ps
module tb_hgi_hc_coeff_bank;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,wr_v=0;reg[2:0]wr_index=0;reg[127:0]wr_data=0;
 wire[127:0]coef0,coef1,coef2,coef3,coef4;
`ifdef COEFF_ASSOC_MUT
 ot_hgi_hc_coeff_bank_assoc_mut dut(.*);
`else
 ot_hgi_hc_coeff_bank dut(.*);
`endif
 reg[127:0]want[0:4];wire[127:0]got[0:4];
 assign got[0]=coef0;assign got[1]=coef1;assign got[2]=coef2;assign got[3]=coef3;assign got[4]=coef4;
 integer errors=0,checks=0,i,j;
 task check_all;begin
  for(integer k=0;k<5;k=k+1)begin checks++;if(got[k]!==want[k])begin errors++;$display("ERR bank%0d got%h want%h",k,got[k],want[k]);end end
 end endtask
 task send(input[2:0]index,input[127:0]data);begin @(negedge clk);wr_v=1;wr_index=index;wr_data=data;end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  // Sustained one-command/edge writes must preserve each 128-bit word's bank and word association.
  for(i=0;i<5;i=i+1)begin want[i]={32'h100+i,32'h200+i,32'h300+i,32'h400+i};send(i,want[i]);end
  @(negedge clk);wr_v=0;repeat(3)@(negedge clk);check_all();
  for(j=0;j<3;j=j+1)begin
   for(i=4;i>=0;i=i-1)begin want[i]={32'h500+j+i,32'h600+j+i,32'h700+j+i,32'h800+j+i};send(i,want[i]);end
   @(negedge clk);wr_v=0;repeat(3)@(negedge clk);check_all();
  end
  // Invalid command indices leave retained banks intact.
  for(i=5;i<8;i=i+1)send(i,128'hdeadbeef);@(negedge clk);wr_v=0;repeat(3)@(negedge clk);check_all();
  // Asynchronous abort between capture and write must discard the pending command while retaining coefficients.
  send(2,128'hfeedface);@(negedge clk);rst_n=0;wr_v=0;repeat(3)@(negedge clk);check_all();
  rst_n=1;repeat(4)@(negedge clk);check_all();
  want[2]=128'h1234567890abcdef0123456789abcdef;send(2,want[2]);@(negedge clk);wr_v=0;repeat(3)@(negedge clk);check_all();
  if(errors==0)$display("HC_COEFF_BANK PASS checks=%0d",checks);else $display("HC_COEFF_BANK FAIL errors=%0d checks=%0d",errors,checks);$finish;
 end
endmodule
