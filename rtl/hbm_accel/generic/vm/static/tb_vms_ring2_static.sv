`timescale 1ns/1ps
`default_nettype none
// HBM-BIND 2026-10-24: two-stop VM ring bench (B2 die: hb_vms_NW + hb_vms_NE only).
// Two hubs back to back through LINK relay flops per direction (NW.ccw_out -> NE.ccw_in, NE.cw_out -> NW.cw_in).
// SYM=0: the bound B2 masters hfd_hgi_vms_glue_nw2_t (NC=2: argmax, idx__ctl) + hfd_hgi_vms_static_NE2_glue (NC=0).
// SYM=1: two ot_vms_slice_static_glue NSTOP=2 NC=1 (sid 2, 3) so PREQ/PRSP also run NE->NW / NW->NE.
// Random compiler-scheduled traffic of every kind (local, remote PREQ + replay + PRSP, hub mirror write, bank mirror
// egress + commit + WACK) placed by a reservation table; a cycle-exact reference (latency formulas below + shadow
// memory) checks every bank request, every client response, every remote bank write (xq) and both mirror_busy, and
// that ring_fault / hub_status / vmstat flags stay 0.  Behavioural banks: pq -> pr after BL edges; xq -> xq_done
// after CD = 5 + BANK_PIN_IN edges.
// Node wrapper: uniform ports; local clients 0..NC-1, replay client = NC; bank_client 2 bits per bank (low CW used).
module tb_ring2_node #(parameter integer Q=0, SYM=0, RMUT=0, HMUT=0) (
    input wire clk, rst_n,
    input wire [675:0] cq, output wire [547:0] cr,
    input wire [5:0] client_seq, input wire [2:0] response_enable, input wire [5:0] response_seq,
    input wire [7:0] bank_enable, input wire [15:0] bank_client,
    input wire hub_ring_enable, input wire [1:0] hub_ring_client,
    input wire ring_tx_enable, input wire [2:0] ring_tx_source, input wire replay_enable,
    input wire [2223:0] ring_in, output wire [2223:0] ring_out,
    output wire [2207:0] bk_xq, bk_xq2, input wire [7:0] bk_xq_done, bk_xq2_done,
    input wire [2207:0] bk_eg, output wire [2279:0] bk_pq, input wire [2127:0] bk_pr,
    output wire [2:0] hub_status, output wire [1:0] mirror_busy, output wire [18:0] vmstat, output wire [2:0] ring_fault
);
    wire [7:0] bc1;
    for(genvar b=0;b<8;b=b+1) begin:g_bc assign bc1[b]=bank_client[b*2]; end
    if(SYM==0 && Q==0) begin:nw2
        hfd_hgi_vms_glue_nw2_t #(.RMUT(RMUT),.HMUT(HMUT)) dut(.clk(clk),.rst_n(rst_n),.cq(cq),.cr(cr),
        .client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),
        .bank_enable(bank_enable),.bank_client(bank_client),.hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client),
        .cw_in(ring_in),.ccw_out(ring_out),.ring_tx_enable(ring_tx_enable),.ring_tx_source(ring_tx_source),.replay_enable(replay_enable),
        .b0_xq(bk_xq[0+:276]),.b0_xq2(bk_xq2[0+:276]),.b0_xq_done(bk_xq_done[0]),.b0_xq2_done(bk_xq2_done[0]),
        .b0_eg(bk_eg[0+:276]),.b0_pq(bk_pq[0+:285]),.b0_pr(bk_pr[0+:266]),.b0_status(18'd0),.b0_flt(1'b0),
        .b1_xq(bk_xq[276+:276]),.b1_xq2(bk_xq2[276+:276]),.b1_xq_done(bk_xq_done[1]),.b1_xq2_done(bk_xq2_done[1]),
        .b1_eg(bk_eg[276+:276]),.b1_pq(bk_pq[285+:285]),.b1_pr(bk_pr[266+:266]),.b1_status(18'd0),.b1_flt(1'b0),
        .b2_xq(bk_xq[552+:276]),.b2_xq2(bk_xq2[552+:276]),.b2_xq_done(bk_xq_done[2]),.b2_xq2_done(bk_xq2_done[2]),
        .b2_eg(bk_eg[552+:276]),.b2_pq(bk_pq[570+:285]),.b2_pr(bk_pr[532+:266]),.b2_status(18'd0),.b2_flt(1'b0),
        .b3_xq(bk_xq[828+:276]),.b3_xq2(bk_xq2[828+:276]),.b3_xq_done(bk_xq_done[3]),.b3_xq2_done(bk_xq2_done[3]),
        .b3_eg(bk_eg[828+:276]),.b3_pq(bk_pq[855+:285]),.b3_pr(bk_pr[798+:266]),.b3_status(18'd0),.b3_flt(1'b0),
        .b4_xq(bk_xq[1104+:276]),.b4_xq2(bk_xq2[1104+:276]),.b4_xq_done(bk_xq_done[4]),.b4_xq2_done(bk_xq2_done[4]),
        .b4_eg(bk_eg[1104+:276]),.b4_pq(bk_pq[1140+:285]),.b4_pr(bk_pr[1064+:266]),.b4_status(18'd0),.b4_flt(1'b0),
        .b5_xq(bk_xq[1380+:276]),.b5_xq2(bk_xq2[1380+:276]),.b5_xq_done(bk_xq_done[5]),.b5_xq2_done(bk_xq2_done[5]),
        .b5_eg(bk_eg[1380+:276]),.b5_pq(bk_pq[1425+:285]),.b5_pr(bk_pr[1330+:266]),.b5_status(18'd0),.b5_flt(1'b0),
        .b6_xq(bk_xq[1656+:276]),.b6_xq2(bk_xq2[1656+:276]),.b6_xq_done(bk_xq_done[6]),.b6_xq2_done(bk_xq2_done[6]),
        .b6_eg(bk_eg[1656+:276]),.b6_pq(bk_pq[1710+:285]),.b6_pr(bk_pr[1596+:266]),.b6_status(18'd0),.b6_flt(1'b0),
        .b7_xq(bk_xq[1932+:276]),.b7_xq2(bk_xq2[1932+:276]),.b7_xq_done(bk_xq_done[7]),.b7_xq2_done(bk_xq2_done[7]),
        .b7_eg(bk_eg[1932+:276]),.b7_pq(bk_pq[1995+:285]),.b7_pr(bk_pr[1862+:266]),.b7_status(18'd0),.b7_flt(1'b0),
        .hub_status(hub_status),.mirror_busy(mirror_busy),.vmstat(vmstat),.ring_fault(ring_fault));
    end else if(SYM==0) begin:ne2
        assign cr=548'd0;
        hfd_hgi_vms_static_NE2_glue #(.RMUT(RMUT),.HMUT(HMUT)) dut(.clk_hub(clk),.clk_ring({clk,clk}),.clk_replay(clk),.rst_n(rst_n),
        .client_seq(client_seq[1:0]),.response_enable(response_enable[0]),.response_seq(response_seq[1:0]),
        .bank_enable(bank_enable),.bank_client(bc1),.hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client[0]),
        .ccw_in(ring_in),.cw_out(ring_out),.ring_tx_enable(ring_tx_enable),.ring_tx_source(ring_tx_source),.replay_enable(replay_enable),
        .bank_status(144'd0),.bk_xq(bk_xq),.bk_xq2(bk_xq2),.bk_xq_done(bk_xq_done),.bk_xq2_done(bk_xq2_done),
        .bk_eg(bk_eg),.bk_pq(bk_pq),.bk_pr(bk_pr),
        .hub_status(hub_status),.mirror_busy(mirror_busy),.vmstat(vmstat),.ring_fault(ring_fault));
    end else begin:sym
        // TX dir: NW (Q 0) ccw, NE (Q 1) cw; RX stop = the other.
        localparam integer TXD=(Q==0)?1:0;
        wire [2223:0] cw_out,ccw_out;
        assign cr[547:274]=274'd0;
        ot_vms_slice_static_glue #(.NC(1),.RG(5),.WG(2),.NATIVE_SHAPE(1),.BANK_PIN_IN(1),.NSTOP(2),.RMUT(RMUT),.HMUT(HMUT)) dut(
        .clk_hub(clk),.clk_ring({clk,clk}),.clk_replay(clk),.rst_n(rst_n),.sid(Q==0?2'd2:2'd3),
        .cq(cq[337:0]),.cr(cr[273:0]),.client_seq(client_seq[3:0]),.response_enable(response_enable[1:0]),.response_seq(response_seq[3:0]),
        .bank_enable(bank_enable),.bank_client(bc1),
        .hub_ring_enable(TXD==1?{hub_ring_enable,1'b0}:{1'b0,hub_ring_enable}),
        .hub_ring_client(TXD==1?{hub_ring_client[0],1'b0}:{1'b0,hub_ring_client[0]}),
        .cw_in(TXD==1?ring_in:2224'd0),.ccw_in(TXD==1?2224'd0:ring_in),.cw_out(cw_out),.ccw_out(ccw_out),
        .ring_tx_enable(TXD==1?{ring_tx_enable,1'b0}:{1'b0,ring_tx_enable}),
        .ring_tx_source(TXD==1?{ring_tx_source,3'd0}:{3'd0,ring_tx_source}),
        .replay_enable(replay_enable),.replay_source(TXD==1?1'b0:1'b1),
        .bank_status(144'd0),.bk_xq(bk_xq),.bk_xq2(bk_xq2),.bk_xq_done(bk_xq_done),.bk_xq2_done(bk_xq2_done),
        .bk_eg(bk_eg),.bk_pq(bk_pq),.bk_pr(bk_pr),
        .hub_status(hub_status),.mirror_busy(mirror_busy),.vmstat(vmstat),.ring_fault(ring_fault));
        assign ring_out=TXD==1?ccw_out:cw_out;
    end
endmodule
module tb_vms_ring2_static;
parameter integer SYM=0, LINK=0, NTX=240, SEED=1, RMUT=0, HMUT=0;
localparam integer T=12000, BL=2, CD=6, LK=LINK;
reg clk=0; always #5 clk=~clk;
reg rst_n=0;
// ---- DUT pins, packed per node (node 0 = NW sid 2, node 1 = NE sid 3)
reg [2*676-1:0] cq_f; reg [2*6-1:0] cseq_f; reg [2*3-1:0] ren_f; reg [2*6-1:0] rseq_f;
reg [2*8-1:0] ben_f; reg [2*16-1:0] bcl_f; reg [1:0] hre_f; reg [2*2-1:0] hrc_f;
reg [1:0] txe_f; reg [2*3-1:0] txs_f; reg [1:0] rep_f;
reg [2*8-1:0] xd0_f, xd1_f; reg [2*2208-1:0] eg_f; reg [2*2128-1:0] pr_f;
wire [2*548-1:0] cr_f; wire [2*2224-1:0] rout_f, rin_f; wire [2*2208-1:0] xq0_f, xq1_f; wire [2*2280-1:0] pq_f;
wire [2*3-1:0] hst_f; wire [2*2-1:0] mb_f; wire [2*19-1:0] vms_f; wire [2*3-1:0] rf_f;
for(genvar n=0;n<2;n=n+1) begin:N
    tb_ring2_node #(.Q(n),.SYM(SYM),.RMUT(RMUT),.HMUT(HMUT)) node(.clk(clk),.rst_n(rst_n),
        .cq(cq_f[n*676+:676]),.cr(cr_f[n*548+:548]),.client_seq(cseq_f[n*6+:6]),.response_enable(ren_f[n*3+:3]),
        .response_seq(rseq_f[n*6+:6]),.bank_enable(ben_f[n*8+:8]),.bank_client(bcl_f[n*16+:16]),
        .hub_ring_enable(hre_f[n]),.hub_ring_client(hrc_f[n*2+:2]),.ring_tx_enable(txe_f[n]),.ring_tx_source(txs_f[n*3+:3]),
        .replay_enable(rep_f[n]),.ring_in(rin_f[n*2224+:2224]),.ring_out(rout_f[n*2224+:2224]),
        .bk_xq(xq0_f[n*2208+:2208]),.bk_xq2(xq1_f[n*2208+:2208]),.bk_xq_done(xd0_f[n*8+:8]),.bk_xq2_done(xd1_f[n*8+:8]),
        .bk_eg(eg_f[n*2208+:2208]),.bk_pq(pq_f[n*2280+:2280]),.bk_pr(pr_f[n*2128+:2128]),
        .hub_status(hst_f[n*3+:3]),.mirror_busy(mb_f[n*2+:2]),.vmstat(vms_f[n*19+:19]),.ring_fault(rf_f[n*3+:3]));
    // die link: LINK relay flops (fixed latency, no flow control) from the peer's ring output
    if(LINK==0) begin:direct assign rin_f[n*2224+:2224]=rout_f[(1-n)*2224+:2224]; end
    else begin:relay
        reg [2223:0] r[0:LINK-1];
        always @(posedge clk) begin r[0]<=rout_f[(1-n)*2224+:2224]; for(integer i=1;i<LINK;i=i+1) r[i]<=r[i-1]; end
        assign rin_f[n*2224+:2224]=r[LINK-1];
    end
end
// ---- configuration
integer NCn[0:1], SIDn[0:1], RXP[0:1], TXD[0:1];
// ---- reservation tables (compiler calendar resources)
reg r_cq[0:1][0:2][0:T-1], r_ben[0:1][0:7][0:T-1], r_hr[0:1][0:T-1], r_tx[0:1][0:T-1], r_rep[0:1][0:T-1];
reg r_resp[0:1][0:2][0:T-1], r_slot[0:1][0:2][0:3][0:T-1];
// ---- per-cycle drive / expectation (ids are +1, 0 = none)
integer d_cq[0:1][0:2][0:T-1], d_ben[0:1][0:7][0:T-1], d_hr[0:1][0:T-1], d_tx[0:1][0:T-1], d_rep[0:1][0:T-1];
integer d_resp[0:1][0:2][0:T-1], d_eg[0:1][0:T-1];
integer e_pq[0:1][0:7][0:T-1], e_cr[0:1][0:2][0:T-1], e_xq[0:1][0:T-1];
integer ev_inc[0:1][0:T-1], ev_dec[0:1][0:T-1];
// ---- transaction records
localparam integer MX=4096;
integer t_kind[0:MX-1], t_n[0:MX-1], t_c[0:MX-1], t_k[0:MX-1], t_km[0:MX-1], t_bank[0:MX-1], t_row[0:MX-1];
reg t_we[0:MX-1], t_mir[0:MX-1]; reg [255:0] t_data[0:MX-1], t_rdata[0:MX-1]; reg [7:0] t_wm[0:MX-1]; reg [15:0] t_tag[0:MX-1];
integer a_txn[0:MX-1], a_node[0:MX-1], a_cl[0:MX-1], a_seq[0:MX-1]; integer na=0, nt=0, ng=0;
reg [2207:0] g_lanes[0:MX-1];
// ---- memories: reference shadow + behavioural bank env (index node,bank,mirror,row3)
reg [255:0] shadow[0:127], envm[0:127];
reg [265:0] env_pr[0:1][0:7][0:T-1]; reg [7:0] env_xd[0:1][0:1][0:T-1];
integer seed, checks=0, errors=0, n_pq=0, n_cr=0, n_xq=0, n_busy=0, cnt_kind[0:3], busy_cnt[0:1];
integer t, n, b, c, k, i, s, X, E, m, kind, tries, cursor, ok, ncl;
function automatic integer midx(input integer nn, input integer bb, input integer mir, input integer row);
    midx=nn*64+bb*8+mir*4+(row%4)+0; // rows 0..3 per (mirror) half
endfunction
function automatic [9:0] row10(input integer r); row10=10'(r*197+3); endfunction
function automatic [31:0] bm32(input [7:0] wm); for(integer w=0;w<8;w=w+1) bm32[w*4+:4]={4{wm[w]}}; endfunction
task automatic err(input string msg);
    begin errors=errors+1; if(errors<=12) $display("VMS_RING2 ERROR t=%0d %0s",t,msg); end
endtask
function automatic integer free1(input integer x); free1=(x>=0 && x<T-2); endfunction
// ---- scheduler
task automatic try_place(input integer kind, input integer nn, input integer cc, input integer bb, input integer s0, output integer placed);
    integer mm, kk, km, XX, EE, okk, u, lastn, lastm, ncn, ncm, f;
    begin
        placed=0; mm=1-nn; ncn=NCn[nn]; ncm=NCn[mm];
        XX=s0+9+LK+BL; EE=s0+3+LK; okk=1; kk=-1; km=-1;
        if(kind==0) begin // local
            lastn=s0+1+BL;
            if(!free1(lastn)) okk=0;
            if(okk) okk=!r_cq[nn][cc][s0] && !r_ben[nn][bb][s0] && !r_resp[nn][cc][lastn];
            for(integer q=0;q<4 && okk && kk<0;q=q+1) begin
                f=1; for(u=s0;u<=lastn;u=u+1) if(r_slot[nn][cc][q][u]) f=0; if(f) kk=q; end
            if(kk<0) okk=0;
            if(okk) begin
                r_cq[nn][cc][s0]=1; r_ben[nn][bb][s0]=1; r_resp[nn][cc][lastn]=1; for(u=s0;u<=lastn;u=u+1) r_slot[nn][cc][kk][u]=1;
                t_kind[nt]=0; t_n[nt]=nn; t_c[nt]=cc; t_k[nt]=kk; t_bank[nt]=bb;
                d_cq[nn][cc][s0]=nt+1; d_ben[nn][bb][s0]=cc+1; d_resp[nn][cc][lastn]=kk+1;
                a_txn[na]=nt; a_node[na]=nn; a_cl[na]=cc; a_seq[na]=kk; e_pq[nn][bb][s0+1]=na+1; na=na+1;
                e_cr[nn][cc][lastn+1]=nt+1; nt=nt+1; placed=1;
            end
        end else if(kind==1 || kind==2) begin // remote PREQ (1) / hub mirror write (2): n -> m -> n
            lastn=XX+8+LK;
            if(!free1(lastn)) okk=0;
            if(okk) okk=!r_cq[nn][cc][s0] && !r_hr[nn][s0] && !r_tx[nn][s0+2] && !r_rep[mm][s0+6+LK] && !r_cq[mm][ncm][s0+8+LK]
                       && !r_ben[mm][bb][s0+8+LK] && !r_resp[mm][ncm][XX] && !r_tx[mm][XX+4] && !r_resp[nn][cc][lastn]
                       && (kind==1 || !r_ben[nn][bb][s0]);
            for(integer q=0;q<4 && okk && kk<0;q=q+1) begin
                f=1; for(u=s0;u<=lastn;u=u+1) if(r_slot[nn][cc][q][u]) f=0; if(f) kk=q; end
            for(integer q=0;q<4 && okk && km<0;q=q+1) begin
                f=1; for(u=s0+8+LK;u<=XX;u=u+1) if(r_slot[mm][ncm][q][u]) f=0; if(f) km=q; end
            if(kk<0 || km<0) okk=0;
            if(okk) begin
                r_cq[nn][cc][s0]=1; r_hr[nn][s0]=1; r_tx[nn][s0+2]=1; r_rep[mm][s0+6+LK]=1; r_cq[mm][ncm][s0+8+LK]=1;
                r_ben[mm][bb][s0+8+LK]=1; r_resp[mm][ncm][XX]=1; r_tx[mm][XX+4]=1; r_resp[nn][cc][lastn]=1;
                for(u=s0;u<=lastn;u=u+1) r_slot[nn][cc][kk][u]=1; for(u=s0+8+LK;u<=XX;u=u+1) r_slot[mm][ncm][km][u]=1;
                t_kind[nt]=kind; t_n[nt]=nn; t_c[nt]=cc; t_k[nt]=kk; t_km[nt]=km; t_bank[nt]=bb;
                d_cq[nn][cc][s0]=nt+1; d_hr[nn][s0]=cc+1; d_tx[nn][s0+2]=1+1; d_rep[mm][s0+6+LK]=1;
                d_cq[mm][ncm][s0+8+LK]=nt+1; d_ben[mm][bb][s0+8+LK]=ncm+1; d_resp[mm][ncm][XX]=km+1; d_tx[mm][XX+4]=3+1;
                d_resp[nn][cc][lastn]=kk+1;
                a_txn[na]=nt; a_node[na]=mm; a_cl[na]=ncm; a_seq[na]=km; e_pq[mm][bb][s0+9+LK]=na+1; na=na+1;
                if(kind==2) begin
                    r_ben[nn][bb][s0]=1; d_ben[nn][bb][s0]=cc+1;
                    a_txn[na]=nt; a_node[na]=nn; a_cl[na]=cc; a_seq[na]=kk; e_pq[nn][bb][s0+1]=na+1; na=na+1;
                end
                e_cr[nn][cc][lastn+1]=nt+1; nt=nt+1; placed=1;
            end
        end else begin // bank mirror egress n -> m, commit, WACK m -> n
            lastn=EE+CD+6+LK;
            if(!free1(lastn)) okk=0;
            if(okk) okk=!r_tx[nn][s0] && !r_tx[mm][EE+CD+1];
            if(okk) begin
                r_tx[nn][s0]=1; r_tx[mm][EE+CD+1]=1;
                d_tx[nn][s0]=2+1; d_eg[nn][s0]=ng+1; d_tx[mm][EE+CD+1]=4+1;
                e_xq[mm][EE]=ng+1; ev_inc[nn][s0+1]=ev_inc[nn][s0+1]+1; ev_dec[nn][lastn]=ev_dec[nn][lastn]+1;
                ng=ng+1; placed=1;
            end
        end
    end
endtask
// ---- drive the calendar + env inputs for edge u
task automatic drive(input integer u);
    integer id, nn, bb, cc, kk;
    reg [31:0] addr;
    begin
        cq_f=0; cseq_f=0; ren_f=0; rseq_f=0; ben_f=0; bcl_f=0; hre_f=0; hrc_f=0; txe_f=0; txs_f=0; rep_f=0; eg_f=0; pr_f=0;
        xd0_f=0; xd1_f=0;
        for(nn=0;nn<2;nn=nn+1) begin
            for(cc=0;cc<=NCn[nn];cc=cc+1) begin
                id=d_cq[nn][cc][u];
                if(id!=0) begin
                    id=id-1;
                    if(cc<NCn[nn]) begin // local client request pins
                        addr={11'd0,t_mir[id],(t_mir[id]?2'd0:2'(t_kind[id]==1?SIDn[1-nn]:SIDn[nn])),row10(t_row[id]),3'(t_bank[id]),5'd0};
                        cq_f[nn*676+cc*338+:338]={1'b1,t_we[id],addr,t_data[id],bm32(t_wm[id]),t_tag[id]};
                        cseq_f[nn*6+cc*2+:2]=2'(t_k[id]);
                    end else cseq_f[nn*6+cc*2+:2]=2'(t_km[id]); // replay client: hq comes from the rcl
                end
                if(d_resp[nn][cc][u]!=0) begin ren_f[nn*3+cc]=1; rseq_f[nn*6+cc*2+:2]=2'(d_resp[nn][cc][u]-1); end
            end
            for(bb=0;bb<8;bb=bb+1) begin
                if(d_ben[nn][bb][u]!=0) begin ben_f[nn*8+bb]=1; bcl_f[nn*16+bb*2+:2]=2'(d_ben[nn][bb][u]-1); end
                pr_f[nn*2128+bb*266+:266]=env_pr[nn][bb][u];
                if(RXP[nn]==0) xd0_f[nn*8+bb]=env_xd[nn][0][u][bb]; else xd1_f[nn*8+bb]=env_xd[nn][1][u][bb];
            end
            if(d_hr[nn][u]!=0) begin hre_f[nn]=1; hrc_f[nn*2+:2]=2'(d_hr[nn][u]-1); end
            if(d_tx[nn][u]!=0) begin txe_f[nn]=1; txs_f[nn*3+:3]=3'(d_tx[nn][u]-1); end
            if(d_rep[nn][u]!=0) rep_f[nn]=1;
            if(d_eg[nn][u]!=0) eg_f[nn*2208+:2208]=g_lanes[d_eg[nn][u]-1];
        end
    end
endtask
reg [284:0] pexp, pgot; reg [273:0] cexp; reg [2207:0] xg; reg [255:0] mv; integer ai, ti, mi;
initial begin
    seed=SEED;
    NCn[0]=(SYM==0)?2:1; NCn[1]=(SYM==0)?0:1; SIDn[0]=2; SIDn[1]=3; RXP[0]=0; RXP[1]=1; TXD[0]=1; TXD[1]=0;
    for(i=0;i<4;i=i+1) cnt_kind[i]=0;
    for(n=0;n<2;n=n+1) for(t=0;t<T;t=t+1) begin
        r_hr[n][t]=0; r_tx[n][t]=0; r_rep[n][t]=0; d_hr[n][t]=0; d_tx[n][t]=0; d_rep[n][t]=0; d_eg[n][t]=0; e_xq[n][t]=0;
        ev_inc[n][t]=0; ev_dec[n][t]=0;
        for(c=0;c<3;c=c+1) begin r_cq[n][c][t]=0; r_resp[n][c][t]=0; d_cq[n][c][t]=0; d_resp[n][c][t]=0; e_cr[n][c][t]=0;
            for(k=0;k<4;k=k+1) r_slot[n][c][k][t]=0; end
        for(b=0;b<8;b=b+1) begin r_ben[n][b][t]=0; d_ben[n][b][t]=0; e_pq[n][b][t]=0; env_pr[n][b][t]=0; end
        env_xd[n][0][t]=0; env_xd[n][1][t]=0;
    end
    for(i=0;i<128;i=i+1) begin shadow[i]={8{32'(32'h5bd1e995*(i+1))}}; envm[i]=shadow[i]; end
    // ---- random compiler schedule
    cursor=20;
    for(i=0;i<NTX;i=i+1) begin
        kind=$unsigned($random(seed))%4;
        n=$unsigned($random(seed))%2;
        if(kind!=3 && NCn[n]==0) n=1-n;
        c=(NCn[n]>1)?$unsigned($random(seed))%NCn[n]:0;
        b=$unsigned($random(seed))%8;
        t_we[nt]=(kind==2)?1'b1:1'($random(seed)); t_mir[nt]=(kind==2)?1'b1:((kind==0)?($unsigned($random(seed))%3==0 && !t_we[nt]):1'b0);
        t_row[nt]=$unsigned($random(seed))%4; t_data[nt]={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
        t_wm[nt]=8'($random(seed)); if(t_wm[nt]==0) t_wm[nt]=8'h81; t_tag[nt]=16'($random(seed)); t_rdata[nt]=0;
        if(kind==3) begin
            g_lanes[ng]=0;
            for(integer l=0;l<8;l=l+1) if($unsigned($random(seed))%3!=0 || l==b)
                g_lanes[ng][l*276+:276]={1'b1,11'($random(seed)),{$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)},8'($random(seed))};
        end
        s=cursor+$unsigned($random(seed))%3; ok=0;
        for(tries=0;tries<4000 && !ok;tries=tries+1) begin try_place(kind,n,c,b,s,ok); if(!ok) s=s+1; end
        if(!ok) begin $display("VMS_RING2 FAIL scheduler could not place txn %0d",i); $finish; end
        cnt_kind[kind]=cnt_kind[kind]+1;
        cursor=cursor+$unsigned($random(seed))%3;
    end
    // ---- run
    busy_cnt[0]=0; busy_cnt[1]=0;
    repeat(3) @(negedge clk); rst_n=1;
    for(t=0;t<T-1;t=t+1) begin
        @(negedge clk); drive(t);
        @(posedge clk); #1;
        for(n=0;n<2;n=n+1) begin
            // faults / status
            checks=checks+1; if(rf_f[n*3+:3]!==0 || hst_f[n*3+:3]!==0 || vms_f[n*19+16+:3]!==0) err($sformatf("node%0d fault ring%b hub%b vmstat%b",n,rf_f[n*3+:3],hst_f[n*3+:3],vms_f[n*19+16+:3]));
            // bank requests (+ reference shadow / env memory at the access edge)
            for(b=0;b<8;b=b+1) begin
                pgot=pq_f[n*2280+b*285+:285];
                ai=e_pq[n][b][t];
                checks=checks+1;
                if(ai==0) begin if(pgot[284]!==1'b0) err($sformatf("node%0d bank%0d unexpected pq",n,b)); end
                else begin
                    ai=ai-1; ti=a_txn[ai];
                    pexp={1'b1,t_we[ti],t_mir[ti],row10(t_row[ti]),t_data[ti],t_wm[ti],4'(a_cl[ai]),2'b00,2'(a_seq[ai])};
                    if(pgot!==pexp) err($sformatf("node%0d bank%0d pq mismatch txn%0d",n,b,ti)); else n_pq=n_pq+1;
                    mi=midx(n,b,t_mir[ti],t_row[ti]);
                    if(!t_we[ti]) t_rdata[ti]=shadow[mi];
                    else for(integer w=0;w<8;w=w+1) if(t_wm[ti][w]) shadow[mi][w*32+:32]=t_data[ti][w*32+:32];
                end
                // behavioural bank env (acts on the DUT's pq)
                if(pgot[284]===1'b1) begin
                    mi=midx(n,b,pgot[282],(pgot[281:272]-3)/197);
                    mv=envm[mi];
                    if(pgot[283]) for(integer w=0;w<8;w=w+1) if(pgot[8+w]) envm[mi][w*32+:32]=pgot[16+w*32+:32];
                    if(t+BL<T) env_pr[n][b][t+BL]={1'b1,pgot[283],pgot[7:0],pgot[283]?256'd0:mv};
                end
            end
            // client responses
            for(c=0;c<NCn[n];c=c+1) begin
                ti=e_cr[n][c][t]; checks=checks+1;
                if(ti==0) begin if(cr_f[n*548+c*274+273]!==1'b0) err($sformatf("node%0d client%0d unexpected cr",n,c)); end
                else begin
                    ti=ti-1; cexp={1'b1,t_tag[ti],t_we[ti],t_we[ti]?256'd0:t_rdata[ti]};
                    if(cr_f[n*548+c*274+:274]!==cexp) err($sformatf("node%0d client%0d cr mismatch txn%0d kind%0d",n,c,ti,t_kind[ti])); else n_cr=n_cr+1;
                end
            end
            // remote bank writes: RX port carries exactly the scheduled mirror egress; TX port idle
            xg=(RXP[n]==0)?xq0_f[n*2208+:2208]:xq1_f[n*2208+:2208]; checks=checks+2;
            if(e_xq[n][t]==0) begin if(xg!==0) err($sformatf("node%0d unexpected xq",n)); end
            else if(xg!==g_lanes[e_xq[n][t]-1]) err($sformatf("node%0d xq mismatch egress%0d",n,e_xq[n][t]-1)); else n_xq=n_xq+1;
            if(((RXP[n]==0)?xq1_f[n*2208+:2208]:xq0_f[n*2208+:2208])!==0) err($sformatf("node%0d TX-port xq not idle",n));
            for(b=0;b<8;b=b+1) if(xg[b*276+275]===1'b1 && t+CD<T) env_xd[n][RXP[n]][t+CD][b]=1'b1;
            // mirror_busy: TX stop counts its outstanding egress (WACK observation); RX stop never busy
            checks=checks+1;
            if(mb_f[n*2+TXD[n]]!==(busy_cnt[n]!=0) || mb_f[n*2+1-TXD[n]]!==1'b0)
                err($sformatf("node%0d mirror_busy %b expected %0d",n,mb_f[n*2+:2],busy_cnt[n]!=0));
        end
        for(n=0;n<2;n=n+1) begin if(busy_cnt[n]!=0) n_busy=n_busy+1; busy_cnt[n]=busy_cnt[n]+ev_inc[n][t]-ev_dec[n][t]; end
    end
    if(errors==0 && (cnt_kind[3]==0 || (cnt_kind[1]+cnt_kind[2])==0)) begin $display("VMS_RING2 FAIL coverage"); errors=1; end
    if(errors==0 && (n_pq!=na || n_cr!=nt || n_xq!=ng)) begin $display("VMS_RING2 FAIL matched events pq%0d/%0d cr%0d/%0d xq%0d/%0d",n_pq,na,n_cr,nt,n_xq,ng); errors=1; end
    if(errors==0) $display("VMS_RING2 PASS SYM=%0d LINK=%0d checks=%0d errors=0 txns local=%0d preq=%0d hubmirror=%0d egress=%0d matched pq=%0d cr=%0d xq=%0d busy_cycles=%0d",
        SYM,LINK,checks,cnt_kind[0],cnt_kind[1],cnt_kind[2],cnt_kind[3],n_pq,n_cr,n_xq,n_busy);
    else $display("VMS_RING2 FAIL SYM=%0d LINK=%0d checks=%0d errors=%0d",SYM,LINK,checks,errors);
    $finish;
end
endmodule
`default_nettype wire
