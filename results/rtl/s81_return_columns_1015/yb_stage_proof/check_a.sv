module check_a;
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
reg [WA-1:0] rd_in;
reg [8*64*SH-1:0] hrq_n;
reg [8*64*SH-1:0] hrq_s;
reg [8*16-1:0] yb_n;
reg [8*16-1:0] yb_s;
reg [4*32-1:0] cs;
reg [7:0] nflt_n;
reg [7:0] nflt_s;
reg  hov_d;
reg [3:0] hnz_n;
reg [3:0] hnz_s;
reg [3:0] pflt_n;
reg [3:0] pflt_s;
wire [S_RT+3:0] ref_rvm, dut_rvm;
reg [S_RT+3:0] prev_rvm, prev2_rvm;
wire [WA-1:0] ref_rdm, dut_rdm;
reg [WA-1:0] prev_rdm, prev2_rdm;
wire [16*S_RT-1:0] ref_rq_q, dut_rq_q;
reg [16*S_RT-1:0] prev_rq_q, prev2_rq_q;
wire  ref_hs_run, dut_hs_run;
reg  prev_hs_run, prev2_hs_run;
wire [15:0] ref_hs_c, dut_hs_c;
reg [15:0] prev_hs_c, prev2_hs_c;
wire [16*S_RT-1:0] ref_rq_q_c1, dut_rq_q_c1;
reg [16*S_RT-1:0] prev_rq_q_c1, prev2_rq_q_c1;
wire [16*S_RT-1:0] ref_rq_q_c2, dut_rq_q_c2;
reg [16*S_RT-1:0] prev_rq_q_c2, prev2_rq_q_c2;
wire [16*S_RT-1:0] ref_rq_q_c3, dut_rq_q_c3;
reg [16*S_RT-1:0] prev_rq_q_c3, prev2_rq_q_c3;
wire  ref_hs_run_c1, dut_hs_run_c1;
reg  prev_hs_run_c1, prev2_hs_run_c1;
wire  ref_hs_run_c2, dut_hs_run_c2;
reg  prev_hs_run_c2, prev2_hs_run_c2;
wire  ref_hs_run_c3, dut_hs_run_c3;
reg  prev_hs_run_c3, prev2_hs_run_c3;
wire [15:0] ref_hs_c_c1, dut_hs_c_c1;
reg [15:0] prev_hs_c_c1, prev2_hs_c_c1;
wire [15:0] ref_hs_c_c2, dut_hs_c_c2;
reg [15:0] prev_hs_c_c2, prev2_hs_c_c2;
wire [15:0] ref_hs_c_c3, dut_hs_c_c3;
reg [15:0] prev_hs_c_c3, prev2_hs_c_c3;
reg [S_RT+3:0] d_rv_in;
reg [WA-1:0] d_rd_in;
reg [8*64*SH-1:0] d_hrq_n;
reg [8*64*SH-1:0] d_hrq_s;
ot_s81_hc_ctra #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1)) ref_dut(.clk(clk),.rst_in(rst_in),.tid(tid),.last(last),.fv(fv),.fdx(fdx),.rv_in(rv_in),.rd_in(rd_in),.hrq_n(hrq_n),.hrq_s(hrq_s),.yb_n(yb_n),.yb_s(yb_s),.cs(cs),.nflt_n(nflt_n),.nflt_s(nflt_s),.hov_d(hov_d),.hnz_n(hnz_n),.hnz_s(hnz_s),.pflt_n(pflt_n),.pflt_s(pflt_s),.rvm(ref_rvm),.rdm(ref_rdm),.rq_q(ref_rq_q),.hs_run(ref_hs_run),.hs_c(ref_hs_c),.rq_q_c1(ref_rq_q_c1),.rq_q_c2(ref_rq_q_c2),.rq_q_c3(ref_rq_q_c3),.hs_run_c1(ref_hs_run_c1),.hs_run_c2(ref_hs_run_c2),.hs_run_c3(ref_hs_run_c3),.hs_c_c1(ref_hs_c_c1),.hs_c_c2(ref_hs_c_c2),.hs_c_c3(ref_hs_c_c3));
ot_s81_hc_ctra_columns #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1),.YB_STAGE(1)) dut(.clk_col({4{clk}}),.rst_in(rst_in),.tid(tid),.last(last),.fv(fv),.fdx(fdx),.rv_in(d_rv_in),.rd_in(d_rd_in),.hrq_n(d_hrq_n),.hrq_s(d_hrq_s),.yb_n(yb_n),.yb_s(yb_s),.cs(cs),.nflt_n(nflt_n),.nflt_s(nflt_s),.hov_d(hov_d),.hnz_n(hnz_n),.hnz_s(hnz_s),.pflt_n(pflt_n),.pflt_s(pflt_s),.rvm(dut_rvm),.rdm(dut_rdm),.rq_q(dut_rq_q),.hs_run(dut_hs_run),.hs_c(dut_hs_c),.rq_q_c1(dut_rq_q_c1),.rq_q_c2(dut_rq_q_c2),.rq_q_c3(dut_rq_q_c3),.hs_run_c1(dut_hs_run_c1),.hs_run_c2(dut_hs_run_c2),.hs_run_c3(dut_hs_run_c3),.hs_c_c1(dut_hs_c_c1),.hs_c_c2(dut_hs_c_c2),.hs_c_c3(dut_hs_c_c3),.yb_rel());
initial begin
d_rv_in=0;
d_rd_in=0;
d_hrq_n=0;
d_hrq_s=0;
rst_in=0;
tid=0;
last=0;
fv=0;
fdx=0;
rv_in=0;
rd_in=0;
hrq_n=0;
hrq_s=0;
yb_n=0;
yb_s=0;
cs=0;
nflt_n=0;
nflt_s=0;
hov_d=0;
hnz_n=0;
hnz_s=0;
pflt_n=0;
pflt_s=0;
for(cycle=0;cycle<2500;cycle=cycle+1) begin
clk=0; #1;
rst_in=(cycle>=6 && !(cycle>=1200 && cycle<1204));
for(j=0;j<$bits(tid);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);tid[j]=rng[0];end
last=rng[cycle%32];
for(j=0;j<$bits(fv);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);fv[j]=rng[0];end
for(j=0;j<$bits(fdx);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);fdx[j]=rng[0];end
for(j=0;j<$bits(rv_in);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);rv_in[j]=rng[0];end
for(j=0;j<$bits(rd_in);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);rd_in[j]=rng[0];end
for(j=0;j<$bits(hrq_n);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);hrq_n[j]=rng[0];end
for(j=0;j<$bits(hrq_s);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);hrq_s[j]=rng[0];end
for(j=0;j<$bits(yb_n);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);yb_n[j]=rng[0];end
for(j=0;j<$bits(yb_s);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);yb_s[j]=rng[0];end
for(j=0;j<$bits(cs);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);cs[j]=rng[0];end
for(j=0;j<$bits(nflt_n);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);nflt_n[j]=rng[0];end
for(j=0;j<$bits(nflt_s);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);nflt_s[j]=rng[0];end
hov_d=rng[cycle%32];
for(j=0;j<$bits(hnz_n);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);hnz_n[j]=rng[0];end
for(j=0;j<$bits(hnz_s);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);hnz_s[j]=rng[0];end
for(j=0;j<$bits(pflt_n);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);pflt_n[j]=rng[0];end
for(j=0;j<$bits(pflt_s);j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);pflt_s[j]=rng[0];end
tid=cycle%64; last=(cycle%31==0);
fv='0;
fv[S_RD+1]=(cycle%97==0); fv[S_RD+4]=(cycle%83==0); fv[S_RD+2]=(cycle%7==0); fv[S_RD+3]=(cycle%41==0); fdx[63 +:8]=cycle%5;
for(j=0;j<S_RT;j=j+1) begin rd_in[S_RT+8*j +:8]=(cycle+j)%5;rd_in[S_RT+8*S_RT+16*j +:16]=(cycle+j)%640;end
rd_in[S_RT+24*S_RT +:8]=cycle%5;
prev2_rvm=prev_rvm;
prev_rvm=ref_rvm;
prev2_rdm=prev_rdm;
prev_rdm=ref_rdm;
prev2_rq_q=prev_rq_q;
prev_rq_q=ref_rq_q;
prev2_hs_run=prev_hs_run;
prev_hs_run=ref_hs_run;
prev2_hs_c=prev_hs_c;
prev_hs_c=ref_hs_c;
prev2_rq_q_c1=prev_rq_q_c1;
prev_rq_q_c1=ref_rq_q_c1;
prev2_rq_q_c2=prev_rq_q_c2;
prev_rq_q_c2=ref_rq_q_c2;
prev2_rq_q_c3=prev_rq_q_c3;
prev_rq_q_c3=ref_rq_q_c3;
prev2_hs_run_c1=prev_hs_run_c1;
prev_hs_run_c1=ref_hs_run_c1;
prev2_hs_run_c2=prev_hs_run_c2;
prev_hs_run_c2=ref_hs_run_c2;
prev2_hs_run_c3=prev_hs_run_c3;
prev_hs_run_c3=ref_hs_run_c3;
prev2_hs_c_c1=prev_hs_c_c1;
prev_hs_c_c1=ref_hs_c_c1;
prev2_hs_c_c2=prev_hs_c_c2;
prev_hs_c_c2=ref_hs_c_c2;
prev2_hs_c_c3=prev_hs_c_c3;
prev_hs_c_c3=ref_hs_c_c3;
#1;clk=1;
d_rv_in<=rv_in;
d_rd_in<=rd_in;
d_hrq_n<=hrq_n;
d_hrq_s<=hrq_s;
#1;
if(cycle>14 && !(cycle>=1200 && cycle<1215)) begin
if(dut_rvm !== prev2_rvm) $fatal(1,"a rvm mismatch cycle=%0d",cycle);
if(dut_rdm !== prev2_rdm) $fatal(1,"a rdm mismatch cycle=%0d",cycle);
if(dut_rq_q !== prev_rq_q) $fatal(1,"a rq_q mismatch cycle=%0d",cycle);
if(dut_hs_run !== prev_hs_run) $fatal(1,"a hs_run mismatch cycle=%0d",cycle);
if(dut_hs_c !== prev_hs_c) $fatal(1,"a hs_c mismatch cycle=%0d",cycle);
if(dut_rq_q_c1 !== prev_rq_q_c1) $fatal(1,"a rq_q_c1 mismatch cycle=%0d",cycle);
if(dut_rq_q_c2 !== prev_rq_q_c2) $fatal(1,"a rq_q_c2 mismatch cycle=%0d",cycle);
if(dut_rq_q_c3 !== prev_rq_q_c3) $fatal(1,"a rq_q_c3 mismatch cycle=%0d",cycle);
if(dut_hs_run_c1 !== prev_hs_run_c1) $fatal(1,"a hs_run_c1 mismatch cycle=%0d",cycle);
if(dut_hs_run_c2 !== prev_hs_run_c2) $fatal(1,"a hs_run_c2 mismatch cycle=%0d",cycle);
if(dut_hs_run_c3 !== prev_hs_run_c3) $fatal(1,"a hs_run_c3 mismatch cycle=%0d",cycle);
if(dut_hs_c_c1 !== prev_hs_c_c1) $fatal(1,"a hs_c_c1 mismatch cycle=%0d",cycle);
if(dut_hs_c_c2 !== prev_hs_c_c2) $fatal(1,"a hs_c_c2 mismatch cycle=%0d",cycle);
if(dut_hs_c_c3 !== prev_hs_c_c3) $fatal(1,"a hs_c_c3 mismatch cycle=%0d",cycle);
end
end
$display("PASS a 2500 cycles exact delayed return and unchanged requests");$finish;end
endmodule