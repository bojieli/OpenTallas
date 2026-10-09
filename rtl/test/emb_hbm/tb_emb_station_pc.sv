`timescale 1ps/1fs
module tb_emb_station_pc;
 parameter integer STAGES=0,NEG=0;
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
 integer cyc=0,last_send=0,read_sum=0,credit_sum=0,max_inflight=0,sent=0;
 integer read_min=100000,read_max=0;
 always @(posedge clk) cyc=cyc+1;
 reg [255:0] expected[0:63];
 wire [287:0] source_cmd={s_v,w_v,s_we,s_bank,s_col,s_row,w_d};
 wire [287:0] station_cmd;
 wire [259:0] backend_ret;
 ot_qfd_emb_station_pair #(.STAGES(STAGES)) station(.clk(clk),.rst_n(rst_n),.cmd_i(source_cmd),.cmd_o(station_cmd),.ret_i(backend_ret),.ret_o({s_credit,e_v,e_d}));
 ot_qfd_emb_pc_bus #(.ENABLE(1)) dut(
  .clk(clk),.rst_n(rst_n),.hclk(hclk),.hrst_n(rst_n),
  .cmd_v(1'b0),.cmd(32'd0),.read_credit(3'd0),.cmd_credit(cmd_credit),
  .emb_cmd(station_cmd ^ (NEG ? 288'b1 : 288'b0)),.emb_ret(backend_ret),
  .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
  .col_v(col_v),.col_we(col_we),.col_sr(col_sr),.col_bank(col_bank),.col_col(col_col),.busy(busy),
  .r_v(r_v),.r_d(r_d),.wd(wd),.kv_v(kv_v),.kv_d(kv_d),.fault_core(fc),.fault_hbm(fh));
 tb_emb_dram_pc #(.NMEM(128)) dram(
  .clk(hclk),.rst_n(rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
  .col_v(col_v),.col_we(col_we),.col_sr(col_sr),.col_bank(col_bank),.col_col(col_col),
  .wd(wd),.r_v(r_v),.r_d(r_d));
 always @(posedge clk) if(rst_n) begin
  if(sent-credits>max_inflight) max_inflight=sent-credits;
  if(sent-credits>4) $fatal(1,"FAIL speculative SQD credit");
  if(s_credit) begin credits=credits+1;credit_sum=credit_sum+(cyc-last_send);end
  if(e_v) begin
   read_sum=read_sum+(cyc-last_send);
   if(cyc-last_send<read_min)read_min=cyc-last_send;
   if(cyc-last_send>read_max)read_max=cyc-last_send;
   if(responses==1) begin if(!e_d[257]) errors=errors+1;end
   else if(e_d[255:0]!==expected[responses] || e_d[257] || e_d[256]!=(responses==0)) errors=errors+1;
   responses=responses+1;
  end
 end
 task send(input integer idx,input bit wr);
  begin
   @(negedge clk);last_send=cyc;sent=sent+1;s_v=1;w_v=wr;s_we=wr;s_bank=idx%32;s_col=idx/32;w_d=expected[idx];
   @(negedge clk);s_v=0;w_v=0;
  end
 endtask
 integer i,j;
 initial begin
  for(i=0;i<64;i=i+1) for(j=0;j<256;j=j+1) expected[i][j]=((i*19+j*7+j/11)%31)<15;
  repeat(4) @(negedge clk);
  if(STAGES>0 && {station_cmd,s_credit,e_v,e_d} !== 0) $fatal(1,"FAIL resetzero stations");
  rst_n=1;
  repeat(20) @(negedge clk);
  for(i=0;i<64;i=i+1) begin send(i,1);wait(credits==i+1);end
  wait(dram.n_swr==64);
  @(negedge hclk);dram.flip(0,24427,0,5,-1);dram.flip(1,24427,0,5,6);
  for(i=0;i<64;i=i+1) begin send(i,0);wait(credits==65+i && responses==i+1);end
  if(errors || fc || fh || dram.viol || kv_v)
   $fatal(1,"FAIL emb_pc errors=%0d faults=%b%b JEDEC=%0d",errors,fc,fh,dram.viol);
  $display("PASS station_pc STAGES=%0d writes64 reads64 CE1 UE1 JEDEC0 max_inflight=%0d read_sum=%0d read_min=%0d read_max=%0d credit_sum=%0d total_cycles=%0d core833.333334ps HBM1024ps",STAGES,max_inflight,read_sum,read_min,read_max,credit_sum,cyc);
  $finish;
 end
endmodule
