`timescale 1ns/1fs
module tb_nx_forward;
reg ck=0;always #0.416500 ck=~ck;reg rst_n=0;reg[3:0]sid=0;reg[1103:0]iw=0,ie=0;reg[275:0]iv=0;integer cyc=0,phase=0,trial=0,side=0,hops=0,errors=0,words=0,deliveries=0;
wire[1103:0]oe[0:1],ow[0:1];wire[275:0]ov[0:1];wire[172:0]wi[0:1],ei[0:1],eo[0:1],wo[0:1];wire[2:0]dv[0:1];wire[23:0]db[0:1];wire[479:0]dd[0:1];wire[1:0]fault,xfault;integer seen[0:1],del[0:1];reg[1103:0]word_;reg[159:0]payload;integer elapsed;
ot_s81sl_rstop r0(.clk(ck),.rst_n(rst_n),.sid(sid),.ri_w(iw),.ri_e(ie),.vi(iv),.ro_e(oe[0]),.ro_w(ow[0]),.vo(ov[0]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[0]),.nx_ei(ei[0]),.nx_eo(eo[0]),.nx_wo(wo[0]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(fault[0]));
ot_s81dv_xstop #(.K(5),.HE(8),.HW(7)) x0(.clk(ck),.rst_n(rst_n),.eng(1'b0),.inj_v(1'b0),.inj_base(8'd0),.inj_d(160'd0),.ej_v(1'b0),.ej_b(8'd0),.ej_d(160'd0),.dl_v(dv[0]),.dl_b(db[0]),.dl_d(dd[0]),.fault(xfault[0]),.wi_v(wi[0][172]),.wi_h(wi[0][171:168]),.wi_b(wi[0][167:160]),.wi_d(wi[0][159:0]),.ei_v(ei[0][172]),.ei_h(ei[0][171:168]),.ei_b(ei[0][167:160]),.ei_d(ei[0][159:0]),.eo_v(eo[0][172]),.eo_h(eo[0][171:168]),.eo_b(eo[0][167:160]),.eo_d(eo[0][159:0]),.wo_v(wo[0][172]),.wo_h(wo[0][171:168]),.wo_b(wo[0][167:160]),.wo_d(wo[0][159:0]));
ot_s81sl_rstopt_xo r1(.clk(ck),.rst_n(rst_n),.sid(sid),.ri_w(iw),.ri_e(ie),.vi(iv),.ro_e(oe[1]),.ro_w(ow[1]),.vo(ov[1]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_wi(wi[1]),.nx_ei(ei[1]),.nx_eo(eo[1]),.nx_wo(wo[1]),.ci_dir(3'd0),.ci_b(1104'd0),.fault(fault[1]));
ot_s81dv_xstop #(.K(5),.HE(8),.HW(7)) x1(.clk(ck),.rst_n(rst_n),.eng(1'b0),.inj_v(1'b0),.inj_base(8'd0),.inj_d(160'd0),.ej_v(1'b0),.ej_b(8'd0),.ej_d(160'd0),.dl_v(dv[1]),.dl_b(db[1]),.dl_d(dd[1]),.fault(xfault[1]),.wi_v(wi[1][172]),.wi_h(wi[1][171:168]),.wi_b(wi[1][167:160]),.wi_d(wi[1][159:0]),.ei_v(ei[1][172]),.ei_h(ei[1][171:168]),.ei_b(ei[1][167:160]),.ei_d(ei[1][159:0]),.eo_v(eo[1][172]),.eo_h(eo[1][171:168]),.eo_b(eo[1][167:160]),.eo_d(eo[1][159:0]),.wo_v(wo[1][172]),.wo_h(wo[1][171:168]),.wo_b(wo[1][167:160]),.wo_d(wo[1][159:0]));
initial begin seen[0]=0;seen[1]=0;del[0]=0;del[1]=0;end
always @(negedge ck)begin
 phase=cyc%128;trial=cyc/128;sid=4'(trial/6);side=(trial/3)%2;hops=(trial%3==0)?1:((trial%3==1)?2:8);rst_n=(phase>=16);iw=0;ie=0;iv=0;
 if(phase==0)begin seen[0]=0;seen[1]=0;del[0]=0;del[1]=0;end
 payload={5{32'h3f000000+32'(trial)}};
 if(phase==64)begin word_=0;word_[0]=1;word_[3:1]=3'd3;word_[8:4]=5'(hops);word_[20:13]=8'(5*int'(sid));word_[21+:160]=payload;
  if((side==0&&((!sid[0]&&sid[3:1]==0)||(sid[0]&&sid[3:1]==7)))||(side==1&&((!sid[0]&&sid[3:1]==7)||(sid[0]&&sid[3:1]==0))))iv=word_[275:0];
  else if((side==0&&!sid[0])||(side==1&&sid[0]))iw=word_;else ie=word_;
 end end
always @(posedge ck)begin cyc=cyc+1;#0.000001;
 if(rst_n)for(integer c=0;c<2;c=c+1)begin
  if(fault[c]||xfault[c])begin errors=errors+1;$display("FAULT trial%0d cls%0d",trial,c);end
  if(|dv[c])begin del[c]=del[c]+1;deliveries=deliveries+1;if(cyc%128!=67||dv[c]!=(side==0?3'd2:3'd4)||db[c][8*(side+1)+:8]!==8'(5*int'(sid))||dd[c][160*(side+1)+:160]!==payload)begin errors=errors+1;$display("BAD_DEL trial%0d cls%0d age%0d",trial,c,cyc%128-64);end end
  if(oe[c][0]||ow[c][0]||ov[c][0])begin seen[c]=seen[c]+1;words=words+1;elapsed=cyc%128-64;
   if((side==0&&((!sid[0]&&sid[3:1]==7)||(sid[0]&&sid[3:1]==0)))||(side==1&&((!sid[0]&&sid[3:1]==0)||(sid[0]&&sid[3:1]==7))))word_={{828{1'b0}},ov[c]};
   else if((side==0&&!sid[0])||(side==1&&sid[0]))word_=oe[c];else word_=ow[c];
   if(elapsed!=6||hops<=1||word_[3:0]!==4'd7||word_[8:4]!==5'(hops-1)||word_[20:13]!==8'(5*int'(sid))||word_[21+:160]!==payload)begin errors=errors+1;$display("BAD_OUT trial%0d cls%0d age%0d hops%0d word%h",trial,c,elapsed,hops,word_[180:0]);end
  end
 end
 if(cyc%128==100)for(integer c=0;c<2;c=c+1)if(seen[c]!=(hops>1?1:0)||del[c]!=1)begin errors=errors+1;$display("BAD_COUNT trial%0d cls%0d seen%0d del%0d",trial,c,seen[c],del[c]);end
 if(cyc==12287)begin $display("NX_FORWARD words%0d deliveries%0d errors%0d clock_ps833",words,deliveries,errors);if(errors==0&&words==128&&deliveries==192)$display("NX_FORWARD_PASS");else $fatal(1,"NX_FORWARD_FAIL");$finish;end
end
endmodule
