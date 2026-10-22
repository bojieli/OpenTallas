`timescale 1ns/1ps
module tb_col8_residual_equiv;
 reg clk=0;always#5 clk=~clk;
 reg rst_n=0,half=0,keep_en=1,ql_v=0,beat_v=0;
 reg[7:0]rank=0,ql_head=0,beat_index=0;reg[10:0]first_ord=0;reg[11:0]nkeys=2736;
 reg[170:0]keep_bitmap=171'h5555555555555555555555555555555555555555555;
 reg[511:0]ql_codes=0;reg[31:0]ql_sc=0;reg[15:0]ql_w=0;reg[4395:0]key_lines=0;
 reg[1023:0]cut_cs=0;reg[31:0]cut_cf=0;reg[127:0]cut_prdy=0;
 wire[305:0]s0,s1;wire f0,f1;wire[31:0]r0,r1,v0,v1;
 wire[18175:0]q0,q1;wire[17407:0]k0,k1;wire[2047:0]h0,h1;
 integer n=0,checks=0,valid=0;reg[31:0]rng=32'h35270391;
 function automatic[31:0]step(input[31:0]x);reg[31:0]z;begin z=x^(x<<13);z=z^(z>>17);step=z^(z<<5);end endfunction
 wire[170:0]dut_keep=`ifdef RESID_MUT_KEEP ~keep_bitmap `else keep_bitmap `endif;
 ot_col8_quarter_reference #(.TP(192)) refq(.clk_ctl(clk),.clk_engine({2{clk}}),.clk_meta({2{clk}}),.clk_tail({2{clk}}),.clk_chunk({8{clk}}),.clk_hslice({256{clk}}),.rst_n(rst_n),.half(half),.rank(rank),.first_ord(first_ord),.nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.beat_v(beat_v),.beat_index(beat_index),.key_lines(key_lines),.score(s0),.fault(f0),.cut_rst_n(r0),.cut_qv(v0),.cut_q(q0),.cut_key(k0),.cut_hid(h0),.cut_cs(cut_cs),.cut_cf(cut_cf),.cut_prdy(cut_prdy));
 ot_hbm_idx_score_quarter_col8_control #(.TP(192)) dut(.clk_ctl(clk),.clk_engine({2{clk}}),.clk_meta({2{clk}}),.clk_tail({2{clk}}),.clk_chunk({8{clk}}),.clk_hslice({256{clk}}),.rst_n(rst_n),.half(half),.rank(rank),.first_ord(first_ord),.nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(dut_keep),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.beat_v(beat_v),.beat_index(beat_index),.key_lines(key_lines),.score(s1),.fault(f1),.cut_rst_n(r1),.cut_qv(v1),.cut_q(q1),.cut_key(k1),.cut_hid(h1),.cut_cs(cut_cs),.cut_cf(cut_cf),.cut_prdy(cut_prdy));
 always@(negedge clk)begin
  if(n>2&&r0!==r1)$fatal(1,"COL8_RESIDUAL_EQUIV_FAIL reset cycle=%0d",n);
  if(n>200)begin
   if({v0,q0,k0,h0}!=={v1,q1,k1,h1})$fatal(1,"COL8_RESIDUAL_EQUIV_FAIL delivery cycle=%0d",n);
   if(s0[0]!==s1[0] || (s0[0]&&s0!==s1) || f0!==f1)$fatal(1,"COL8_RESIDUAL_EQUIV_FAIL score cycle=%0d ref=%h dut=%h",n,s0,s1);
   checks=checks+1;if(s0[0])valid=valid+1;
  end
 end
 initial begin
  repeat(1800)begin
   @(posedge clk);#1;n=n+1;rst_n=(n>4&&(n%509)!=0&&(n%509)!=1);
   rng=step(rng);half=rng[0];rank=8'(n%192);first_ord=11'(n%32);nkeys=12'(1000+n%1700);
   keep_en=(n%7!=0);keep_bitmap={keep_bitmap[169:0],rng[7]};ql_v=(n%29==1);ql_head=8'(n%32);ql_codes={16{rng}};ql_sc=rng;ql_w=rng[15:0];
   beat_v=(n%3!=0);beat_index=8'(n%171);cut_prdy=rst_n?{128{1'b1}}:0;
   for(integer j=0;j<4;j=j+1)begin key_lines[j*1099+:1099]={35{rng}};key_lines[j*1099]=1;key_lines[j*1099+1+:10]=10'((4*int'(half)+j)*128+int'(beat_index));end
   for(integer j=0;j<32;j=j+1)cut_cs[j*32+:32]=32'h3f000000+32'((n+j)%2000)*32'h4000;
   cut_cf=(n%37==0)?32'h55555555:0;
  end
  @(negedge clk);#1;if(valid<100)$fatal(1,"COL8_RESIDUAL_EQUIV_TOO_FEW_VALID %0d",valid);
  $display("COL8_RESIDUAL_EQUIV_PASS checks=%0d valid=%0d TP=192 real_controllers_no_array",checks,valid);$finish;
 end
endmodule
