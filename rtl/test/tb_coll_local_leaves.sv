`timescale 1ns/1ps
// Independent original-parent references. No reference output drives a DUT.
// The reference S ring instantiates the same actual SRAM macro model as DUT.
module tb_coll_local_leaves;
parameter integer LS=376;
reg clk=0;always #5 clk=~clk;
reg rst_counter_n=0,rst_data_n=0,rst_meta_n=0;
reg tc_d=0,gd_d=0,tc_v=0,tc_o=0,tc_l=0,g_run=0,g_od=0,g_l=0;
reg[31:0]tc_t=0,g_t=0;reg[1:0]pkg=0,g_r=0,td_r=0;
reg tf_v_d=0,tf_o_d=0,tf_v=0,tf_l=0,rf_e=0,gd_v=0,td_od=0,td_l=0;
reg die_d=0,token_d=0;reg[3:0]fold_error=0;
reg[511:0]pf=0,lo=0,hi=0,rr=0,dr=0,td=0,sr0=0,sr1=0,sr2=0,local_data=0,peer_data=0;

// Original common cc, replicated tcv/gd selects, s_wd packing and five macros.
reg[8:0]ref_cc=0;
reg[3:0]ref_tcv=0,ref_gd=0;
always @(posedge clk or negedge rst_counter_n)if(!rst_counter_n)ref_cc<=0;else ref_cc<=ref_cc+9'd1;
always @(posedge clk or negedge rst_data_n)
 if(!rst_data_n)begin ref_tcv<=0;ref_gd<=0;end else begin ref_tcv<={4{tc_d}};ref_gd<={4{gd_d}};end
wire[511:0]ref_wdata;
for(genvar q=0;q<4;q=q+1)begin:g_ref_wdata
 assign ref_wdata[128*q+:128]=ref_tcv[q]?pf[128*q+:128]:(ref_gd[q]?hi[128*q+:128]:lo[128*q+:128]);
end
wire[639:0]ref_swd={90'd0,tc_v||g_run,tc_v?2'd0:g_r,tc_v?tc_o:g_od,!tc_v,tc_v?tc_l:g_l,tc_v?tc_t:g_t,ref_wdata};
wire[639:0]ref_ring,ring;
for(genvar bank=0;bank<5;bank=bank+1)begin:g_ref_sring
 ot_sram_1r1w_512x128_m4_r2c2 u_m(.clk(clk),.r_ce_in(1'b1),.r_addr_in(ref_cc-9'(LS+1)),.rd_out(ref_ring[128*bank+:128]),
  .w_ce_in(1'b1),.w_addr_in(ref_cc),.wd_in(ref_swd[128*bank+:128]),.w_mask_in({128{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
end
for(genvar q=0;q<4;q=q+1)begin:g_ring_data
 ot_coll_local_sring_data #(.LS(LS),.ID(37+q))u_dut(.ctl_ck(clk),.mem_ck(clk),.rst_counter_n(rst_counter_n),.rst_select_n(rst_data_n),
  .tc_d(tc_d),.gd_d(gd_d),.pf(pf[128*q+:128]),.lo(lo[128*q+:128]),.hi(hi[128*q+:128]),.rd(ring[128*q+:128]));
end
ot_coll_local_sring_meta #(.LS(LS),.ID(41))u_ring_meta(.ctl_ck(clk),.mem_ck(clk),.rst_counter_n(rst_counter_n),
 .tc_v(tc_v),.tc_o(tc_o),.tc_l(tc_l),.tc_t(tc_t),.g_run(g_run),.g_r(g_r),.g_od(g_od),.g_l(g_l),.g_t(g_t),.rd(ring[512+:128]));

// Original three physical SX registers, each carrying the whole 546-bit word.
reg[1:0]ref_pkg;
always @(posedge clk)ref_pkg<=pkg;
wire ref_send=tc_v?(tc_v&&tc_o):(g_run&&g_r==ref_pkg);
wire[545:0]ref_send_data={tc_v?tc_t:g_t,!tc_v,tc_v?tc_l:g_l,ref_wdata};
reg[545:0]ref_sx[0:2];reg[2:0]ref_sxv=0;
always @(posedge clk)for(integer f=0;f<3;f=f+1)ref_sx[f]<=ref_send_data;
always @(posedge clk or negedge rst_meta_n)if(!rst_meta_n)ref_sxv<=0;else ref_sxv<={3{ref_send}};
wire[545:0]sx[0:2];wire[2:0]sxv;
wire[33:0]unused_qm[0:2][0:3];wire unused_qv[0:2][0:3];
for(genvar face=0;face<3;face=face+1)begin:g_sx
 for(genvar q=0;q<4;q=q+1)begin:g_q
  wire[33:0]qm;wire qv;
  ot_coll_local_sx_quarter #(.ID(face*4+q),.META(q==0))u_dut(.clk(clk),.rst_data_n(rst_data_n),.rst_meta_n(rst_meta_n),
   .tc_d(tc_d),.gd_d(gd_d),.pf(pf[128*q+:128]),.lo(lo[128*q+:128]),.hi(hi[128*q+:128]),
   .pkg_d(pkg),.tc_v(tc_v),.tc_o(tc_o),.tc_l(tc_l),.tc_t(tc_t),.g_run(g_run),.g_r(g_r),.g_l(g_l),.g_t(g_t),
   .q(sx[face][128*q+:128]),.qm(qm),.qv(qv));
  if(q==0)begin assign sx[face][512+:34]=qm;assign sxv[face]=qv;end
  assign unused_qm[face][q]=qm;assign unused_qv[face][q]=qv;
 end
end

// Original output: registered PK and replicated tfv/tfo, then gather/reduce.
reg[3:0]ref_tfv=0,ref_tfo=0;
always @(posedge clk or negedge rst_meta_n)
 if(!rst_meta_n)begin ref_tfv<=0;ref_tfo<=0;end else begin ref_tfv<={4{tf_v_d}};ref_tfo<={4{tf_o_d}};end
wire[1:0]ref_jr=td_r-ref_pkg+2'd3;
wire[511:0]ref_gather=(td_r==ref_pkg)?td:(ref_jr==2'd0)?sr0:(ref_jr==2'd1)?sr1:sr2;
reg[511:0]ref_output;reg ref_ov=0,ref_ol,ref_oe;reg[2:0]ref_or;
always @(posedge clk)begin
 for(integer q=0;q<4;q=q+1)
  ref_output[128*q+:128]<=ref_tfv[q]?(ref_tfo[q]?rr[128*q+:128]:dr[128*q+:128]):ref_gather[128*q+:128];
 ref_ol<=tf_v?tf_l:(td_l&&td_od&&td_r==2'd3);
 ref_or<=tf_v?3'd0:{td_od,td_r};ref_oe<=tf_v?rf_e:1'b0;
end
always @(posedge clk or negedge rst_meta_n)if(!rst_meta_n)ref_ov<=0;else ref_ov<=tf_v||gd_v;
wire[511:0]output_data;wire[3:0]ov,ol,oe;wire[2:0]orr[0:3];
for(genvar q=0;q<4;q=q+1)begin:g_output
 ot_coll_local_output #(.W(128),.ID(q))u_dut(.clk(clk),.rst_n(rst_meta_n),.pkg_d(pkg),
  .tf_v_d(tf_v_d),.tf_o_d(tf_o_d),.tf_v(tf_v),.tf_l(tf_l),.rf_e(rf_e),.gd_v(gd_v),.td_r(td_r),.td_od(td_od),.td_l(td_l),
  .rr(rr[128*q+:128]),.dr(dr[128*q+:128]),.td(td[128*q+:128]),.sr0(sr0[128*q+:128]),.sr1(sr1[128*q+:128]),.sr2(sr2[128*q+:128]),
  .q(output_data[128*q+:128]),.qv(ov[q]),.ql(ol[q]),.qe(oe[q]),.qr(orr[q]));
end

// Original B1 conditional lo/hi capture and error-to-canonical-NaN capture.
reg ref_die;reg ref_token=0;reg[511:0]ref_pair_lo,ref_pair_hi,ref_fold;
always @(posedge clk)ref_die<=die_d;
always @(posedge clk or negedge rst_data_n)if(!rst_data_n)ref_token<=0;else ref_token<=token_d;
always @(posedge clk)begin
 if(ref_token)begin ref_pair_lo<=!ref_die?local_data:peer_data;ref_pair_hi<=!ref_die?peer_data:local_data;end
 for(integer q=0;q<4;q=q+1)ref_fold[128*q+:128]<=fold_error[q]?{4{32'h7fc00000}}:pf[128*q+:128];
end
wire[511:0]pair_lo,pair_hi,fold;
for(genvar q=0;q<4;q=q+1)begin:g_pair
 ot_coll_local_pair_capture #(.W(128),.ID(q))u_pair(.clk(clk),.rst_n(rst_data_n),.die_d(die_d),.token_d(token_d),
  .local_data(local_data[128*q+:128]),.peer_data(peer_data[128*q+:128]),.lo(pair_lo[128*q+:128]),.hi(pair_hi[128*q+:128]));
 ot_coll_local_fold_capture #(.W(128),.ID(q))u_fold(.clk(clk),.error(fold_error[q]),.d(pf[128*q+:128]),.q(fold[128*q+:128]));
end

function automatic[511:0]pattern(input integer cycle,input integer channel);
 reg[31:0]a;
 begin
  for(integer l=0;l<16;l=l+1)begin
   a=32'(cycle)*32'h9e3779b9^32'(channel)*32'h85ebca6b^32'(l)*32'hc2b2ae35;
   case((cycle+channel+l)%16)
    0:a=32'h7fc00000^32'(channel+l);1:a=32'h7f800000;2:a=32'hff800000;
    3:a=32'h80000000;4:a=32'd1;5:a=32'h00800000;default:a=a;
   endcase
   pattern[32*l+:32]=a;
  end
 end
endfunction
integer cycle=0,checks=0,ring_checks=0,known_ring_checks=0;
integer ring_errors=0,sx_errors=0,output_errors=0,pair_errors=0,fold_errors=0,meta_errors=0;
integer warm=0;reg started=0;
integer pkg_seen[0:3];
always @(posedge clk or negedge rst_counter_n)if(!rst_counter_n)warm<=0;else warm<=warm+1;
always @(negedge clk)begin
 #1;
 if(started&&cycle<6000)begin
  checks=checks+1;pkg_seen[pkg]=pkg_seen[pkg]+1;
  if(ring!==ref_ring)ring_errors=ring_errors+1;
  ring_checks=ring_checks+1;
  if(warm>512)begin known_ring_checks=known_ring_checks+1;if((^ring)===1'bx)ring_errors=ring_errors+1;end
  for(integer f=0;f<3;f=f+1)begin
   if(sx[f]!==ref_sx[f])sx_errors=sx_errors+1;
   if(sxv[f]!==ref_sxv[f])meta_errors=meta_errors+1;
   for(integer q=1;q<4;q=q+1)if(unused_qm[f][q]!==0||unused_qv[f][q]!==0)meta_errors=meta_errors+1;
  end
  if(output_data!==ref_output)output_errors=output_errors+1;
  for(integer q=0;q<4;q=q+1)
   if({ov[q],ol[q],oe[q],orr[q]}!=={ref_ov,ref_ol,ref_oe,ref_or})meta_errors=meta_errors+1;
  if(pair_lo!==ref_pair_lo||pair_hi!==ref_pair_hi)pair_errors=pair_errors+1;
  if(fold!==ref_fold)fold_errors=fold_errors+1;
 end
end
initial begin
 for(integer p=0;p<4;p=p+1)pkg_seen[p]=0;
 repeat(8)@(negedge clk);started=1;
 for(cycle=0;cycle<6000;cycle=cycle+1)begin
  rst_counter_n=(cycle>=4)&&!(cycle>=3100&&cycle<3104);
  rst_data_n=(cycle>=6)&&!(cycle>=3102&&cycle<3107);
  rst_meta_n=(cycle>=5)&&!(cycle>=3101&&cycle<3106);
  pkg=2'(cycle/97);g_r=2'(cycle/3);td_r=2'(cycle/7);
  tc_d=(cycle%3)!=0;gd_d=(cycle%5)<2;tc_v=(cycle%7)<3;tc_o=1'(cycle>>2);tc_l=(cycle%11)==0;
  g_run=(cycle%13)<9;g_od=1'(cycle>>3);g_l=(cycle%17)==0;
  tc_t=32'(cycle)*32'h10204081;g_t=~(32'(cycle)*32'h01010101);
  tf_v_d=(cycle%4)<2;tf_o_d=1'(cycle>>2);tf_v=(cycle%9)<4;tf_l=(cycle%19)==0;rf_e=(cycle%23)==0;
  gd_v=(cycle%5)==0;td_od=1'(cycle>>4);td_l=(cycle%29)==0;
  die_d=1'(cycle>>1);token_d=(cycle%6)!=0;fold_error=4'(cycle);
  pf=pattern(cycle,1);lo=pattern(cycle,2);hi=pattern(cycle,3);rr=pattern(cycle,4);dr=pattern(cycle,5);
  td=pattern(cycle,6);sr0=pattern(cycle,7);sr1=pattern(cycle,8);sr2=pattern(cycle,9);
  local_data=pattern(cycle,10);peer_data=pattern(cycle,11);
  @(negedge clk);
 end
 #2;started=0;
 $display("LOCAL_LEAVES checks=%0d ring_checks=%0d known_ring_checks=%0d ring_errors=%0d sx_errors=%0d output_errors=%0d pair_errors=%0d fold_errors=%0d meta_errors=%0d pk0=%0d pk1=%0d pk2=%0d pk3=%0d",checks,ring_checks,known_ring_checks,ring_errors,sx_errors,output_errors,pair_errors,fold_errors,meta_errors,pkg_seen[0],pkg_seen[1],pkg_seen[2],pkg_seen[3]);
 if(checks!=6000||known_ring_checks<4900)$fatal(1,"incomplete full-shape stimulus");
 if(ring_errors+sx_errors+output_errors+pair_errors+fold_errors+meta_errors)$fatal(1,"LOCAL_LEAVES FAIL");
 $display("LOCAL_LEAVES PASS");$finish;
end
endmodule
