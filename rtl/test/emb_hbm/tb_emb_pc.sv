`timescale 1ps/1fs
module tb_emb_pc;
 reg clk=0,hclk=0,rst_n=0;
 always #416.666667 clk=~clk;
 always #512 hclk=~hclk;
 reg s_v=0,w_v=0,s_we=0;
 reg [4:0] s_bank=0,s_col=0;reg [18:0] s_row=24427;
 reg [255:0] w_d=0;
 wire s_credit,e_v,kv_v,fc,fh,row_v,col_v,col_we,col_sr,busy,cmd_credit;
 wire [257:0] e_d;wire [287:0] wd,r_d,kv_d;
 wire r_v;wire [2:0] row_op;wire [4:0] row_bank,col_bank,col_col;wire [18:0] row_row;
 integer credits=0,responses=0,errors=0;
 reg [255:0] expected[0:63];
 ot_qfd_emb_pc #(.ENABLE(1)) dut(
  .clk(clk),.rst_n(rst_n),.hclk(hclk),.hrst_n(rst_n),
  .cmd_v(1'b0),.cmd(32'd0),.read_credit(3'd0),.cmd_credit(cmd_credit),
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
   if(responses==1) begin if(!e_d[257]) errors=errors+1;end
   else if(e_d[255:0]!==expected[responses] || e_d[257] || e_d[256]!=(responses==0)) errors=errors+1;
   responses=responses+1;
  end
 end
 task send(input integer idx,input bit wr);
  begin
   @(negedge clk);s_v=1;w_v=wr;s_we=wr;s_bank=idx%32;s_col=idx/32;w_d=expected[idx];
   @(negedge clk);s_v=0;w_v=0;
  end
 endtask
 integer i,j;
 initial begin
  for(i=0;i<64;i=i+1) for(j=0;j<256;j=j+1) expected[i][j]=((i*19+j*7+j/11)%31)<15;
  repeat(4) @(negedge clk);rst_n=1;
  repeat(20) @(negedge clk);
  for(i=0;i<64;i=i+1) begin send(i,1);wait(credits==i+1);end
  wait(dram.n_swr==64);
  @(negedge hclk);dram.flip(0,24427,0,5,-1);dram.flip(1,24427,0,5,6);
  for(i=0;i<64;i=i+1) begin send(i,0);wait(credits==65+i && responses==i+1);end
  if(errors || fc || fh || dram.viol || kv_v)
   $fatal(1,"FAIL emb_pc errors=%0d faults=%b%b JEDEC=%0d",errors,fc,fh,dram.viol);
  $display("PASS emb_pc writes=64 reads=64 CE=1 UE=1 JEDEC=0 core833.333334ps HBM1024ps");
  $finish;
 end
endmodule
