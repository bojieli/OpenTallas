`timescale 1ps/1ps
// HBM-REFORM-B9: landing-fault bench for ot_svgr_landing (head-register form, B8).
// Instance a: 8 good rows -> 8 credits, 1 complete, no fault, rows read back.
// Instance b: rows 0,1,2, duplicate row 1 (seen -> fault), rows 3,4,5 queued behind it.
//   Expect fault, exactly 4 credits (entries up to and including the faulted one), 3 landing writes, no complete.
//   A FIFO that pops past the faulted head returns a 5th credit (pop-every-cycle mutant).
module tb_svgr_landing_fault;
 localparam integer LB=2, IW=283+LB; localparam [2:0] BID=3'd3; localparam [15:0] EP=16'h55a1;
 reg hclk=0, sclk=0, rst_n=0, stop=1; always #512 hclk=~hclk; always #417 sclk=~sclk;
 reg [1:0] in_v=0; reg [IW-1:0] in_d[0:1]; reg res_v=0; reg rd_v=0; reg [5:0] rd_row=0;
 wire [1:0] fr_a, fr_b; wire cv_a, cv_b, f_a, f_b; wire [LB-1:0] cb_a, cb_b; wire [255:0] rd_a, rd_b;
 ot_svgr_landing u_a(.hbm_clk(hclk),.hbm_rst_n(rst_n),.stream_clk(sclk),.stream_rst_n(rst_n),.bank_id(BID),
  .in_v(in_v[0]),.in_data(in_d[0]),.freed(fr_a),.reserve_v(res_v),.reserve_bank(2'd1),.reserve_epoch(EP),.reserve_total(12'd64),.stop(stop),
  .complete_v(cv_a),.complete_bank(cb_a),.fault(f_a),.read_v(rd_v),.read_bank(2'd1),.read_row(rd_row),.read_data(rd_a));
 ot_svgr_landing u_b(.hbm_clk(hclk),.hbm_rst_n(rst_n),.stream_clk(sclk),.stream_rst_n(rst_n),.bank_id(BID),
  .in_v(in_v[1]),.in_data(in_d[1]),.freed(fr_b),.reserve_v(res_v),.reserve_bank(2'd1),.reserve_epoch(EP),.reserve_total(12'd64),.stop(stop),
  .complete_v(cv_b),.complete_bank(cb_b),.fault(f_b),.read_v(rd_v),.read_bank(2'd1),.read_row(rd_row),.read_data(rd_b));
 function automatic [255:0] pay(input integer r); pay={8{r[7:0]^8'h3c,24'hc0ffee}}^{32{r[7:0]}}; endfunction
 function automatic [IW-1:0] pkt(input integer r); pkt={2'b00,r[5:0],BID,2'd1,EP,pay(r)}; endfunction
 integer cr_a=0, cr_b=0, cm_a=0, cm_b=0, wr_b=0, errs=0, i;
 always @(posedge hclk) if(rst_n) begin cr_a<=cr_a+fr_a; cr_b<=cr_b+fr_b; end
 always @(posedge sclk) if(rst_n) begin cm_a<=cm_a+cv_a; cm_b<=cm_b+cv_b; wr_b<=wr_b+(u_b.landing_write?1:0); end
 integer rows_b[0:6]; initial begin rows_b[0]=0;rows_b[1]=1;rows_b[2]=2;rows_b[3]=1;rows_b[4]=3;rows_b[5]=4;rows_b[6]=5; end
 task chk(input bit ok, input string m); if(!ok) begin errs=errs+1; $display("FAULT %s", m); end endtask
 initial begin
  in_d[0]=0; in_d[1]=0;
  repeat(4) @(posedge hclk); rst_n=1; repeat(6) @(posedge sclk);
  @(negedge sclk) res_v=1; @(negedge sclk) res_v=0;
  for(i=0;i<8;i=i+1) begin @(negedge hclk); in_v=2'b01|(i<7?2'b10:2'b00); in_d[0]=pkt(i); in_d[1]=pkt(i<7?rows_b[i]:0); end
  @(negedge hclk); in_v=0;
  repeat(8) @(posedge sclk); @(negedge sclk) stop=0;
  repeat(120) @(posedge sclk);
  chk(cr_a==8, $sformatf("a credits %0d exp 8", cr_a)); chk(cm_a==1, $sformatf("a completes %0d exp 1", cm_a)); chk(f_a==0, "a fault set");
  chk(f_b==1, "b fault not set"); chk(cr_b==4, $sformatf("b credits %0d exp 4", cr_b)); chk(wr_b==3, $sformatf("b writes %0d exp 3", wr_b)); chk(cm_b==0, $sformatf("b completes %0d exp 0", cm_b));
  for(i=0;i<8;i=i+1) begin @(negedge sclk); rd_v=1; rd_row=i[5:0]; @(negedge sclk); rd_v=0; @(posedge sclk); #1; chk(rd_a==pay(i), $sformatf("a row %0d data", i)); end
  if(errs==0) $display("LANDING_FAULT_BENCH PASS"); else $display("LANDING_FAULT_BENCH FAIL errs=%0d", errs);
  $finish;
 end
endmodule
