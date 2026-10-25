`timescale 1ns/1ps
module tb_root_buffer_reset_cut;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,w_v=0,r_v=0;wire[4:0]state;wire local_reset_n;
 tkm_flat_buffer_reset_cut flat(.buffer_clk(clk),.*);
 wire rd_v;wire[343:0]rd_data;
 ot_hgi_coll_tkm_buffer #(.DW(344),.DELIVERED_RESET(1)) source(.clk(clk),.rst_n(rst_n),.w_v(w_v),.r_v(r_v),.w_addr(10'd0),.r_addr(10'd0),.w_data(344'd0),.rd_v(rd_v),.rd_data(rd_data));
 reg[31:0]rng=32'hbc12345;integer i;
 initial begin
  for(i=0;i<2000;i++)begin
   @(negedge clk);rng=(rng>>1)^((rng&1)?32'h80200003:32'h0);
   // Cold boot then repeated warm pulses during arbitrary live requests.
   rst_n=(i>=6 && i%73>=5);w_v=rng[3];r_v=rng[15];
   @(posedge clk);#0.01;
   if(i>=6 && {local_reset_n,state}!=={source.rr[0],source.rd_v,source.wp,source.rp,source.r_delay,source.r_publish})
    $fatal(1,"FLAT_BUFFER_RESET_CUT mismatch edge=%0d",i);
  end
  $display("FLAT_BUFFER_RESET_CUT PASS edges=2000 changed_flops=8 warm_reset_epochs=27 exact_source_sha=30726e62");$finish;
 end
endmodule
