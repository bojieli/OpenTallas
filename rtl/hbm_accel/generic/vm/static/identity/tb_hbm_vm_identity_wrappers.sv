`timescale 1ns/1ps
`default_nettype none
// Native group-count successors: RG7/WG3(NW/NE), RG5/WG1(SW/SE).
// Real eight-bank SRAM vehicle; no bank or response substitute.
module tb_hbm_vm_identity_wrappers;
    parameter integer SID=0,RG=5,WG=1;
    parameter integer MUT=0; //1: wrong response-group wiring at actual bank output
    localparam RB=$clog2(RG+1),WB=$clog2(WG+5);
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [8*RG*17-1:0] rq=0;
    reg [8*281-1:0] dq=0;
    reg [7:0] rslot_v=0,wslot_v=0;
    reg [8*RB-1:0] rslot=0;
    reg [8*WB-1:0] wslot=0;
    reg [8*285-1:0] pq=0;
    wire [8*RG*257-1:0] actual_rr,rr;
    wire [8*266-1:0] pr;
    wire [7:0] dq_done;
    wire [143:0] status;
    for(genvar b=0;b<8;b=b+1)begin:bank
        if(SID==0 && b==0)begin: literal_q0_b0
          hfd_vms_bank_identity_q0_b0 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==0 && b==1)begin: literal_q0_b1
          hfd_vms_bank_identity_q0_b1 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==0 && b==2)begin: literal_q0_b2
          hfd_vms_bank_identity_q0_b2 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==0 && b==3)begin: literal_q0_b3
          hfd_vms_bank_identity_q0_b3 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==0 && b==4)begin: literal_q0_b4
          hfd_vms_bank_identity_q0_b4 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==0 && b==5)begin: literal_q0_b5
          hfd_vms_bank_identity_q0_b5 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==0 && b==6)begin: literal_q0_b6
          hfd_vms_bank_identity_q0_b6 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==0 && b==7)begin: literal_q0_b7
          hfd_vms_bank_identity_q0_b7 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==1 && b==0)begin: literal_q1_b0
          hfd_vms_bank_identity_q1_b0 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==1 && b==1)begin: literal_q1_b1
          hfd_vms_bank_identity_q1_b1 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==1 && b==2)begin: literal_q1_b2
          hfd_vms_bank_identity_q1_b2 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==1 && b==3)begin: literal_q1_b3
          hfd_vms_bank_identity_q1_b3 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==1 && b==4)begin: literal_q1_b4
          hfd_vms_bank_identity_q1_b4 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==1 && b==5)begin: literal_q1_b5
          hfd_vms_bank_identity_q1_b5 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==1 && b==6)begin: literal_q1_b6
          hfd_vms_bank_identity_q1_b6 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==1 && b==7)begin: literal_q1_b7
          hfd_vms_bank_identity_q1_b7 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.wq0(281'd0),.wq_done0());
        end
        if(SID==2 && b==0)begin: literal_q2_b0
          hfd_vms_bank_identity_q2_b0 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==2 && b==1)begin: literal_q2_b1
          hfd_vms_bank_identity_q2_b1 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==2 && b==2)begin: literal_q2_b2
          hfd_vms_bank_identity_q2_b2 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==2 && b==3)begin: literal_q2_b3
          hfd_vms_bank_identity_q2_b3 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==2 && b==4)begin: literal_q2_b4
          hfd_vms_bank_identity_q2_b4 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==2 && b==5)begin: literal_q2_b5
          hfd_vms_bank_identity_q2_b5 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==2 && b==6)begin: literal_q2_b6
          hfd_vms_bank_identity_q2_b6 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==2 && b==7)begin: literal_q2_b7
          hfd_vms_bank_identity_q2_b7 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==3 && b==0)begin: literal_q3_b0
          hfd_vms_bank_identity_q3_b0 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==3 && b==1)begin: literal_q3_b1
          hfd_vms_bank_identity_q3_b1 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==3 && b==2)begin: literal_q3_b2
          hfd_vms_bank_identity_q3_b2 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==3 && b==3)begin: literal_q3_b3
          hfd_vms_bank_identity_q3_b3 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==3 && b==4)begin: literal_q3_b4
          hfd_vms_bank_identity_q3_b4 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==3 && b==5)begin: literal_q3_b5
          hfd_vms_bank_identity_q3_b5 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==3 && b==6)begin: literal_q3_b6
          hfd_vms_bank_identity_q3_b6 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        if(SID==3 && b==7)begin: literal_q3_b7
          hfd_vms_bank_identity_q3_b7 memory(.clk(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(status[b*18+:18]),.rq0(rq[(b*RG+0)*17+:17]),.rr0(actual_rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(actual_rr[(b*RG+1)*257+:257]),.rq2(rq[(b*RG+2)*17+:17]),.rr2(actual_rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(actual_rr[(b*RG+3)*257+:257]),.rq4(rq[(b*RG+4)*17+:17]),.rr4(actual_rr[(b*RG+4)*257+:257]),.rq5(rq[(b*RG+5)*17+:17]),.rr5(actual_rr[(b*RG+5)*257+:257]),.wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.wq2(281'd0),.wq_done2());
        end
        for(genvar g=0;g<RG;g=g+1)begin:group_wire
            assign rr[(b*RG+g)*257+:257]=actual_rr[(b*RG+(MUT==1?(g+1)%RG:g))*257+:257];
        end
    end
    function automatic [255:0] payload(input integer b,row);
        for(integer w=0;w<8;w=w+1)payload[w*32+:32]=32'hbeaf1280^32'(b<<24)^32'(row<<9)^32'(w*31);
    endfunction
    reg [7:0] exp_done[0:4095],exp_pr_v[0:4095];
    reg [8*RG-1:0] exp_rr_v[0:4095];
    reg [2047:0] exp_data[0:4095];
    reg [63:0] exp_pr_tag[0:4095];
    integer cycle=0,writes=0,reads=0,packet_reads=0;
    integer group_reads[0:RG-1];
    reg fault_expected=0;
    task clear_inputs;
        begin rq=0;dq=0;rslot_v=0;wslot_v=0;rslot=0;wslot=0;pq=0;end
    endtask
    task tick;
        integer group_id,row;
        begin
            @(posedge clk);
            if(rst_n)for(integer b=0;b<8;b=b+1)begin
                if(dq[b*281+280])exp_done[cycle+3][b]=1;
                if(rslot_v[b])begin
                    group_id=int'(rslot[b*RB+:RB]);
                    if(group_id<RG&&rq[(b*RG+group_id)*17+16])begin
                        row=int'(rq[(b*RG+group_id)*17+3+:10]);
                        exp_rr_v[cycle+6][b*RG+group_id]=1;
                        exp_data[cycle+6][b*256+:256]=payload(b,row);
                    end else if(group_id==RG&&pq[b*285+284])begin
                        row=int'(pq[b*285+272+:10]);exp_pr_v[cycle+6][b]=1;
                        exp_data[cycle+6][b*256+:256]=payload(b,row);
                        exp_pr_tag[cycle+6][b*8+:8]=pq[b*285+:8];
                    end
                end
            end
            #2;
            if(rst_n)begin
                if(!fault_expected&&status!==0)$fatal(1,"bank fault RG=%0d cycle=%0d status=%h",RG,cycle,status);
                if(dq_done!==exp_done[cycle])$fatal(1,"DMA commit phase RG=%0d cycle=%0d",RG,cycle);
                for(integer b=0;b<8;b=b+1)begin
                    if(dq_done[b])writes=writes+1;
                    for(integer g=0;g<RG;g=g+1)begin
                        if(rr[(b*RG+g)*257+256]!==exp_rr_v[cycle][b*RG+g])
                            $fatal(1,"actual bank response group mismatch RG=%0d cycle=%0d bank=%0d group=%0d",RG,cycle,b,g);
                        if(exp_rr_v[cycle][b*RG+g])begin
                            if(rr[(b*RG+g)*257+:256]!==exp_data[cycle][b*256+:256])$fatal(1,"actual SRAM readback mismatch");
                            reads=reads+1;group_reads[g]=group_reads[g]+1;
                        end
                    end
                    if(pr[b*266+265]!==exp_pr_v[cycle][b])$fatal(1,"packet phase mismatch");
                    if(exp_pr_v[cycle][b])begin
                        if(pr[b*266+:266]!=={1'b1,1'b0,exp_pr_tag[cycle][b*8+:8],exp_data[cycle][b*256+:256]})$fatal(1,"packet memory/tag mismatch");
                        packet_reads=packet_reads+1;
                    end
                end
            end
            cycle=cycle+1;@(negedge clk);
        end
    endtask
    initial begin
        integer row,group_id;
        for(integer c=0;c<4096;c=c+1)begin exp_done[c]=0;exp_pr_v[c]=0;exp_rr_v[c]=0;exp_data[c]=0;exp_pr_tag[c]=0;end
        for(integer g=0;g<RG;g=g+1)group_reads[g]=0;
        repeat(3)tick();rst_n=1;repeat(3) @(negedge clk); /* ot_rst_relay release: initialization mode, 3 edges */
        // Actual DMA port fills128rows inall8banks at8sectors/cycle.
        for(row=0;row<128;row=row+1)begin
            clear_inputs();wslot_v=8'hff;
            for(integer b=0;b<8;b=b+1)begin
                wslot[b*WB+:WB]=WB'(WG+4);
                dq[b*281+:281]={1'b1,1'b0,2'(SID),10'(row),3'(b),payload(b,row),8'hff};
            end
            tick();
        end
        clear_inputs();repeat(8)tick();
        // Every wide group reads every row in every bank. Group selection
        // varies every cycle and independently by bank; unselected outputs
        // must stay invalid. Includes addedCOLL5/IDX6 onRG7.
        for(integer t=0;t<RG*128;t=t+1)begin
            clear_inputs();rslot_v=8'hff;
            for(integer b=0;b<8;b=b+1)begin
                group_id=(t+b)%RG;row=(t/RG+b*3)%128;
                rslot[b*RB+:RB]=RB'(group_id);
                rq[(b*RG+group_id)*17+:17]={1'b1,1'b0,2'(SID),10'(row),3'(b)};
            end
            tick();
        end
        clear_inputs();repeat(9)tick();
        if(writes!=1024||reads!=RG*1024)$fatal(1,"missing allgroup inventory");
        for(integer g=0;g<RG;g=g+1)if(group_reads[g]!=1024)$fatal(1,"group throughput mismatch group=%0d count=%0d",g,group_reads[g]);
        // Packetport is now ownerRG, seven onlargestshape; it remains distinct
        // from allseven wide outputs and preserves original8bitbank tag.
        rslot_v=8'hff;
        for(integer b=0;b<8;b=b+1)begin
            rslot[b*RB+:RB]=RB'(RG);
            pq[b*285+:285]={1'b1,1'b0,1'b0,10'(b*7),256'd0,8'd0,8'(8'h90+b)};
        end
        tick();clear_inputs();repeat(9)tick();
        if(packet_reads!=8)$fatal(1,"packet owner missing");
        // Deliberately activate two groups but reserveonlygroup0. Thebank
        // must execute exactlygroup0, raiseFAULT, andneverdefergroup1.
        fault_expected=1;rslot_v=8'hff;
        for(integer b=0;b<8;b=b+1)begin
            rslot[b*RB+:RB]=0;
            rq[(b*RG+0)*17+:17]={1'b1,1'b0,2'(SID),10'd7,3'(b)};
            rq[(b*RG+1)*17+:17]={1'b1,1'b0,2'(SID),10'd33,3'(b)};
        end
        tick();clear_inputs();repeat(12)tick();
        for(integer b=0;b<8;b=b+1)if(status[b*18+17]!==1)$fatal(1,"unselected secondgroup didnotfault");
        $display("VM_ALLGROUPS_STATIC PASS RG=%0d WG=%0d banks=8 SRAMs=24 DMAwrites=1024 exactwide_reads=%0d eachgroup_reads=1024 packet_reads=8 sectors_per_cycle=8 return_edges=6 conflict_fault_no_arbitration=1",RG,WG,RG*1024);
        $finish;
    end
endmodule
`default_nettype wire
