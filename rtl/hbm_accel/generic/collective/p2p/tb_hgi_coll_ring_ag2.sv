`timescale 1ns/1ps
`default_nettype none
// HBM-B-RTL3c: x all-gather over TWO cross-quadrant rings (coordinator 0dr). Per quadrant: ring A =
// ot_hgi_coll_ring_ag (full COLL stop) + ring B = ot_hgi_coll_ring_ag_lane (gather-only stop), 2x2 ring
// q0->q1->q3->q2->q0 on both. +RINGS=1: every flit on ring A (= the one-ring RTL3 schedule, ring B idle).
// +RINGS=2: flit i on ring i%2, each ring scheduled by the RTL3 production rule (MODE 0: one direction a
// flit, alternating, ttl 3; greedy earliest legal edge, every directed link edge collision-checked).
// Every stop must publish each of the other 3F flits exactly once, bit-exact with source and tag, at the
// compiled edge, on the compiled ring; no fault. +fault=N (ring B): 1 missing arrival, 2 inject ttl 0,
// 3 missing transit -> must fault. Lane mutants (MUT_TTL / MUT_SRC on ring B) must FAIL.
module tb_hgi_coll_ring_ag2;
    // BLK=1 (HBM-RTL4): ring B is the die block ot_hgi_coll_ring_b_stop (reset relay + 1-edge command pin register):
    // its commands are driven one edge earlier (BLK_LEAD) and the timeline starts IDLE edges after reset release.
    // BLK_PIPE=0 with BLK=1 is the block mutant (commands early, no pin register) and must FAIL.
    parameter integer MUT_TTL=0,MUT_SRC=0,BLK=0,BLK_PIPE=1;
    localparam integer BLK_LEAD=BLK?1:0,IDLE=BLK?6:0;
    localparam integer NC=1400,READ_LEAD=2;
    reg clk=0,rst_n=0;always #0.5 clk=~clk;
    typedef struct packed {
        bit lp_we;bit[2:0] lp_tag;bit[255:0] lp_data;
        bit read_tx;bit[2:0] read_tx_tag;
        bit[1:0] inject,fwd;bit[2:0] tx_tag;bit[3:0] ttl;
        bit[1:0] rx;bit[3:0] kind,src;bit[5:0] tag;
    } slot_t;
    slot_t prog[0:1][0:3][0:NC-1],cmd[0:1][0:3];
    bit ex_v[0:1][0:3][0:1][0:NC-1];bit[1:0] ex_src[0:1][0:3][0:1][0:NC-1];bit[2:0] ex_tag[0:1][0:3][0:1][0:NC-1];
    bit[255:0] ex_d[0:1][0:3][0:1][0:NC-1];
    bit outb[0:1][0:3][0:1][0:NC-1];
    wire [279:0] co[0:1][0:3],no[0:1][0:3];
    wire [3:0] fault[0:1];wire [1:0] ag_v[0:1][0:3];wire [3:0] ag_src[0:1][0:3];wire [5:0] ag_tag[0:1][0:3];wire [511:0] ag_d[0:1][0:3];
    function automatic integer nextq(input integer q);case(q)0:nextq=1;1:nextq=3;3:nextq=2;default:nextq=0;endcase endfunction
    function automatic integer prevq(input integer q);case(q)0:prevq=2;1:prevq=0;3:prevq=1;default:prevq=3;endcase endfunction
    for(genvar q=0;q<4;q=q+1)begin:g_q
        wire rr_v;wire [2:0] rr_tag;wire [255:0] rr_d;
        ot_hgi_coll_ring_ag #(.SPLIT_CLOCKS(1),.AG(1)) ra(
            .clk(clk),.rst_n(rst_n),.clk_ctl(clk),.clk_state({8{clk}}),.clk_add({8{clk}}),.qid(2'(q)),
            .cw_i(co[0][prevq(q)]),.ccw_i(no[0][nextq(q)]),.cw_o(co[0][q]),.ccw_o(no[0][q]),
            .lp_we(cmd[0][q].lp_we),.lp_tag(cmd[0][q].lp_tag),.lp_data(cmd[0][q].lp_data),
            .state_read_add(1'b0),.state_read_tx(cmd[0][q].read_tx),.state_read_rr(1'b0),
            .state_add_tag(3'd0),.state_add_src(2'd0),.state_add_rhs_acc(1'b0),
            .state_tx_tag(cmd[0][q].read_tx_tag),.state_tx_acc(1'b0),.state_rr_tag(3'd0),
            .add_v(1'b0),.add_tag(3'd0),.add_src(2'd0),.add_rhs_acc(1'b0),
            .tx_inject(cmd[0][q].inject),.tx_forward(cmd[0][q].fwd),.tx_tag(cmd[0][q].tx_tag),.tx_dst(2'(q)),
            .tx_result(1'b0),.tx_acc(1'b0),.tx_gather(|cmd[0][q].inject),.tx_ttl(cmd[0][q].ttl),
            .rx_slot(cmd[0][q].rx),.rx_kind(cmd[0][q].kind),.rx_src(cmd[0][q].src),.rx_tag(cmd[0][q].tag),
            .rr_local(1'b0),.rr_local_tag(3'd0),.rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),
            .ag_v(ag_v[0][q]),.ag_src(ag_src[0][q]),.ag_tag(ag_tag[0][q]),.ag_d(ag_d[0][q]),.fault(fault[0][q]));
        if(BLK)begin:g_blk
        ot_hgi_coll_ring_b_stop #(.MUT_TTL(MUT_TTL),.MUT_SRC(MUT_SRC),.CMD_PIPE(BLK_PIPE)) rb(
            .clk(clk),.rst_n(rst_n),.qid(2'(q)),
            .cw_i(co[1][prevq(q)]),.ccw_i(no[1][nextq(q)]),.cw_o(co[1][q]),.ccw_o(no[1][q]),
            .lp_we(cmd[1][q].lp_we),.lp_tag(cmd[1][q].lp_tag),.lp_data(cmd[1][q].lp_data),
            .state_read_tx(cmd[1][q].read_tx),.state_tx_tag(cmd[1][q].read_tx_tag),
            .tx_inject(cmd[1][q].inject),.tx_forward(cmd[1][q].fwd),.tx_tag(cmd[1][q].tx_tag),.tx_ttl(cmd[1][q].ttl),
            .rx_slot(cmd[1][q].rx),.rx_kind(cmd[1][q].kind),.rx_src(cmd[1][q].src),.rx_tag(cmd[1][q].tag),
            .ag_v(ag_v[1][q]),.ag_src(ag_src[1][q]),.ag_tag(ag_tag[1][q]),.ag_d(ag_d[1][q]),.fault(fault[1][q]));
        end else begin:g_lane
        ot_hgi_coll_ring_ag_lane #(.MUT_TTL(MUT_TTL),.MUT_SRC(MUT_SRC)) rb(
            .clk(clk),.rst_n(rst_n),.qid(2'(q)),
            .cw_i(co[1][prevq(q)]),.ccw_i(no[1][nextq(q)]),.cw_o(co[1][q]),.ccw_o(no[1][q]),
            .lp_we(cmd[1][q].lp_we),.lp_tag(cmd[1][q].lp_tag),.lp_data(cmd[1][q].lp_data),
            .state_read_tx(cmd[1][q].read_tx),.state_tx_tag(cmd[1][q].read_tx_tag),
            .tx_inject(cmd[1][q].inject),.tx_forward(cmd[1][q].fwd),.tx_tag(cmd[1][q].tx_tag),.tx_ttl(cmd[1][q].ttl),
            .rx_slot(cmd[1][q].rx),.rx_kind(cmd[1][q].kind),.rx_src(cmd[1][q].src),.rx_tag(cmd[1][q].tag),
            .ag_v(ag_v[1][q]),.ag_src(ag_src[1][q]),.ag_tag(ag_tag[1][q]),.ag_d(ag_d[1][q]),.fault(fault[1][q]));
        end
    end
    function automatic [255:0] payload(input integer q,input integer i);
        reg [255:0] v;
        for(integer l=0;l<8;l=l+1)v[l*32+:32]=32'h3c000000^(32'(q)*32'h9e3779b9)^(32'(i)*32'h85ebca6b)^(32'(l)*32'hc2b2ae35);
        return v;
    endfunction
    integer F=224,RINGS=2,scenario=0,last_cycle=0,checked=0,errors=0,first_inj=-1;bit saw_fault=0;
    integer last_inj[0:1][0:3][0:7],last_w[0:1][0:3],last_c[0:1][0:3],nb[0:1];
    integer b1_q=-1,b1_t,b1_d,bi_q=-1,bi_t;   // ring-B fault targets: first transit hop / an injection
    task automatic route(input integer r,input integer q,input integer d,input integer hops,input integer c,input integer i,input integer k);
        integer s,t;s=q;t=c;
        if(outb[r][q][d][c])$fatal(1,"compiler injection collision");
        outb[r][q][d][c]=1;prog[r][q][c].inject[d]=1;prog[r][q][c].ttl[d*2+:2]=2'(hops);
        if(r==1 && k==5 && q==2)begin bi_q=q;bi_t=c;end
        for(integer h=1;h<=hops;h=h+1)begin
            s=d?prevq(s):nextq(s);t=t+2;
            if(prog[r][s][t].rx[d])$fatal(1,"compiler receive collision");
            prog[r][s][t].rx[d]=1;prog[r][s][t].kind[d*2+:2]=3;prog[r][s][t].src[d*2+:2]=2'(q);prog[r][s][t].tag[d*3+:3]=3'(k%8);
            if(ex_v[r][s][d][t])$fatal(1,"compiler publish collision");
            ex_v[r][s][d][t]=1;ex_src[r][s][d][t]=2'(q);ex_tag[r][s][d][t]=3'(k%8);ex_d[r][s][d][t]=payload(q,i);
            if(r==1 && q==0 && k==4 && h==1)begin b1_q=s;b1_t=t;b1_d=d;end
            if(h<hops)begin
                if(outb[r][s][d][t])$fatal(1,"compiler forwarding collision");
                outb[r][s][d][t]=1;prog[r][s][t].fwd[d]=1;
            end
        end
    endtask
    function automatic bit free(input integer r,input integer q,input integer dl,input integer c);
        integer n,n2;n=dl?prevq(q):nextq(q);n2=dl?prevq(n):nextq(n);
        return !outb[r][q][dl][c] && !outb[r][n][dl][c+2] && !outb[r][n2][dl][c+4];
    endfunction
    initial begin
        if($value$plusargs("fault=%d",scenario))begin end
        if($value$plusargs("F=%d",F))begin end
        if($value$plusargs("RINGS=%d",RINGS))begin end
        if(RINGS<1 || RINGS>2)$fatal(1,"RINGS must be 1 or 2");
        if(scenario!=0 && RINGS!=2)$fatal(1,"fault traces are ring-B traces: RINGS=2");
        for(integer r=0;r<2;r=r+1)for(integer q=0;q<4;q=q+1)begin
            cmd[r][q]='0;last_w[r][q]=-1;last_c[r][q]=0;
            for(integer t=0;t<8;t=t+1)last_inj[r][q][t]=-1;
            for(integer c=0;c<NC;c=c+1)begin prog[r][q][c]='0;for(integer d=0;d<2;d=d+1)begin ex_v[r][q][d][c]=0;outb[r][q][d][c]=0;end end
        end
        nb[0]=0;nb[1]=0;
        // Compiler: flit i -> ring i%RINGS, k = its index on that ring; per ring the RTL3 MODE-0 rule.
        for(integer i=0;i<F;i=i+1)begin
            integer r,k;r=i%RINGS;k=nb[r];nb[r]=nb[r]+1;
            for(integer q=0;q<4;q=q+1)begin
                integer w,c,dl,tg;
                tg=k%8;dl=k%2;
                w=last_inj[r][q][tg]+1;if(w<=last_w[r][q])w=last_w[r][q]+1;
                c=w+3;if(c<=last_c[r][q])c=last_c[r][q]+1;
                while(!free(r,q,dl,c))c=c+1;
                if(c+6>=NC)$fatal(1,"timeline too long");
                prog[r][q][w].lp_we=1;prog[r][q][w].lp_tag=3'(tg);prog[r][q][w].lp_data=payload(q,i);
                if(prog[r][q][c-READ_LEAD].read_tx)$fatal(1,"compiler read collision");
                prog[r][q][c-READ_LEAD].read_tx=1;prog[r][q][c-READ_LEAD].read_tx_tag=3'(tg);
                prog[r][q][c].tx_tag=3'(tg);
                route(r,q,dl,3,c,i,k);
                last_w[r][q]=w;last_c[r][q]=c;last_inj[r][q][tg]=c;
                if(first_inj<0 || c<first_inj)first_inj=c;
                if(c+6>last_cycle)last_cycle=c+6;
            end
        end
        case(scenario)
            1:prog[1][b1_q][b1_t].rx[b1_d]=0;            // ring B: missing arrival reservation
            2:prog[1][bi_q][bi_t].ttl=0;                 // ring B: inject with ttl 0
            3:prog[1][b1_q][b1_t].fwd[b1_d]=0;           // ring B: missing transit (ttl > 1)
            default:begin end
        endcase
        repeat(5)@(negedge clk);rst_n=1;
        repeat(IDLE)@(negedge clk);
        for(integer c=-BLK_LEAD;c<=last_cycle;c=c+1)begin
            for(integer r=0;r<2;r=r+1)for(integer q=0;q<4;q=q+1)begin
                integer cc;cc=(r==1)?c+BLK_LEAD:c;
                cmd[r][q]=(cc>=0 && cc<NC)?prog[r][q][cc]:'0;
            end
            @(posedge clk);#0.01;
            if(c<0)begin @(negedge clk);continue;end
            if(|fault[0] || |fault[1])saw_fault=1;
            if(scenario==0)begin
                if(|fault[0] || |fault[1])begin if(errors<10)$display("RING_AG2 unexpected fault cycle%0d A%h B%h",c,fault[0],fault[1]);errors=errors+1;end
                for(integer r=0;r<2;r=r+1)for(integer q=0;q<4;q=q+1)for(integer d=0;d<2;d=d+1)begin
                    if(ag_v[r][q][d]!==ex_v[r][q][d][c])begin
                        if(errors<10)$display("RING_AG2 publish r%0d q%0d d%0d cyc%0d got%0d exp%0d",r,q,d,c,ag_v[r][q][d],ex_v[r][q][d][c]);errors=errors+1;
                    end else if(ag_v[r][q][d])begin
                        if(ag_src[r][q][d*2+:2]!==ex_src[r][q][d][c] || ag_tag[r][q][d*3+:3]!==ex_tag[r][q][d][c] || ag_d[r][q][d*256+:256]!==ex_d[r][q][d][c])begin
                            if(errors<10)$display("RING_AG2 data r%0d q%0d d%0d cyc%0d src%0d/%0d tag%0d/%0d",r,q,d,c,ag_src[r][q][d*2+:2],ex_src[r][q][d][c],ag_tag[r][q][d*3+:3],ex_tag[r][q][d][c]);
                            errors=errors+1;
                        end else checked=checked+1;
                    end
                end
            end
            @(negedge clk);
        end
        if(scenario!=0)begin
            if(!saw_fault)$fatal(1,"RING_AG2 reservation mutant escaped %0d",scenario);
            $display("RING_AG2 FAULT PASS scenario=%0d timeline=%0d",scenario,last_cycle);
        end else if(errors!=0 || checked!=4*3*F)begin
            $display("RING_AG2 FAIL errors=%0d checked=%0d expected=%0d",errors,checked,4*3*F);
        end else begin
            $display("RING_AG2 PASS rings=%0d quadrants=4 flits_per_quadrant=%0d published=%0d gather_edges=%0d ringA_flits=%0d ringB_flits=%0d",
                RINGS,F,checked,last_cycle-first_inj,nb[0],nb[1]);
        end
        $finish;
    end
endmodule
`default_nettype wire
