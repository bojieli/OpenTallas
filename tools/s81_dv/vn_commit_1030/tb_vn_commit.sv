`timescale 1ps/1fs
module tb_vn_commit;
reg ck=0,rs=0;always #416.5 ck=~ck;
reg hv=0,hh=0,wv=0;reg[2:0]hj=0,wi=0;reg[255:0]hd=0,wd=0;wire fault;
ot_s81sl_vn_sp #(.LM(5),.LA(6))u(.clk(ck),.rst_n(rs),.hw_v(hv),.hw_j(hj),.hw_hf(hh),.hw_d(hd),.hr_v(1'b0),.hr_j(3'd0),.hr_hf(1'b0),.n_go(1'b0),.n_pre(128'd0),.wl_v(wv),.wl_i(wi),.wl_d(wd),.rb_v(1'b0),.rb_d(32'd0),.fault(fault));
integer cycle=0,err=0,checks=0,ha=-1,hb=-1,ga=-1,gb=-1,badpayload=0,badage=0;
always @(posedge ck)begin #2;cycle=cycle+1;end
function automatic[255:0]pattern(input integer tag_);
pattern={32'h13579bdf^32'(tag_),32'h2468ace0^32'(tag_*2),32'h87654321^32'(tag_*3),32'h10203040^32'(tag_*4),32'h11223344^32'(tag_*5),32'h55667788^32'(tag_*6),32'h99aabbcc^32'(tag_*7),32'haabbccdd^32'(tag_*8)};
endfunction
integer t,j,h,start,agea,ageb;reg[255:0]want;
initial begin
badpayload=$test$plusargs("bad_payload");badage=$test$plusargs("bad_age");
for(t=0;t<2;t=t+1)begin
rs=0;repeat(64)begin @(posedge ck);#5;end rs=1;repeat(64)begin @(posedge ck);#5;end
for(h=0;h<2;h=h+1)for(j=0;j<8;j=j+1)begin
 @(posedge ck);#5;start=cycle;want=pattern(1+t*16+h*8+j);hd=want;if(badpayload&&t==0&&h==0&&j==3)hd[77]=~hd[77];
 hv=1;hh=1'(h);hj=3'(j);agea=-1;
 for(integer d=0;d<8;d=d+1)begin
  @(posedge ck);#5;if(d==0)hv=0;
  if(agea<0&&((h==0&&u.u_a.u_h0.arr[j][255:0]===want)||(h==1&&u.u_b.u_h1.arr[j][255:0]===want)))agea=cycle-start;
 end
 if(agea<0)err=err+1;else begin
  if(h==0)begin if(ha<0)ha=agea;if(agea!=ha+badage)err=err+1;end
  else begin if(hb<0)hb=agea;if(agea!=hb+badage)err=err+1;end
  checks=checks+1;
 end
end
for(j=0;j<8;j=j+1)begin
 @(posedge ck);#5;start=cycle;want=pattern(100+t*8+j);wd=want;wv=1;wi=3'(j);agea=-1;ageb=-1;
 for(integer d=0;d<8;d=d+1)begin
  @(posedge ck);#5;if(d==0)wv=0;
  if(agea<0&&u.u_a.u_g.u_w.m[j]===want[127:0])agea=cycle-start;
  if(ageb<0&&u.u_b.u_g.u_w.m[j]===want[255:128])ageb=cycle-start;
 end
 if(agea<0||ageb<0)err=err+1;else begin
  if(ga<0)ga=agea;if(gb<0)gb=ageb;
  if(agea!=ga+badage||ageb!=gb+badage)err=err+1;checks=checks+2;
 end
end
end
$display("VN_COMMIT %s checks%0d errors%0d H_A%0d H_B%0d G_A%0d G_B%0d clock833",err==0?"PASS":"FAIL",checks,err,ha,hb,ga,gb);
if(err)$fatal(1,"actual VN store commit payload/age");$finish;
end
endmodule
