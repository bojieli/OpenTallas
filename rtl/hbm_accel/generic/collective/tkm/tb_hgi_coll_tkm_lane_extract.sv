`timescale 1ns/1ps
module tb_hgi_coll_tkm_lane_extract #(parameter integer MUT_LANE=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;
 reg[3:0]dv=0,dr=0;reg[2179:0]df=0;
 wire[3:0]permit;wire busy,done,fault;
 ot_hgi_coll_tkm_seq #(.KMAX(64)) gold(.clk(clk),.rst_n(rst_n),.start(start),
  .cfg_n(12'd256),.cfg_k(13'd64),.cfg_g(8'd1),.cfg_gbase(8'd0),.cfg_pf(16'd32),.cfg_nout(13'd64),
  .cfg_obase(40'd1024),.cfg_rbase(40'd4096),.cfg_has_r(1'b1),
  .del_reserve(dr),.del_permit(permit),.del_valid(dv),.del_flit(df),.w_rdy(1'b1),
  .busy(busy),.done(done),.fault(fault),.chain_up(340'd0),.chain_tau(84'd0),.chain_busy(1'b0));
 wire p,ft,decv,fe,ldv;wire[679:0]de,he;wire[7:0]hm,taken,occ;wire[1:0]hn,early;
 ot_hgi_coll_tkm_lane #(.MUT(MUT_LANE)) dut(.clk(clk),.rst_n(rst_n),.del_valid(dv[0]),.del_reserve(dr[0]),.del_flit(df[544:0]),
  .cfg_g(gold.g_q),.cfg_gbase(gold.gb_q),.cfg_pf(gold.pf_q),.ins_live(gold.ins_live),.tau(gold.tau),
  .sel_take(gold.sel_take[0]),.sel_pop(gold.sel_pop[0]),.del_permit(p),.fault(ft),.early_valid(early),
  .decoded_v(decv),.decoded_e(de),.head_e(he),.head_m(hm),.taken(taken),.head_n(hn),.occ(occ),
  .landing_v(ldv),.fifo_empty(fe));
 integer checked=0,cyc=0,flits=0;
 always @(negedge clk)begin
  cyc=cyc+1;
  if(cyc>12&&rst_n)begin
   checked=checked+1;
   if(p!==permit[0]||decv!==gold.d2_v[0]||hn!==gold.st_n[0]||taken!==gold.dn[0]||occ!==gold.occ[0]||
      ldv!==gold.ld_v[0]||fe!==gold.fe[0]||early!=={gold.d1_v[0],gold.d0_v[0]})begin
    $display("TKM_LANE_EXTRACT FAIL controls cycle=%0d checks=%0d p=%b/%b hn=%d/%d occ=%d/%d",cyc,checked,p,permit[0],hn,gold.st_n[0],occ,gold.occ[0]);$fatal(1);
   end
   if(decv&&de!==gold.d2_e[0])begin $display("TKM_LANE_EXTRACT FAIL decoder cycle=%0d",cyc);$fatal(1);end
   if(hn!=0&&(he!==gold.st_e[0][0]||hm!==gold.st_m[0][0]))begin $display("TKM_LANE_EXTRACT FAIL head cycle=%0d",cyc);$fatal(1);end
  end
 end
 initial begin
  repeat(5)@(negedge clk);rst_n=1;repeat(15)@(negedge clk);start=1;@(negedge clk);start=0;
  wait(gold.ins_live);@(negedge clk);
  for(integer f=0;f<32;f=f+1)begin
   while(!permit[0])@(negedge clk);
   df='0;df[544]=1;df[512+:16]=16'(f);df[528+:8]=0;
   for(integer j=0;j<8;j=j+1)begin df[j*32+:32]=32'h3f000000|($random&32'h007fffff);df[(8+j)*32+:32]=32'(8*f+j);end
   dv=1;dr=1;flits=flits+1;@(negedge clk);
   dv=0;dr=0;
   if((f%3)==0)repeat(2)@(negedge clk);
  end
  repeat(800)@(negedge clk);
  if(ft)begin $display("TKM_LANE_EXTRACT FAIL fault");$fatal(1);end
  $display("TKM_LANE_EXTRACT PASS checked=%0d flits=%0d",checked,flits);$finish;
 end
 initial begin #100000;$display("TKM_LANE_EXTRACT FAIL progress");$fatal(1);end
endmodule
