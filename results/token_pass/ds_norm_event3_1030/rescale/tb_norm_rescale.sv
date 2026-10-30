`timescale 1ps/1fs
module tb_norm_rescale;
reg ck=0;always #416.5 ck=~ck;
reg rs=0,cv=0,sv=0;reg[159:0]cd=0;reg[9:0]sa=0;reg[255:0]sd=0;reg[7:0]sm=0;
reg rbv=0;reg[31:0]rstd[0:0];wire yv;wire[2:0]yi;wire[127:0]y;
wire hv,hh,hrv,hrh,hqv,ng,wv,pv,fvp,fvn;wire[2:0]hj,hrj,wi;wire[255:0]hd,hqd,wd;wire[127:0]pre;wire[31:0]pd;
ot_s81sl_vp #(.ML(7),.AL(6),.HPL(33),.CS_HI_D(0),.CS_HI_GS(0),.CS_HO_D(0),.CS_HO_GS(0),.CS_H_G(4),.HQX(0))vp(
.clk(ck),.rst_n(rs),.c_v(cv),.c_d(cd),.sw_v(sv),.sw_a(sa),.sw_m(sm),.sw_d(sd),.cw_v(2'd0),.cw_a(24'd0),.cw_d(64'd0),
.x_rv(1'b0),.x_ra(10'd0),.x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),
.hw_v(hv),.hw_j(hj),.hw_hf(hh),.hw_d(hd),.hr_v(hrv),.hr_j(hrj),.hr_hf(hrh),.hq_v(hqv),.hq_d(hqd),
.n_go(ng),.n_pre(pre),.wl_v(wv),.wl_i(wi),.wl_d(wd),.fault(fvp));
ot_s81sl_vn_sp #(.LM(5),.LA(6))vn(.clk(ck),.rst_n(rs),.hw_v(hv),.hw_j(hj),.hw_hf(hh),.hw_d(hd),
.hr_v(hrv),.hr_j(hrj),.hr_hf(hrh),.hq_v(hqv),.hq_d(hqd),.n_go(ng),.n_pre(pre),.wl_v(wv),.wl_i(wi),.wl_d(wd),.rb_v(rbv),.rb_d(rstd[0]),.p_v(pv),.p_d(pd),.y_v(yv),.y_i(yi),.y(y),.fault(fvn));
reg[127:0]y_expected[0:639];integer rpin=-1,yfirst=-1,yage=-1,ycount=0,ychecks=0,badrstd=0;
reg[143:0]image[0:3919];reg[31:0]expected[0:79];integer cyc=0,errors=0,checks=0,leaf=-1,pin=-1,ngo_age=-1,partial_age=-1,expected_age=-1,expected_go=-1,seen=0,go_seen=0,mut_payload=0,mut_age=0;
always @(posedge ck)begin #2;cyc=cyc+1;
 if(rs&&pin>=0)begin
  if(yv&&rpin>=0)begin
   if(yfirst<0)yfirst=cyc-rpin;
   if(yi!==3'(ycount)||y!==y_expected[8*leaf+ycount])begin errors=errors+1;$display("Y_DATA leaf%0d i%0d got%032x want%032x",leaf,yi,y,y_expected[8*leaf+ycount]);end
   ycount=ycount+1;ychecks=ychecks+1;
  end
  if(ng)begin go_seen=go_seen+1;ngo_age=cyc-pin;end
  if(pv)begin seen=seen+1;partial_age=cyc-pin;checks=checks+1;
   if(pd!==expected[leaf])begin errors=errors+1;$display("PARTIAL_DATA leaf%0d got%08x want%08x",leaf,pd,expected[leaf]);end
  end
 end
end
 task tick(input integer n);repeat(n)begin @(posedge ck);#5;end endtask
 task command(input integer op,input integer a0,input integer a1,input integer n);
 begin cv=1;cd=0;cd[3:0]=4'(op);cd[13:4]=10'(a0);cd[23:14]=10'(a1);cd[31:24]=8'(n);tick(1);cv=0;end
 endtask
initial begin
mut_payload=$test$plusargs("bad_payload");mut_age=$test$plusargs("bad_age");$readmemh("entry.memh",image);$readmemh("partial.memh",expected);$readmemh("actual_rstd.hex",rstd);$readmemh("expected_y.memh",y_expected);badrstd=$test$plusargs("bad_rstd");if(badrstd)rstd[0]=rstd[0]^32'h00400000;
for(leaf=0;leaf<80;leaf=leaf+1)begin
 rs=0;pin=-1;rpin=-1;rbv=0;ycount=0;yfirst=-1;tick(64);rs=1;tick(64);seen=0;go_seen=0;
 for(integer j=0;j<49;j=j+1)begin
  sv=1;sa=image[49*leaf+j][137:128];sm=8'h0f;sd={128'd0,image[49*leaf+j][127:0]};
  if(mut_payload&&leaf==0&&j==0)sd[14]=~sd[14];tick(1);sv=0;tick(1);
 end
 tick(8);command(3,0,0,0);tick(40);command(1,64,0,0);tick(30);
 pin=cyc;command(7,1008,leaf,1);tick(240);
 if(expected_age<0)begin expected_age=partial_age;expected_go=ngo_age;end
 if(seen!=1||go_seen!=1||partial_age!=expected_age+mut_age||ngo_age!=expected_go||fvp||fvn)begin errors=errors+1;$display("NORM_CONTROL leaf%0d seen%0d go%0d partial_age%0d ngo_age%0d faults%b%b",leaf,seen,go_seen,partial_age,ngo_age,fvp,fvn);end
 $display("NORM_PRODUCER leaf%0d norm_pin%0d n_go_age%0d partial_age%0d data%08x",leaf,pin,ngo_age,partial_age,pd);
 rpin=cyc;rbv=1;tick(1);rbv=0;tick(100);
 if(yage<0)yage=yfirst;
 if(ycount!=8||yfirst!=yage||fvp||fvn)begin errors=errors+1;$display("Y_CONTROL leaf%0d count%0d firstage%0d expected%0d faults%b%b",leaf,ycount,yfirst,yage,fvp,fvn);end
 $display("CURRENT_Y leaf%0d vectors%0d rstd_to_y0%0d",leaf,ycount,yfirst);
end
$display("NORM_PRODUCER_%s checks%0d errors%0d clock833 currentVN05da VPpin_to_partial%0d VPpin_to_ngo%0d",errors==0?"PASS":"FAIL",checks,errors,expected_age,expected_go);
$display("RESCALE_%s vectors%0d BF16elements%0d errors%0d rstd%08x rstd_to_y0%0d clock833",errors==0?"PASS":"FAIL",ychecks,8*ychecks,errors,rstd[0],yage);if(ychecks!=640||errors)$fatal(1,"current genuine norm rescale");$finish;
end
initial begin tick(70000);$fatal(1,"finite native norm producer limit");end
endmodule
