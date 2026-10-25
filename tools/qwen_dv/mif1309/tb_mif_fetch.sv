`timescale 1ps/1fs
module tb_mif_fetch; reg ck=0;always #416.5 ck=~ck;integer cyc,checks=0,active=0;
qfd_dv_s8_suvm_rp1 #(.MIF(0)) g();
qfd_dv_s8_suvm_rp1 #(.MIF(1)) d();
wire [1313:0] ga={g_gb,g_gv,g_lv1,g_pd1,g_su_nr,g_su_idle,g_su_fault,g_su_prog,g_su_rows};
wire [1313:0] da={d_gb,d_gv,d_lv1,d_pd1,d_su_nr,d_su_idle,d_su_fault,d_su_prog,d_su_rows};
reg [1313:0] prev=0;always @(posedge ck)prev<=ga;
initial begin
l_retire=255;l_last=255;rd_v=1;tw_kind=3;
for(cyc=0;cyc<1400;cyc=cyc+1)begin
@(negedge ck);rst_n=(cyc>15);tw_we=(cyc>=32&&cyc<48);tw_addr=(cyc-32)*4;
tw_data=0;tw_data[18:1]=1;tw_data[36:19]=8;tw_data[512+18:513]=2;tw_data[512+36:512+19]=16;
su_cmd=0;if(cyc>=96&&cyc%128==96)su_cmd={1'b1,9'(2*((cyc/128)%8))};
@(posedge ck);#1;
if(cyc>64)begin checks=checks+1;if(da!==prev)begin $display("MIF_FETCH FAIL cyc=%0d diff=%h",cyc,da^prev);$fatal;end if(d_lv1!=0)active=active+1;end
end
if(checks<1000||active<10)$fatal(1,"insufficient active fetches %0d",active);
$display("MIF_FETCH PASS checks=%0d live=%0d",checks,active);$finish;end endmodule
