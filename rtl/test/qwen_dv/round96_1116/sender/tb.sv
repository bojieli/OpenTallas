`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;reg rst=0,cfg=0;reg[3:0]sc=0,nc=0;wire[1:0]nb;integer cy,n=0,first=-1,last=-1;
qfd_dv_s8_station_tail1_cb55 #(.SKEW(55),.ENABLE_DELAY55(1)) a(.ck(ck),.rst_n(rst),.cfg_v_p(cfg),.cfg_mode_p(2'd3),.cfg_wsrc_p(1'b0),.cfg_nwords_p(8'd8),.cfg_sbase_p(9'd0),.cfg_kcm1_p(8'd7),.rs_s_lo_p(64'd0),.rs_s_hi_p(64'd0),.rs_n_lo_p(64'd0),.rs_n_hi_p(64'd0),.rs_s_c_p(sc),.rs_n_c_p(nc),.nb_d_p(64'd0),.nb_c_p(2'd0),.bt_q_p(32'h3f803f80),.flt_bank_i(4'd0),.flt_vld_i(4'd0),.nb_oc(nb));
initial begin
 repeat(16)@(negedge ck);rst=1;
 for(cy=0;cy<400;cy++)begin
 @(negedge ck);cfg=cy==40;sc=0;nc=0;
 if(cy>=120&&cy<184)begin sc[1:0]=1;nc[1:0]=1;end
 if(cy>=175&&cy<239)begin sc[3:2]=1;nc[3:2]=1;end
 @(posedge ck);if(nb[0])begin if(first<0)first=cy;last=cy;n++;end
 end
 if(n!=8||first!=247||last!=254)$fatal(1,"SENDER_AGE n%0d first%0d last%0d",n,first,last);
 $display("STN55_SENDER_VALID_PASS words8 far_final231 nb_first247 nb_last254 age16 arithmetic_unobserved");$finish;
end
endmodule
