`timescale 1ps/1fs
module tb_xrt_target5;
reg ck=0,rs=0;always #416.5 ck=~ck;
reg[3:0]sid=0;reg ev=0,wv=0,vv=0;reg[1075:0]word_=0;
wire[4:0]sv[0:1];wire[49:0]sa[0:1];wire[39:0]sm[0:1];wire[1279:0]sd[0:1];wire[1:0]fault;
for(genvar g=0;g<2;g=g+1)begin:G
if(g==0)begin:T1
 ot_s81sl_xrt1 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'o01234),.QDELAYS(128'd0))u(
 .clk(ck),.rst_n(rs),.sid(sid),.dl_ev(ev),.dl_e(word_[1075:1]),.dl_wv(wv),.dl_w(word_[1075:1]),.dl_vv(vv),.dl_vb(word_[275:1]),
 .sw_v(sv[g]),.sw_a(sa[g]),.sw_m(sm[g]),.sw_d(sd[g]),.lo_v(5'd0),.lo_d(1280'd0),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(fault[g]));
end else begin:T3
 ot_s81sl_xrt3 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'o01234),.QDELAYS(128'd0))u(
 .clk(ck),.rst_n(rs),.sid(sid),.dl_ev(ev),.dl_e(word_[1075:1]),.dl_wv(wv),.dl_w(word_[1075:1]),.dl_vv(vv),.dl_vb(word_[275:1]),.bi(1046'd0),
 .sw_v(sv[g]),.sw_a(sa[g]),.sw_m(sm[g]),.sw_d(sd[g]),.lo_v(5'd0),.lo_d(1280'd0),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(fault[g]));
end end
integer cycle=0,job=0,errors=0,checks=0,mut=0,bad_age=0;reg armed=0;
integer at[0:255],port_[0:255],leaf_[0:255],row_[0:255];reg[127:0]want[0:255];
integer age[0:1][0:2],got[0:1];reg[255:0]seen[0:1];
always @(posedge ck)begin #2;cycle=cycle+1;if(armed)begin
 if(fault!=0)errors=errors+1;
 for(integer a=0;a<2;a=a+1)for(integer k=0;k<5;k=k+1)if(sv[a][k])begin
  integer tag_,dt;tag_=int'(sd[a][256*k+:32]);
  if(tag_<1||tag_>240)begin errors=errors+1;$display("BAD_TAG %0d",tag_);end else begin
   got[a]=got[a]+1;checks=checks+1;dt=cycle-at[tag_];
   if(age[a][port_[tag_]]<0)age[a][port_[tag_]]=dt;
   if(seen[a][tag_]||leaf_[tag_]!=k||sa[a][10*k+:10]!==10'(row_[tag_])||sm[a][8*k+:8]!==8'h0f||
      sd[a][256*k+:256]!=={128'd0,want[tag_]}||dt!=age[a][port_[tag_]]+(bad_age?1:0))begin
    errors=errors+1;if(errors<6)$display("BAD_TARGET5 actor%0d tag%0d port%0d age%0d",a,tag_,port_[tag_],dt);
   end
   seen[a][tag_]=1;
  end
 end
end end
integer s,k,p,j;
initial begin
mut=$test$plusargs("bad_payload");bad_age=$test$plusargs("bad_age");
for(j=0;j<256;j=j+1)begin at[j]=-1;port_[j]=0;leaf_[j]=0;row_[j]=0;want[j]=0;end
for(j=0;j<2;j=j+1)begin got[j]=0;seen[j]=0;for(p=0;p<3;p=p+1)age[j][p]=-1;end
repeat(64)begin @(posedge ck);#5;end rs=1;repeat(64)begin @(posedge ck);#5;end armed=1;
for(s=0;s<16;s=s+1)begin
 sid=4'(s);repeat(4)begin @(posedge ck);#5;end
 for(k=0;k<5;k=k+1)for(p=0;p<3;p=p+1)begin
  @(posedge ck);#5;job=job+1;at[job]=cycle;port_[job]=p;leaf_[job]=k;row_[job]=(job%49==48)?1008:job%32;
  want[job]={32'h87654321^32'(job),32'h13579bdf^32'(s),32'h2468ace0^32'(k),32'(job)};
  word_=0;word_[21+:16]=16'd1<<s;word_[37+:5]=5'd5;word_[42+:5]=5'd1<<k;
  word_[47+:10]=10'(row_[job]);word_[57+:4]=4'hf;word_[61+:128]=want[job];
  if(mut&&job==13)word_[138]=~word_[138];ev=(p==0);wv=(p==1);vv=(p==2);
  @(posedge ck);#5;ev=0;wv=0;vv=0;word_=0;
 end
end
repeat(20)begin @(posedge ck);#5;end
if(got[0]!=240||got[1]!=240||fault)errors=errors+1;
$display("XRT_TARGET5 %s jobs=%0d checks=%0d got=%0d/%0d errors=%0d age_t1=%0d/%0d/%0d age_t3=%0d/%0d/%0d clock833",errors==0?"PASS":"FAIL",job,checks,got[0],got[1],errors,age[0][0],age[0][1],age[0][2],age[1][0],age[1][1],age[1][2]);
if(errors)$fatal(1,"target5 payload/date control");$finish;end
endmodule
