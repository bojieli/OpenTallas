`timescale 1ps/1fs
module tb_entry_reload;
reg ck=0;always #416.5 ck=~ck;
reg rst_n=0;reg[514:0]f_host=0;reg[52:0]f_ks=0;
wire[275:0]vo_n,vo_s;wire[76:0]t_host;wire[53:0]t_kd;wire[3:0]t_mf=dut.t_mf;
wire cw_v;wire[9:0]cw_a;wire[255:0]cw_d;
 dsdv_hostb_seqhost_mux #(.HOSTB_ENABLE(0),.STATIC_KS6(0)) dut(
 .ck(ck),.rst_n(rst_n),.tap_k(8'd0),.sink_k(8'd0),.vi_s(276'd0),.vi_n(276'd0),.vo_s(vo_s),.vo_n(vo_n),
 .select_hbe(1'b0),.hbe_f_host(515'd0),.starter_f_ks(53'd0),.hbe_ks_slot(3'd0),
 .f_host(f_host),.t_host(t_host),.f_lf(4'b0101),.f_ks(f_ks),.t_kd(t_kd),
 .sid_ri(1'b0),.vid_ri(1'b0),.s_jd_w(2'd0),.s_jd_e(2'd0),.s_hc_w(9'd0),.s_hc_e(9'd0),
 .st_rg_w(2'b01),.st_rg_e(2'b01),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),.mu_rt_7n(32'd0),.mu_rt_0n(32'd0));


reg[514:0]page0[0:451],page1[0:416];reg[275:0]wn[0:152],ws[0:50];
integer cyc=0,errors=0,nn=0,ns=0,kits=0,ks0=-1,ks1=-1,badmu=0,badpayload=0;reg armed=0;
always @(posedge ck)begin #2;cyc=cyc+1;if(armed)begin
 if(t_host[75]||t_mf)errors=errors+1;
 if(vo_n[0])begin if(nn>=153||vo_n!==wn[nn])errors=errors+1;nn=nn+1;end
 if(vo_s[0])begin if(ns>=51||vo_s!==ws[ns])errors=errors+1;ns=ns+1;end
 if(t_kd[53])begin
  if(t_kd!=={1'b1,21'(77+kits),10'(31+kits),21'(55+kits),1'b0})errors=errors+1;
  if(cyc-(kits==0?ks0:ks1)!=490)errors=errors+1;kits=kits+1;
 end
end end
task host(input[514:0]w);begin
 f_host=w;@(posedge ck);#5;f_host=0;repeat(4)begin @(posedge ck);#5;end
end endtask
task launch(input integer j);begin
 if((cyc-64)%4!=3)$fatal(1,"test launch violates selected relative-reset phase");
 if(j==0)ks0=cyc;else ks1=cyc;
 f_ks={1'b1,10'(31+j),21'(77+j),21'(55+j)};@(posedge ck);#5;f_ks=0;
end endtask
integer i;reg[514:0]w;
initial begin
badmu=$test$plusargs("bad_mu");badpayload=$test$plusargs("bad_payload");
$readmemh("page0.host.memh",page0);$readmemh("page1.host.memh",page1);$readmemh("expect_n.memh",wn);$readmemh("expect_s.memh",ws);
repeat(64)begin @(posedge ck);#5;end rst_n=1;
repeat(80)begin @(posedge ck);#5;end armed=1;
for(i=0;i<452;i=i+1)host(page0[i]);
repeat(16)begin @(posedge ck);#5;end
while((cyc-64)%4!=3)begin @(posedge ck);#5;end
if(!dut.u_seqhost.u.u_u.u_l1.u_iss.sealed)$fatal(1,"first page notsealed");launch(0);
while(cyc<ks0+492)begin @(posedge ck);#5;end
if(dut.u_seqhost.u.u_u.u_l1.u_iss.busy)$fatal(1,"reload before prior END");
for(i=0;i<417;i=i+1)begin
 w=page1[i];if(badmu&&i==0)w=page0[0];
 if(badpayload&&((w>>1)&255)==19&&(((w>>1)>>8)&127)==0)w[17]=~w[17];
 host(w);
end
while(cyc<ks0+2596)begin @(posedge ck);#5;end
if(cyc!=ks0+2596)$fatal(1,"compiled next KS slot missed");
if(!dut.u_seqhost.u.u_u.u_l1.u_iss.sealed)$fatal(1,"second page notsealed");launch(1);
repeat(550)begin @(posedge ck);#5;end
if(nn!=153||ns!=51||kits!=2||dut.u_seqhost.u.u_u.u_l1.u_iss.busy)errors=errors+1;
$display("ENTRY_RELOAD %s north%0d south%0d kits%0d errors%0d mf%h code%0d ks_gap%0d clock833",errors==0?"PASS":"FAIL",nn,ns,kits,errors,t_mf,dut.u_seqhost.u.u_u.u_l1.u_iss.fault_code,ks1-ks0);
if(errors)$fatal(1,"actual native reload/payload/return");$finish;
end
endmodule
