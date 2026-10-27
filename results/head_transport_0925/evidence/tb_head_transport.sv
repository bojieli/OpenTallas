`timescale 1ns/1ps
module tb_head_transport;
reg ck=0;always #0.4165 ck=~ck;reg raw=0,start=0;integer c=0,post_checks=0,nnew=0,nold=0;
reg[514:0] st_in={1'b1,2'b10,512'hA515B};reg[64:0] mission_in={1'b1,64'h1234};
wire[275:0] hstream;reg hv=0;reg[552:0] hf=0;wire txf;wire[276:0] hu_in={1'b1,hstream};
ot_s81hd_host276_tx tx(.ck(ck),.rn(raw),.v(hv),.frame(hf),.lane(hstream),.fault(txf));
wire[514:0] st_new_u_o;
wire[512:0] st_new_d_o;
wire[64:0] st_new_tx_o;
wire[64:0] st_new_rx_o;
coupon_st_new st_new(.clk(ck),.clk_t1(ck),.clk_t2(ck),.clk_t3(ck),.clk_t4(ck),.clk_t5(ck),.clk_t6(ck),.clk_t7(ck),.clk_t8(ck),.clk_t9(ck),.clk_t10(ck),.clk_t11(ck),.clk_t12(ck),.clk_t13(ck),.clk_t14(ck),.clk_t15(ck),.arst_n(raw),.start_i(start),.u_i(st_in),.u_o(st_new_u_o),.d_i(513'd0),.d_o(st_new_d_o),.tx_i(mission_in),.tx_o(st_new_tx_o),.rx_i(65'd0),.rx_o(st_new_rx_o));
wire[514:0] st_old_u_o;
wire[512:0] st_old_d_o;
wire[64:0] st_old_tx_o;
wire[64:0] st_old_rx_o;
coupon_st_old st_old(.clk(ck),.clk_t1(ck),.clk_t2(ck),.clk_t3(ck),.clk_t4(ck),.clk_t5(ck),.clk_t6(ck),.clk_t7(ck),.clk_t8(ck),.clk_t9(ck),.clk_t10(ck),.clk_t11(ck),.clk_t12(ck),.clk_t13(ck),.clk_t14(ck),.clk_t15(ck),.arst_n(raw),.start_i(start),.u_i(st_in),.u_o(st_old_u_o),.d_i(513'd0),.d_o(st_old_d_o),.tx_i(mission_in),.tx_o(st_old_tx_o),.rx_i(65'd0),.rx_o(st_old_rx_o));
wire[0:0] sp_new_rst_o_0;
wire[0:0] sp_new_rst_o_1;
wire[0:0] sp_new_start_o_0;
wire[0:0] sp_new_start_o_1;
wire[565:0] sp_new_b_o;
wire[565:0] sp_new_xw_o;
wire[565:0] sp_new_xe_o;
wire[276:0] sp_new_hu_o;
wire[277:0] sp_new_hd_o;
wire[64:0] sp_new_au_o;
wire[64:0] sp_new_ad_o;
wire[64:0] sp_new_bu_o;
wire[64:0] sp_new_bd_o;
coupon_sp_new sp_new(.clk(ck),.clk_t1(ck),.clk_t2(ck),.clk_t3(ck),.clk_t4(ck),.clk_t5(ck),.clk_t6(ck),.clk_t7(ck),.clk_t8(ck),.clk_t9(ck),.clk_t10(ck),.clk_t11(ck),.clk_t12(ck),.clk_t13(ck),.clk_t14(ck),.clk_t15(ck),.clk_t16(ck),.clk_t17(ck),.clk_t18(ck),.clk_t19(ck),.clk_t20(ck),.clk_t21(ck),.clk_t22(ck),.clk_t23(ck),.clk_t24(ck),.clk_t25(ck),.clk_t26(ck),.clk_t27(ck),.clk_t28(ck),.clk_t29(ck),.clk_t30(ck),.clk_t31(ck),.clk_t32(ck),.clk_t33(ck),.clk_t34(ck),.clk_t35(ck),.clk_t36(ck),.arst_n(raw),.rst_o_0(sp_new_rst_o_0),.rst_o_1(sp_new_rst_o_1),.start_i(start),.start_o_0(sp_new_start_o_0),.start_o_1(sp_new_start_o_1),.x_i(566'd0),.b_o(sp_new_b_o),.xw_o(sp_new_xw_o),.xe_o(sp_new_xe_o),.bw_i(566'd0),.be_i(566'd0),.hu_i(hu_in),.hu_o(sp_new_hu_o),.hd_i(278'd0),.hd_o(sp_new_hd_o),.au_i(mission_in),.au_o(sp_new_au_o),.ad_i(65'd0),.ad_o(sp_new_ad_o),.bu_i(65'd0),.bu_o(sp_new_bu_o),.bd_i(65'd0),.bd_o(sp_new_bd_o));
wire[0:0] sp_old_rst_o_0;
wire[0:0] sp_old_rst_o_1;
wire[0:0] sp_old_start_o_0;
wire[0:0] sp_old_start_o_1;
wire[565:0] sp_old_b_o;
wire[565:0] sp_old_xw_o;
wire[565:0] sp_old_xe_o;
wire[276:0] sp_old_hu_o;
wire[277:0] sp_old_hd_o;
wire[64:0] sp_old_au_o;
wire[64:0] sp_old_ad_o;
wire[64:0] sp_old_bu_o;
wire[64:0] sp_old_bd_o;
coupon_sp_old sp_old(.clk(ck),.clk_t1(ck),.clk_t2(ck),.clk_t3(ck),.clk_t4(ck),.clk_t5(ck),.clk_t6(ck),.clk_t7(ck),.clk_t8(ck),.clk_t9(ck),.clk_t10(ck),.clk_t11(ck),.clk_t12(ck),.clk_t13(ck),.clk_t14(ck),.clk_t15(ck),.clk_t16(ck),.clk_t17(ck),.clk_t18(ck),.clk_t19(ck),.clk_t20(ck),.clk_t21(ck),.clk_t22(ck),.clk_t23(ck),.clk_t24(ck),.clk_t25(ck),.clk_t26(ck),.clk_t27(ck),.clk_t28(ck),.clk_t29(ck),.clk_t30(ck),.clk_t31(ck),.clk_t32(ck),.clk_t33(ck),.clk_t34(ck),.clk_t35(ck),.clk_t36(ck),.arst_n(raw),.rst_o_0(sp_old_rst_o_0),.rst_o_1(sp_old_rst_o_1),.start_i(start),.start_o_0(sp_old_start_o_0),.start_o_1(sp_old_start_o_1),.x_i(566'd0),.b_o(sp_old_b_o),.xw_o(sp_old_xw_o),.xe_o(sp_old_xe_o),.bw_i(566'd0),.be_i(566'd0),.hu_i(hu_in),.hu_o(sp_old_hu_o),.hd_i(278'd0),.hd_o(sp_old_hd_o),.au_i(mission_in),.au_o(sp_old_au_o),.ad_i(65'd0),.ad_o(sp_old_ad_o),.bu_i(65'd0),.bu_o(sp_old_bu_o),.bd_i(65'd0),.bd_o(sp_old_bd_o));
wire[0:0] phy_new_rst_o_0;
wire[0:0] phy_new_start_o_0;
wire[514:0] phy_new_coll_o0;
wire[543:0] phy_new_pma_tx;
wire[0:0] phy_new_pma_tck;
coupon_phy_new phy_new(.clk(ck),.clk_t1(ck),.clk_t2(ck),.clk_t3(ck),.clk_t4(ck),.clk_t5(ck),.clk_t6(ck),.clk_t7(ck),.clk_t8(ck),.clk_t9(ck),.clk_t10(ck),.clk_t11(ck),.clk_t12(ck),.clk_t13(ck),.clk_t14(ck),.clk_t15(ck),.clk_t16(ck),.clk_t17(ck),.clk_t18(ck),.clk_t19(ck),.clk_t20(ck),.clk_t21(ck),.clk_t22(ck),.clk_t23(ck),.clk_t24(ck),.clk_t25(ck),.clk_t26(ck),.clk_t27(ck),.clk_t28(ck),.clk_t29(ck),.clk_t30(ck),.clk_t31(ck),.arst_n(raw),.rst_o_0(phy_new_rst_o_0),.start_i(start),.start_o_0(phy_new_start_o_0),.coll_i0(513'd0),.coll_o0(phy_new_coll_o0),.pma_tx(phy_new_pma_tx),.pma_tck(phy_new_pma_tck),.pma_rx(544'd0),.pma_rck(ck));
wire[0:0] phy_old_rst_o_0;
wire[0:0] phy_old_start_o_0;
wire[514:0] phy_old_coll_o0;
wire[543:0] phy_old_pma_tx;
wire[0:0] phy_old_pma_tck;
coupon_phy_old phy_old(.clk(ck),.clk_t1(ck),.clk_t2(ck),.clk_t3(ck),.clk_t4(ck),.clk_t5(ck),.clk_t6(ck),.clk_t7(ck),.clk_t8(ck),.clk_t9(ck),.clk_t10(ck),.clk_t11(ck),.clk_t12(ck),.clk_t13(ck),.clk_t14(ck),.clk_t15(ck),.clk_t16(ck),.clk_t17(ck),.clk_t18(ck),.clk_t19(ck),.clk_t20(ck),.clk_t21(ck),.clk_t22(ck),.clk_t23(ck),.clk_t24(ck),.clk_t25(ck),.clk_t26(ck),.clk_t27(ck),.clk_t28(ck),.clk_t29(ck),.clk_t30(ck),.clk_t31(ck),.arst_n(raw),.rst_o_0(phy_old_rst_o_0),.start_i(start),.start_o_0(phy_old_start_o_0),.coll_i0(513'd0),.coll_o0(phy_old_coll_o0),.pma_tx(phy_old_pma_tx),.pma_tck(phy_old_pma_tck),.pma_rx(544'd0),.pma_rck(ck));
wire rv_new;wire[552:0] rf_new;wire rxf_new;
ot_s81hd_host276_rx rx_new(.ck(ck),.rn(raw),.lane(sp_new_hu_o[275:0]),.v(rv_new),.frame(rf_new),.fault(rxf_new));
wire rv_old;wire[552:0] rf_old;wire rxf_old;
ot_s81hd_host276_rx rx_old(.ck(ck),.rn(raw),.lane(sp_old_hu_o[275:0]),.v(rv_old),.frame(rf_old),.fault(rxf_old));

function automatic[552:0] config_frame(input integer n);begin
 config_frame=553'd0;config_frame[552]=1;config_frame[3:0]=6;config_frame[23:16]=9;config_frame[87:24]=64'hC0DE0000+n;
end endfunction
always@(negedge ck)begin
 c=c+1;raw=(c>=16);hv=0;
 if(c==100||c==120||c==140)begin hv=1;hf=config_frame((c-100)/20);end
 if(c==190)begin
  if(st_new_u_o[513:0]!==st_in[513:0]||st_old_u_o[513:0]!==st_in[513:0])$fatal(1,"station payload did not move before START");
  if(st_new_u_o[514]!==1||st_old_u_o[514]!==0)$fatal(1,"station bootstrap epoch role mismatch");
  if(sp_new_hu_o[276]!==1||sp_old_hu_o[276]!==0)$fatal(1,"spine bootstrap epoch role mismatch");
  if(phy_new.u_phy.rst_n!==1||phy_old.u_phy.rst_n!==0)$fatal(1,"actual PHY provider reset role mismatch");
  if(sp_new.u_spo.rst_n!==0||sp_new.u_spr.rst_n!==0||sp_old.u_spo.rst_n!==0||sp_old.u_spr.rst_n!==0)$fatal(1,"mission spine core released before START");
  if(st_new_tx_o[64]!==0||sp_new_au_o[64]!==0)$fatal(1,"undeclared mission epoch released before START");
  if(nnew!=3||nold!=3)$fatal(1,"embedded-valid HOST276 frame delivery mismatch new%0d old%0d",nnew,nold);
  $display("PRESTART_PAYLOAD real_HOST276_new=%0d old=%0d station_payload_both=PASS epoch_new_old=1/0 PHY_reset_new_old=1/0 mission_spo_spr_reset=0",nnew,nold);
  $display("OLD_ROLE_MUTANT_CAUGHT missing_raw_epoch_and_PHY_reset; payload_was_not_blocked");
 end
 if(c==200)start=1;
 if(c>=250)begin
  st_in[31:0]=c;
  if(st_new_u_o!==st_old_u_o||sp_new_hu_o!==sp_old_hu_o||st_new_tx_o!==st_old_tx_o||sp_new_au_o!==sp_old_au_o)$fatal(1,"post-START transport lockstep mismatch");
  if(sp_new.u_spo.rst_n!==1||sp_new.u_spr.rst_n!==1)$fatal(1,"mission cores did not release after START");
  post_checks=post_checks+1;
 end
 if(c==450)begin
  if(txf||rxf_new||rxf_old)$fatal(1,"real HOST276 codec fault");
  $display("HEAD_TRANSPORT_BOOT PASS post_START_lockstep_checks=%0d source_cycles_added=0; PHY traffic/token/production dates NOT CLAIMED",post_checks);$finish;
 end
end
always@(posedge ck)begin
 #0.1;
 if(rv_new)begin if(rf_new!==config_frame(nnew))$fatal(1,"new decoded CSR payload mismatch");nnew=nnew+1;end
 if(rv_old)begin if(rf_old!==config_frame(nold))$fatal(1,"old decoded CSR payload mismatch");nold=nold+1;end
end
endmodule

