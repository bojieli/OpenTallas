`timescale 1ns/1ps
// Cycle equivalence: 16 monolithic ot_hgi_sfu_lane_map (grid wiring, lane_j = j) vs 4 ot_hgi_sfu_bcast_e0 nodes + 16
// ot_hgi_sfu_lane_map_e123.  Every output bit of every lane compared every cycle, random controller words, random warm
// resets; the pass payload (no reset by design) is exempt only during the 4 edges after a reset release, its load strobe
// (pass[460]) and emit never.  Lane 5 additionally runs a live (changing) lane_j on both sides.
module tb_hgi_sfu_bcast_tree #(parameter integer MUT=0);
 reg clk=0; always #0.4167 clk=~clk;
 reg rst_n=0;
 reg [479:0] terms; reg [23:0] ov,iv,row; reg [3:0] ls,lvw; reg emit; reg [460:0] pass; reg [3:0] jl;
 wire [1199:0] a_ldc[0:15], b_ldc[0:15]; wire [23:0] a_o[0:15],a_i[0:15],a_r[0:15],b_o[0:15],b_i[0:15],b_r[0:15];
 wire [3:0] a_ls[0:15],a_lvw[0:15],b_ls[0:15],b_lvw[0:15]; wire a_e[0:15],b_e[0:15]; wire [460:0] a_p[0:15],b_p[0:15];
 wire [479:0] n_terms[0:3]; wire [23:0] n_ov[0:3],n_iv[0:3],n_row[0:3]; wire [3:0] n_ls[0:3],n_lvw[0:3]; wire n_emit[0:3],n_ld[0:3];
 wire [459:0] n_pass[0:3];
 for(genvar q=0;q<4;q++) begin:g_n
  ot_hgi_sfu_bcast_e0 u_n(.clk(clk),.rst_n(rst_n),.ld_terms(terms),.i_o_v(ov),.i_i_v(iv),.i_krow(row),.i_ls(ls),.i_lvw(lvw),
   .i_emit(emit),.i_pass(pass),.e0_terms(n_terms[q]),.e0_ov(n_ov[q]),.e0_iv(n_iv[q]),.e0_row(n_row[q]),.e0_ls(n_ls[q]),
   .e0_lvw(n_lvw[q]),.e0_emit(n_emit[q]),.e0_pass(n_pass[q]),.e0_ld(n_ld[q]));
 end
 for(genvar j=0;j<16;j++) begin:g_l
  wire [3:0] lj = (j==5) ? jl : 4'(j);
  ot_hgi_sfu_lane_map u_a(.clk(clk),.rst_n(rst_n),.lane_j(lj),.ld_terms(terms),.i_o_v(ov),.i_i_v(iv),.i_krow(row),.i_ls(ls),
   .i_lvw(lvw),.i_emit(emit),.i_pass(pass),.o_ld_c(a_ldc[j]),.o_o_v(a_o[j]),.o_i_v(a_i[j]),.o_krow(a_r[j]),.o_ls(a_ls[j]),
   .o_lvw(a_lvw[j]),.o_emit(a_e[j]),.o_pass(a_p[j]));
  ot_hgi_sfu_lane_map_e123 #(.MUT_LANE(MUT==1 && j==9),.MUT_PASS(MUT==2)) u_b(.clk(clk),.rst_n(rst_n),.lane_j(lj),
   .e0_terms(n_terms[j/4]),.e0_ov(n_ov[j/4]),.e0_iv(n_iv[j/4]),.e0_row(n_row[j/4]),.e0_ls(n_ls[j/4]),.e0_lvw(n_lvw[j/4]),
   .e0_emit(n_emit[j/4]),.e0_pass(n_pass[j/4]),.e0_ld(n_ld[j/4]),
   .o_ld_c(b_ldc[j]),.o_o_v(b_o[j]),.o_i_v(b_i[j]),.o_krow(b_r[j]),.o_ls(b_ls[j]),.o_lvw(b_lvw[j]),.o_emit(b_e[j]),.o_pass(b_p[j]));
 end
 integer checks=0, errors=0, since_rst=100, resets=0, emits=0, loads=0;
 always @(posedge clk) begin
  #0.01;
  if(rst_n) since_rst=since_rst+1; else since_rst=0;
  for(integer j=0;j<16;j++) begin
   checks++;
   if(a_ldc[j]!==b_ldc[j] || a_o[j]!==b_o[j] || a_i[j]!==b_i[j] || a_r[j]!==b_r[j] || a_ls[j]!==b_ls[j] || a_lvw[j]!==b_lvw[j] ||
      a_e[j]!==b_e[j] || a_p[j][460]!==b_p[j][460] || (since_rst>4 && a_p[j][459:0]!==b_p[j][459:0])) begin
    errors++; if(errors<8) $display("BCAST_MISMATCH t%0t lane%0d emit %b/%b ld %b/%b",$time,j,a_e[j],b_e[j],a_p[j][460],b_p[j][460]);
   end
   if(a_e[j]) emits++; if(a_p[j][460]) loads++;
  end
 end
 initial begin
  terms=0;ov=0;iv=0;row=0;ls=0;lvw=0;emit=0;pass=0;jl=5;
  repeat(6) @(negedge clk); rst_n=1;
  for(integer n=0;n<20000;n++) begin
   @(negedge clk);
   for(integer k=0;k<20;k++) terms[k*24+:24]=$urandom;
   ov=$urandom; iv=$urandom; row=$urandom; ls=$urandom%10; lvw=$urandom; emit=$urandom; jl=($urandom%8==0) ? 4'($urandom) : jl;
   for(integer k=0;k<15;k++) pass[k*30+:30]=30'($urandom); pass[460:450]=11'($urandom);
   if(n%3001==1500) begin rst_n=0; resets++; repeat(1+$urandom%5) @(negedge clk); rst_n=1; since_rst=0; end
  end
  repeat(10) @(negedge clk);
  if(emits<1000 || loads<1000 || resets<5) begin errors++; $display("INSUFFICIENT_COVERAGE"); end
  if(errors==0) $display("PASS SFU_BCAST_TREE checks=%0d emits=%0d loads=%0d warm_resets=%0d", checks, emits, loads, resets);
  else $display("SFU_BCAST_TREE FAIL errors=%0d", errors);
  $finish;
 end
endmodule
