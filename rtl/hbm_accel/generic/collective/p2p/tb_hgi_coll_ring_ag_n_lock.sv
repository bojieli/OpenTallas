`timescale 1ns/1ps
`default_nettype none
// ELEM-GAPS/HBMN1 (10-18): lockstep of the NATIVE stop ot_hgi_coll_ring_ag_n against the v1 stop ot_hgi_coll_ring_ag
// (closed ctl + the same CLOSED lanes) on dense random traffic over EVERY port (adds, results, rr, carries, gathers).
// v1 gets the command stream X(t); native gets X(t+1) on the lead-1 ports, X(t+2) on the tx-read group, and the same
// lp_data(t) and ring words cw_i/ccw_i(t). Every functional output (cw_o, ccw_o, rr_v/tag/d, ag_v/src/tag/d) must be
// equal at every edge; fault_native(t) == fault_v1(t-1). The only stimulus constraint is the native legality rule:
// no lp write (local) / acc write (acc) of the tx tag at the lane read edge (inject-3).
// r5: the rr-read group (state_read_rr, state_rr_tag) also gets X(t+2) (lead 2); legality: no acc write of the rr tag at
// the lane read edge (rr_local-3).  +rr=1: a DIRECTED legal reduce program (lp write, kind-1 carry arrival, add read, add,
// rr read, rr_local per tag, overlapped) -- neither stop may fault and every rr publish must match;  +rr=2: the same with
// one rr read at the earliest v1-legal edge (acc write at the native lane read edge) -- v1 must not fault, native MUST fault.
module tb_hgi_coll_ring_ag_n_lock;
    parameter integer MUT_TXLEAD=0,MUT_CW=0,MUT_HZ=0,MUT_RRLEAD=0,LAT=8;
    localparam integer N=6000;
    reg clk=0;always #0.5 clk=~clk;
    reg rst_n=0;reg [2:0] rsh=0;
    always @(posedge clk or negedge rst_n) if(!rst_n)rsh<=0;else rsh<={rsh[1:0],1'b1};
    wire rst_v1=rsh[2];           // = the native relay release (2 sync + 1 tree)
    typedef struct packed {
        bit lp_we;bit[2:0] lp_tag;
        bit rd_add,rd_tx,rd_rr;bit[2:0] sat,stt,srt;bit[1:0] sas;bit sar,sta;
        bit add_v;bit[2:0] add_tag;bit[1:0] add_src;bit add_rhs;
        bit[1:0] inj,fwd;bit[2:0] txt;bit[1:0] dst;bit res,txa,gath;bit[3:0] ttl;
        bit[1:0] rx;bit[3:0] kind,src;bit[5:0] rxt;
        bit rrl;bit[2:0] rrlt;
    } c_t;
    c_t X[0:N+3];
    bit [255:0] LPD[0:N+3];bit [279:0] CW[0:N+3],CCW[0:N+3];
    c_t a,b,r;bit [255:0] lpd;bit [279:0] cwi,ccwi;
    wire [279:0] co1,cc1,co2,cc2;wire rv1,rv2;wire [2:0] rt1,rt2;wire [255:0] rd1,rd2;
    wire [1:0] av1,av2;wire [3:0] as1,as2;wire [5:0] at1,at2;wire [511:0] ad1,ad2;wire f1,f2;
    ot_hgi_coll_ring_ag #(.LAT(LAT)) u1(.clk(clk),.rst_n(rst_v1),.clk_ctl(clk),.clk_state({8{clk}}),.clk_add({8{clk}}),.qid(2'd1),
        .cw_i(cwi),.ccw_i(ccwi),.cw_o(co1),.ccw_o(cc1),.lp_we(a.lp_we),.lp_tag(a.lp_tag),.lp_data(lpd),
        .state_read_add(a.rd_add),.state_read_tx(a.rd_tx),.state_read_rr(a.rd_rr),.state_add_tag(a.sat),.state_tx_tag(a.stt),
        .state_rr_tag(a.srt),.state_add_src(a.sas),.state_add_rhs_acc(a.sar),.state_tx_acc(a.sta),
        .add_v(a.add_v),.add_tag(a.add_tag),.add_src(a.add_src),.add_rhs_acc(a.add_rhs),
        .tx_inject(a.inj),.tx_forward(a.fwd),.tx_tag(a.txt),.tx_dst(a.dst),.tx_result(a.res),.tx_acc(a.txa),.tx_gather(a.gath),.tx_ttl(a.ttl),
        .rx_slot(a.rx),.rx_kind(a.kind),.rx_src(a.src),.rx_tag(a.rxt),.rr_local(a.rrl),.rr_local_tag(a.rrlt),
        .rr_v(rv1),.rr_tag(rt1),.rr_d(rd1),.ag_v(av1),.ag_src(as1),.ag_tag(at1),.ag_d(ad1),.fault(f1));
    ot_hgi_coll_ring_ag_n #(.LAT(LAT),.MUT_TXLEAD(MUT_TXLEAD),.MUT_CW(MUT_CW),.MUT_HZ(MUT_HZ),.MUT_RRLEAD(MUT_RRLEAD)) u2(.clk(clk),.rst_n(rst_n),.clk_ctl(clk),.clk_state({8{clk}}),.clk_add({8{clk}}),.qid(2'd1),
        .cw_i(cwi),.ccw_i(ccwi),.cw_o(co2),.ccw_o(cc2),.lp_we(b.lp_we),.lp_tag(b.lp_tag),.lp_data(lpd),
        .state_read_add(b.rd_add),.state_read_tx(r.rd_tx),.state_read_rr(r.rd_rr),.state_add_tag(b.sat),.state_tx_tag(r.stt),
        .state_rr_tag(r.srt),.state_add_src(b.sas),.state_add_rhs_acc(b.sar),.state_tx_acc(r.sta),
        .add_v(b.add_v),.add_tag(b.add_tag),.add_src(b.add_src),.add_rhs_acc(b.add_rhs),
        .tx_inject(b.inj),.tx_forward(b.fwd),.tx_tag(b.txt),.tx_dst(b.dst),.tx_result(b.res),.tx_acc(b.txa),.tx_gather(b.gath),.tx_ttl(b.ttl),
        .rx_slot(b.rx),.rx_kind(b.kind),.rx_src(b.src),.rx_tag(b.rxt),.rr_local(b.rrl),.rr_local_tag(b.rrlt),
        .rr_v(rv2),.rr_tag(rt2),.rr_d(rd2),.ag_v(av2),.ag_src(as2),.ag_tag(at2),.ag_d(ad2),.fault(f2));
    function automatic bit [279:0] rword(input integer seed);
        bit [279:0] w;
        for(integer k=0;k<9;k=k+1)w[k*32+:32]=$urandom;
        w[279]=($urandom%4)!=0;w[278:277]=2'($urandom%4);w[274:273]=($urandom%2)?2'd1:2'($urandom%4);
        w[267:256]=($urandom%8)==0?12'h1:12'h0;
        return w;
    endfunction
    integer errs=0,cmp=0,fault_cmp=0,seed=1,first_f1=-1,rrm=0,nrr=0,nrr_exp=0,first_f2=-1;bit f1_prev=0;
    initial begin
        if($value$plusargs("seed=%d",seed))begin end
        if($value$plusargs("rr=%d",rrm))begin end
        void'($urandom(seed));
        for(integer t=0;t<N+4;t=t+1)begin
            c_t c;c='0;
            c.lp_we=($urandom%3)==0;c.lp_tag=3'($urandom);
            c.rd_add=($urandom%3)==0;c.rd_tx=($urandom%3)==0;c.rd_rr=($urandom%3)==0;
            c.sat=3'($urandom);c.stt=3'($urandom);c.srt=3'($urandom);c.sas=2'($urandom);c.sar=1'($urandom);c.sta=1'($urandom);
            c.add_v=($urandom%3)==0;c.add_tag=3'($urandom);c.add_src=2'($urandom);c.add_rhs=1'($urandom);
            c.inj=2'($urandom);c.fwd=2'($urandom);c.txt=3'($urandom);c.dst=2'($urandom);c.res=($urandom%4)==0;c.txa=1'($urandom);
            c.gath=1'($urandom);c.ttl=4'($urandom);
            c.rx=2'($urandom);c.kind=4'($urandom);c.src=4'($urandom);c.rxt=6'($urandom);
            c.rrl=($urandom%3)==0;c.rrlt=3'($urandom);
            X[t]=c;LPD[t]={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
            CW[t]=rword(t);CCW[t]=rword(t+7);
        end
        // native legality: no write of the tx tag at the lane read edge (v1 frame: read at t -> lane reads at t-1)
        for(integer t=1;t<N+4;t=t+1)if(X[t].rd_tx)begin
            if(!X[t].sta && X[t-1].lp_we && X[t-1].lp_tag==X[t].stt)X[t-1].lp_tag=X[t].stt+3'd1;
            if(X[t].sta && t-1-LAT>=0 && X[t-1-LAT].add_v && X[t-1-LAT].add_tag==X[t].stt)X[t-1-LAT].add_v=0;
        end
        // the add-tag fix may only clear writes; re-check the local fix did not create a new collision for a later read
        for(integer t=1;t<N+4;t=t+1)if(X[t].rd_tx && !X[t].sta && X[t-1].lp_we && X[t-1].lp_tag==X[t].stt)X[t-1].lp_we=0;
        // r5 native legality for the rr-read group: no acc write of the rr tag at the lane read edge
        for(integer t=1;t<N+4;t=t+1)if(X[t].rd_rr && t-1-LAT>=0 && X[t-1-LAT].add_v && X[t-1-LAT].add_tag==X[t].srt)X[t-1-LAT].add_v=0;
        if(rrm!=0)begin   // directed legal reduce program (replaces the random stream)
            for(integer t=0;t<N+4;t=t+1)begin X[t]='0;CW[t]=0;CCW[t]=0;end
            for(integer j=0;10*j+40<N;j=j+1)begin
                integer T,k,t3;T=10+10*j;k=j%8;
                X[T].lp_we=1;X[T].lp_tag=3'(k);                                        // local operand (LPD[T])
                CW[T]={1'b1,2'd1,2'd0,2'd1,2'd0,3'(k),1'b0,11'b0,
                       {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}};
                X[T+1].rx[0]=1;X[T+1].kind[1:0]=2'd1;X[T+1].src[1:0]=2'd0;X[T+1].rxt[2:0]=3'(k);   // carry for qid 1
                X[T+3].rd_add=1;X[T+3].sat=3'(k);X[T+3].sas=2'd0;X[T+3].sar=0;
                X[T+5].add_v=1;X[T+5].add_tag=3'(k);X[T+5].add_src=2'd0;X[T+5].add_rhs=0;  // acc write at T+5+LAT
                t3=T+5+LAT+2;if(rrm==2 && j==3)t3=T+5+LAT+1;   // +rr=2: earliest v1-legal read (native hazard)
                X[t3].rd_rr=1;X[t3].srt=3'(k);
                X[t3+2].rrl=1;X[t3+2].rrlt=3'(k);
                nrr_exp=nrr_exp+1;
            end
        end
        a='0;b='0;r='0;lpd=0;cwi=0;ccwi=0;
        repeat(4)@(negedge clk);rst_n=1;
        repeat(4)@(negedge clk);   // v1 release (rsh[2]) and the native relay rise together, then idle
        for(integer t=-2;t<N;t=t+1)begin
            a=(t>=0)?X[t]:'0;b=(t+1>=0)?X[t+1]:'0;r=X[t+2];lpd=(t>=0)?LPD[t]:0;cwi=(t>=0)?CW[t]:0;ccwi=(t>=0)?CCW[t]:0;
            @(posedge clk);#0.01;
            if(t<0)begin f1_prev=f1;@(negedge clk);continue;end
            if(f1 && first_f1<0)first_f1=t;
            if(f2 && first_f2<0)first_f2=t;
            if(rv1)nrr=nrr+1;
            if(rrm==2)begin f1_prev=f1;@(negedge clk);continue;end
            if({co1,cc1}!=={co2,cc2} || rv1!==rv2 || (rv1 && (rt1!==rt2 || rd1!==rd2)) || av1!==av2 ||
               (av1[0] && (as1[1:0]!==as2[1:0] || at1[2:0]!==at2[2:0] || ad1[255:0]!==ad2[255:0])) ||
               (av1[1] && (as1[3:2]!==as2[3:2] || at1[5:3]!==at2[5:3] || ad1[511:256]!==ad2[511:256])))begin
                if(errs<8)$display("RING_AG_N LOCK mismatch t=%0d cw %0d ccw %0d rr %0d/%0d ag %b/%b",t,co1!==co2,cc1!==cc2,rv1,rv2,av1,av2);
                errs=errs+1;
            end else cmp=cmp+1;
            if(t>0)begin if(f2!==f1_prev)begin if(errs<8)$display("RING_AG_N LOCK fault t=%0d v1(t-1)=%0d native=%0d",t,f1_prev,f2);errs=errs+1;end else fault_cmp=fault_cmp+1;end
            f1_prev=f1;
            @(negedge clk);
        end
        if(rrm==1)begin
            if(errs==0 && first_f1<0 && first_f2<0 && nrr==nrr_exp)$display("RING_AG_N RR PASS rr_publishes=%0d edges=%0d",nrr,cmp);
            else $display("RING_AG_N RR FAIL errors=%0d v1_fault=%0d native_fault=%0d rr=%0d/%0d",errs,first_f1,first_f2,nrr,nrr_exp);
        end else if(rrm==2)begin
            if(first_f1<0 && first_f2>=0)$display("RING_AG_N RR HZ PASS native_fault_edge=%0d",first_f2);
            else $display("RING_AG_N RR HZ FAIL v1_fault=%0d native_fault=%0d",first_f1,first_f2);
        end else if(errs==0)$display("RING_AG_N LOCK PASS seed=%0d edges=%0d fault_edges=%0d v1_first_fault=%0d",seed,cmp,fault_cmp,first_f1);
        else $display("RING_AG_N LOCK FAIL seed=%0d errors=%0d",seed,errs);
        $finish;
    end
endmodule
`default_nettype wire
