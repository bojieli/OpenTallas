`timescale 1ps/1ps
module tb;
reg clk=0,rst=0;
always begin #416 clk=1; #417 clk=0;end
reg [419:0] rt[0:2]; reg cv=0; reg [159:0] cd[0:2];
wire [9:0] v[0:2]; wire [119:0] a[0:2];wire[319:0] d[0:2];wire[2:0]fault;
ot_s81sl_capc5r_e6 #(.MUT(0)) e6(.ck_rt(clk),.ck_cw(clk),.ck_ce(clk),.ck_rn(clk),.ck_rs(clk),.rst_n_rt(rst),.rst_n_cw(rst),.rst_n_ce(rst),.rst_n_rn(rst),.rst_n_rs(rst),.rt_w(rt[0][279:0]),.rt_e(rt[0][419:280]),.cfg_v(cv),.cfg_d(cd[0]),.cw_s_v(v[0][5:0]),.cw_s_a(a[0][71:0]),.cw_s_d(d[0][191:0]),.cw_n_v(v[0][9:6]),.cw_n_a(a[0][119:72]),.cw_n_d(d[0][319:192]),.fault(fault[0]));
ot_s81sl_capc5r_w3 #(.MUT(0)) w3(.ck_rt(clk),.ck_cw(clk),.ck_rn(clk),.ck_rs(clk),.rst_n_rt(rst),.rst_n_cw(rst),.rst_n_rn(rst),.rst_n_rs(rst),.rt_w(rt[1][209:0]),.cfg_v(cv),.cfg_d(cd[1]),.cw_s_v(v[1][5:0]),.cw_s_a(a[1][71:0]),.cw_s_d(d[1][191:0]),.cw_n_v(v[1][9:6]),.cw_n_a(a[1][119:72]),.cw_n_d(d[1][319:192]),.fault(fault[1]));
ot_s81sl_capc2_w3 c2(.clk(clk),.rst_n(rst),.rt_w(rt[2][209:0]),.cfg_v(cv),.cfg_d(cd[2]),.cw_s_v(v[2][5:0]),.cw_s_a(a[2][71:0]),.cw_s_d(d[2][191:0]),.cw_n_v(v[2][9:6]),.cw_n_a(a[2][119:72]),.cw_n_d(d[2][319:192]),.fault(fault[2]));
reg[69:0] stim0[0:1599],stim1[0:1599],stim2[0:1599];
integer n,j,p,lane=0,mut=0;string root;
initial begin
if(!$value$plusargs("DIR=%s",root))$fatal;
if(!$value$plusargs("LANE=%d",lane))lane=0;
if(!$value$plusargs("MUT=%d",mut))mut=0;
$readmemh({root,"/stim0.hex"},stim0);$readmemh({root,"/stim1.hex"},stim1);$readmemh({root,"/stim2.hex"},stim2);
$readmemh({root,"/cfg.hex"},cd);
for(j=0;j<3;j=j+1)rt[j]=0;
for(n=0;n<1600;n=n+1)begin
@(negedge clk);
rst=(n>=64);cv=(n==100);
for(j=0;j<3;j=j+1)rt[j]=0;
rt[0][70*lane+:70]=stim0[n];rt[1][0+:70]=stim1[n];rt[2][0+:70]=stim2[n];
if(mut==1 && n==500)rt[0][70*lane+65]=~rt[0][70*lane+65];
@(posedge clk);#1;
for(j=0;j<3;j=j+1)for(p=0;p<10;p=p+1)if(v[j][p])$display("WRITE %0d %0d %0d %0d %08x",j,n,p,a[j][12*p+:12],d[j][32*p+:32]);
end
$display("FAULT %b causes %h %h %h tree %b%b",fault,e6.u_rt.fcause,w3.u_rt.fcause,c2.u_core.u_rt.fcause,e6.u_tw.fault,e6.u_te.fault);$finish;
end
endmodule
