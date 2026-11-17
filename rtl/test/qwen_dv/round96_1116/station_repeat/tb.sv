`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;reg rst=0,cfg=0;reg[3:0]sc=0,nc=0;reg[7:0]kcm1=1;wire rv;wire[7:0]idx;
qfd_dv_s8_station_tail1_cb55 #(.SKEW(55),.ENABLE_DELAY55(1)) a(.ck(ck),.rst_n(rst),.cfg_v_p(cfg),.cfg_mode_p(2'd1),.cfg_wsrc_p(1'b0),.cfg_nwords_p(8'd8),.cfg_sbase_p(9'd0),.cfg_kcm1_p(kcm1),.rs_s_lo_p(64'd0),.rs_s_hi_p(64'd0),.rs_n_lo_p(64'd0),.rs_n_hi_p(64'd0),.rs_s_c_p(sc),.rs_n_c_p(nc),.nb_d_p(64'd0),.nb_c_p(2'd0),.bt_q_p(32'h3f803f80),.flt_bank_i(4'd0),.flt_vld_i(4'd0),.r_v(rv),.r_idx(idx));
integer cy,K=2,P=104,n=0,cf=0,overlap=0,last=-1,first=-1,expect_fault=0,origin,LEAD=6;
initial begin
 if($value$plusargs("K=%d",K))begin end
 if($value$plusargs("P=%d",P))begin end
 if($value$plusargs("expect_fault=%d",expect_fault))begin end
 if($value$plusargs("LEAD=%d",LEAD))begin end
 kcm1=K-1;repeat(16)@(negedge ck);rst=1;
 for(cy=0;cy<800;cy++)begin
 @(negedge ck);cfg=cy==175-LEAD;sc=0;nc=0;
 for(integer r=0;r<3;r++)begin
  origin=120+r*P;
  if(r>0&&cy==origin+55-LEAD)cfg=1;
  if(cy>=origin&&cy<origin+8*K)begin sc[1:0]=1;nc[1:0]=1;end
  if(cy>=origin+55&&cy<origin+55+8*K)begin sc[3:2]=1;nc[3:2]=1;end
 end
 @(posedge ck);
 if(a.cfg_schedule_fault)cf++;
 if(cfg&&rv)overlap++;
 if(rv)begin if(first<0)first=cy;last=cy;$display("RV edge%0d idx%0d",cy,idx);n++;end
 end
 if(expect_fault==0&&(cf||overlap||n!=24))$fatal(1,"REPEAT_SUMMARY K%0d P%0d n%0d cfgfault%0d readdress%0d",K,P,n,cf,overlap);
 if(expect_fault!=0&&cf==0&&overlap==0)$fatal(1,"NEGATIVE_NOT_CAUGHT K%0d P%0d",K,P);
 $display("STN_REPEAT K%0d P%0d words%0d first%0d last%0d cfgfault%0d readdress%0d expectfault%0d",K,P,n,first,last,cf,overlap,expect_fault);$finish;
end
endmodule
