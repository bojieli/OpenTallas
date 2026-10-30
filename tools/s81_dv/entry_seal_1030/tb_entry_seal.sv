`timescale 1ps/1fs
module tb_entry_seal;
reg ck=0;always #416.5 ck=~ck;
reg rst_n=0;reg[514:0]f_host=0;reg[52:0]f_ks=0;
wire[275:0]vo_n,vo_s;wire[76:0]t_host;wire[53:0]t_kd;
wire cw_v;wire[9:0]cw_a;wire[255:0]cw_d;
 dsdv_hostb_seqhost_mux #(.HOSTB_ENABLE(0),.STATIC_KS6(0)) dut(
 .ck(ck),.rst_n(rst_n),.tap_k(8'd0),.sink_k(8'd0),.vi_s(276'd0),.vi_n(276'd0),.vo_s(vo_s),.vo_n(vo_n),
 .select_hbe(1'b0),.hbe_f_host(515'd0),.starter_f_ks(53'd0),.hbe_ks_slot(3'd0),
 .f_host(f_host),.t_host(t_host),.f_lf(4'b0101),.f_ks(f_ks),.t_kd(t_kd),
 .sid_ri(1'b0),.vid_ri(1'b0),.s_jd_w(2'd0),.s_jd_e(2'd0),.s_hc_w(9'd0),.s_hc_e(9'd0),
 .st_rg_w(2'b01),.st_rg_e(2'b01),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),.mu_rt_7n(32'd0),.mu_rt_0n(32'd0));

reg[514:0]words[0:451];integer cycle=0,errors=0,mut=0;reg armed=0;
always @(posedge ck)begin #2;cycle=cycle+1;if(armed&&t_host[75])errors=errors+1;end
integer i;reg[514:0]w;
initial begin
mut=$test$plusargs("bad_seal");$readmemh("page.host_boot.memh",words);
repeat(64)begin @(posedge ck);#5;end rst_n=1;
repeat(80)begin @(posedge ck);#5;end armed=1;
for(i=0;i<452;i=i+1)begin
 w=words[i];
 if(mut&&((w>>1)&255)==16&&((w>>59)&3)==3&&w[58])w[40]=~w[40];
 @(posedge ck);#5;f_host=w;@(posedge ck);#5;f_host=0;
 repeat(3)begin @(posedge ck);#5;end
end
repeat(160)begin @(posedge ck);#5;end
if(!dut.u_seqhost.u.u_u.u_l1.u_iss.sealed)errors=errors+1;
if(dut.u_seqhost.u.u_u.u_l1.u_iss.length_q!=104)errors=errors+1;
$display("ENTRY_SEAL %s words452 rows104 errors%0d sealed%0b code%0d clock833",errors==0?"PASS":"FAIL",errors,dut.u_seqhost.u.u_u.u_l1.u_iss.sealed,dut.u_seqhost.u.u_u.u_l1.u_iss.fault_code);
if(errors)$fatal(1,"actual selected local native SEAL");$finish;
end
endmodule
