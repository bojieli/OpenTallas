module check_b;
localparam NG=256,D=5120,NCOL=3,GS=8,S_RD=2,S_RT=4,SH=2;
localparam O_D=104, P_D=108,WA=1132,WB=1152;
reg clk=0; reg [31:0] rng=32'h12345678;
integer cycle,j; reg active;
reg  rst_in;
reg [7:0] tid;
reg  last;
reg [S_RD+4:0] fv;
reg [O_D-1:0] fdx;
reg [S_RT+3:0] rv_in;
reg [P_D-1:0] rdh_in;
reg [WB-1:0] rdd_in;
reg [8*64*SH-1:0] hrq_n;
reg [8*64*SH-1:0] hrq_s;
reg [8*16-1:0] yb_n;
reg [8*16-1:0] yb_s;
wire [512*SH-1:0] ref_rdm, dut_rdm;
reg [512*SH-1:0] prev_rdm, prev2_rdm;
reg [S_RT+3:0] d_rv_in;
reg [P_D-1:0] d_rdh_in;
reg [WB-1:0] d_rdd_in;
reg [8*64*SH-1:0] d_hrq_n;
reg [8*64*SH-1:0] d_hrq_s;
reg [8*16-1:0] d_yb_n;
reg [8*16-1:0] d_yb_s;
ot_s81_hc_ctrb #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1)) ref_dut(.clk(clk),.rst_in(rst_in),.tid(tid),.last(last),.fv(fv),.fdx(fdx),.rv_in(rv_in),.rdh_in(rdh_in),.rdd_in(rdd_in),.hrq_n(hrq_n),.hrq_s(hrq_s),.yb_n(yb_n),.yb_s(yb_s),.rdm(ref_rdm));
ot_s81_hc_ctrb_columns #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1),.YB_STAGE(1)) dut(.clk_col({4{clk}}),.rst_in(rst_in),.tid(tid),.last(last),.fv(fv),.fdx(fdx),.rv_in(d_rv_in),.rdh_in(d_rdh_in),.rdd_in(d_rdd_in),.hrq_n(d_hrq_n),.hrq_s(d_hrq_s),.yb_n(d_yb_n),.yb_s(d_yb_s),.rdm(dut_rdm));
initial begin
d_rv_in=0;
d_rdh_in=0;
d_rdd_in=0;
d_hrq_n=0;
d_hrq_s=0;
d_yb_n=0;
d_yb_s=0;
rst_in=0;
tid=0;
last=0;
fv=0;
fdx=0;
rv_in=0;
rdh_in=0;
rdd_in=0;
hrq_n=0;
hrq_s=0;
yb_n=0;
yb_s=0;
for(cycle=0;cycle<2500;cycle=cycle+1) begin
clk=0; #1;
rst_in=(cycle>=6 && !(cycle>=1200 && cycle<1204));
for(j=0;j<$bits(tid);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);tid[j]=rng[0];end
last=rng[cycle%32];
for(j=0;j<$bits(fv);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);fv[j]=rng[0];end
for(j=0;j<$bits(fdx);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);fdx[j]=rng[0];end
for(j=0;j<$bits(rv_in);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);rv_in[j]=rng[0];end
for(j=0;j<$bits(rdh_in);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);rdh_in[j]=rng[0];end
for(j=0;j<$bits(rdd_in);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);rdd_in[j]=rng[0];end
for(j=0;j<$bits(hrq_n);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);hrq_n[j]=rng[0];end
for(j=0;j<$bits(hrq_s);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);hrq_s[j]=rng[0];end
for(j=0;j<$bits(yb_n);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);yb_n[j]=rng[0];end
for(j=0;j<$bits(yb_s);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);yb_s[j]=rng[0];end
tid=cycle%64; last=(cycle%31==0);
fv='0;
fv[S_RD+1]=(cycle%97==0); fv[S_RD+4]=(cycle%83==0); fv[S_RD+2]=(cycle%7==0); fv[S_RD+3]=(cycle%41==0); fdx[63 +:8]=cycle%5;
for(j=0;j<S_RT;j=j+1) begin rdh_in[S_RT+8*j +:8]=(cycle+j)%5;rdh_in[S_RT+8*S_RT+16*j +:16]=(cycle+j)%640;end
rdh_in[S_RT+24*S_RT +:8]=cycle%5;
prev2_rdm=prev_rdm;
prev_rdm=ref_rdm;
#1;clk=1;
d_rv_in<=rv_in;
d_rdh_in<=rdh_in;
d_rdd_in<=rdd_in;
d_hrq_n<=hrq_n;
d_hrq_s<=hrq_s;
d_yb_n<=yb_n;
d_yb_s<=yb_s;
#1;
if(cycle>14 && !(cycle>=1200 && cycle<1215)) begin
if(dut_rdm !== prev2_rdm) $fatal(1,"b rdm mismatch cycle=%0d",cycle);
end
end
$display("PASS b 2500 cycles exact delayed return and unchanged requests");$finish;end
endmodule