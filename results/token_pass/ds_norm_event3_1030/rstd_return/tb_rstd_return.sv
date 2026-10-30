`timescale 1ps/1fs
module tb_rstd_return;
reg ck=0;always #416.5 ck=~ck;
reg rs=0,cv=0,sv=0;reg[159:0]cd=0;reg[9:0]sa=0;reg[255:0]sd=0;reg[7:0]sm=0;
reg rbv=0;reg[31:0]rstd[0:0];wire return_valid;wire[31:0]return_data;
reg fclk=0;integer fshift=0,badlink=0,source_event=-1,xr_event=-1,return_event=-1,return_seen=0;real first_fedge;
initial begin
 if(!$value$plusargs("FCLK_SHIFT_PS=%d",fshift))$fatal(1,"explicit conditional source-clock profile required");
 first_fedge=416.5+fshift;if(first_fedge<=0||first_fedge>=833)$fatal(1,"source-clock profile outside one period");
 #(first_fedge);forever begin fclk=~fclk;#416.5;end
end
wire carrier;ot_dp_dly #(.W(1),.D(6))u_reset_carrier(.clk(ck),.d(rs),.q(carrier));
wire xr_rs;ot_dp_dly #(.W(1),.D(7))u_xr_reset(.clk(ck),.d(carrier),.q(xr_rs));
wire xr_rv;wire[31:0]xr_rd;wire xr_fault;
ot_s81sl_xrt1 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'o01234),.QDELAYS(128'd0))xr(
.clk(ck),.rst_n(xr_rs),.sid(4'd0),.dl_ev(1'b0),.dl_e(1075'd0),.dl_wv(1'b0),.dl_w(1075'd0),.dl_vv(1'b0),.dl_vb(275'd0),
.lo_v(5'd0),.lo_d(1280'd0),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),
.x_rbv(rbv),.x_rbd(rstd[0]),.rb_v(xr_rv),.rb_d(xr_rd),.fault(xr_fault));
reg[594:0]packet;always @*begin packet=0;packet[0]=carrier;packet[68]=xr_rv;packet[67:36]=xr_rd;if(badlink)packet[58]=~packet[58];end
wire[595:0]source_word,landed;wire land_ready,land_fault;
ot_dp_st #(.W(595))source_boundary(.clk(ck),.rst_n(rs),.d(packet),.ea(rs),.q(source_word[594:0]),.eq(source_word[595]));
ot_dp_clk_landing #(.W(596))u_cland_ft2_i(.fclk(fclk),.clk(ck),.rst_n(rs),.d(source_word),.q(landed),.ready(land_ready),.fault(land_fault));
wire[595:0]ft[0:6];assign ft[0]=landed;
for(genvar f=0;f<6;f=f+1)begin:FT
 ot_dp_st #(.W(595))u(.clk(ck),.rst_n(rs),.d(ft[f][594:0]),.ea(ft[f][595]),.q(ft[f+1][594:0]),.eq(ft[f+1][595]));
end
wire[594:0]dn;wire dn_epoch;
ot_dp_st #(.W(595))dest_boundary(.clk(ck),.rst_n(rs),.d(ft[6][594:0]),.ea(ft[6][595]),.q(dn),.eq(dn_epoch));
wire consumer_reset=dn[0];assign return_valid=dn[68];assign return_data=dn[67:36];wire yv;wire[2:0]yi;wire[127:0]y;
wire hv,hh,hrv,hrh,hqv,ng,wv,pv,fvp,fvn;wire[2:0]hj,hrj,wi;wire[255:0]hd,hqd,wd;wire[127:0]pre;wire[31:0]pd;
ot_s81sl_vp #(.ML(7),.AL(6),.HPL(33),.CS_HI_D(0),.CS_HI_GS(0),.CS_HO_D(0),.CS_HO_GS(0),.CS_H_G(4),.HQX(0))vp(
.clk(ck),.rst_n(consumer_reset),.c_v(cv),.c_d(cd),.sw_v(sv),.sw_a(sa),.sw_m(sm),.sw_d(sd),.cw_v(2'd0),.cw_a(24'd0),.cw_d(64'd0),
.x_rv(1'b0),.x_ra(10'd0),.x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),
.hw_v(hv),.hw_j(hj),.hw_hf(hh),.hw_d(hd),.hr_v(hrv),.hr_j(hrj),.hr_hf(hrh),.hq_v(hqv),.hq_d(hqd),
.n_go(ng),.n_pre(pre),.wl_v(wv),.wl_i(wi),.wl_d(wd),.fault(fvp));
ot_s81sl_vn_sp #(.LM(5),.LA(6))vn(.clk(ck),.rst_n(consumer_reset),.hw_v(hv),.hw_j(hj),.hw_hf(hh),.hw_d(hd),
.hr_v(hrv),.hr_j(hrj),.hr_hf(hrh),.hq_v(hqv),.hq_d(hqd),.n_go(ng),.n_pre(pre),.wl_v(wv),.wl_i(wi),.wl_d(wd),.rb_v(return_valid),.rb_d(return_data),.p_v(pv),.p_d(pd),.y_v(yv),.y_i(yi),.y(y),.fault(fvn));
reg[127:0]y_expected[0:639];integer rpin=-1,yfirst=-1,yage=-1,ycount=0,ychecks=0,badrstd=0;
reg[143:0]image[0:3919];reg[31:0]expected[0:79];integer cyc=0,errors=0,checks=0,leaf=-1,pin=-1,ngo_age=-1,partial_age=-1,expected_age=-1,expected_go=-1,seen=0,go_seen=0,mut_payload=0,mut_age=0;
always @(posedge ck)begin #2;cyc=cyc+1;
 if(rs&&pin>=0)begin
  if(xr_rv)xr_event=cyc;
  if(return_valid)begin return_seen=return_seen+1;rpin=cyc;return_event=cyc;
   if(return_data!==rstd[0]||!dn_epoch)begin errors=errors+1;$display("RSTD_TRANSPORT_DATA got%08x want%08x epoch%b",return_data,rstd[0],dn_epoch);end
  end
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
mut_payload=$test$plusargs("bad_payload");badlink=$test$plusargs("bad_link");mut_age=$test$plusargs("bad_age");$readmemh("entry.memh",image);$readmemh("partial.memh",expected);$readmemh("actual_rstd.hex",rstd);$readmemh("expected_y.memh",y_expected);badrstd=$test$plusargs("bad_rstd");if(badrstd)rstd[0]=rstd[0]^32'h00400000;
for(leaf=2;leaf<3;leaf=leaf+1)begin
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
 source_event=cyc;rbv=1;tick(1);rbv=0;tick(160);
 if(yage<0)yage=17;
 if(ycount!=8||yfirst!=yage||fvp||fvn)begin errors=errors+1;$display("Y_CONTROL leaf%0d count%0d firstage%0d expected%0d faults%b%b",leaf,ycount,yfirst,yage,fvp,fvn);end
 $display("CURRENT_Y leaf%0d vectors%0d rstd_to_y0%0d",leaf,ycount,yfirst);
end
$display("NORM_PRODUCER_%s checks%0d errors%0d clock833 currentVN05da VPpin_to_partial%0d VPpin_to_ngo%0d",errors==0?"PASS":"FAIL",checks,errors,expected_age,expected_go);
$display("RESCALE_%s vectors%0d BF16elements%0d errors%0d rstd%08x rstd_to_y0%0d clock833",errors==0?"PASS":"FAIL",ychecks,8*ychecks,errors,rstd[0],yage);if(return_seen!=1||xr_event-source_event!=2||!land_ready||land_fault||xr_fault)errors=errors+1;$display("ACTUAL_RETURN source%0d XR%0d VN%0d XRlocal%0d native_link%0d firstY%0d shift%0d ready%b fault%b epoch%b",source_event,xr_event,return_event,xr_event-source_event,return_event-xr_event,yfirst,fshift,land_ready,land_fault,dn_epoch);if(ychecks!=8||errors)$fatal(1,"current genuine norm rescale");$finish;
end
initial begin tick(70000);$fatal(1,"finite native norm producer limit");end
endmodule
