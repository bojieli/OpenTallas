`timescale 1ns/1ps
`default_nettype none
// ELEM-GAPS/HBMN1 (10-18): tb_hgi_coll_ring_ag ported to the NATIVE stop ot_hgi_coll_ring_ag_n. Same program and the
// same expected publishes at the same absolute edges; the driver issues every command ONE edge early (lead 1) and the
// tx-read group TWO edges early (lead 2); lp_data unchanged; the compiler rule lp-write -> inject is >= 4 (v1: 3).
// +fault=8: lp write of the tx tag at the lane read edge (inject-3) -> must fault (v1-legal, native-illegal).
// Base: HBM-B-RTL3 on-die all-gather over the 2x2 COLL ring (4 actual stops).
// Every quadrant holds F flits (256 b) of its slice of x; a small in-bench compiler emits the
// ENTIRE static timeline (injections, transits, arrivals, lp writes and state reads), checking
// every directed link edge for collision. +MODE=0 (production schedule): even flits CW, odd flits
// CCW, each with ttl 3 (one direction a flit, so a stop's other direction stays free to forward):
// 1.5 link slots a flit, F flits gathered in ~1.5 F + 3 hops. +MODE=1 (coverage of the dual-direction
// injection): even flits CW ttl 2 + CCW ttl 1, odd flits CW ttl 1 + CCW ttl 2 (~2 F edges). Every stop must publish each of the other 3F flits exactly once,
// bit-exact, with its source and tag, at exactly the compiled edge; no fault may rise.
// +fault=N runs a reservation-violating trace (must fault). Mutant parameters must FAIL.
module tb_hgi_coll_ring_ag_n;
    parameter integer MUT_TTL=0,MUT_SRC=0,MUT_TAG=0,AG=1,MUT_TXLEAD=0,MUT_CW=0,MUT_HZ=0,MUT_RRLEAD=0;
    localparam integer NC=1400,READ_LEAD=2;
    reg clk=0,rst_n=0;always #0.5 clk=~clk;
    typedef struct packed {
        bit lp_we;bit[2:0] lp_tag;bit[255:0] lp_data;
        bit read_tx;bit[2:0] read_tx_tag;
        bit[1:0] inject,fwd;bit[2:0] tx_tag;bit[3:0] ttl;
        bit[1:0] rx;bit[3:0] kind,src;bit[5:0] tag;
    } slot_t;
    slot_t prog[0:3][0:NC-1],cmd[0:3],cmd1[0:3],cmd2[0:3];
    bit ex_v[0:3][0:1][0:NC-1];bit[1:0] ex_src[0:3][0:1][0:NC-1];bit[2:0] ex_tag[0:3][0:1][0:NC-1];
    bit[255:0] ex_d[0:3][0:1][0:NC-1];
    wire [279:0] co[0:3],no[0:3];
    wire [3:0] fault;wire [1:0] ag_v[0:3];wire [3:0] ag_src[0:3];wire [5:0] ag_tag[0:3];wire [511:0] ag_d[0:3];
    function automatic integer nextq(input integer q);case(q)0:nextq=1;1:nextq=3;3:nextq=2;default:nextq=0;endcase endfunction
    function automatic integer prevq(input integer q);case(q)0:prevq=2;1:prevq=0;3:prevq=1;default:prevq=3;endcase endfunction
    for(genvar q=0;q<4;q=q+1)begin:g_q
        wire rr_v;wire [2:0] rr_tag;wire [255:0] rr_d;
        ot_hgi_coll_ring_ag_n #(.SPLIT_CLOCKS(1),.AG(AG),.MUT_TTL(MUT_TTL),.MUT_SRC(MUT_SRC),.MUT_TAG(MUT_TAG),.MUT_TXLEAD(MUT_TXLEAD),.MUT_CW(MUT_CW),.MUT_HZ(MUT_HZ),.MUT_RRLEAD(MUT_RRLEAD)) dut(
            .clk(clk),.rst_n(rst_n),.clk_ctl(clk),.clk_state({8{clk}}),.clk_add({8{clk}}),.qid(2'(q)),
            .cw_i(co[prevq(q)]),.ccw_i(no[nextq(q)]),.cw_o(co[q]),.ccw_o(no[q]),
            .lp_we(cmd1[q].lp_we),.lp_tag(cmd1[q].lp_tag),.lp_data(cmd[q].lp_data),
            .state_read_add(1'b0),.state_read_tx(cmd2[q].read_tx),.state_read_rr(1'b0),
            .state_add_tag(3'd0),.state_add_src(2'd0),.state_add_rhs_acc(1'b0),
            .state_tx_tag(cmd2[q].read_tx_tag),.state_tx_acc(1'b0),.state_rr_tag(3'd0),
            .add_v(1'b0),.add_tag(3'd0),.add_src(2'd0),.add_rhs_acc(1'b0),
            .tx_inject(cmd1[q].inject),.tx_forward(cmd1[q].fwd),.tx_tag(cmd1[q].tx_tag),.tx_dst(2'(q)),
            .tx_result(1'b0),.tx_acc(1'b0),.tx_gather(|cmd1[q].inject),.tx_ttl(cmd1[q].ttl),
            .rx_slot(cmd1[q].rx),.rx_kind(cmd1[q].kind),.rx_src(cmd1[q].src),.rx_tag(cmd1[q].tag),
            .rr_local(1'b0),.rr_local_tag(3'd0),.rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),
            .ag_v(ag_v[q]),.ag_src(ag_src[q]),.ag_tag(ag_tag[q]),.ag_d(ag_d[q]),.fault(fault[q]));
    end
    function automatic [255:0] payload(input integer q,input integer i);
        reg [255:0] v;
        for(integer l=0;l<8;l=l+1)v[l*32+:32]=32'h3c000000^(32'(q)*32'h9e3779b9)^(32'(i)*32'h85ebca6b)^(32'(l)*32'hc2b2ae35);
        return v;
    endfunction
    bit outb[0:3][0:1][0:NC-1];
    integer F=224,MODE=0,scenario=0,last_cycle=0,checked=0,errors=0;bit saw_fault=0;
    integer last_inj[0:3][0:7],last_w[0:3],last_c[0:3];
    integer inj_edge[0:3][0:2047],w_edge[0:3][0:2047];
    integer h1_q[0:2047],h1_t[0:2047],h1_d[0:2047],hl_q[0:2047],hl_t[0:2047];   // source-0 flit: first / last hop
    // reserve one hop chain from source q, direction d, ttl hops, injected at edge c
    task automatic route(input integer q,input integer d,input integer hops,input integer c,input integer i);
        integer s,t;s=q;t=c;
        if(outb[q][d][c])$fatal(1,"compiler injection collision");
        outb[q][d][c]=1;prog[q][c].inject[d]=1;prog[q][c].ttl[d*2+:2]=2'(hops);
        for(integer h=1;h<=hops;h=h+1)begin
            s=d?prevq(s):nextq(s);t=t+2;
            if(prog[s][t].rx[d])$fatal(1,"compiler receive collision");
            prog[s][t].rx[d]=1;prog[s][t].kind[d*2+:2]=3;prog[s][t].src[d*2+:2]=2'(q);prog[s][t].tag[d*3+:3]=3'(i%8);
            if(ex_v[s][d][t])$fatal(1,"compiler publish collision");
            ex_v[s][d][t]=1;ex_src[s][d][t]=2'(q);ex_tag[s][d][t]=3'(i%8);ex_d[s][d][t]=payload(q,i);
            if(q==0 && h==1 && hops>1)begin h1_q[i]=s;h1_t[i]=t;h1_d[i]=d;end
            if(q==0 && h==hops && (MODE==0 || d==i%2))begin hl_q[i]=s;hl_t[i]=t;end
            if(h<hops)begin
                if(outb[s][d][t])$fatal(1,"compiler forwarding collision");
                outb[s][d][t]=1;prog[s][t].fwd[d]=1;
            end
        end
    endtask
    function automatic bit free(input integer q,input integer dl,input integer c);
        integer n,n2;n=dl?prevq(q):nextq(q);n2=dl?prevq(n):nextq(n);
        if(MODE==0)return !outb[q][dl][c] && !outb[n][dl][c+2] && !outb[n2][dl][c+4];
        return !outb[q][0][c] && !outb[q][1][c] && !outb[n][dl][c+2];
    endfunction
    initial begin
        if($value$plusargs("fault=%d",scenario))begin end
        if($value$plusargs("F=%d",F))begin end
        if($value$plusargs("MODE=%d",MODE))begin end
        for(integer q=0;q<4;q=q+1)begin
            cmd[q]='0;cmd1[q]='0;cmd2[q]='0;last_w[q]=-1;last_c[q]=0;
            for(integer t=0;t<8;t=t+1)last_inj[q][t]=-1;
            for(integer c=0;c<NC;c=c+1)begin prog[q][c]='0;for(integer d=0;d<2;d=d+1)begin ex_v[q][d][c]=0;outb[q][d][c]=0;end end
        end
        // Compiler: round-robin over sources, flit by flit (greedy earliest legal edge).
        for(integer i=0;i<F;i=i+1)begin
            for(integer q=0;q<4;q=q+1)begin
                integer w,c,dl,tg;
                tg=i%8;dl=i%2;
                w=last_inj[q][tg]+1;if(w<=last_w[q])w=last_w[q]+1;
                c=w+4;if(c<=last_c[q])c=last_c[q]+1;   // native: lp write -> inject >= 4
                while(!free(q,dl,c))c=c+1;
                if(c+6>=NC)$fatal(1,"timeline too long");
                // lp write at w (tag freed by its previous injection), state read at c-2, inject at c
                prog[q][w].lp_we=1;prog[q][w].lp_tag=3'(tg);prog[q][w].lp_data=payload(q,i);
                if(prog[q][c-READ_LEAD].read_tx)$fatal(1,"compiler read collision");
                prog[q][c-READ_LEAD].read_tx=1;prog[q][c-READ_LEAD].read_tx_tag=3'(tg);
                prog[q][c].tx_tag=3'(tg);
                if(MODE==0)route(q,dl,3,c,i);else begin route(q,dl,2,c,i);route(q,1-dl,1,c,i);end
                last_w[q]=w;last_c[q]=c;last_inj[q][tg]=c;inj_edge[q][i]=c;w_edge[q][i]=w;
                if(c+6>last_cycle)last_cycle=c+6;
            end
        end
        case(scenario)
            1:prog[h1_q[5]][h1_t[5]].rx[h1_d[5]]=0;                     // missing arrival reservation
            2:prog[h1_q[4]][h1_t[4]].src[h1_d[4]*2+:2]=2;               // wrong source
            3:prog[h1_q[4]][h1_t[4]].fwd[h1_d[4]]=0;                    // missing transit (ttl > 1)
            4:prog[2][inj_edge[2][7]].ttl=0;                            // inject with ttl 0
            5:begin prog[3][inj_edge[3][9]-1].lp_we=1;prog[3][inj_edge[3][9]-1].lp_tag=3'(9%8);end // tag reuse
            6:prog[hl_q[6]][hl_t[6]].fwd[6%2]=1;                        // forward a ttl-1 arrival
            7:prog[h1_q[4]][h1_t[4]].kind[h1_d[4]*2+:2]=1;              // wrong kind
            8:begin   // a flit's own lp write moved to inject-3 (v1-legal: read at inject-2 > write; native lane reads at inject-3)
                integer i8,c8;i8=9;
                while(prog[1][inj_edge[1][i8]-3].lp_we)i8=i8+1;
                c8=inj_edge[1][i8];
                prog[1][w_edge[1][i8]].lp_we=0;
                prog[1][c8-3].lp_we=1;prog[1][c8-3].lp_tag=3'(i8%8);prog[1][c8-3].lp_data=payload(1,i8);
            end
            default:begin end
        endcase
        repeat(5)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);   // relay release +3
        for(integer c=-2;c<=last_cycle;c=c+1)begin
            for(integer q=0;q<4;q=q+1)begin
                cmd[q]=(c>=0)?prog[q][c]:'0;cmd1[q]=(c+1>=0 && c+1<NC)?prog[q][c+1]:'0;cmd2[q]=(c+2>=0 && c+2<NC)?prog[q][c+2]:'0;
            end
            @(posedge clk);#0.01;
            if(c<0)begin @(negedge clk);continue;end
            if(|fault)saw_fault=1;
            if(scenario==0)begin
                if(|fault)begin $display("RING_AG unexpected fault cycle%0d mask%h",c,fault);errors=errors+1;end
                for(integer q=0;q<4;q=q+1)for(integer d=0;d<2;d=d+1)begin
                    if(ag_v[q][d]!==ex_v[q][d][c])begin
                        if(errors<10)$display("RING_AG publish q%0d d%0d cyc%0d got%0d exp%0d",q,d,c,ag_v[q][d],ex_v[q][d][c]);errors=errors+1;
                    end else if(ag_v[q][d])begin
                        if(ag_src[q][d*2+:2]!==ex_src[q][d][c] || ag_tag[q][d*3+:3]!==ex_tag[q][d][c] || ag_d[q][d*256+:256]!==ex_d[q][d][c])begin
                            if(errors<10)$display("RING_AG data q%0d d%0d cyc%0d src%0d/%0d tag%0d/%0d",q,d,c,ag_src[q][d*2+:2],ex_src[q][d][c],ag_tag[q][d*3+:3],ex_tag[q][d][c]);
                            errors=errors+1;
                        end else checked=checked+1;
                    end
                end
            end
            @(negedge clk);
        end
        if(scenario!=0)begin
            if(!saw_fault)$fatal(1,"RING_AG reservation mutant escaped %0d",scenario);
            $display("RING_AG FAULT PASS scenario=%0d timeline=%0d",scenario,last_cycle);
        end else if(errors!=0 || checked!=4*3*F)begin
            $display("RING_AG FAIL errors=%0d checked=%0d expected=%0d",errors,checked,4*3*F);
        end else begin
            $display("RING_AG PASS mode=%0d quadrants=4 flits_per_quadrant=%0d published=%0d gather_edges=%0d first_inject=%0d last_inject=%0d last_arrival=%0d",
                MODE,F,checked,last_cycle-inj_edge[0][0],inj_edge[0][0],inj_edge[3][F-1],last_cycle);
        end
        $finish;
    end
endmodule
`default_nettype wire
