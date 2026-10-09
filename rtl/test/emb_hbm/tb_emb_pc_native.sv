`timescale 1ps/1fs
module tb_emb_pc_native;
 parameter integer ENABLE=1;
 import ot_qfd_emb_pkg::*;
 reg clk=0,hclk=0,rst_n=0;
 always #416.666667 clk=~clk;
 always #512 hclk=~hclk;
 reg s_v=0,w_v=0,s_we=0;reg desc_v=0,go_v=0,wr_v=0,window_retired=0,write_quiet=1,transport_quiet=1;reg[18:0]desc_row=24427;reg[10:0]desc_n=64;reg[4:0]wr_bank=0,wr_col=0;wire desc_take,go_take,wr_take;wire[2:0]read_release=kv_v?3'd1:3'd0;integer native_responses=0,native_commands=0;
 reg [4:0] s_bank=0,s_col=0;reg [18:0] s_row=24427;
 reg [255:0] w_d=0;
 wire s_credit,e_v,kv_v,fc,fh,row_v,col_v,col_we,col_sr,busy,cmd_credit;
 wire [257:0] e_d;wire [287:0] wd,r_d,kv_d;
 wire r_v;wire [2:0] row_op;wire [4:0] row_bank,col_bank,col_col;wire [18:0] row_row;
 integer credits=0,responses=0,errors=0;
 reg [255:0] expected[0:63];
 ot_qfd_emb_pc_native #(.ENABLE(ENABLE)) dut(
  .clk(clk),.rst_n(rst_n),.hclk(hclk),.hrst_n(rst_n),
  .desc_v(desc_v),.desc_row(desc_row),.desc_n(desc_n),.go_v(go_v),.wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.window_retired(window_retired),.write_quiet(write_quiet),.transport_quiet(transport_quiet),.read_release(read_release),.desc_take(desc_take),.go_take(go_take),.wr_take(wr_take),
  .s_v(s_v),.w_v(w_v),.s_we(s_we),.s_bank(s_bank),.s_col(s_col),.s_row(s_row),.w_d(w_d),
  .s_credit(s_credit),.e_v(e_v),.e_d(e_d),
  .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
  .col_v(col_v),.col_we(col_we),.col_sr(col_sr),.col_bank(col_bank),.col_col(col_col),.busy(busy),
  .r_v(r_v),.r_d(r_d),.wd(wd),.kv_v(kv_v),.kv_d(kv_d),.fault_core(fc),.fault_hbm(fh));
 tb_emb_dram_pc #(.NMEM(128)) dram(
  .clk(hclk),.rst_n(rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
  .col_v(col_v),.col_we(col_we),.col_sr(col_sr),.col_bank(col_bank),.col_col(col_col),
  .wd(wd),.r_v(r_v),.r_d(r_d));
 always @(posedge clk) if(rst_n) begin
  if(s_credit) credits=credits+1;
  if(e_v) begin
   if(e_d[255:0]!==expected[responses] || e_d[257] || e_d[256]) errors=errors+1;
   responses=responses+1;
  end
 end
 task send(input integer idx,input bit wr);
  begin
   @(negedge clk);s_v=1;w_v=wr;s_we=wr;s_bank={(3'(idx>>7)),2'(idx)};s_col=5'(idx>>2);w_d=expected[idx];
   @(negedge clk);s_v=0;w_v=0;
  end
 endtask
 always @(posedge hclk)if(rst_n)begin
 if(dut.cmd_v)native_commands=native_commands+1;
 if(kv_v)begin
 if(kv_d!==enc256(expected[native_responses]))$fatal(1,"nativeprotectedreturn mismatch %0d",native_responses);
 native_responses=native_responses+1;
 end
 end
 integer cycles=0;always @(posedge hclk)if(rst_n)begin cycles<=cycles+1;if(cycles>20000)$fatal(1,"nativePC finitegate incomplete");end
 integer i,j;
 initial begin
  for(i=0;i<64;i=i+1) for(j=0;j<256;j=j+1) expected[i][j]=((i*19+j*7+j/11)%31)<15;
  repeat(4) @(negedge clk);rst_n=1;
  repeat(20) @(negedge clk);
  if(ENABLE==0)begin
   desc_v=1;go_v=1;s_v=1;w_v=1;s_we=1;
   repeat(20)@(negedge hclk);
   if(desc_take||go_take||wr_take||row_v||col_v||e_v||kv_v||fc||fh||s_credit)$fatal(1,"defaultoff wrapper active");
   $display("PASS emb_pc_native defaultoff quiet");$finish;
  end
  for(i=0;i<64;i=i+1) begin send(i,1);wait(credits==i+1);end
  wait(dram.n_swr==64);
  // Actual nativeprovider DESC/GO causes64 realcontroller KV-class reads.
  @(negedge hclk);desc_v=1;go_v=1;
  @(negedge hclk);desc_v=0;go_v=0;
  wait(native_responses==64);
  @(negedge hclk);window_retired=1;@(negedge hclk);window_retired=0;
  repeat(5)@(negedge hclk);
  for(i=0;i<64;i=i+1) begin send(i,0);wait(credits==65+i && responses==i+1);end
  if(errors || fc || fh || dram.viol)
   $fatal(1,"FAIL emb_pc errors=%0d faults=%b%b JEDEC=%0d",errors,fc,fh,dram.viol);
  if(native_commands!=2||native_responses!=64)$fatal(1,"nativeDESC/GO path unexercised");
  $display("PASS emb_pc_native staticWR64/staticRD64/nativeRD64 providerDESC/GO2 actualreadcredit recycle JEDEC0 core833.333334ps HBM1024ps");
  $finish;
 end
endmodule
