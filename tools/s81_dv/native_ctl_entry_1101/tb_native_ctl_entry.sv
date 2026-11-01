`timescale 1ps/1fs
module tb_native_ctl_entry;
reg ck=0,rs=0;always #416.5 ck=~ck;
reg[3:0]sid=0;reg[1103:0]ri_e=0,ri_w=0;reg[275:0]vi=0;
wire ev,wv,vv,is_v,cfg_v,fr,fx;wire[1103:0]dl_e,dl_w,ci_b,ro_e,ro_w;wire[275:0]dl_vb,vo;
wire[2:0]ci_dir;wire[159:0]is_d,cfg_d;
ot_s81sl_rstopt_xo r(.clk(ck),.rst_n(rs),.sid(sid),.ri_e(ri_e),.ri_w(ri_w),.vi(vi),.ro_e(ro_e),.ro_w(ro_w),.vo(vo),
 .xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_eo(173'd0),.nx_wo(173'd0),.dl_ev(ev),.dl_e(dl_e),.dl_wv(wv),.dl_w(dl_w),.dl_vv(vv),.dl_vb(dl_vb),
 .ci_dir(ci_dir),.ci_b(ci_b),.fault(fr));
ot_s81sl_xrt1 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'o01234),.QDELAYS(128'd0)) x(.clk(ck),.rst_n(rs),.sid(sid),
 .dl_ev(ev),.dl_e(dl_e[1075:1]),.dl_wv(wv),.dl_w(dl_w[1075:1]),.dl_vv(vv),.dl_vb(dl_vb[275:1]),
 .ci_dir(ci_dir),.ci_b(ci_b[1075:0]),.is_v(is_v),.is_d(is_d),.cfg_v(cfg_v),.cfg_d(cfg_d),
 .lo_v(5'd0),.lo_d(1280'd0),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(fx));
wire is_v3,cfg_v3,fx3;wire[159:0]is_d3,cfg_d3;
ot_s81sl_xrt3 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'o01234),.QDELAYS(128'd0)) x3(.clk(ck),.rst_n(rs),.sid(sid),
 .dl_ev(ev),.dl_e(dl_e[1075:1]),.dl_wv(wv),.dl_w(dl_w[1075:1]),.dl_vv(vv),.dl_vb(dl_vb[275:1]),.bi(1046'd0),
 .is_v(is_v3),.is_d(is_d3),.cfg_v(cfg_v3),.cfg_d(cfg_d3),
 .lo_v(5'd0),.lo_d(1280'd0),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(fx3));
integer cycle=0,job=0,errors=0,checks=0,mut=0,bad_age=0;reg armed=0;
integer at[0:255],port_[0:255],target_[0:255];reg[159:0]want[0:255];reg[255:0]seen=0;
integer age[0:2][0:1];
always @(posedge ck)begin #2;cycle=cycle+1;if(armed)begin
 if(is_v!==is_v3||cfg_v!==cfg_v3||((is_v||is_v3)&&is_d!==is_d3)||((cfg_v||cfg_v3)&&cfg_d!==cfg_d3)||fx!==fx3)begin errors=errors+1;if(errors<6)$display("XRT1_XRT3_MISMATCH cycle%0d",cycle);end
 if(fr||fx)begin errors=errors+1;if(errors<6)$display("FAULT r=%0d x=%0d cycle%0d",fr,fx,cycle);end
 if(is_v||cfg_v)begin
  integer tag_,target,dt;reg[159:0]data;
  data=is_v?is_d:cfg_d;target=is_v?2:3;tag_=int'(data[31:0]);
  if(is_v&&cfg_v||tag_<1||tag_>96)begin errors=errors+1;$display("BAD_TAG %0d",tag_);end else begin
   checks=checks+1;dt=cycle-at[tag_];
   if(age[port_[tag_]][target-2]<0)age[port_[tag_]][target-2]=dt;
   if(seen[tag_]||target!=target_[tag_]||data!==want[tag_]||dt!=age[port_[tag_]][target-2]+(bad_age?1:0))begin
    errors=errors+1;if(errors<6)$display("BAD_ENTRY tag%0d port%0d target%0d age%0d",tag_,port_[tag_],target,dt);
   end
   seen[tag_]=1;
  end
 end
end end
integer s,p,t,j;reg[1103:0]word_;
initial begin
mut=$test$plusargs("bad_payload");bad_age=$test$plusargs("bad_age");
for(j=0;j<256;j=j+1)begin at[j]=-1;port_[j]=0;target_[j]=0;want[j]=0;end
for(p=0;p<3;p=p+1)for(t=0;t<2;t=t+1)age[p][t]=-1;
repeat(64)begin @(posedge ck);#5;end rs=1;repeat(64)begin @(posedge ck);#5;end armed=1;
for(s=0;s<16;s=s+1)begin sid=4'(s);repeat(8)begin @(posedge ck);#5;end
 for(p=0;p<3;p=p+1)for(t=2;t<=3;t=t+1)begin
  @(posedge ck);#5;job=job+1;at[job]=cycle;port_[job]=p;target_[job]=t;
  want[job]={32'hffff2468^32'(s),32'h87654321^32'(job),32'h13579bdf^32'(p),32'h2468ace0^32'(t),32'(job)};
  word_=0;word_[0]=1;word_[21+:16]=16'd1<<s;word_[37+:5]=5'(t);word_[47+:160]=want[job];
  if(mut&&job==13)word_[138]=~word_[138];
  if(p==0)ri_e=word_;else if(p==1)ri_w=word_;else vi=word_[275:0];
  @(posedge ck);#5;ri_e=0;ri_w=0;vi=0;
  repeat(12)begin @(posedge ck);#5;end
 end
end
repeat(20)begin @(posedge ck);#5;end
if(checks!=96||fr||fx)errors=errors+1;
$display("NATIVE_CTL_ENTRY %s checks=%0d errors=%0d target2_age=%0d/%0d/%0d target3_age=%0d/%0d/%0d clock833",errors==0?"PASS":"FAIL",checks,errors,age[0][0],age[1][0],age[2][0],age[0][1],age[1][1],age[2][1]);
if(errors)$fatal(1,"entry payload/date control");$finish;
end
endmodule
