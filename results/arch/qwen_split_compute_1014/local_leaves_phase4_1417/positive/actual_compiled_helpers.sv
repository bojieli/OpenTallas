(* keep_hierarchy = 1 *) module ot_coll_local_sring_data #(parameter integer LS=376,ID=0)(
 input wire ctl_ck,mem_ck,rst_counter_n,rst_select_n,tc_d,gd_d,input wire[127:0]pf,lo,hi,output wire[127:0]rd);
 reg[8:0]cc;reg tc_q,gd_q;
 always @(posedge ctl_ck or negedge rst_counter_n)if(!rst_counter_n)cc<=0;else cc<=cc+9'd1;
 always @(posedge ctl_ck or negedge rst_select_n)
  if(!rst_select_n)begin tc_q<=0;gd_q<=0;end else begin tc_q<=tc_d;gd_q<=gd_d;end
`ifdef OT_TP8S_MUT_GATHER
 wire[127:0]wd=tc_q?pf:(!gd_q?hi:lo);
`else
 wire[127:0]wd=tc_q?pf:(gd_q?hi:lo);
`endif
 ot_sram_1r1w_512x128_m4_r2c2 u_m(.clk(mem_ck),.r_ce_in(1'b1),.r_addr_in(cc-9'(LS+1)),.rd_out(rd),
  .w_ce_in(1'b1),.w_addr_in(cc),.wd_in(wd),.w_mask_in({128{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_sring_meta #(parameter integer LS=376,ID=0)(
 input wire ctl_ck,mem_ck,rst_counter_n,tc_v,tc_o,tc_l,input wire[31:0]tc_t,
 input wire g_run,input wire[1:0]g_r,input wire g_od,g_l,input wire[31:0]g_t,output wire[127:0]rd);
 reg[8:0]cc;
 always @(posedge ctl_ck or negedge rst_counter_n)if(!rst_counter_n)cc<=0;else cc<=cc+9'd1;
 wire[127:0]wd={90'd0,tc_v||g_run,tc_v?2'd0:g_r,tc_v?tc_o:g_od,!tc_v,tc_v?tc_l:g_l,tc_v?tc_t:g_t};
 ot_sram_1r1w_512x128_m4_r2c2 u_m(.clk(mem_ck),.r_ce_in(1'b1),.r_addr_in(cc-9'(LS+1)),.rd_out(rd),
  .w_ce_in(1'b1),.w_addr_in(cc),.wd_in(wd),.w_mask_in({128{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_sx_quarter #(parameter integer ID=0,META=0)(
 input wire clk,rst_data_n,rst_meta_n,tc_d,gd_d,input wire[127:0]pf,lo,hi,
 input wire[1:0]pkg_d,input wire tc_v,tc_o,tc_l,input wire[31:0]tc_t,
 input wire g_run,input wire[1:0]g_r,input wire g_l,input wire[31:0]g_t,
 output reg[127:0]q,output wire[33:0]qm,output wire qv);
 reg tc_q,gd_q;
 always @(posedge clk or negedge rst_data_n)
  if(!rst_data_n)begin tc_q<=0;gd_q<=0;end else begin tc_q<=tc_d;gd_q<=gd_d;end
`ifdef OT_TP8S_MUT_GATHER
 always @(posedge clk)q<=tc_q?pf:(!gd_q?hi:lo);
`else
 always @(posedge clk)q<=tc_q?pf:(gd_q?hi:lo);
`endif
 generate if(META)begin:g_meta
  reg[1:0]pkg_q;reg[33:0]meta_q;reg v_q;
  always @(posedge clk)begin pkg_q<=pkg_d;meta_q<={tc_v?tc_t:g_t,!tc_v,tc_v?tc_l:g_l};end
  always @(posedge clk or negedge rst_meta_n)
   if(!rst_meta_n)v_q<=0;else v_q<=tc_v?(tc_v&&tc_o):(g_run&&g_r==pkg_q);
  assign qm=meta_q;assign qv=v_q;
 end else begin:g_data assign qm=0;assign qv=0;end endgenerate
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_output #(parameter integer W=128,ID=0)(
 input wire clk,rst_n,input wire[1:0]pkg_d,input wire tf_v_d,tf_o_d,tf_v,tf_l,rf_e,gd_v,
 input wire[1:0]td_r,input wire td_od,td_l,input wire[W-1:0]rr,dr,td,sr0,sr1,sr2,
 output reg[W-1:0]q,output reg qv,ql,qe,output reg[2:0]qr);
 reg[1:0]pkg_q;reg tfv_q,tfo_q;
 always @(posedge clk)pkg_q<=pkg_d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin tfv_q<=0;tfo_q<=0;end else begin tfv_q<=tf_v_d;tfo_q<=tf_o_d;end
 wire[1:0]jr=td_r-pkg_q+2'd3;
 wire[W-1:0]gather=(td_r==pkg_q)?td:(jr==0)?sr0:(jr==1)?sr1:sr2;
 always @(posedge clk)begin
  q<=tfv_q?(tfo_q?rr:dr):gather;
  ql<=tf_v?tf_l:(td_l&&td_od&&td_r==2'd3);
  qr<=tf_v?3'd0:{td_od,td_r};qe<=tf_v?rf_e:1'b0;
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)qv<=0;else qv<=tf_v||gd_v;
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_pair_capture #(parameter integer W=128,ID=0)(
 input wire clk,rst_n,die_d,token_d,input wire[W-1:0]local_data,peer_data,
 output reg[W-1:0]lo,hi);
 reg die_q,token_q;
 always @(posedge clk)die_q<=die_d;
 always @(posedge clk or negedge rst_n)if(!rst_n)token_q<=0;else token_q<=token_d;
 always @(posedge clk)if(token_q)begin
  lo<=die_q?peer_data:local_data;hi<=die_q?local_data:peer_data;
 end
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_fold_capture #(parameter integer W=128,ID=0)(
 input wire clk,error,input wire[W-1:0]d,output reg[W-1:0]q);
 always @(posedge clk)q<=error?{(W/32){32'h7fc00000}}:d;
endmodule
