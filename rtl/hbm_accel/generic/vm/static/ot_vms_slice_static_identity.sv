`timescale 1ns/1ps
`default_nettype none
// Actual static VM composition. Per-child clocks are independent physical
// roots at the SAME compiler edge/phase. This wrapper contains only wires.
// NC excludes the ring replay client; NC=0 has no local packet clients.
// The fixed compiler calendar controls bank, hub, ring and response slots.
module ot_vms_slice_static_identity #(
    parameter integer SLICE_ID=0,
    parameter integer NC=7,RG=3,WG=1,
    parameter integer CW=((NC+1)>1)?$clog2(NC+1):1,
    parameter integer RB=((RG+1)>1)?$clog2(RG+1):1,
    parameter integer WB=$clog2(WG+5),
    parameter integer RMUT=0
)(
    input wire [7:0] clk_bank,
    input wire clk_hub,
    input wire [1:0] clk_ring,
    input wire clk_replay,
    input wire rst_n,
    input wire [((NC>0)?NC:1)*338-1:0] cq,
    output wire [((NC>0)?NC:1)*274-1:0] cr,
    input wire [(NC+1)*2-1:0] client_seq,
    input wire [(NC+1)-1:0] response_enable,
    input wire [(NC+1)*2-1:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [8*CW-1:0] bank_client,
    input wire [1:0] hub_ring_enable,
    input wire [2*CW-1:0] hub_ring_client,
    input wire [7:0] rslot_v,wslot_v,
    input wire [8*RB-1:0] rslot,
    input wire [8*WB-1:0] wslot,
    input wire [RG*8*17-1:0] rq,
    output wire [RG*8*257-1:0] rr,
    input wire [WG*8*281-1:0] wq,
    output wire [WG*8-1:0] wq_done,
    input wire [8*281-1:0] dq,kq,
    output wire [7:0] dq_done,kq_done,
    input wire [2223:0] cw_in,ccw_in,
    output wire [2223:0] cw_out,ccw_out,
    input wire [1:0] ring_tx_enable,
    input wire [5:0] ring_tx_source,
    input wire replay_enable,replay_source,
    output wire [143:0] bank_status,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);
    localparam [1:0] sid=2'(SLICE_ID);
    initial begin
        if(SLICE_ID<0 || SLICE_ID>3) $fatal(1,"compiled slice identity");
        if((SLICE_ID==0 && (RG!=5||WG!=1)) || (SLICE_ID==1 && (RG!=4||WG!=1)) || (SLICE_ID>=2 && (RG!=6||WG!=3)))
            $fatal(1,"compiled slice profile must match literal physical masters");
    end
    wire [(NC+1)*338-1:0] hcq;
    wire [(NC+1)*274-1:0] hcr;
    wire [337:0] hq;
    wire [273:0] hr=hcr[NC*274+:274];
    generate if(NC>0)begin:g_local
        assign hcq={hq,cq};assign cr=hcr[NC*274-1:0];
    end else begin:g_no_local
        assign hcq=hq;assign cr='0;
    end endgenerate
    wire [8*285-1:0] pq;
    wire [8*266-1:0] pr;
    wire [289:0] pi0,pi1;
    wire [263:0] cco0,cco1;
    wire [2207:0] eg,xq0,xq1;
    wire [7:0] xd0,xd1;
    wire [287:0] rce0,rce1;
    wire [265:0] ri0,ri1;
    wire [2:0] wk01,wk10;
    wire ack01,ack10;
    ot_vms_hub_static #(.NC(NC),.CW(CW)) u_hub(
        .clk(clk_hub),.rst_n(rst_n),.sid(sid),.cq(hcq),.cr(hcr),
        .client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),
        .bank_enable(bank_enable),.bank_client(bank_client),
        .cw_enable(hub_ring_enable[0]),.cw_client(hub_ring_client[0+:CW]),
        .ccw_enable(hub_ring_enable[1]),.ccw_client(hub_ring_client[CW+:CW]),
        .pq(pq),.pr(pr),.cwi(pi0),.cci(pi1),.cco0(cco0),.cco1(cco1),.status(hub_status));
    genvar b,g;
    generate for(b=0;b<8;b=b+1)begin:g_bank
        wire [RG*17-1:0] brq;
        wire [RG*257-1:0] brr;
        wire [WG*281-1:0] bwq;
        wire [WG-1:0] bdone;
        for(g=0;g<RG;g=g+1)begin:g_r
            assign brq[g*17+:17]=rq[(g*8+b)*17+:17];
            assign rr[(g*8+b)*257+:257]=brr[g*257+:257];
        end
        for(g=0;g<WG;g=g+1)begin:g_w
            assign bwq[g*281+:281]=wq[(g*8+b)*281+:281];
            assign wq_done[g*8+b]=bdone[g];
        end
        if(SLICE_ID==0 && b==0)begin:g_identity_q0_b0
            hfd_vms_bank_identity_q0_b0 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==0 && b==1)begin:g_identity_q0_b1
            hfd_vms_bank_identity_q0_b1 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==0 && b==2)begin:g_identity_q0_b2
            hfd_vms_bank_identity_q0_b2 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==0 && b==3)begin:g_identity_q0_b3
            hfd_vms_bank_identity_q0_b3 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==0 && b==4)begin:g_identity_q0_b4
            hfd_vms_bank_identity_q0_b4 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==0 && b==5)begin:g_identity_q0_b5
            hfd_vms_bank_identity_q0_b5 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==0 && b==6)begin:g_identity_q0_b6
            hfd_vms_bank_identity_q0_b6 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==0 && b==7)begin:g_identity_q0_b7
            hfd_vms_bank_identity_q0_b7 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==1 && b==0)begin:g_identity_q1_b0
            hfd_vms_bank_identity_q1_b0 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==1 && b==1)begin:g_identity_q1_b1
            hfd_vms_bank_identity_q1_b1 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==1 && b==2)begin:g_identity_q1_b2
            hfd_vms_bank_identity_q1_b2 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==1 && b==3)begin:g_identity_q1_b3
            hfd_vms_bank_identity_q1_b3 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==1 && b==4)begin:g_identity_q1_b4
            hfd_vms_bank_identity_q1_b4 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==1 && b==5)begin:g_identity_q1_b5
            hfd_vms_bank_identity_q1_b5 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==1 && b==6)begin:g_identity_q1_b6
            hfd_vms_bank_identity_q1_b6 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==1 && b==7)begin:g_identity_q1_b7
            hfd_vms_bank_identity_q1_b7 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]));
        end
        if(SLICE_ID==2 && b==0)begin:g_identity_q2_b0
            hfd_vms_bank_identity_q2_b0 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==2 && b==1)begin:g_identity_q2_b1
            hfd_vms_bank_identity_q2_b1 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==2 && b==2)begin:g_identity_q2_b2
            hfd_vms_bank_identity_q2_b2 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==2 && b==3)begin:g_identity_q2_b3
            hfd_vms_bank_identity_q2_b3 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==2 && b==4)begin:g_identity_q2_b4
            hfd_vms_bank_identity_q2_b4 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==2 && b==5)begin:g_identity_q2_b5
            hfd_vms_bank_identity_q2_b5 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==2 && b==6)begin:g_identity_q2_b6
            hfd_vms_bank_identity_q2_b6 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==2 && b==7)begin:g_identity_q2_b7
            hfd_vms_bank_identity_q2_b7 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==3 && b==0)begin:g_identity_q3_b0
            hfd_vms_bank_identity_q3_b0 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==3 && b==1)begin:g_identity_q3_b1
            hfd_vms_bank_identity_q3_b1 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==3 && b==2)begin:g_identity_q3_b2
            hfd_vms_bank_identity_q3_b2 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==3 && b==3)begin:g_identity_q3_b3
            hfd_vms_bank_identity_q3_b3 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==3 && b==4)begin:g_identity_q3_b4
            hfd_vms_bank_identity_q3_b4 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==3 && b==5)begin:g_identity_q3_b5
            hfd_vms_bank_identity_q3_b5 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==3 && b==6)begin:g_identity_q3_b6
            hfd_vms_bank_identity_q3_b6 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
        if(SLICE_ID==3 && b==7)begin:g_identity_q3_b7
            hfd_vms_bank_identity_q3_b7 u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),.wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(kq[b*281+:281]),.kq_done(kq_done[b]),.xq(xq0[b*276+:276]),.xq_done(xd0[b]),.xq2(xq1[b*276+:276]),.xq2_done(xd1[b]),.eg(eg[b*276+:276]),.pq(pq[b*285+:285]),.pr(pr[b*266+:266]),.status(bank_status[b*18+:18]),.rq0(brq[0*17+:17]),.rr0(brr[0*257+:257]),.rq1(brq[1*17+:17]),.rr1(brr[1*257+:257]),.rq2(brq[2*17+:17]),.rr2(brr[2*257+:257]),.rq3(brq[3*17+:17]),.rr3(brr[3*257+:257]),.rq4(brq[4*17+:17]),.rr4(brr[4*257+:257]),.rq5(brq[5*17+:17]),.rr5(brr[5*257+:257]),.wq0(bwq[0*281+:281]),.wq_done0(bdone[0]),.wq1(bwq[1*281+:281]),.wq_done1(bdone[1]),.wq2(bwq[2*281+:281]),.wq_done2(bdone[2]));
        end
    end endgenerate
    ot_vms_rstop_static #(.MUT(RMUT)) u_cw(
        .clk(clk_ring[0]),.rst_n(rst_n),.sid(sid),.dir(1'b0),
        .tx_enable(ring_tx_enable[0]),.tx_source(ring_tx_source[0+:3]),
        .l_in(cw_in),.l_out(cw_out),.pi(pi0),.eg(eg),.xq(xq0),.xq_done(xd0),
        .rce(rce0),.ri(ri0),.wko(wk01),.wki(wk10),.cco(cco0),
        .ack_o(ack01),.ack_i(ack10),.mirror_busy(mirror_busy[0]),.fault(ring_fault[0]));
    ot_vms_rstop_static #(.MUT(RMUT)) u_ccw(
        .clk(clk_ring[1]),.rst_n(rst_n),.sid(sid),.dir(1'b1),
        .tx_enable(ring_tx_enable[1]),.tx_source(ring_tx_source[3+:3]),
        .l_in(ccw_in),.l_out(ccw_out),.pi(pi1),.eg(eg),.xq(xq1),.xq_done(xd1),
        .rce(rce1),.ri(ri1),.wko(wk10),.wki(wk01),.cco(cco1),
        .ack_o(ack10),.ack_i(ack01),.mirror_busy(mirror_busy[1]),.fault(ring_fault[1]));
    ot_vms_rcl_static u_replay(.clk(clk_replay),.rst_n(rst_n),.sid(sid),
        .rx_enable(replay_enable),.rx_source(replay_source),.rce0(rce0),.rce1(rce1),
        .hq(hq),.hr(hr),.ri0(ri0),.ri1(ri1),.fault(ring_fault[2]));
    ot_vms_status_static u_status(.clk(clk_hub),.rst_n(rst_n),
        .bank_status(bank_status),.hub_status(hub_status),.ring_fault(|ring_fault),.vmstat(vmstat));
endmodule
`default_nettype wire
